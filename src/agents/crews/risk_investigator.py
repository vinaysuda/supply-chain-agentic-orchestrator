from typing import cast

from crewai import LLM, Agent, Crew, Process, Task

from src.core.config import settings
from src.schemas.telemetry import RiskAssessment, TelemetryEvent


def run_risk_investigation_crew(event: TelemetryEvent) -> RiskAssessment:
    print(f"\n[SYSTEM] Initializing CrewAI Pod (Provider: {settings.ACTIVE_LLM_PROVIDER.upper()})...")

    # 1. ENTERPRISE GUARDRAIL: Native CrewAI LLM Instantiation
    # We use CrewAI's native LLM wrapper to completely bypass LangChain/Pydantic validation clashes
    if settings.ACTIVE_LLM_PROVIDER == "azure":
        crew_llm = LLM(
            model=f"azure/{settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME}",
            api_key=settings.AZURE_OPENAI_API_KEY,
            base_url=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0.1,
        )
    elif settings.ACTIVE_LLM_PROVIDER == "openai":
        crew_llm = LLM(model="gpt-4o", api_key=settings.OPENAI_API_KEY, temperature=0.1)
    else:
        crew_llm = LLM(model="gemini/gemini-2.5-flash-lite", api_key=settings.GEMINI_API_KEY, temperature=0.1)

    # 2. Define Agents
    data_analyst = Agent(
        role="Supplier Data Analyst",
        goal="Analyze the raw telemetry data and identify the core issue and immediate manufacturing impact.",
        backstory="You are an expert supply chain data analyst. You specialize in decoding raw telemetry logs and identifying root causes of delays.",
        llm=crew_llm,
        verbose=True,
        allow_delegation=False,
    )

    risk_scout = Agent(
        role="Enterprise Risk Mitigation Specialist",
        goal="Calculate the global financial severity of the anomaly and structure the final Risk Assessment payload.",
        backstory="You are a senior risk assessment officer. You take localized data analysis and map it to global financial and SLA consequences.",
        llm=crew_llm,
        verbose=True,
        allow_delegation=False,
    )

    # 3. Define Tasks
    analysis_task = Task(
        description=f"Analyze this telemetry event: {event.model_dump_json()}. Identify the supplier issue and assembly line impact.",
        expected_output="A detailed summary of the supplier failure and its immediate impact on the assembly line.",
        agent=data_analyst,
    )

    mitigation_task = Task(
        description="Based on the data analyst's report, determine the severity, estimate financial impact, and format the output into a strict data schema.",
        expected_output="A structured risk assessment.",
        agent=risk_scout,
        output_pydantic=RiskAssessment,
    )

    # 4. Assemble and Run the Crew
    crew = Crew(
        agents=[data_analyst, risk_scout],
        tasks=[analysis_task, mitigation_task],
        process=Process.sequential,  # If there is a need for a debate between agents, comment this line and uncomment the next two lines.
        # process=Process.hierarchical,  # Creates a manager to orchestrate a debate
        # manager_llm=crew_llm,
        verbose=True,
    )

    # Execute the crew and force the output into our strict Pydantic model
    result = crew.kickoff()

    # ENTERPRISE GUARDRAIL: Safely extract to avoid Mypy Union errors
    pydantic_output = getattr(result, "pydantic", None)

    if not pydantic_output:
        raise ValueError("CrewAI failed to return a valid RiskAssessment Pydantic object.")

    # Explicitly cast the generic BaseModel to our strict schema to satisfy Mypy
    return cast(RiskAssessment, pydantic_output)
