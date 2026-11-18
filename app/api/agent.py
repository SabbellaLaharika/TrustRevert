from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.tools import AgentExecuteRequest, AgentExecuteResponse
from app.services.orchestrator import orchestrate_agent_call
from app.services.interceptor import process_agent_intent

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post("/execute", response_model=AgentExecuteResponse)
def execute_agent_command(
    request: AgentExecuteRequest,
    db: Session = Depends(get_db)
):
    """Trigger the agent to execute a state mutation under progressive autonomy.

    - The LLM orchestrator parses the prompt into a typed tool intent schema.
    - The interceptor verifies if the tool has earned enough trust (TRUST_THRESHOLD).
    - If untrusted, execution is paused and staged into the pending approval queue.
    - If trusted, execution proceeds immediately with deterministic action logging.
    """
    try:
        # Formulate tool intent
        intent = orchestrate_agent_call(request.prompt, request.target_id)
        # Intercept and evaluate trust
        result = process_agent_intent(intent, db)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not exist in content_queue" in str(e) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )
