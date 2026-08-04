# name=backend/app/services/hls_service.py
"""
HLS 服务层：包含题目生成、答案计算（ASAP/ALAP 简单实现）与提交评判逻辑
"""
import logging
import uuid
from typing import Dict, Any, Tuple, List, Set
from app.adapters.db.mysql.session import SessionLocal
from app.adapters.db.mysql.models import HLSChallenge, HLSSubmission
from sqlalchemy.orm import Session
from collections import defaultdict, deque

logger = logging.getLogger("hls_service")


def _validate_dag(dag: Dict[str, Any]) -> bool:
    """
    简单检查 DAG 无环（拓扑排序）
    dag: {"nodes":[{"id":1,...}], "edges":[{"from":1,"to":2}]}
    """
    nodes = {n["id"] for n in dag.get("nodes", [])}
    indeg = {n: 0 for n in nodes}
    g = {n: [] for n in nodes}
    for e in dag.get("edges", []):
        f = e["from"]
        t = e["to"]
        if f not in nodes or t not in nodes:
            return False
        g[f].append(t)
        indeg[t] += 1
    q = deque([n for n in nodes if indeg[n] == 0])
    cnt = 0
    while q:
        u = q.popleft()
        cnt += 1
        for v in g[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return cnt == len(nodes)


def asap_schedule(dag: Dict[str, Any]) -> Dict[int, int]:
    """
    计算 ASAP 调度（每个节点最早时间）
    返回 node_id -> cycle
    """
    nodes = {n["id"]: n for n in dag.get("nodes", [])}
    g = defaultdict(list)
    indeg = {nid: 0 for nid in nodes}
    for e in dag.get("edges", []):
        g[e["from"]].append(e["to"])
        indeg[e["to"]] += 1
    ready = deque([nid for nid, d in indeg.items() if d == 0])
    est = {nid: 0 for nid in nodes}
    while ready:
        u = ready.popleft()
        for v in g[u]:
            est[v] = max(est[v], est[u] + nodes[u].get("delay", 1))
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)
    return est


def alap_schedule(dag: Dict[str, Any], total_cycles: int) -> Dict[int, int]:
    """
    计算 ALAP 调度（推后）
    简化：先计算拓扑和最长路径，设 latest = total_cycles - slack...
    """
    nodes = {n["id"]: n for n in dag.get("nodes", [])}
    # 先 compute ASAP to get earliest times
    est = asap_schedule(dag)
    # compute critical path length
    max_est = max(est.values()) if est else 0
    # 基本实现： latest = total_cycles - (est[node])
    laat = {}
    for nid in nodes:
        laat[nid] = max(0, total_cycles - est.get(nid, 0))
    return laat


def list_scheduling(dag: Dict[str, Any], resources: Dict[str, int]) -> Dict[int, int]:
    """
    简单的 LIST 调度：每 cycle 调度可执行节点，优先级 = earliest time
    这里使用非常简化的算法：全部节点按 asap 时间排序，分配到可用资源的最早周期
    """
    est = asap_schedule(dag)
    # nodes by est asc
    nodes_order = sorted(est.items(), key=lambda x: x[1])
    assignment = {}
    cycle_resources = defaultdict(lambda: defaultdict(int))  # cycle -> resource -> used
    # map node types to resource names
    for nid, _ in nodes_order:
        # find node type
        node = next(n for n in dag.get("nodes", []) if n["id"] == nid)
        rtype = node.get("type", "add")
        # choose resource name
        resname = "adders" if rtype in ("add", "sub") else ("multipliers" if rtype in ("mul",) else "adders")
        # find earliest cycle where resource available
        cyc = 0
        while True:
            used = cycle_resources[cyc][resname]
            cap = resources.get(resname, 1)
            if used < cap:
                assignment[nid] = cyc
                cycle_resources[cyc][resname] += 1
                break
            cyc += 1
    return assignment


