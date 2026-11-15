from unittest.mock import Mock

import pytest

from app.services.rag.rag_service import (
    NoRelevantContextError,
    RAGService,
    create_rag_service,
)
from app.services.retrieval.hybrid_retriever import HybridRetriever


def _chunk(path="src/auth.py", content="def authenticate(): return True"):
    return {
        "id": f"{path}:0",
        "content": content,
        "metadata": {
            "file_path": path,
            "symbol_name": "authenticate",
            "start_line": 10,
            "end_line": 12,
            "language": "Python",
        },
    }


def _context_from_prompt(prompt):
    return prompt.split("Repository context:\n", 1)[1].split(
        "\n\nAnswer clearly", 1
    )[0]


def test_successful_rag_uses_scoped_retrieval_and_returns_citations():
    retriever = Mock()
    retriever.retrieve.return_value = [_chunk()]
    ollama = Mock()
    ollama.generate.return_value = "Authentication returns true."
    service = RAGService(retriever, ollama)

    result = service.ask("17", "How does authentication work?")

    retriever.retrieve.assert_called_once_with(
        repository_id="17",
        query="How does authentication work?",
        top_k=7,
    )
    assert result["answer"] == "Authentication returns true."
    assert result["repository_id"] == "17"
    assert result["sources"] == [{
        "file_path": "src/auth.py",
        "symbol_name": "authenticate",
        "start_line": 10,
        "end_line": 12,
        "snippet": "def authenticate(): return True",
    }]
    prompt = ollama.generate.call_args.args[0]
    assert "src/auth.py" in prompt
    assert "Lines: 10-12" in prompt
    assert "cannot determine" in prompt
    assert "untrusted data" in prompt


def test_explicit_file_scope_excludes_unrelated_files():
    retriever = Mock()
    retriever.retrieve.return_value = [
        _chunk("backend/app/worker.py", "worker selection code"),
        _chunk("backend/app/api/routes/jobs.py", "jobs API code"),
    ]
    ollama = Mock()
    ollama.generate.return_value = "The worker selects a job."

    result = RAGService(retriever, ollama).ask(
        "1", "In backend/app/worker.py, what does the worker select?"
    )

    context = _context_from_prompt(ollama.generate.call_args.args[0])
    assert [source["file_path"] for source in result["sources"]] == [
        "backend/app/worker.py"
    ]
    assert "worker selection code" in context
    assert "jobs API code" not in context


def test_explicit_function_scope_excludes_unrelated_functions():
    execute_chunk = _chunk("backend/app/worker.py", "execute job body")
    execute_chunk["metadata"]["symbol_name"] = "execute_job"
    process_chunk = _chunk(
        "backend/app/worker.py", "process next job body"
    )
    process_chunk["metadata"]["symbol_name"] = "process_next_job"
    api_chunk = _chunk("backend/app/api/routes/jobs.py", "other function body")
    api_chunk["metadata"]["symbol_name"] = "list_jobs"
    retriever = Mock()
    retriever.retrieve.return_value = [
        execute_chunk,
        process_chunk,
        api_chunk,
    ]
    ollama = Mock()
    ollama.generate.return_value = "The function executes a job."

    result = RAGService(retriever, ollama).ask(
        "1", "What does execute_job() do?"
    )

    context = _context_from_prompt(ollama.generate.call_args.args[0])
    assert [source["symbol_name"] for source in result["sources"]] == [
        "execute_job",
    ]
    assert "execute job body" in context
    assert "process next job body" not in context
    assert "other function body" not in context


def test_combined_file_and_function_scope_requires_both_metadata_matches():
    matching = _chunk("backend/app/worker.py", "execute job body")
    matching["metadata"]["symbol_name"] = "execute_job"
    same_file_other_function = _chunk(
        "backend/app/worker.py", "process next job body"
    )
    same_file_other_function["metadata"]["symbol_name"] = "process_next_job"
    other_file_same_function = _chunk(
        "backend/app/api/routes/jobs.py", "API execute body"
    )
    other_file_same_function["metadata"]["symbol_name"] = "execute_job"

    retriever = Mock()
    retriever.retrieve.return_value = [
        matching,
        same_file_other_function,
        other_file_same_function,
    ]
    ollama = Mock()
    ollama.generate.return_value = "The worker executes the job."

    result = RAGService(retriever, ollama).ask(
        "1", "In backend/app/worker.py, what does execute_job() do?"
    )

    context = _context_from_prompt(ollama.generate.call_args.args[0])
    assert result["sources"] == [{
        "file_path": "backend/app/worker.py",
        "symbol_name": "execute_job",
        "start_line": 10,
        "end_line": 12,
        "snippet": "execute job body",
    }]
    assert "execute job body" in context
    assert "process next job body" not in context
    assert "API execute body" not in context


