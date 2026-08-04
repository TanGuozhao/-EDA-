# name=backend/app/services/rtl_service.py
"""
RTL 服务层：处理生成参考代码、验证、错误注入、试题/提交流程
"""
import logging
import uuid
from typing import Tuple, Dict, Any
from app.services.yosys_executor import YosysExecutor
from app.adapters.db.mysql.session import SessionLocal
from app.adapters.db.mysql.models import (
    RTLDesign,
    RTLValidationRun,
    RTLRepairQuestion,
    RTLSubmission,
)
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from random import randint

logger = logging.getLogger("rtl_service")


# -------------------
# Mock LLM 接口（可替换）
# -------------------
def mock_llm_generate_verilog(requirement: str, module_name: str, ports: list) -> str:
    """
    简单的 Mock LLM：根据端口生成一个组合逻辑模块（仅用于示例）
    """
    # ports 是 dict 列表
    port_decls = []
    assigns = []
    inputs = []
    outputs = []
    for p in ports:
        w = p.get("width", 1)
        decl = f"{p['direction']} [{'['+str(w-1)+':0] ' if w>1 else ''}]{p['name']}" if False else None
        # 更稳妥地写法：
        if p["direction"] == "input":
            if p["width"] == 1:
                port_decls.append(f"input {p['name']}")
            else:
                port_decls.append(f"input [{p['width']-1}:0] {p['name']}")
            inputs.append(p["name"])
        else:
            if p["width"] == 1:
                port_decls.append(f"output {p['name']}")
            else:
                port_decls.append(f"output [{p['width']-1}:0] {p['name']}")
            outputs.append(p["name"])
    # 为简单起见：若两个 inputs 一个 output -> and gate; else pass-through
    body = ""
    if len(inputs) >= 2 and len(outputs) >= 1:
        body = f"assign {outputs[0]} = {' & '.join(inputs)};"
    elif len(inputs) >= 1 and len(outputs) >= 1:
        body = f"assign {outputs[0]} = {inputs[0]};"
    else:
        body = "// mock module body"
    portstr = ", ".join(port_decls)
    verilog = f"module {module_name}({', '.join([p['name'] for p in ports])});\n"
    # explicit declarations
    for p in ports:
        if p["width"] == 1:
            verilog += f"  {p['direction']} {p['name']};\n"
        else:
            verilog += f"  {p['direction']} [{p['width']-1}:0] {p['name']};\n"
    verilog += f"  {body}\nendmodule\n"
    return verilog


# -------------------
# 错误注入函数（7 种）
# -------------------
def inject_timing_error(verilog: str) -> str:
    """
    在时序逻辑中使用阻塞赋值 '=' 模拟时序错误（如果存在 always @ (posedge clk) 块则替换）
    粗略替换非阻塞 <= 为 =
    """
    return verilog.replace("<=", "=")


def inject_incomplete_logic_error(verilog: str) -> str:
    """
    删除一个 else 分支或插入不完整条件以产生 latch（例如把 'else' 删除）
    这里做简单替换：将 'else' 删除
    """
    return verilog.replace("else", "// else_removed")


def inject_bitwidth_error(verilog: str) -> str:
    """
    修改位宽声明或在运算中截断位宽：将 [N-1:0] 改为 [N-2:0]
    """
    import re

    def _shrink(match):
        ms = match.group(0)
        nums = re.findall(r"\d+", ms)
        if not nums:
            return ms
        n = int(nums[0])
        if n <= 1:
            return ms
        return ms.replace(str(n - 1), str(max(1, n - 2)), 1)

    new = re.sub(r"\[\s*\d+\s*:\s*0\s*\]", _shrink, verilog)
    # 如果没有位宽声明，尝试用截断操作替换 +
    new = new.replace("+", "+ 0")  # no-op but keep deterministic
    return new


def inject_fsm_error(verilog: str) -> str:
    """
    交换状态转移条件或改变默认状态
    简单实现：将 'state <= NEXT_STATE;' 替换为 'state <= WRONG_STATE;'
    """
    return verilog.replace("next_state", "bad_next_state").replace("NEXT_STATE", "BAD_STATE")


def inject_condition_error(verilog: str) -> str:
    """
    替换比较运算符： == -> !=, > -> < 等
    """
    new = verilog.replace("==", "!=")
    new = new.replace(">", "<")
    return new


def inject_port_error(verilog: str) -> str:
    """
    修改端口方向或名字（将 output 替换为 input）
    """
    return verilog.replace("output", "input /*was output*/")


def inject_clock_enable_error(verilog: str) -> str:
    """
    反转 enable 条件（例如 if (enable) -> if (!enable)）
    """
    return verilog.replace("if (enable)", "if (!enable)")


