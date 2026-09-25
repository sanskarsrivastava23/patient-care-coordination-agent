from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class AgentTask(BaseModel):
    agent: Literal[
        "patient_agent",
        "clinical_agent",
        "care_management_agent"
    ] = Field(
        description="The specialist agent responsible for this task."
    )

    task: str = Field(
        description="Clear instruction describing what the specialist agent should do."
    )


# ---------------------------------------------------------
# 2. Define Supervisor's complete structured output
# ---------------------------------------------------------

class SupervisorDecision(BaseModel):

    intent: str = Field(
        description="Short description of the user's overall intent."
    )

    tasks: List[AgentTask] = Field(
        description="List of tasks that need to be executed."
    )

    needs_clarification: bool = Field(
        default=False,
        description="True when important information is missing."
    )

    clarification_question: Optional[str] = Field(
        default=None,
        description="Question to ask the user if clarification is required."
    )
