from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.repository import Repository
from app.schemas.question import QuestionRequest, QuestionResponse
from app.services.rag.ollama_client import OllamaError
from app.services.rag.rag_service import (
    NoRelevantContextError,
    RAGService,
    create_rag_service,
)


router = APIRouter(prefix="/repositories", tags=["Repository Questions"])


@router.post(
    "/{repository_id}/ask",
    response_model=QuestionResponse,
)
def ask_repository(
    repository_id: int,
    request: QuestionRequest,
    db: Session = Depends(get_db),
    rag_service: RAGService = Depends(create_rag_service),
):
    repository = db.query(Repository).filter(
        Repository.id == repository_id
    ).first()
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )
    if repository.status not in {"indexed", "partial"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository is not indexed yet.",
        )

    try:
        return rag_service.ask(str(repository_id), request.question)
    except NoRelevantContextError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except OllamaError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Answer generation is unavailable: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository question processing failed.",
        ) from exc