class HLSService:
    def __init__(self):
        pass

    def get_current_challenge(self) -> Dict[str, Any]:
        """
        返回最新的一道题（随机或最新）
        """
        session = SessionLocal()
        try:
            c = session.query(HLSChallenge).order_by(HLSChallenge.created_at.desc()).first()
            if not c:
                return None
            return {
                "challenge_id": c.challenge_id,
                "algorithm": c.algorithm,
                "dag": c.dag_json,
                "resource_constraints": c.resource_constraints,
                "total_cycles": c.correct_answer.get("total_cycles") if c.correct_answer else None,
                "description": f"请使用 {c.algorithm} 算法调度此 DAG",
            }
        finally:
            session.close()

    def generate_challenge(self, algorithm: str = "ASAP", max_nodes: int = 6) -> Dict[str, Any]:
        """
        使用 mock LLM 生成 DAG 并校验无环，然后保存题目
        """
        # 简单生成器：链式或小图
        nodes = []
        edges = []
        for i in range(1, max_nodes + 1):
            nodes.append({"id": i, "label": f"NODE{i}", "type": "add" if i % 2 == 1 else "mul", "delay": 1})
            if i > 1:
                edges.append({"from": i - 1, "to": i})
        dag = {"nodes": nodes, "edges": edges}
        if not _validate_dag(dag):
            raise ValueError("生成的 DAG 非法")
        challenge_id = uuid.uuid4().hex[:8]
        # 计算正确答案（非常简单）
        if algorithm == "ASAP":
            correct = {"schedule": asap_schedule(dag)}
        elif algorithm == "ALAP":
            correct = {"schedule": alap_schedule(dag, total_cycles=5), "total_cycles": 5}
        else:
            correct = {"schedule": list_scheduling(dag, {"adders": 1, "multipliers": 1})}
        session = SessionLocal()
        try:
            ch = HLSChallenge(
                challenge_id=challenge_id,
                dag_json=dag,
                resource_constraints={"adders": 1, "multipliers": 1},
                algorithm=algorithm,
                correct_answer=correct,
            )
            session.add(ch)
            session.commit()
            return {
                "challenge_id": challenge_id,
                "algorithm": algorithm,
                "dag": dag,
                "resource_constraints": {"adders": 1, "multipliers": 1},
                "total_cycles": correct.get("total_cycles"),
                "description": f"请使用 {algorithm} 算法调度此 DAG",
            }
        except Exception:
            session.rollback()
            logger.exception("保存 HLS 题目失败")
            raise
        finally:
            session.close()

    def get_challenge(self, challenge_id: str) -> Dict[str, Any]:
        session = SessionLocal()
        try:
            c = session.query(HLSChallenge).filter(HLSChallenge.challenge_id == challenge_id).first()
            if not c:
                return None
            return {
                "challenge_id": c.challenge_id,
                "algorithm": c.algorithm,
                "dag": c.dag_json,
                "resource_constraints": c.resource_constraints,
                "total_cycles": c.correct_answer.get("total_cycles") if c.correct_answer else None,
                "description": f"请使用 {c.algorithm} 算法调度此 DAG",
            }
        finally:
            session.close()

    def submit(self, challenge_id: str, user_id: int, student_answer: Dict[str, Any]) -> Dict[str, Any]:
        session = SessionLocal()
        try:
            ch = session.query(HLSChallenge).filter(HLSChallenge.challenge_id == challenge_id).first()
            if not ch:
                raise LookupError("challenge not found")

            dag = ch.dag_json
            correct_schedule = ch.correct_answer.get("schedule", {})

            # 解析节点
            nodes_list = dag.get("nodes", [])
            nodes_by_id = {n["id"]: n for n in nodes_list}

            # 1. 检查节点位置
            student_positions = student_answer.get("node_positions", {})
            correct_nodes = []
            wrong_nodes = []
            for nid in nodes_by_id.keys():
                student_cycle = student_positions.get(str(nid))
                correct_cycle = correct_schedule.get(str(nid))  # 用字符串去查
                if student_cycle is None:
                    wrong_nodes.append(nid)
                else:
                    if int(student_cycle) == int(correct_cycle):
                        correct_nodes.append(nid)
                    else:
                        wrong_nodes.append(nid)

            # 2. 检查边
            student_edges = student_answer.get("edges", [])
            student_edges_set = {(e.get("from"), e.get("to")) for e in student_edges}
            true_edges_set = {(e["from"], e["to"]) for e in dag.get("edges", [])}
            missing_edges = [{"from": f, "to": t} for (f, t) in true_edges_set - student_edges_set]
            wrong_edges = [{"from": f, "to": t} for (f, t) in student_edges_set - true_edges_set]

            # 3. 检查资源约束
            res_constraints = ch.resource_constraints or {"adders": 1, "multipliers": 1}
            usage = {}
            resource_violations = []
            for nid, node in nodes_by_id.items():
                node_type = node.get("type", "add")
                resname = "adders" if node_type in ("add", "sub") else "multipliers"
                cyc = int(student_positions.get(str(nid), 0))
                if cyc not in usage:
                    usage[cyc] = {}
                usage[cyc][resname] = usage[cyc].get(resname, 0) + 1

            for cyc, rdict in usage.items():
                for rname, used in rdict.items():
                    cap = res_constraints.get(rname, 1)
                    if used > cap:
                        resource_violations.append(f"周期{cyc}使用了{used}个{rname}，但只有{cap}个")

            # 4. 计算分数（节点60%，边40%）
            total_nodes = len(nodes_by_id)
            correct_count = len(correct_nodes)
            node_score = int(60 * correct_count / total_nodes) if total_nodes > 0 else 0

            total_edges = len(dag.get("edges", []))
            correct_edges = total_edges - len(missing_edges) - len(wrong_edges)
            edge_score = int(40 * correct_edges / total_edges) if total_edges > 0 else 0

            score = node_score + edge_score

            # 资源违规扣分：每条违规扣10分
            score -= 10 * len(resource_violations)
            score = max(0, min(100, score))

            # 判定是否通过
            passed = (
                correct_count == total_nodes and
                len(missing_edges) == 0 and
                len(wrong_edges) == 0 and
                len(resource_violations) == 0
            )

            # 保存提交记录
            sub = HLSSubmission(
                challenge_id=challenge_id,
                user_id=user_id,
                student_answer_json=student_answer,
                passed=passed,
                score=score,
                feedback={
                    "correct_nodes": correct_nodes,
                    "wrong_nodes": wrong_nodes,
                    "missing_edges": missing_edges,
                    "wrong_edges": wrong_edges,
                    "resource_violations": resource_violations,
                },
            )
            session.add(sub)
            session.commit()

            return {
                "passed": passed,
                "score": score,
                "feedback": {
                    "correct_nodes": correct_nodes,
                    "wrong_nodes": wrong_nodes,
                    "missing_edges": missing_edges,
                    "wrong_edges": wrong_edges,
                    "resource_violations": resource_violations,
                }
            }

        except LookupError:
            logger.exception("未找到 HLS 题目")
            raise
        except Exception:
            logger.exception("HLS 提交处理出错")
            session.rollback()
            raise
        finally:
            session.close()