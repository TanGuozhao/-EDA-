import asyncio
import json

from app.llm.config import LlmGatewaySettings
from app.llm.openai_compatible import ChatGenerationResult
from app.timing.analysis import TimingAnalysisEngine
from app.timing import parse_timing_dag_text
from app.timing.agent import TimingAnalysisAgent


COMPLEX_DAG_TEXT = """START-A
A-B
A-C
A-D
B-E
B-F
C-E
D-F
E-G
F-G
G-H
G-I
G-J
H-K
I-K
J-L
K-M
L-M
H-M
M-N
N-END
A:2
B:3
C:4
D:2
E:3
F:4
G:2
H:3
I:4
J:2
K:3
L:4
M:2
N:3"""

ASYMMETRIC_COMPLEX_DAG_TEXT = """START-A
A-B
A-C
A-D
B-E
B-F
C-I
C-J
C-G
D-L
D-M
E-H
H-O
H-K
O-G
F-G
I-K
J-K
L-K
M-K
G-N
K-N
N-END
A:2
B:3
C:1
D:2
E:1
F:2
G:3
H:1
I:2
J:1
K:2
L:1
M:3
N:2
O:1"""


class FakeChatClient:
    async def generate_text(self, messages, options):
        return ChatGenerationResult(
            content=f'{{"dag_text": {COMPLEX_DAG_TEXT!r}, "clock_period": 100}}'.replace("'", '"'),
            finish_reason="stop",
            usage={},
        )


class NoClockFakeChatClient:
    async def generate_text(self, messages, options):
        return ChatGenerationResult(
            content=json.dumps({"dag_text": COMPLEX_DAG_TEXT}),
            finish_reason="stop",
            usage={},
        )


class HangingChatClient:
    async def generate_text(self, messages, options):
        await asyncio.Event().wait()


def test_agent_writes_fixed_complexity_dag_and_derives_all_five_questions(tmp_path):
    settings = LlmGatewaySettings(
        provider_name="test",
        base_url="http://example.invalid/v1",
        api_key="test",
        default_model="test-model",
        timeout_seconds=1,
        gateway_api_key=None,
    )
    challenge = asyncio.run(
        TimingAnalysisAgent(settings, chat_client=FakeChatClient(), storage_dir=tmp_path).generate(topic="arrival")
    )

    assert challenge.dag_file.read_text(encoding="utf-8").startswith("START-A\nA-B\nA-C\n")
    assert len(challenge.dag.nodes) - 2 == 14
    assert [question["type"] for question in challenge.questions] == [
        "arrival_time",
        "required_time",
        "slack",
        "path_delay",
        "shortest_path",
    ]
    assert all(len(question["target_node_ids"]) == 4 for question in challenge.questions[:3])
    assert len(challenge.questions[3]["path"]) - 2 >= 7


def test_agent_rejects_a_dag_outside_the_fixed_complexity_profile():
    dag = parse_timing_dag_text("START-A\nA-END\nA:1", clock_period=10)

    try:
        TimingAnalysisAgent._validate_fixed_complexity(dag)
    except ValueError as error:
        assert "12 to 15" in str(error)
    else:
        raise AssertionError("Expected the small DAG to be rejected")


def test_agent_detects_the_repetitive_serial_diamond_pattern():
    dag = parse_timing_dag_text(
        """START-A
START-B
A-C
A-D
B-C
B-D
C-E
D-E
E-F
E-G
F-H
G-H
H-I
H-J
I-K
J-K
K-L
K-M
L-N
M-N
N-END
A:2
B:3
C:4
D:2
E:3
F:4
G:2
H:3
I:4
J:2
K:3
L:4
M:2
N:3"""
    )

    assert TimingAnalysisAgent._simple_binary_diamond_count(
        {node.id: [edge.to for edge in dag.edges if edge.from_ == node.id] for node in dag.nodes},
        TimingAnalysisEngine().analyze(dag).topological_order,
    ) > 1
    try:
        TimingAnalysisAgent._validate_fixed_complexity(dag)
    except ValueError as error:
        assert "three-way branch" in str(error)
    else:
        raise AssertionError("Expected the serial-diamond DAG to be rejected")


def test_agent_accepts_an_asymmetric_multilayer_topology():
    TimingAnalysisAgent._validate_fixed_complexity(parse_timing_dag_text(ASYMMETRIC_COMPLEX_DAG_TEXT))


def test_agent_accepts_a_dag_without_clock_period_metadata(tmp_path):
    settings = LlmGatewaySettings(
        provider_name="test",
        base_url="http://example.invalid/v1",
        api_key="test",
        default_model="test-model",
        timeout_seconds=1,
        gateway_api_key=None,
    )

    challenge = asyncio.run(
        TimingAnalysisAgent(settings, chat_client=NoClockFakeChatClient(), storage_dir=tmp_path).generate(topic="arrival")
    )

    assert challenge.dag.clock_period is None


def test_agent_enforces_the_configured_end_to_end_generation_timeout(tmp_path):
    settings = LlmGatewaySettings(
        provider_name="test",
        base_url="http://example.invalid/v1",
        api_key="test",
        default_model="test-model",
        timeout_seconds=0.01,
        gateway_api_key=None,
    )

    try:
        asyncio.run(TimingAnalysisAgent(settings, chat_client=HangingChatClient(), storage_dir=tmp_path).generate(topic="arrival"))
    except ValueError as error:
        assert "timed out after 0.01 seconds" in str(error)
    else:
        raise AssertionError("Expected the hanging model request to time out")
