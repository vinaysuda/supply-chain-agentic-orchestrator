from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from pydantic import BaseModel, Field

from src.core.config import settings
from src.state.graph_state import GraphState


class RoutingDecision(BaseModel):
    """Deterministic routing schema for the Supervisor."""

    is_valid_anomaly: bool = Field(description="True if this is a valid supply chain anomaly, False if noise.")
    reasoning: str = Field(description="Brief justification for the routing decision.")


def supervise_telemetry(state: GraphState) -> dict[str, Any]:
    """
    The Gateway Node.
    Analyzes raw telemetry and decides if it warrants a full multi-agent investigation.
    """
    event = state["event"]

    print(f"\n[SYSTEM] Supervisor analyzing telemetry (Provider: {settings.ACTIVE_LLM_PROVIDER.upper()})...")

    # ENTERPRISE GUARDRAIL: explicitly type the variable as the polymorphic base class
    llm: BaseChatModel

    # Dynamically instantiate the correct LLM based on config
    if settings.ACTIVE_LLM_PROVIDER == "azure":
        llm = AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0.0,
        )
    elif settings.ACTIVE_LLM_PROVIDER == "openai":
        llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    else:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.0, api_key=settings.GEMINI_API_KEY)

    # Bind the strict schema to the selected LLM
    chain = llm.with_structured_output(RoutingDecision)

    # Force the LLM to output a strict True/False routing decision
    raw_decision = chain.invoke(
        f"Analyze this incoming manufacturing telemetry: {event.model_dump_json()}. "
        "Is this a valid anomaly requiring investigation, or standard noise?"
    )

    # ENTERPRISE GUARDRAIL: Strict Mypy type casting for LangChain's loose types
    decision = cast(RoutingDecision, raw_decision)

    if decision.is_valid_anomaly:
        return {"next_node": "investigate"}
    else:
        return {
            "next_node": "end",
            "validation_errors": state.get("validation_errors", []) + ["Telemetry classified as noise."],
        }
