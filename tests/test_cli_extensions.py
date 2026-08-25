from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pytest import MonkeyPatch
from typer.testing import CliRunner

from langgraph_agent_lab import cli


class FakeDrawableGraph:
    def draw_mermaid(self) -> str:
        return "graph TD\n  START --> finalize\n"


class FakeCompiledGraph:
    def get_graph(self) -> FakeDrawableGraph:
        return FakeDrawableGraph()


def test_snapshot_summary_is_json_ready() -> None:
    snapshot = SimpleNamespace(
        values={
            "route": "simple",
            "attempt": 0,
            "final_answer": "done",
            "events": [{"node": "finalize"}],
        },
        metadata={"step": 3},
        config={
            "configurable": {
                "thread_id": "thread-S01_simple",
                "checkpoint_id": "checkpoint-1",
            }
        },
        next=(),
    )

    summary = cli._snapshot_summary(snapshot)

    assert summary == {
        "thread_id": "thread-S01_simple",
        "checkpoint_id": "checkpoint-1",
        "step": 3,
        "next": [],
        "route": "simple",
        "attempt": 0,
        "final_answer_present": True,
        "events_count": 1,
    }


def test_export_diagram_writes_mermaid(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    output = tmp_path / "graph.mmd"
    runner = CliRunner()

    monkeypatch.setattr(cli, "build_graph", lambda checkpointer=None: FakeCompiledGraph())
    result = runner.invoke(cli.app, ["export-diagram", "--output", str(output)])

    assert result.exit_code == 0
    assert output.read_text(encoding="utf-8").startswith("graph TD")
