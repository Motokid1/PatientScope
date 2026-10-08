# Clarity - Groq API edition

A patient-specific medical records chatbot using React + Vite, FastAPI, Groq,
local Hugging Face embeddings, and MongoDB Atlas. It answers from each account's
uploaded records with citations. It is a record assistant, not a diagnostic tool.

The source directory contains only:

```text
clarity/
  frontend/     React source, public assets, package files and Vite configuration
  backend/      API source, glossary configuration, dependency files and .env.example
  README.md     Setup and run commands
```

No setup scripts, Docker files, reports, duplicate documentation, tests, model
weights, virtual environments, node_modules, or compiled frontend are included.
The original working project is preserved separately. Running the commands below
creates the necessary generated files inside frontend or backend, never at root.

## 1. Requirements and backend dependencies

Use Windows PowerShell with Python 3.11 and Node.js 22.12 or newer.
Replace the path with your extracted project location.

```powershell
cd "D:\Projects - AI\Clarity\backend"
py -3.11 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip "setuptools>=77.0.3"
& ".\.venv\Scripts\python.exe" -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
& ".\.venv\Scripts\python.exe" -m pip install -c requirements.lock -c requirements-huggingface.lock -e ".[huggingface]"
& ".\.venv\Scripts\python.exe" -m pip install -c requirements.lock https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
```

The virtual environment isolates Python packages. CPU PyTorch and sentence-transformers
provide local embeddings. The spaCy model supports personal identifier masking.
Using the virtualenv executable directly does not require PowerShell activation.

## 2. Configure backend secrets

If you already have backend/.env, preserve it and skip copying the example.
For a fresh installation:

```powershell
Copy-Item .env.example .env
& ".\.venv\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(48))"
notepad .env
```

Set MONGODB_URI to your Atlas connection string, JWT_SECRET to the generated
value, and GROQ_API_KEY to your own Groq key. Keep these only in backend/.env.
Allow your current IP in Atlas Network Access and give the database user the
permissions required to create collections and indexes.

The defaults use sentence-transformers/all-MiniLM-L6-v2 with 384 dimensions.
No Hugging Face token is needed for this public model. LLM_API_KEY,
HUGGINGFACE_TOKEN and EMBEDDING_API_KEY can remain empty.

For an existing database, preserve VECTOR_INDEX_NAME from your existing .env.
Never mix vectors from different embedding models in one index; select a new
index and re-upload records when changing embedding models.

## 3. Download and cache the embedding model

Run from backend. This command downloads only model weights; it sends no records.

```powershell
& ".\.venv\Scripts\python.exe" -c "from app.config import Settings; from app.services.embeddings import HuggingFaceEmbeddingService; settings=Settings(); settings.embedding_local_files_only=False; HuggingFaceEmbeddingService(settings).client(); print('Model cached and embedding dimensions verified.')"
```

It creates the configured models/embeddings cache. Startup and subsequent queries
use that cache with EMBEDDING_LOCAL_FILES_ONLY=true. If moving from your previous
installation, you can copy its backend/models folder instead of downloading again.

## 4. Create MongoDB indexes

Run this explicit command block from backend. It creates the unique patient email
index, document ownership indexes, and the patient-filtered Atlas vector index.
It checks an existing vector index instead of replacing it or deleting records.

```powershell
@'
import asyncio
from pymongo.operations import SearchIndexModel
from app.config import Settings
from app.database.mongodb import MongoDatabase

async def main():
    settings = Settings()
    database = MongoDatabase(settings)
    try:
        await database.ping()
        await database.ensure_indexes()
        definition = {"fields": [
            {"type": "vector", "path": "embedding", "numDimensions": settings.embedding_dimensions, "similarity": "cosine"},
            {"type": "filter", "path": "patient_id"},
            {"type": "filter", "path": "document_type"},
            {"type": "filter", "path": "document_id"}
        ]}
        cursor = await database.db.medical_chunks.list_search_indexes()
        indexes = await cursor.to_list(None)
        existing = next((i for i in indexes if i["name"] == settings.vector_index_name), None)
        if existing:
            stored = existing.get("latestDefinition") or existing.get("definition") or {}
            fields = stored.get("fields", [])
            vector = next((f for f in fields if f.get("type") == "vector" and f.get("path") == "embedding"), None)
            filters = {f.get("path") for f in fields if f.get("type") == "filter"}
            if not vector or vector.get("numDimensions") != settings.embedding_dimensions or vector.get("similarity") != "cosine" or not {"patient_id", "document_type", "document_id"} <= filters:
                raise ValueError("Existing index is incompatible. Use a new VECTOR_INDEX_NAME; do not overwrite the old index.")
            print("Existing vector index verified. Queryable:", existing.get("queryable"))
        else:
            name = await database.db.medical_chunks.create_search_index(SearchIndexModel(definition=definition, name=settings.vector_index_name, type="vectorSearch"))
            print("Created vector index:", name)
        print("Wait until Atlas shows the vector index as queryable before asking questions.")
    finally:
        await database.close()

asyncio.run(main())
'@ | & ".\.venv\Scripts\python.exe" -
```

