from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from src.core.config import settings
from src.schemas.telemetry import EscalationAction
from src.state.graph_state import GraphState
from src.tools.erp_mock import trigger_erp_action


def draft_escalation(state: GraphState) -> dict[str, Any]:
    """
    Drafts the formal action payload based on the CrewAI Risk Assessment.
    This prepares the data for human review.
    """
    assessment = state.get("risk_assessment")
    if not assessment:
        return {"validation_errors": state.get("validation_errors", []) + ["Missing Risk Assessment."]}

    # ENTERPRISE GUARDRAIL: explicitly type the variable
    llm: BaseChatModel

    if settings.ACTIVE_LLM_PROVIDER == "azure":
        llm = AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0.1,
        )
    elif settings.ACTIVE_LLM_PROVIDER == "openai":
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    else:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.1, api_key=settings.GEMINI_API_KEY)

    # Force the generation of the strict EscalationAction schema
    raw_action = llm.with_structured_output(EscalationAction).invoke(
        f"Based on this risk assessment, draft a formal escalation action: {assessment.model_dump_json()}"
    )

    # ENTERPRISE GUARDRAIL: Strict type casting
    action = cast(EscalationAction, raw_action)

    return {"escalation_action": action, "next_node": "execute"}


def execute_escalation(state: GraphState) -> dict[str, Any]:
    """
    THE GOVERNANCE BOUNDARY.
    In the LangGraph compiler, we will set interrupt_before=["execute"].
    This node only runs AFTER a human explicitly approves the drafted action.
    """
    action = state.get("escalation_action")

    # ENTERPRISE GUARDRAIL: Prove to Mypy that 'action' is not None before using it
    if not action:
        print("\n[SYSTEM] Error: Escalation action is missing from state.")
        return {"next_node": "end"}

    # Trigger the simulated external system (SAP / Azure / Oracle)
    success = trigger_erp_action(action_type=action.action_type, justification=action.justification)

    if success:
        print("\n[SYSTEM] Execution Confirmed: Lifecycle complete.")
    else:
        print("\n[SYSTEM] FATAL: ERP integration failed.")
        return {"validation_errors": state.get("validation_errors", []) + ["ERP execution failed."]}

    return {"next_node": "end"}
