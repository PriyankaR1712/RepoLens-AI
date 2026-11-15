
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.repository import Repository
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryIngestRequest,
    RepositoryIngestResponse,
    RepositoryResponse,
)
from app.services.ingestion.github import parse_github_url
from app.services.ingestion.github_ingestion import ingest_github_repository
from app.services.retrieval.indexing_service import IndexingService


router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"]
)


@router.post(
    "/",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED
)
def create_repository(
    repository_data: RepositoryCreate,
    db: Session = Depends(get_db)
):
    repository = Repository(
        name=repository_data.name,
        source_type=repository_data.source_type,
        source_url=repository_data.source_url
    )

    try:
        db.add(repository)
        db.commit()
        db.refresh(repository)

        return repository

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create repository"
        )


@router.post(
    "/ingest",
    response_model=RepositoryIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_repository(
    request: RepositoryIngestRequest,
    db: Session = Depends(get_db),
):
    """Ingest and index a public GitHub repository synchronously."""
    try:
        parsed_url = parse_github_url(request.source_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    canonical_url = parsed_url["url"]
    existing = db.query(Repository).filter(
        Repository.source_url == canonical_url
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "This repository has already been registered.",
                "repository_id": existing.id,
                "status": existing.status,
            },
        )

    repository = Repository(
        name=parsed_url["repository"],
        source_type="github",
        source_url=canonical_url,
        status="indexing",
    )
    try:
        db.add(repository)
        db.commit()
        db.refresh(repository)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create repository record.",
        ) from exc

    try:
        ingestion_result = ingest_github_repository(canonical_url)
    except Exception as exc:
        repository.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Repository ingestion failed: {exc}",
        ) from exc

    if not isinstance(ingestion_result, dict) or ingestion_result.get(
        "status"
    ) not in {"success", "partial"}:
        repository.status = "failed"
        db.commit()
        detail = (
            ingestion_result.get("message", "GitHub ingestion failed.")
            if isinstance(ingestion_result, dict)
            else "GitHub ingestion returned an invalid result."
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    try:
        indexing_result = IndexingService().index_repository(
            ingestion_result=ingestion_result,
            repository_id=str(repository.id),
        )
    except Exception as exc:
        repository.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repository indexing failed: {exc}",
        ) from exc

    if not isinstance(indexing_result, dict) or indexing_result.get(
        "status"
    ) not in {"success", "partial"}:
        repository.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Repository indexing failed.",
                "indexing": indexing_result,
            },
        )

    repository.status = (
        "partial"
        if "partial" in {
            ingestion_result.get("status"), indexing_result.get("status")
        }
        else "indexed"
    )
    db.commit()
    db.refresh(repository)

    return {
        "repository": repository,
        "ingestion": ingestion_result,
        "indexing": indexing_result,
    }


@router.post(
    "/{repository_id}/index",
    response_model=RepositoryIngestResponse,
)
def index_existing_repository(
    repository_id: int,
    db: Session = Depends(get_db),
):
    """Ingest and index an existing pending or failed GitHub record."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id
    ).first()
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )

    if repository.status not in {"pending", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Repository cannot be indexed from status "
                f"'{repository.status}'."
            ),
        )

    if repository.source_type != "github" or not repository.source_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only repositories with a stored GitHub URL can be indexed.",
        )

    try:
        canonical_url = parse_github_url(repository.source_url)["url"]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stored GitHub URL is invalid: {exc}",
        ) from exc

    repository.status = "indexing"
    db.commit()

    try:
        ingestion_result = ingest_github_repository(canonical_url)
    except Exception as exc:
        repository.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Repository ingestion failed: {exc}",
        ) from exc

    if not isinstance(ingestion_result, dict) or ingestion_result.get(
        "status"
    ) not in {"success", "partial"}:
        repository.status = "failed"
        db.commit()
        detail = (
            ingestion_result.get("message", "GitHub ingestion failed.")
            if isinstance(ingestion_result, dict)
            else "GitHub ingestion returned an invalid result."
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    try:
        indexing_result = IndexingService().index_repository(
            ingestion_result=ingestion_result,
            repository_id=str(repository.id),
        )
    except Exception as exc:
        repository.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repository indexing failed: {exc}",
        ) from exc

    if not isinstance(indexing_result, dict) or indexing_result.get(
        "status"
    ) not in {"success", "partial"}:
        repository.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Repository indexing failed.",
                "indexing": indexing_result,
            },
        )

    repository.status = (
        "partial"
        if "partial" in {
            ingestion_result.get("status"), indexing_result.get("status")
        }
        else "indexed"
    )
    db.commit()
    db.refresh(repository)

    return {
        "repository": repository,
        "ingestion": ingestion_result,
        "indexing": indexing_result,
    }


@router.get(
    "/",
    response_model=list[RepositoryResponse]
)
def get_repositories(db: Session = Depends(get_db)):
    repositories = (
        db.query(Repository)
        .order_by(Repository.created_at.desc())
        .all()
    )

    return repositories


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse
)
def get_repository(
    repository_id: int,
    db: Session = Depends(get_db)
):
    repository = db.query(Repository).filter(
        Repository.id == repository_id
    ).first()

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    return repository
