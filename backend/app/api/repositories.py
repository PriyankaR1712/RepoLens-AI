
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.repository import Repository
from app.schemas.repository import RepositoryCreate, RepositoryResponse


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
