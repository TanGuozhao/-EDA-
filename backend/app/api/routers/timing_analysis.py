from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from fastapi import Depends

from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import TimingGraphRecord

router = APIRouter()


class TimingEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str


class TimingGraph(BaseModel):
    id: int = 1
    name: str = "默认时序分析 DAG"
    clock_period: float = 15
    edges: list[TimingEdge]
    delays: dict[str, float]


DEFAULT_GRAPH = {
    "id": 1,
    "name": "默认时序分析 DAG",
    "clock_period": 15,
    "edges": [
        {"from": "START", "to": "A"},
        {"from": "START", "to": "B"},
        {"from": "START", "to": "C"},
        {"from": "A", "to": "D"},
        {"from": "A", "to": "E"},
        {"from": "B", "to": "D"},
        {"from": "B", "to": "E"},
        {"from": "B", "to": "F"},
        {"from": "C", "to": "E"},
        {"from": "C", "to": "F"},
        {"from": "D", "to": "G"},
        {"from": "E", "to": "G"},
        {"from": "E", "to": "H"},
        {"from": "E", "to": "I"},
        {"from": "F", "to": "H"},
        {"from": "F", "to": "I"},
        {"from": "G", "to": "J"},
        {"from": "G", "to": "K"},
        {"from": "H", "to": "K"},
        {"from": "H", "to": "L"},
        {"from": "I", "to": "L"},
        {"from": "J", "to": "END"},
        {"from": "K", "to": "END"},
        {"from": "L", "to": "END"},
    ],
    "delays": {
        "A": 1,
        "B": 3,
        "C": 2,
        "D": 7,
        "E": 4,
        "F": 4,
        "G": 3,
        "H": 6,
        "I": 2,
        "J": 2,
        "K": 4,
        "L": 1,
    },
}


def _validate_graph(graph: TimingGraph):
    node_ids = set()
    indegree = {}
    next_nodes = {}
    for edge in graph.edges:
        source = edge.from_
        target = edge.to
        node_ids.update([source, target])
        next_nodes.setdefault(source, []).append(target)
        next_nodes.setdefault(target, [])
        indegree.setdefault(source, 0)
        indegree[target] = indegree.get(target, 0) + 1

    if "START" not in node_ids or "END" not in node_ids:
        raise HTTPException(status_code=400, detail="Graph must include START and END")

    queue = [node for node in node_ids if indegree.get(node, 0) == 0]
    visited = 0
    while queue:
        node = queue.pop(0)
        visited += 1
        for target in next_nodes.get(node, []):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)

    if visited != len(node_ids):
        raise HTTPException(status_code=400, detail="Graph must be acyclic")


def _record_to_response(record: TimingGraphRecord):
    return {
        "id": record.id,
        "name": record.name,
        "clock_period": record.clock_period,
        "edges": record.edges,
        "delays": record.delays,
    }


def _get_or_create_default_graph(db: Session):
    record = db.query(TimingGraphRecord).filter(TimingGraphRecord.id == 1).first()
    if record:
        return record

    record = TimingGraphRecord(
        id=1,
        name=DEFAULT_GRAPH["name"],
        clock_period=DEFAULT_GRAPH["clock_period"],
        edges=DEFAULT_GRAPH["edges"],
        delays=DEFAULT_GRAPH["delays"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/graph")
def get_current_graph(db: Session = Depends(get_db)):
    record = _get_or_create_default_graph(db)
    return _record_to_response(record)


@router.post("/import")
def import_graph(graph: TimingGraph, db: Session = Depends(get_db)):
    _validate_graph(graph)
    record = _get_or_create_default_graph(db)
    payload = graph.model_dump(by_alias=True)
    record.name = payload["name"]
    record.clock_period = payload["clock_period"]
    record.edges = payload["edges"]
    record.delays = payload["delays"]
    db.commit()
    db.refresh(record)
    return {"status": "ok", "graph": _record_to_response(record)}
