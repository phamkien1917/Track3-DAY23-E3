"""Report generation helper based on the lab-report template."""

from __future__ import annotations

from pathlib import Path

from .metrics import MetricsReport


def _markdown_cell(value: object) -> str:
    """Escape one value for safe use in a Markdown table cell."""
    text = str(value).replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")
    return text or "—"


def _yes_no(value: bool) -> str:
    """Render a boolean consistently in the report."""
    return "Yes" if value else "No"


def render_report(metrics: MetricsReport) -> str:
    """Render a complete lab report from metrics data.

    Include metric summaries, per-scenario outcomes, architecture notes,
    failure analysis, persistence evidence, and an improvement plan.
    """
    scenario_rows = [
        "| {scenario_id} | {expected_route} | {actual_route} | {success} | "
        "{retries} | {interrupts} | {latency_ms} |".format(
            scenario_id=_markdown_cell(item.scenario_id),
            expected_route=_markdown_cell(item.expected_route),
            actual_route=_markdown_cell(item.actual_route or "not set"),
            success=_yes_no(item.success),
            retries=item.retry_count,
            interrupts=item.interrupt_count,
            latency_ms=item.latency_ms,
        )
        for item in metrics.scenario_metrics
    ]
    error_rows = [
        f"- **{_markdown_cell(item.scenario_id)}**: "
        f"{_markdown_cell('; '.join(item.errors))}"
        for item in metrics.scenario_metrics
        if item.errors
    ]
    scenario_table = "\n".join(scenario_rows) or "| — | — | — | — | — | — | — |"
    observed_errors = "\n".join(error_rows) or "- No errors were recorded."
    recovery_summary = (
        "SQLite checkpoint history was retrieved successfully after every scenario."
        if metrics.resume_success
        else "No state-history or crash-resume demonstration was recorded in this run."
    )
    persistence_details = (
        "The default configuration uses `SqliteSaver` with WAL mode in "
        "`checkpoints.db`; each scenario has its own `thread_id`."
        if metrics.resume_success
        else "Add the checkpointer configuration and state-history command here before submission."
    )

    return f"""# Day 08 Lab Report

## 1. Team / student

- Name: _Complete before submission_
- Repo/commit: _Complete before submission_
- Date: _Complete before submission_

## 2. Architecture

The solution is a LangGraph `StateGraph` for customer-support tickets. It
normalizes a query, classifies its intent with a structured LLM response, then
uses conditional edges to choose a direct answer, a tool lookup, clarification,
human approval, or a bounded retry/dead-letter flow. All completed routes pass
through `finalize` before `END`.

## 3. State schema

| Field | Reducer | Why |
|---|---|---|
| Audit: messages, tool results, errors, events | append | Preserve workflow history. |
| Control: route, risk level, attempt, final answer | overwrite | Store current decisions. |
| Flow fields: evaluation, clarification, action, approval | overwrite | Carry node decisions. |

## 4. Scenario results

| Metric | Value |
|---|---:|
| Total scenarios | {metrics.total_scenarios} |
| Success rate | {metrics.success_rate:.2%} |
| Average nodes visited | {metrics.avg_nodes_visited:.2f} |
| Total retries | {metrics.total_retries} |
| Total approval/HITL events | {metrics.total_interrupts} |
| Resume success | {_yes_no(metrics.resume_success)} |

| Scenario | Expected route | Actual route | Success | Retries | Interrupts | Latency (ms) |
|---|---|---|---|---:|---:|---:|
{scenario_table}

### Recorded errors

{observed_errors}

## 5. Failure analysis

1. **Transient tool failure:** `evaluate` sends an unsuccessful tool result to
   `retry`. The retry node increments `attempt`; once `max_attempts` is reached,
   the graph routes to `dead_letter`, preventing an infinite loop.
2. **Risky action without approval:** side-effecting requests are routed through
   `risky_action` and `approval`. A rejected request goes to clarification rather
   than continuing to the tool.

## 6. Persistence / recovery evidence

{recovery_summary} {persistence_details}

## 7. Extension work

Three Phase 5 extensions are implemented:

1. **SQLite persistence:** the default lab run writes checkpoints in WAL mode,
   using one `thread_id` per scenario.
2. **Time-travel inspection:** `make inspect-history` exports compact checkpoint
   snapshots for `thread-S01_simple` to `outputs/state_history.json`.
3. **Graph diagram:** `make graph-diagram` exports the compiled workflow Mermaid
   diagram to `outputs/graph.mmd` via `graph.get_graph().draw_mermaid()`.

## 8. Improvement plan

The next production improvement is stronger observability: measure per-node
latency, trace LLM and tool calls, and use a grounded evaluator to validate tool
results before answering customers.
"""


def write_report(metrics: MetricsReport, output_path: str | Path) -> None:
    """Write the rendered report to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(metrics), encoding="utf-8")