def test_question_without_explicit_scope_preserves_all_retrieved_chunks():
    retriever = Mock()
    retriever.retrieve.return_value = [
        _chunk("backend/app/worker.py", "worker code"),
        _chunk("backend/app/api/routes/jobs.py", "API code"),
    ]
    ollama = Mock()
    ollama.generate.return_value = "The worker processes jobs."

    result = RAGService(retriever, ollama).ask(
        "1", "How does the worker process a job?"
    )

    context = _context_from_prompt(ollama.generate.call_args.args[0])
    assert [source["file_path"] for source in result["sources"]] == [
        "backend/app/worker.py",
        "backend/app/api/routes/jobs.py",
    ]
    assert "worker code" in context
    assert "API code" in context


def test_explicit_scope_with_no_matches_falls_back_to_all_retrieved_chunks():
    retriever = Mock()
    retriever.retrieve.return_value = [
        _chunk("backend/app/worker.py", "worker code"),
        _chunk("backend/app/api/routes/jobs.py", "API code"),
    ]
    ollama = Mock()
    ollama.generate.return_value = "No matching scope was found."

    result = RAGService(retriever, ollama).ask(
        "1", "In backend/app/missing.py, what does missing_job() do?"
    )

    context = _context_from_prompt(ollama.generate.call_args.args[0])
    assert len(result["sources"]) == 2
    assert "worker code" in context
    assert "API code" in context


def test_citations_match_only_chunks_in_scoped_context():
    matching = _chunk("backend/app/worker.py", "execute job source")
    matching["metadata"]["symbol_name"] = "execute_job"
    excluded = _chunk("frontend/src/App.jsx", "frontend source")

    retriever = Mock()
    retriever.retrieve.return_value = [matching, excluded]
    ollama = Mock()
    ollama.generate.return_value = "The worker executes a job."

    result = RAGService(retriever, ollama).ask(
        "1", "In backend/app/worker.py, what does execute_job() do?"
    )

    context = _context_from_prompt(ollama.generate.call_args.args[0])
    assert len(result["sources"]) == 1
    assert result["sources"][0]["file_path"] == "backend/app/worker.py"
    assert result["sources"][0]["snippet"] == "execute job source"
    assert result["sources"][0]["snippet"] in context
    assert "frontend source" not in context


def test_prompt_requires_specific_grounded_and_complete_answers():
    retriever = Mock()
    retriever.retrieve.return_value = [_chunk()]
    ollama = Mock()
    ollama.generate.return_value = "Authentication returns true."

    RAGService(retriever, ollama).ask(
        "17", "What does authentication do, and how does it work?"
    )

    prompt = ollama.generate.call_args.args[0].lower()
    assert "specific aspects" in prompt
    assert "each part" in prompt
    assert "execution flows" in prompt
    assert "actual order" in prompt
    assert "function names" in prompt
    assert "data flow" in prompt
    assert "conditions" in prompt
    assert "state changes" in prompt
    assert "directly supported" in prompt
    assert "reasonable inferences" in prompt
    assert "exactly as shown" in prompt
    assert "never invent or rename" in prompt
    assert "requested component" in prompt
    assert "related api behavior only when asked" in prompt
    assert "only as explicitly shown" in prompt
    assert "visible condition and resulting status changes" in prompt
    assert "omit unrelated behavior" in prompt
    assert "assumptions" in prompt
    assert "general programming knowledge" in prompt
    assert "not present" in prompt
    assert "file paths" in prompt
    assert "line ranges" in prompt


def test_context_is_bounded_and_citations_match_included_snippets():
    retriever = Mock()
    retriever.retrieve.return_value = [
        _chunk(content="x" * 1000),
        *[
            _chunk(f"src/other_{index}.py", "y" * 1000)
            for index in range(6)
        ],
    ]
    ollama = Mock()
    ollama.generate.return_value = "Not enough context to determine."
    service = RAGService(retriever, ollama, max_context_chars=180)

    result = service.ask("17", "What does this code do?")

    prompt = ollama.generate.call_args.args[0]
    context = prompt.split("Repository context:\n", 1)[1].split(
        "\n\nAnswer clearly", 1
    )[0]
    assert len(context) <= 180
    assert len(result["sources"]) == 1
    assert result["sources"][0]["snippet"] in context


def test_multi_chunk_context_fits_exact_limit_and_citations_match_snippets():
    chunks = [
        _chunk("src/first.py", "first chunk content"),
        _chunk("src/second.py", "second chunk content"),
    ]
    service = RAGService(Mock(), Mock(), max_context_chars=1000)
    full_context, _ = service._build_context(chunks)

    exact_service = RAGService(Mock(), Mock(), max_context_chars=len(full_context))
    exact_context, exact_sources = exact_service._build_context(chunks)

    assert len(exact_context) == len(full_context)
    assert len(exact_context) == exact_service.max_context_chars
    assert exact_context.count("\n\n") == 1
    assert [source["file_path"] for source in exact_sources] == [
        "src/first.py",
        "src/second.py",
    ]
    assert all(source["snippet"] in exact_context for source in exact_sources)


