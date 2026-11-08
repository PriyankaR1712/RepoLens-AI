# RepoLens AI

**An AI-powered repository understanding and debugging assistant built around repository-aware Retrieval-Augmented Generation (RAG).**

RepoLens AI is being developed to help developers understand unfamiliar codebases, ask questions about repository code, and investigate errors with answers grounded in source files and line-level context.

> **Development status:** Core repository ingestion, source-code parsing, and structure-aware chunking are implemented. Embedding generation, vector storage, retrieval, RAG responses, and the frontend are planned next.

## Project goals

- Import repositories from public GitHub URLs and ZIP uploads.
- Filter generated, binary, and irrelevant files before analysis.
- Identify supported programming languages and extract code structure.
- Retrieve relevant code using semantic and keyword-based search.
- Provide repository-aware Q&A and debugging assistance with source citations.

## Implemented so far

### Repository ingestion
- Validate public GitHub repository URLs.
- Retrieve repository metadata and recursive file structure.
- Filter unsupported, generated, and irrelevant files.
- Detect supported languages.
- Download supported source files with per-file and total-size limits.
- Report successful, partial, and failed ingestion outcomes.

### Code parsing
- **Python:** built-in `ast` parser extracts classes, functions, methods, nested functions, arguments, and source line ranges.
- **JavaScript, TypeScript, TSX, Java:** Tree-sitter-based parser extracts supported code symbols and source locations.
- Parser results use a consistent structure and report parsing errors.

### Structure-aware chunking
- Create chunks with file path, language, symbol, parent class, line range, content, and chunk index metadata.
- Avoid duplicate class/method chunks for classes that fit within the configured size.
- Split oversized functions and classes while retaining method and class-context information.

### Current verification
- **70 automated tests passing** at the latest recorded full-suite run.
- Tests cover ingestion, filtering, language detection, source downloading, parsing, chunking, and parser-to-chunker integration.

## Technology stack

| Area | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Database layer | SQLAlchemy, PostgreSQL |
| Schema migrations | Alembic |
| GitHub ingestion | PyGithub |
| Python parsing | Python `ast` |
| Multi-language parsing | Tree-sitter |
| Testing | Pytest |
| Planned embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Planned vector store | ChromaDB |
| Planned retrieval | BM25 + vector search + Cross-Encoder reranking |
| Planned frontend | React, TypeScript, Tailwind CSS |
| Planned local LLM runtime | Ollama |

## High-level workflow

```text
Public GitHub repository
          |
          v
 Repository metadata and file discovery
          |
          v
 File filtering and language detection
          |
          v
 Source file downloading
          |
          v
 Python AST / Tree-sitter parsing
          |
          v
 Structure-aware code chunking
          |
          v
 [Next] Embeddings and ChromaDB indexing
          |
          v
 [Planned] Hybrid retrieval, reranking, and RAG
          |
          v
 [Planned] Repository Q&A and debugging interface
```

## Repository structure

```text
RepoLens-AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   │       ├── ingestion/
│   │       ├── analysis/
│   │       └── chunking/
│   ├── migrations/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
└── README.md
```

## Getting started

### Prerequisites

- Python 3.11
- PostgreSQL
- Git

### 1. Clone the repository

```bash
git clone https://github.com/PriyankaR1712/RepoLens-AI.git
cd RepoLens-AI
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

```powershell
cd backend
pip install -r requirements.txt
```

### 4. Configure the environment

Create `backend/.env` using `backend/.env.example` as the reference. Set the PostgreSQL connection details for your local environment. Do not commit `.env` or share database credentials.

Create the PostgreSQL database configured in your environment before running migrations.

### 5. Apply database migrations

```powershell
alembic upgrade head
```

### 6. Start the API

```powershell
uvicorn app.main:app --reload
```

The API runs locally at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Run tests

From the `backend/` directory, with the virtual environment activated:

```powershell
python -m pytest -v
```

The latest recorded full-suite result is **70 passed**. Run the suite again after making changes to verify the current checkout.

## Roadmap

- [ ] Generate code-chunk embeddings with Sentence Transformers.
- [ ] Store embeddings and metadata in ChromaDB.
- [ ] Implement semantic retrieval.
- [ ] Add BM25 keyword retrieval and hybrid result fusion.
- [ ] Add Cross-Encoder reranking.
- [ ] Build repository-aware Q&A with grounded file and line citations.
- [ ] Add stack-trace parsing and debugging assistance.
- [ ] Add basic code relationship analysis.
- [ ] Build the React + TypeScript frontend.
- [ ] Evaluate retrieval and answer quality.
- [ ] Prepare a public demo deployment.

## Project scope

The project is focused on practical repository understanding and debugging. Planned capabilities are intentionally marked as planned above; they should not be considered implemented until they are available and tested.

## License

A license has not yet been specified.
