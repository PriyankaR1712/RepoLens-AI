from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.api import repositories as repository_api
from app.models.repository import Repository
from app.schemas.repository import RepositoryIngestRequest


class FakeQuery:
    def __init__(self, existing=None):
        self.existing = existing

    def filter(self, *_args):
        return self

    def first(self):
        return self.existing


class FakeDatabase:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
        self.commits = 0
        self.status_history = []
        self.query = Mock(return_value=FakeQuery(existing))

    def add(self, record):
        self.added.append(record)

    def commit(self):
        self.commits += 1
        if self.existing is not None:
            self.status_history.append(self.existing.status)

    def refresh(self, record):
        record.id = 17
        record.created_at = datetime.now(timezone.utc)
        record.updated_at = record.created_at

    def rollback(self):
        pass


def _request(url="https://github.com/example/project"):
    return RepositoryIngestRequest(source_url=url)


def _successful_ingestion(_url):
    return {"status": "success", "files": [{"path": "main.py", "content": "pass"}]}


class FakeIndexingService:
    def index_repository(self, ingestion_result, repository_id):
        assert ingestion_result["status"] == "success"
        assert repository_id == "17"
        return {
            "status": "success",
            "total_files": 1,
            "total_chunks": 1,
            "indexed_chunks": 1,
        }