def test_multi_chunk_context_truncates_to_limit_and_citations_match_snippets():
    chunks = [
        _chunk("src/first.py", "first chunk content"),
        _chunk("src/second.py", "second chunk content"),
    ]
    full_context, _ = RAGService(Mock(), Mock(), max_context_chars=1000)._build_context(
        chunks
    )
    limit = len(full_context) - 1

    context, sources = RAGService(
        Mock(), Mock(), max_context_chars=limit
    )._build_context(chunks)

    assert len(context) == limit
    assert len(context) <= limit
    assert len(sources) == 2
    assert all(source["snippet"] in context for source in sources)
    assert sources[0]["snippet"] == "first chunk content"
    assert sources[1]["snippet"] == "second chunk conten"


def test_seven_reranked_chunks_reach_context_and_citations():
    # The first five mirror the recorded primary-query selection; the worker
    # chunks were ranked sixth and seventh in that diagnostic.
    ranked_chunks = [
        _chunk("frontend/src/Home.jsx", "repository home and navigation"),
        _chunk("frontend/src/components/CpuScheduler.jsx", "CPU scheduler UI"),
        _chunk("backend/app/scheduling/algorithms.py", "CPU scheduling algorithm"),
        _chunk("frontend/src/Home.jsx", "home component section"),
        _chunk("frontend/src/App.jsx", "application routes"),
        _chunk("backend/app/worker.py", "worker selects scheduled jobs"),
        _chunk("backend/app/worker.py", "worker executes scheduled jobs"),
    ]
    ranked_chunks[0]["id"] = "frontend/src/Home.jsx:1"
    ranked_chunks[3]["id"] = "frontend/src/Home.jsx:0"
    ranked_chunks[5]["id"] = "backend/app/worker.py:1"
    ranked_chunks[6]["id"] = "backend/app/worker.py:0"
    retriever = Mock()
    retriever.retrieve.return_value = ranked_chunks
    ollama = Mock()
    ollama.generate.return_value = "The worker processes scheduled jobs."

    result = RAGService(retriever, ollama).ask(
        "1",
        "What is the purpose of the job scheduling system, and how are scheduled jobs processed by workers?",
    )

    retriever.retrieve.assert_called_once_with(
        repository_id="1",
        query="What is the purpose of the job scheduling system, and how are scheduled jobs processed by workers?",
        top_k=7,
    )
    prompt = ollama.generate.call_args.args[0]
    context = prompt.split("Repository context:\n", 1)[1].split(
        "\n\nAnswer clearly", 1
    )[0]
    assert len(result["sources"]) == 7
    assert [source["file_path"] for source in result["sources"]] == [
        chunk["metadata"]["file_path"] for chunk in ranked_chunks
    ]
    assert all(source["snippet"] in context for source in result["sources"])
    assert "worker selects scheduled jobs" in context
    assert "worker executes scheduled jobs" in context


def test_empty_retrieval_raises_no_relevant_context():
    retriever = Mock()
    retriever.retrieve.return_value = []
    ollama = Mock()

    with pytest.raises(NoRelevantContextError):
        RAGService(retriever, ollama).ask("17", "Find the login handler")
    ollama.generate.assert_not_called()


def test_hybrid_retriever_runs_cross_encoder_for_rag_query():
    vector_store = Mock()
    vector_store.search.return_value = [_chunk()]
    embedding_service = Mock()
    embedding_service.generate_embeddings.return_value = [
        {"content": "login", "embedding": [0.1, 0.2]}
    ]
    bm25 = Mock()
    bm25.retrieve.return_value = []
    reranker = Mock()
    reranker.rerank.side_effect = lambda query, documents, top_k: documents[:top_k]
    retriever = HybridRetriever(
        vector_store=vector_store,
        embedding_service=embedding_service,
        bm25_retriever=bm25,
        reranker=reranker,
    )
    ollama = Mock()
    ollama.generate.return_value = "Answer"

    RAGService(retriever, ollama).ask("17", "login")

    reranker.rerank.assert_called_once()
    assert reranker.rerank.call_args.kwargs["query"] == "login"


def test_production_factory_connects_cross_encoder(monkeypatch):
    create_rag_service.cache_clear()
    reranker = object()
    constructed = {}

    class FakeHybridRetriever:
        def __init__(self, **kwargs):
            constructed.update(kwargs)

        def retrieve(self, **_kwargs):
            return []

    monkeypatch.setattr("app.services.rag.rag_service.VectorStore", Mock())
    monkeypatch.setattr(
        "app.services.rag.rag_service.get_embedding_service", lambda: "embedder"
    )
    monkeypatch.setattr(
        "app.services.rag.rag_service.CrossEncoderReranker", lambda: reranker
    )
    monkeypatch.setattr(
        "app.services.rag.rag_service.HybridRetriever", FakeHybridRetriever
    )
    monkeypatch.setattr(
        "app.services.rag.rag_service.OllamaClient", lambda: Mock()
    )

    try:
        service = create_rag_service()
        assert constructed["reranker"] is reranker
        assert constructed["candidate_k"] == 15
        assert service.top_k == 7
    finally:
        create_rag_service.cache_clear()
