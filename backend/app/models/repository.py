from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    source_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self):
        return f"<Repository(id={self.id}, name='{self.name}')>"