def test_successful_repository_ingestion_and_indexing(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(
        repository_api, "ingest_github_repository", _successful_ingestion
    )
    monkeypatch.setattr(repository_api, "IndexingService", FakeIndexingService)

    response = repository_api.ingest_repository(_request(), db)

    assert response["repository"].status == "indexed"
    assert response["repository"].source_url == "https://github.com/example/project"
    assert response["indexing"]["indexed_chunks"] == 1
    assert db.commits == 2


def test_invalid_repository_url_is_rejected_before_database_or_network(monkeypatch):
    db = FakeDatabase()
    ingestion = Mock()
    monkeypatch.setattr(repository_api, "ingest_github_repository", ingestion)

    with pytest.raises(HTTPException) as error:
        repository_api.ingest_repository(_request("https://example.com/project"), db)

    assert error.value.status_code == 422
    ingestion.assert_not_called()
    assert db.added == []


def test_ingestion_failure_marks_repository_failed(monkeypatch):
    db = FakeDatabase()

    def fail_ingestion(_url):
        raise RuntimeError("GitHub unavailable")

    monkeypatch.setattr(repository_api, "ingest_github_repository", fail_ingestion)

    with pytest.raises(HTTPException) as error:
        repository_api.ingest_repository(_request(), db)

    assert error.value.status_code == 502
    assert db.added[0].status == "failed"
    assert db.commits == 2


def test_indexing_failure_marks_repository_failed(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(
        repository_api, "ingest_github_repository", _successful_ingestion
    )

    class FailedIndexingService:
        def index_repository(self, ingestion_result, repository_id):
            return {"status": "failed", "errors": [{"message": "storage error"}]}

    monkeypatch.setattr(repository_api, "IndexingService", FailedIndexingService)

    with pytest.raises(HTTPException) as error:
        repository_api.ingest_repository(_request(), db)

    assert error.value.status_code == 500
    assert db.added[0].status == "failed"
    assert db.commits == 2


def test_duplicate_repository_returns_conflict(monkeypatch):
    existing = SimpleNamespace(id=9, status="indexed")
    db = FakeDatabase(existing=existing)
    ingestion = Mock()
    monkeypatch.setattr(repository_api, "ingest_github_repository", ingestion)

    with pytest.raises(HTTPException) as error:
        repository_api.ingest_repository(_request(), db)

    assert error.value.status_code == 409
    assert error.value.detail["repository_id"] == 9
    ingestion.assert_not_called()
    assert db.added == []


def _pending_repository():
    return SimpleNamespace(
        id=17,
        name="Schedulix",
        source_type="github",
        source_url="https://github.com/stored-owner/Schedulix",
        status="pending",
    )


@pytest.mark.parametrize("initial_status", ["pending", "failed"])
def test_index_endpoint_indexes_existing_record_without_duplicate(
    monkeypatch, initial_status,
):
    repository = _pending_repository()
    repository.status = initial_status
    db = FakeDatabase(existing=repository)
    ingest = Mock(return_value=_successful_ingestion(repository.source_url))
    monkeypatch.setattr(repository_api, "ingest_github_repository", ingest)
    monkeypatch.setattr(repository_api, "IndexingService", FakeIndexingService)

    response = repository_api.index_existing_repository(repository.id, db)

    ingest.assert_called_once_with(repository.source_url)
    assert response["repository"] is repository
    assert repository.status == "indexed"
    assert response["indexing"]["indexed_chunks"] == 1
    assert db.added == []
    assert db.commits == 2
    assert db.status_history == ["indexing", "indexed"]


def test_index_endpoint_returns_404_for_unknown_record(monkeypatch):
    db = FakeDatabase()
    ingest = Mock()
    monkeypatch.setattr(repository_api, "ingest_github_repository", ingest)

    with pytest.raises(HTTPException) as error:
        repository_api.index_existing_repository(17, db)

    assert error.value.status_code == 404
    ingest.assert_not_called()
    assert db.added == []


def test_index_endpoint_marks_existing_record_failed_on_ingestion_error(
    monkeypatch,
):
    repository = _pending_repository()
    db = FakeDatabase(existing=repository)
    monkeypatch.setattr(
        repository_api,
        "ingest_github_repository",
        Mock(side_effect=RuntimeError("GitHub unavailable")),
    )

    with pytest.raises(HTTPException) as error:
        repository_api.index_existing_repository(repository.id, db)

    assert error.value.status_code == 502
    assert repository.status == "failed"
    assert db.added == []
    assert db.commits == 2


def test_index_endpoint_marks_existing_record_failed_on_indexing_error(
    monkeypatch,
):
    repository = _pending_repository()
    db = FakeDatabase(existing=repository)
    monkeypatch.setattr(
        repository_api,
        "ingest_github_repository",
        _successful_ingestion,
    )

    class FailedIndexingService:
        def index_repository(self, ingestion_result, repository_id):
            return {"status": "failed", "indexed_chunks": 0}

    monkeypatch.setattr(repository_api, "IndexingService", FailedIndexingService)

    with pytest.raises(HTTPException) as error:
        repository_api.index_existing_repository(repository.id, db)

    assert error.value.status_code == 500
    assert repository.status == "failed"
    assert db.added == []
    assert db.commits == 2


def test_index_endpoint_preserves_partial_status(monkeypatch):
    repository = _pending_repository()
    db = FakeDatabase(existing=repository)
    monkeypatch.setattr(
        repository_api,
        "ingest_github_repository",
        lambda _url: {"status": "partial", "files": []},
    )
    monkeypatch.setattr(
        repository_api,
        "IndexingService",
        lambda: SimpleNamespace(
            index_repository=lambda **_kwargs: {
                "status": "partial",
                "indexed_chunks": 2,
            }
        ),
    )

    response = repository_api.index_existing_repository(repository.id, db)

    assert repository.status == "partial"
    assert response["repository"].status == "partial"
    assert db.added == []


def test_index_endpoint_rejects_non_pending_record_without_reindexing(
    monkeypatch,
):
    repository = _pending_repository()
    repository.status = "indexed"
    db = FakeDatabase(existing=repository)
    ingest = Mock()
    monkeypatch.setattr(repository_api, "ingest_github_repository", ingest)

    with pytest.raises(HTTPException) as error:
        repository_api.index_existing_repository(repository.id, db)

    assert error.value.status_code == 409
    ingest.assert_not_called()
    assert db.commits == 0
    assert db.added == []
