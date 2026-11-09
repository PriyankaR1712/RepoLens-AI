
import pytest

from app.services.retrieval.vector_store import VectorStore


@pytest.fixture
def vector_store(tmp_path):
    return VectorStore(
        persist_directory=str(tmp_path / "chroma_test")
    )


@pytest.fixture
def sample_chunks():
    return [
        {
            "file_path": "app/main.py",
            "language": "Python",
            "symbol_name": "calculate_total",
            "symbol_type": "function",
            "parent_class": None,
            "start_line": 1,
            "end_line": 3,
            "content": "def calculate_total(items):\n    return sum(items)",
            "chunk_index": 0,
            "embedding": [0.1, 0.2, 0.3, 0.4],
        },
        {
            "file_path": "app/models.py",
            "language": "Python",
            "symbol_name": "User",
            "symbol_type": "class",
            "parent_class": None,
            "start_line": 1,
            "end_line": 5,
            "content": "class User:\n    pass",
            "chunk_index": 1,
            "embedding": [0.2, 0.3, 0.4, 0.5],
        },
    ]


def test_add_chunks_successfully(
    vector_store, sample_chunks
):
    stored_count = vector_store.add_chunks(
        "PriyankaR1712/RepoLens-AI",
        sample_chunks,
    )

    assert stored_count == 2

    collection = vector_store.get_or_create_collection(
        "PriyankaR1712/RepoLens-AI"
    )

    assert collection.count() == 2


def test_add_empty_chunks_returns_zero(vector_store):
    result = vector_store.add_chunks(
        "owner/repository",
        [],
    )

    assert result == 0


def test_search_returns_stored_chunks(
    vector_store, sample_chunks
):
    repository_id = "owner/repository"

    vector_store.add_chunks(repository_id, sample_chunks)

    results = vector_store.search(
        repository_id=repository_id,
        query_embedding=[0.1, 0.2, 0.3, 0.4],
        top_k=2,
    )

    assert len(results) == 2
    assert results[0]["content"] == sample_chunks[0]["content"]
    assert results[0]["metadata"]["file_path"] == "app/main.py"
    assert results[0]["metadata"]["symbol_name"] == "calculate_total"


def test_search_empty_collection_returns_empty_list(
    vector_store,
):
    results = vector_store.search(
        repository_id="empty/repository",
        query_embedding=[0.1, 0.2, 0.3, 0.4],
    )

    assert results == []


def test_repository_collections_are_isolated(
    vector_store, sample_chunks
):
    vector_store.add_chunks(
        "owner/repository-one",
        sample_chunks[:1],
    )

    vector_store.add_chunks(
        "owner/repository-two",
        sample_chunks[1:],
    )

    first_results = vector_store.search(
        "owner/repository-one",
        [0.1, 0.2, 0.3, 0.4],
    )

    second_results = vector_store.search(
        "owner/repository-two",
        [0.2, 0.3, 0.4, 0.5],
    )

    assert len(first_results) == 1
    assert len(second_results) == 1

    assert first_results[0]["metadata"]["symbol_name"] == "calculate_total"
    assert second_results[0]["metadata"]["symbol_name"] == "User"


def test_upsert_updates_existing_chunk(
    vector_store, sample_chunks
):
    repository_id = "owner/repository"

    vector_store.add_chunks(
        repository_id,
        sample_chunks[:1],
    )

    updated_chunk = {
        **sample_chunks[0],
        "content": "def calculate_total(items):\n    return sum(items) * 2",
    }

    vector_store.add_chunks(
        repository_id,
        [updated_chunk],
    )

    collection = vector_store.get_or_create_collection(
        repository_id
    )

    assert collection.count() == 1

    results = vector_store.search(
        repository_id,
        [0.1, 0.2, 0.3, 0.4],
    )

    assert results[0]["content"] == updated_chunk["content"]


def test_repository_data_persists_after_reopening(
    tmp_path, sample_chunks
):
    persist_directory = str(tmp_path / "persistent_chroma")
    repository_id = "owner/repository"

    first_store = VectorStore(persist_directory)
    first_store.add_chunks(repository_id, sample_chunks)

    second_store = VectorStore(persist_directory)

    results = second_store.search(
        repository_id,
        [0.1, 0.2, 0.3, 0.4],
        top_k=2,
    )

    assert len(results) == 2


def test_delete_repository(vector_store, sample_chunks):
    repository_id = "owner/repository"

    vector_store.add_chunks(repository_id, sample_chunks)

    deleted = vector_store.delete_repository(repository_id)

    assert deleted is True

    results = vector_store.search(
        repository_id,
        [0.1, 0.2, 0.3, 0.4],
    )

    assert results == []


def test_invalid_top_k_is_rejected(vector_store):
    with pytest.raises(ValueError):
        vector_store.search(
            "owner/repository",
            [0.1, 0.2],
            top_k=0,
        )


def test_invalid_repository_id_is_rejected(vector_store):
    with pytest.raises(ValueError):
        vector_store.get_or_create_collection("")


def test_invalid_embedding_is_rejected(vector_store):
    chunk = {
        "file_path": "main.py",
        "language": "Python",
        "symbol_name": "main",
        "symbol_type": "function",
        "parent_class": None,
        "start_line": 1,
        "end_line": 2,
        "content": "def main(): pass",
        "chunk_index": 0,
        "embedding": [],
    }

    with pytest.raises(ValueError):
        vector_store.add_chunks("owner/repository", [chunk])


def test_sync_chunks_removes_obsolete_chunks(
    vector_store,
    sample_chunks,
):
    repository_id = "owner/repository"

    vector_store.add_chunks(repository_id, sample_chunks)

    updated_chunks = [sample_chunks[0]]

    indexed_count = vector_store.sync_chunks(
        repository_id,
        updated_chunks,
    )

    collection = vector_store.get_or_create_collection(repository_id)

    assert indexed_count == 1
    assert collection.count() == 1

    results = vector_store.search(
        repository_id,
        [0.1, 0.2, 0.3, 0.4],
    )

    assert len(results) == 1
    assert results[0]["metadata"]["file_path"] == "app/main.py"


def test_sync_chunks_updates_existing_chunks(
    vector_store,
    sample_chunks,
):
    repository_id = "owner/repository"

    vector_store.add_chunks(repository_id, sample_chunks)

    updated_chunk = {
        **sample_chunks[0],
        "content": "def calculate_total(items):\n    return 100",
    }

    vector_store.sync_chunks(
        repository_id,
        [updated_chunk],
    )

    results = vector_store.search(
        repository_id,
        [0.1, 0.2, 0.3, 0.4],
    )

    assert len(results) == 1
    assert results[0]["content"] == updated_chunk["content"]


def test_sync_empty_chunks_removes_all_existing_chunks(
    vector_store,
    sample_chunks,
):
    repository_id = "owner/repository"

    vector_store.add_chunks(repository_id, sample_chunks)

    indexed_count = vector_store.sync_chunks(
        repository_id,
        [],
    )

    collection = vector_store.get_or_create_collection(repository_id)

    assert indexed_count == 0
    assert collection.count() == 0


def test_sync_chunks_preserves_existing_data_on_validation_failure(
    vector_store,
    sample_chunks,
):
    repository_id = "owner/repository"

    vector_store.add_chunks(repository_id, sample_chunks)

    invalid_chunk = {
        **sample_chunks[0],
        "embedding": [],
    }

    with pytest.raises(ValueError):
        vector_store.sync_chunks(
            repository_id,
            [invalid_chunk],
        )

    collection = vector_store.get_or_create_collection(repository_id)

    assert collection.count() == 2