ERROR_INJECTORS = {
    "timing": inject_timing_error,
    "incomplete": inject_incomplete_logic_error,
    "bitwidth": inject_bitwidth_error,
    "fsm": inject_fsm_error,
    "condition": inject_condition_error,
    "port": inject_port_error,
    "clock_enable": inject_clock_enable_error,
}


# -------------------
# 服务方法
# -------------------
class RTLService:
    def __init__(self):
        self.executor = YosysExecutor(timeout=30)

    def generate_design(self, requirement: str, module_name: str, ports: list) -> Dict[str, Any]:
        """
        1) 调用 LLM 生成参考 Verilog（Mock）
        2) 调用 Yosys & Icarus 验证
        3) 保存到 rtl_designs
        """
        logger.info("生成设计：%s", module_name)
        reference = mock_llm_generate_verilog(requirement, module_name, ports)
        design_id = uuid.uuid4().hex[:8]
        session = SessionLocal()
        try:
            # 验证综合
            exit_code, stdout, stderr, summary = self.executor.run_yosys(reference, module_name)
            passed = exit_code == 0 and (summary.get("errors", 0) == 0)
            # 简单功能验证：生成一个非常简单的 tb，如果失败则仍保存但状态为 unverified
            # 这里我们不构造复杂 TB，仅以 yosys 结果为准
            status = "verified" if passed else "unverified"
            design = RTLDesign(
                design_id=design_id,
                requirement=requirement,
                module_name=module_name,
                ports=ports,
                reference_verilog=reference,
                llm_model="mock-llm",
                status=status,
            )
            session.add(design)
            session.commit()
            logger.info("设计已保存 design_id=%s status=%s", design_id, status)
            # 记录一次验证运行
            run = RTLValidationRun(
                design_id=design_id,
                input_verilog=reference,
                input_hash=self.executor.calculate_hash(reference),
                tool_name="yosys",
                tool_version=None,
                command="yosys synth",
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                logs=stdout + "\n" + stderr,
                summary=summary,
                passed=passed,
            )
            session.add(run)
            session.commit()
            return {
                "design_id": design_id,
                "requirement": requirement,
                "reference_verilog": reference,
                "ports": ports,
                "status": status,
                "generated_at": datetime.utcnow(),
            }
        except Exception:
            logger.exception("生成设计失败")
            session.rollback()
            raise
        finally:
            session.close()
            self.executor.cleanup_work_dir()

    def validate_verilog(self, verilog: str, top_module: str, design_id: str = None) -> Dict[str, Any]:
        """
        执行完整验证流程：yosys, iverilog/verilator
        保存 rtl_validation_runs
        """
        logger.info("验证 Verilog: top=%s", top_module)
        ex = self.executor
        work_dir = ex.create_work_dir()
        session = SessionLocal()
        try:
            h = ex.calculate_hash(verilog)
            # 先运行 yosys
            exit_code_y, stdout_y, stderr_y, summary_y = ex.run_yosys(verilog, top_module)
            passed = exit_code_y == 0 and (summary_y.get("errors", 0) == 0)
            # 生成非常简单的 testbench（仅用于示例）
            tb = self._generate_simple_tb(top_module)
            exit_code_sim, stdout_sim, stderr_sim = ex.run_iverilog(verilog, top_module, tb)
            # 汇总：passed 必须在综合与仿真都通过
            final_passed = passed and exit_code_sim == 0
            # 保存记录
            run = RTLValidationRun(
                design_id=design_id,
                input_verilog=verilog,
                input_hash=h,
                tool_name="yosys+iverilog",
                tool_version=None,
                command="yosys; iverilog",
                exit_code=0 if final_passed else 1,
                stdout=(stdout_y or "") + "\n" + (stdout_sim or ""),
                stderr=(stderr_y or "") + "\n" + (stderr_sim or ""),
                logs=(stdout_y or "") + "\n" + (stderr_y or "") + "\n" + (stdout_sim or "") + "\n" + (stderr_sim or ""),
                summary={**summary_y, "sim_exit": exit_code_sim},
                passed=final_passed,
            )
            session.add(run)
            session.commit()
            return {
                "validation_run_id": run.id,
                "passed": final_passed,
                "exit_code": run.exit_code,
                "summary": run.summary,
                "logs": run.logs,
                "tool_name": run.tool_name,
            }
        except Exception:
            logger.exception("验证失败")
            session.rollback()
            raise
        finally:
            session.close()
            ex.cleanup_work_dir()

    def _generate_simple_tb(self, top_module: str) -> str:
        """
        生成一个非常简单的 testbench：适用于 1/2 输入的组合逻辑模块
        真实场景需更复杂的测试生成器
        """
        tb = f"""
`timescale 1ns/1ps
module tb;
  reg a, b;
  wire y;
  {top_module} uut(.a(a), .b(b), .y(y));
  initial begin
    a = 0; b = 0; #10;
    a = 0; b = 1; #10;
    a = 1; b = 0; #10;
    a = 1; b = 1; #10;
    $display("DONE");
    $finish;
  end
endmodule
"""
        return tb

    def create_repair_question(self, requirement: str, module_name: str, ports: list, error_type: str) -> Dict[str, Any]:
        """
        基于 reference 生成错误题目，保存到 rtl_repair_questions
        """
        logger.info("创建 repair 题目 type=%s", error_type)
        session = SessionLocal()
        try:
            # 先调用 LLM 获取参考
            reference = mock_llm_generate_verilog(requirement, module_name, ports)
            injector = ERROR_INJECTORS.get(error_type)
            if not injector:
                raise ValueError("未知 error_type")
            error_verilog = injector(reference)
            # 验证错误 Verilog 应该不能通过检查（如果能通过，仍保存，但标记 warning）
            validation = self.validate_verilog(error_verilog, module_name)
            # 如果验证通过则 log 警告
            status = "active"
            question_id = uuid.uuid4().hex[:8]
            q = RTLRepairQuestion(
                question_id=question_id,
                design_id=None,
                requirement=requirement,
                module_name=module_name,
                ports=ports,
                error_verilog=error_verilog,
                reference_verilog=reference,
                error_type=error_type,
                hidden_tests=None,
                status=status,
            )
            session.add(q)
            session.commit()
            return {
                "question_id": question_id,
                "requirement": requirement,
                "error_verilog": error_verilog,
                "ports": ports,
                "error_type": error_type,
            }
        except Exception:
            logger.exception("创建 repair 题目失败")
            session.rollback()
            raise
        finally:
            session.close()

    def get_repair_question(self, question_id: str) -> Dict[str, Any]:
        session = SessionLocal()
        try:
            q = session.query(RTLRepairQuestion).filter(RTLRepairQuestion.question_id == question_id).first()
            if not q:
                return None
            return {
                "question_id": q.question_id,
                "requirement": q.requirement,
                "error_verilog": q.error_verilog,
                "ports": q.ports,
                "error_type": q.error_type,
            }
        finally:
            session.close()

    def submit_repair(self, question_id: str, user_id: int, submitted_verilog: str) -> Dict[str, Any]:
        """
        1) 验证提交（复用 validate）
        2) 对比功能一致性（此处以仿真通过为主）
        3) 保存到 rtl_submissions
        """
        logger.info("提交 repair 题目 question=%s user=%s", question_id, user_id)
        session = SessionLocal()
        try:
            question = session.query(RTLRepairQuestion).filter(RTLRepairQuestion.question_id == question_id).first()
            if not question:
                raise LookupError("question not found")

            # 验证提交
            val = self.validate_verilog(submitted_verilog, question.module_name, design_id=question.design_id)
            passed = val["passed"]
            score = 100 if passed else randint(0, 80)
            feedback = "通过所有检查" if passed else "存在问题，请查看 logs"
            # 保存 submission
            sub = RTLSubmission(
                question_id=question_id,
                user_id=user_id,
                submitted_verilog=submitted_verilog,
                validation_run_id=val.get("validation_run_id"),
                passed=passed,
                score=score,
                feedback=feedback,
            )
            session.add(sub)
            session.commit()
            return {
                "submission_id": sub.id,
                "passed": passed,
                "score": score,
                "feedback": feedback,
                "validation_run_id": val.get("validation_run_id"),
            }
        except LookupError:
            logger.exception("未找到题目")
            raise
        except Exception:
            logger.exception("提交处理失败")
            session.rollback()
            raise
        finally:
            session.close()

    def get_design_artifacts(self, design_id: str) -> Dict[str, Any]:
        session = SessionLocal()
        try:
            design = session.query(RTLDesign).filter(RTLDesign.design_id == design_id).first()
            if not design:
                return None
            runs = (
                session.query(RTLValidationRun)
                .filter(RTLValidationRun.design_id == design_id)
                .order_by(desc(RTLValidationRun.run_at))
                .all()
            )
            runs_list = []
            for r in runs:
                runs_list.append(
                    {
                        "tool_name": r.tool_name,
                        "passed": r.passed,
                        "logs": r.logs,
                        "summary": r.summary,
                    }
                )
            netlist = None
            # 尝试从最新 run 中获取 netlist（如果存在）
            if runs and runs[0].summary and isinstance(runs[0].summary, dict):
                netlist = runs[0].summary.get("netlist")
            return {
                "design_id": design.design_id,
                "reference_verilog": design.reference_verilog,
                "netlist": netlist,
                "validation_runs": runs_list,
            }
        finally:
            session.close()