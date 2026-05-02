import json
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import TypeAdapter

from src.agents.crews.risk_investigator import run_risk_investigation_crew
from src.agents.nodes.escalation import draft_escalation, execute_escalation
from src.agents.nodes.supervisor import supervise_telemetry
from src.core.config import settings
from src.schemas.telemetry import TelemetryEvent
from src.state.graph_state import GraphState


def investigate_risk(state: GraphState) -> dict[str, Any]:
    event = state.get("event")
    if not event:
        return {"validation_errors": state.get("validation_errors", []) + ["Missing event data."]}

    print(f"\n[SYSTEM] Deploying CrewAI Pod for Supplier {event.supplier_id}...")
    assessment = run_risk_investigation_crew(event)

    return {"risk_assessment": assessment, "next_node": "draft"}


def route_supervisor(state: GraphState) -> str:
    return state.get("next_node", "end")


# FIX: Typed as Any to bypass strict LangGraph generic enforcement
def build_graph() -> Any:
    builder = StateGraph(GraphState)
    builder.add_node("supervisor", supervise_telemetry)
    builder.add_node("investigate", investigate_risk)
    builder.add_node("draft", draft_escalation)
    builder.add_node("execute", execute_escalation)
    builder.set_entry_point("supervisor")
    builder.add_conditional_edges("supervisor", route_supervisor, {"investigate": "investigate", "end": END})
    builder.add_edge("investigate", "draft")
    builder.add_edge("draft", "execute")
    builder.add_edge("execute", END)
    return builder


def main() -> None:
    settings.validate_core_settings()

    print("\n[SYSTEM] Connecting to PostgreSQL Audit Database...")

    # FIX: Added dict_row so psycopg returns dictionaries, matching LangGraph's expectations
    connection_kwargs: dict[str, Any] = {
        "autocommit": True,
        "prepare_threshold": 0,
        "row_factory": dict_row,
    }

    with ConnectionPool(conninfo=settings.DATABASE_URI, kwargs=connection_kwargs) as pool:
        # FIX: Mypy struggles with deep generic inference on third-party pools, so we type ignore the arg
        checkpointer = PostgresSaver(pool)  # type: ignore[arg-type]
        checkpointer.setup()

        builder = build_graph()
        app = builder.compile(checkpointer=checkpointer, interrupt_before=["execute"])

        mock_file_path = Path("data/mock_telemetry_main.json")
        if not mock_file_path.exists():
            raise FileNotFoundError(f"[FATAL] Mock data not found at: {mock_file_path}")

        with open(mock_file_path) as f:
            data = json.load(f)

        adapter = TypeAdapter(list[TelemetryEvent])
        events = adapter.validate_python(data)

        print(f"\n[SYSTEM] Batch processing started: {len(events)} events found.")

        for i, mock_event in enumerate(events, 1):
            print(f"\n{'=' * 20} PROCESSING EVENT {i}/{len(events)} {'=' * 20}")

            # FIX: Explicitly cast the standard dictionary into LangChain's strict RunnableConfig type
            config: RunnableConfig = {"configurable": {"thread_id": str(mock_event.event_id)}}

            try:
                for event_chunk in app.stream({"event": mock_event}, config):
                    pass

                # Phase 2: Interrogate the database to see where this specific thread paused
                state = app.get_state(config)

                # If the 'next' queue contains "execute", it means the Human-In-The-Loop was triggered
                if state.next and "execute" in state.next:
                    action = state.values.get("escalation_action")

                    if action:
                        print("\n--- HUMAN IN THE LOOP APPROVAL REQUIRED ---")
                        print(f"Proposed Action: {action.action_type}")
                        print(f"Justification: {action.justification}")

                        # Phase 3: Wait for physical user authorization
                        user_input = input("\nType 'APPROVE' to ratify action (or 'SKIP' to deny): ")

                        if user_input.strip().upper() == "APPROVE":
                            print("\n[SYSTEM] Human Ratification Confirmed. Executing...")

                            # Phase 4: Passing None to stream resumes the paused node
                            for _ in app.stream(None, config):
                                pass
                        else:
                            print("\n[SYSTEM] Action denied by human governance. Moving to next event.")
                    else:
                        print("\n[SYSTEM] Error: Hit execution boundary but no drafted action found.")

                else:
                    # If 'next' is empty, the graph reached the END node autonomously (e.g., noise)
                    print("\n[SYSTEM] Event resolved automatically. No human approval required.")

            except Exception as e:
                print(f"\n[ERROR] Failed to process event {mock_event.event_id}: {e}")
                continue

        print("\n[SYSTEM] Pipeline complete. All telemetry events processed and logged to PostgreSQL.")


if __name__ == "__main__":
    main()
