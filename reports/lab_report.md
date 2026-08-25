# Day 08 Lab Report

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
| Total scenarios | 7 |
| Success rate | 100.00% |
| Average nodes visited | 6.43 |
| Total retries | 3 |
| Total approval/HITL events | 2 |
| Resume success | Yes |

| Scenario | Expected route | Actual route | Success | Retries | Interrupts | Latency (ms) |
|---|---|---|---|---:|---:|---:|
| S01_simple | simple | simple | Yes | 0 | 0 | 5572 |
| S02_tool | tool | tool | Yes | 0 | 0 | 3132 |
| S03_missing | missing_info | missing_info | Yes | 0 | 0 | 1014 |
| S04_risky | risky | risky | Yes | 0 | 1 | 2658 |
| S05_error | error | error | Yes | 2 | 0 | 2580 |
| S06_delete | risky | risky | Yes | 0 | 1 | 2241 |
| S07_dead_letter | error | error | Yes | 1 | 0 | 866 |

### Recorded errors

- **S05_error**: Transient failure recorded. Attempt 1 of 3.; Transient failure recorded. Attempt 2 of 3.
- **S07_dead_letter**: Transient failure recorded. Attempt 1 of 1.

## 5. Failure analysis

1. **Transient tool failure:** `evaluate` sends an unsuccessful tool result to
   `retry`. The retry node increments `attempt`; once `max_attempts` is reached,
   the graph routes to `dead_letter`, preventing an infinite loop.
2. **Risky action without approval:** side-effecting requests are routed through
   `risky_action` and `approval`. A rejected request goes to clarification rather
   than continuing to the tool.

## 6. Persistence / recovery evidence

SQLite checkpoint history was retrieved successfully after every scenario. The default configuration uses `SqliteSaver` with WAL mode in `checkpoints.db`; each scenario has its own `thread_id`.

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
