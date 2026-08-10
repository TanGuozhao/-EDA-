# name=backend/app/services/yosys_executor.py
"""
工具执行器：运行 Yosys / Icarus (iverilog) / Verilator
包含工作目录管理、哈希计算与超时保护（30 秒）
"""
import subprocess
import tempfile
import os
import shutil
import hashlib
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger("yosys_executor")


class YosysExecutor:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.work_dir = None

    def create_work_dir(self) -> str:
        self.work_dir = tempfile.mkdtemp(prefix="rtl_validate_")
        logger.info("创建工作目录：%s", self.work_dir)
        return self.work_dir

    def cleanup_work_dir(self):
        if self.work_dir and os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir, ignore_errors=True)
            logger.info("清理工作目录：%s", self.work_dir)
            self.work_dir = None

    def calculate_hash(self, content: str) -> str:
        h = hashlib.sha256()
        h.update(content.encode("utf-8"))
        return h.hexdigest()

    def _write_file(self, filename: str, content: str) -> str:
        if not self.work_dir:
            self.create_work_dir()
        path = os.path.join(self.work_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def run_yosys(self, verilog_content: str, top_module: str) -> Tuple[int, str, str, Dict[str, Any]]:
        """
        运行 yosys 前端综合流程，返回 (exit_code, stdout, stderr, summary)
        summary 包含 cells/warnings/errors（尽量从 stdout 抽取）
        """
        work_dir = self.create_work_dir()
        src_path = self._write_file("design.v", verilog_content)
        output_netlist = os.path.join(work_dir, "synth_out.v")
        cmd = [
            "yosys",
            "-q",
            "-p",
            f"read_verilog {src_path}; synth -top {top_module}; write_verilog {output_netlist}"
        ]
        logger.info("运行 Yosys: %s", " ".join(cmd))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
            summary = self._parse_yosys_output(stdout + "\n" + stderr)
            # 尝试读取生成的 netlist
            netlist = None
            if os.path.exists(output_netlist):
                with open(output_netlist, "r", encoding="utf-8") as f:
                    netlist = f.read()
            if netlist:
                summary.setdefault("netlist", netlist)
            logger.info("Yosys 退出码=%s", exit_code)
            return exit_code, stdout, stderr, summary
        except subprocess.TimeoutExpired as e:
            logger.error("Yosys 超时")
            return 124, "", f"Timeout after {self.timeout}s", {"errors": 1, "warnings": 0, "cells": 0}
        except FileNotFoundError:
            msg = "Yosys 未安装或未在 PATH 中"
            logger.exception(msg)
            return 127, "", msg, {"errors": 1, "warnings": 0, "cells": 0}
        finally:
            # 不立即清理，调用者可能需要读取产物；调用者负责 cleanup_work_dir()
            pass

    def _parse_yosys_output(self, text: str) -> Dict[str, Any]:
        """
        从 yosys 输出中解析 cells/warnings/errors 的简单 heuristics
        """
        errors = text.count("error:")
        warnings = text.count("warning:")
        cells = None
        # 在 Yosys 的 summary 中经常包含 'Number of cells: N'
        import re
        m = re.search(r"Number of cells:\s*(\d+)", text)
        if m:
            try:
                cells = int(m.group(1))
            except Exception:
                cells = None
        return {"errors": errors, "warnings": warnings, "cells": cells}

    def run_iverilog(self, verilog_content: str, top_module: str, testbench_content: str) -> Tuple[int, str, str]:
        """
        使用 iverilog 进行仿真（iverilog/ vvp）
        """
        work_dir = self.create_work_dir()
        src_path = self._write_file("design.v", verilog_content)
        tb_path = self._write_file("tb.v", testbench_content)
        exe_path = os.path.join(work_dir, "simv")
        cmd_iverilog = ["iverilog", "-o", exe_path, src_path, tb_path]
        logger.info("运行 iverilog: %s", " ".join(cmd_iverilog))
        try:
            proc = subprocess.run(cmd_iverilog, capture_output=True, text=True, timeout=self.timeout)
            if proc.returncode != 0:
                logger.info("iverilog 编译失败，退出码 %s", proc.returncode)
                return proc.returncode, proc.stdout, proc.stderr
            # 运行仿真
            proc2 = subprocess.run([exe_path], capture_output=True, text=True, timeout=self.timeout)
            return proc2.returncode, proc2.stdout, proc2.stderr
        except subprocess.TimeoutExpired:
            logger.error("iverilog/模拟 超时")
            return 124, "", f"Timeout after {self.timeout}s"
        except FileNotFoundError:
            msg = "iverilog 未安装或未在 PATH 中"
            logger.exception(msg)
            return 127, "", msg

    def run_verilator(self, verilog_content: str, top_module: str) -> Tuple[int, str, str]:
        """
        使用 verilator 生成 C++ 模拟框架（这里只做基本调用）
        """
        work_dir = self.create_work_dir()
        src_path = self._write_file("design.v", verilog_content)
        cmd = ["verilator", "--cc", src_path, "--top-module", top_module]
        logger.info("运行 Verilator: %s", " ".join(cmd))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            logger.error("Verilator 超时")
            return 124, "", f"Timeout after {self.timeout}s"
        except FileNotFoundError:
            msg = "Verilator 未安装或未在 PATH 中"
            logger.exception(msg)
            return 127, "", msg