This pipes the visible Python code directly to Python; it does not create a .py
setup script. Run once on a fresh database or after deliberately changing index
configuration. Normal server startup also ensures the regular database indexes.

## 5. Start the backend

```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Keep this terminal open. API documentation is at http://127.0.0.1:8000/docs.
For subsequent runs, this is the only backend command required.

## 6. Start the frontend in a second terminal

```powershell
cd "D:\Projects - AI\Clarity\frontend"
npm ci
npm run dev
```

npm ci creates frontend/node_modules using the pinned package lock. Open
http://localhost:5173. Vite forwards API requests to the backend on port 8000.
For subsequent runs, only npm run dev is needed. Never put backend keys in React.

## 7. Optional production frontend build

From frontend, run:

```powershell
npm run build
```

This creates frontend/dist. Restart the backend, then open http://localhost:8000.
The source archive excludes dist because it is generated by this command.
React source changes require another build. Development on port 5173 does not
require a production build.

## Using the latest fixes

Upload PDF, DOCX, or TXT records and wait for Completed. Detect from record
prefers document headings over incidental mentions of medication or lab values.
Previously saved other classifications require deleting and re-uploading those
original files to be detected again; no background migration edits your records.

Use All document types for a complete overview. Example:
"Summarise all my uploaded clinical records, including diagnoses, medications,
lab trends, investigations, encounters, and follow-up plans."

Explicit summary requests bypass top-K vector search and the specific-question
relevance grader. They still require patient ownership, completed documents,
source citations, privacy checks, and answer validation. The summary context
limit is MAX_CONTEXT_CHARS, with at most 30 documents and 1000 candidate chunks.
Exceeding it returns SUMMARY_TOO_LARGE; select a document type or narrow the request.
Groq limits, network failures and unavailable Atlas indexes can still cause errors.

## What gets created

| Command | Created or changed |
|---|---|
| py -3.11 -m venv .venv | backend/.venv |
| pip install -e | Installed packages and backend package metadata |
| Copy-Item .env.example .env | backend/.env containing your configuration |
| Model cache command | backend/models/embeddings by default |
| Index command | Indexes in your configured Atlas database |
| npm ci | frontend/node_modules |
| npm run build | frontend/dist |
| Python imports | __pycache__ bytecode caches as needed |

These generated items are needed for installation, execution, or caching; none
are included in the clean source ZIP. Keep backend/.env private when sharing.

## API edition notes

This project uses Groq for answer generation. Set GROQ_API_KEY only in backend/.env.
The default generation model is openai/gpt-oss-20b with strict JSON-schema output.
Hugging Face embeddings remain local. MongoDB Atlas stores and searches records.
No local language-model server is needed.

Large summaries remain bounded by MAX_CONTEXT_CHARS and a maximum of 30 documents.
Keep MAX_CONTEXT_CHARS=24000 initially. Increasing it does not increase Groq's
request allowance. HTTP 413 is reported as LLM_REQUEST_TOO_LARGE, HTTP 429 as
LLM_RATE_LIMIT, and timeouts as LLM_TIMEOUT. Narrow the request when necessary.
This edition does not yet implement hierarchical summaries for unlimited records.

Validation for this packaging update: Python source parsed, provider defaults and
archive integrity checked. Existing runtime tests were not rerun and no live Groq
or Atlas requests were made. Keep your existing backend/.env when replacing files.
