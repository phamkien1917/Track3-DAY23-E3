"""CLI for the lab."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any

import typer
import yaml  # type: ignore[import-untyped]

from .graph import build_graph
from .metrics import MetricsReport, metric_from_state, summarize_metrics, write_metrics
from .persistence import build_checkpointer
from .report import write_report
from .scenarios import load_scenarios
from .state import initial_state

app = typer.Typer(no_args_is_help=True)


def _snapshot_summary(snapshot: object) -> dict[str, Any]:
    """Return a compact, JSON-serializable state-history row."""
    values = getattr(snapshot, "values", {}) or {}
    metadata = getattr(snapshot, "metadata", {}) or {}
    config = getattr(snapshot, "config", {}) or {}
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    events = values.get("events", []) if isinstance(values, dict) else []
    return {
        "thread_id": configurable.get("thread_id"),
        "checkpoint_id": configurable.get("checkpoint_id"),
        "step": metadata.get("step") if isinstance(metadata, dict) else None,
        "next": list(getattr(snapshot, "next", ()) or ()),
        "route": values.get("route") if isinstance(values, dict) else None,
        "attempt": values.get("attempt") if isinstance(values, dict) else None,
        "final_answer_present": (
            bool(values.get("final_answer")) if isinstance(values, dict) else False
        ),
        "events_count": len(events) if isinstance(events, list) else 0,
    }


@app.command("run-scenarios")
def run_scenarios(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run all grading scenarios and write metrics JSON."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    scenarios = load_scenarios(cfg["scenarios_path"])
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    graph = build_graph(checkpointer=checkpointer)
    metrics = []
    state_history_verified = checkpointer is not None
    for scenario in scenarios:
        state = initial_state(scenario)
        run_config = {"configurable": {"thread_id": state["thread_id"]}}
        started_at = perf_counter()
        final_state = graph.invoke(state, config=run_config)
        latency_ms = round((perf_counter() - started_at) * 1000)
        metrics.append(
            metric_from_state(
                final_state,
                scenario.expected_route.value,
                scenario.requires_approval,
                latency_ms=latency_ms,
            )
        )
        try:
            latest_snapshot = next(graph.get_state_history(run_config), None)
        except Exception:
            state_history_verified = False
        else:
            state_history_verified = state_history_verified and latest_snapshot is not None
    report = summarize_metrics(metrics, resume_success=state_history_verified)
    write_metrics(report, output)
    if cfg.get("report_path"):
        write_report(report, cfg["report_path"])
    typer.echo(f"Wrote metrics to {output}")


@app.command("validate-metrics")
def validate_metrics(metrics: Annotated[Path, typer.Option("--metrics")]) -> None:
    """Validate metrics JSON schema for grading."""
    payload = json.loads(metrics.read_text(encoding="utf-8"))
    report = MetricsReport.model_validate(payload)
    if report.total_scenarios < 6:
        raise typer.BadParameter("Expected at least 6 scenarios")
    typer.echo(f"Metrics valid. success_rate={report.success_rate:.2%}")


@app.command("export-diagram")
def export_diagram(output: Annotated[Path, typer.Option("--output")]) -> None:
    """Export the compiled graph as a Mermaid diagram."""
    graph = build_graph(checkpointer=None)
    diagram = graph.get_graph().draw_mermaid()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(diagram, encoding="utf-8")
    typer.echo(f"Wrote graph diagram to {output}")


@app.command("inspect-history")
def inspect_history(
    config: Annotated[Path, typer.Option("--config")],
    thread_id: Annotated[str, typer.Option("--thread-id")],
    output: Annotated[Path, typer.Option("--output")],
    limit: Annotated[int, typer.Option("--limit")] = 10,
) -> None:
    """Write a compact checkpoint history for one thread to JSON."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    if checkpointer is None:
        raise typer.BadParameter("State history requires a checkpointer")

    graph = build_graph(checkpointer=checkpointer)
    run_config = {"configurable": {"thread_id": thread_id}}
    history = []
    for snapshot in graph.get_state_history(run_config):
        history.append(_snapshot_summary(snapshot))
        if len(history) >= limit:
            break

    if not history:
        raise typer.BadParameter(f"No checkpoint history found for thread_id={thread_id}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    typer.echo(f"Wrote {len(history)} history snapshots to {output}")


if __name__ == "__main__":
    app()
