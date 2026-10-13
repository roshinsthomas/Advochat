# Advocate Chatbot

A full-stack legal document question-answering application built with Django REST Framework, React, MySQL, ChromaDB, and OpenAI.

The application uses Retrieval-Augmented Generation (RAG) to find relevant passages from an indexed Indian Penal Code document and generate answers with source citations. It supports natural-language questions, explicit section lookups, and follow-up questions within saved conversations.

> This project uses a historical IPC document for educational purposes. Its answers should not be treated as current legal advice.

## Features

- User registration and JWT authentication.
- Access-token refresh.
- User-specific saved conversations.
- Follow-up questions using recent conversation context.
- Semantic retrieval using MiniLM embeddings and ChromaDB.
- Cross-encoder reranking of retrieved passages.
- Exact metadata lookup for explicitly requested section numbers.
- AI-generated answers with source references.
- Expandable source passages with section numbers and PDF page references.
- Instructions for handling unrelated questions and insufficient source material.
- React interface styled with Bootstrap and custom CSS.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, Bootstrap, CSS |
| Backend | Python, Django, Django REST Framework |
| Authentication | Simple JWT |
| Relational database | MySQL |
| Vector database | ChromaDB |
| PDF extraction | pypdf |
| Tokenization | Hugging Face Tokenizers |
| Embeddings | ChromaDB default ONNX MiniLM embedding function |
| Reranking | Sentence Transformers CrossEncoder |
| Answer generation | OpenAI API |

MySQL stores users, conversations, and messages. ChromaDB stores document chunks, embeddings, and source metadata.

## How It Works

### Document indexing

1. Extract text from the PDF.
2. Clean page content and separate footnotes.
3. Identify individual IPC sections.
4. Split sections into token-limited chunks while preserving useful structure.
5. Generate embeddings and store the chunks with metadata in ChromaDB.

### Answer generation

1. The frontend sends an authenticated question to Django.
2. Django loads recent messages when an existing conversation is selected.
3. Explicit section requests use exact section metadata lookup.
4. Other questions use semantic retrieval, with contextual rewriting for follow-ups when needed.
5. A cross-encoder reranks semantic search candidates.
6. Retrieved passages are supplied to the answer-generation model.
7. The answer and cited sources are returned to the frontend.
8. The question and answer are saved in MySQL.

Conversation history provides context for follow-up questions. Retrieved document passages provide the evidence for legal answers.

## Project Structure

- `backend/`
  - `manage.py` — Django command-line entry point.
  - `requirements.txt` — Python dependencies.
  - `.env.example` — Environment variable template.
  - `config/` — Django settings and project URLs.
  - `chatbot/` — Models, serializers, API views, routes, and tests.
    - `migrations/` — Database migrations.
    - `services/` — Document processing, retrieval, answer generation, and conversation logic.
  - `rebuild_search.py` — Builds the structured search collection.
  - `check_retrieval.py` — Manual retrieval diagnostics.
  - `data/` — Local PDF and ChromaDB storage.
- `frontend/`
  - `src/components/` — React components.
  - `src/services/` — API communication.
  - `src/App.jsx` — Main application interface.
  - `src/index.css` — Application styling.
  - `vite.config.js` — Frontend development configuration.
  - `package.json` — Frontend dependencies and scripts.

## Local Setup

The commands below use Windows PowerShell.

### Prerequisites

- Python 3.13.
- Node.js and npm.
- MySQL 8.0.
- Git.
- An OpenAI API key with access to the configured model.
- The IPC PDF used by the indexing pipeline.

Internet access is needed for initial model downloads and OpenAI requests.

### 1. Clone the repository

Replace `<repository-url>` with this repository's GitHub URL.

```powershell
git clone <repository-url> Advocate_Chatbot
cd Advocate_Chatbot
```

### 2. Create a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

### 3. Create the MySQL database

Run the following through MySQL Workbench or the MySQL command-line client using an account with database and user-management permissions.

Replace the example password before running it.

```sql
CREATE DATABASE advocate_chatbot CHARACTER SET utf8mb4;

CREATE USER 'advocate_app'@'localhost'
IDENTIFIED BY 'replace_with_a_strong_password';

GRANT ALL PRIVILEGES ON advocate_chatbot.*
TO 'advocate_app'@'localhost';
```

If the database and application user already exist, reuse them.

### 4. Configure environment variables

```powershell
Copy-Item backend/.env.example backend/.env
```

Update `backend/.env`:

```dotenv
DJANGO_SECRET_KEY=replace_with_your_django_secret_key
DJANGO_DEBUG=True

DB_NAME=advocate_chatbot
DB_USER=advocate_app
DB_PASS=replace_with_your_database_password
DB_HOST=localhost
DB_PORT=3306

OPENAI_API_KEY=replace_with_your_openai_api_key
OPENAI_MODEL=replace_with_your_accessible_model_id
```

Generate a Django secret key with:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Keep actual credentials in `.env`. Commit only the placeholder `.env.example`.

### 5. Apply database migrations

```powershell
cd backend
python manage.py migrate
```

### 6. Prepare and index the document

Place the expected IPC PDF at:

```text
backend/data/raw/ipc.pdf
```

The current cleaning and splitting logic is tailored to the project's source PDF. A different edition or layout may require changes to the extraction configuration.

From `backend`, run:

```powershell
python manage.py shell -c "exec(open('rebuild_search.py', encoding='utf-8').read())"
```

The script prints the generated collection name and stored chunk count.

Ensure `COLLECTION_NAME` in `chatbot/services/semantic_search.py` matches the collection produced by the rebuild script.

The original development build produced 901 chunks. Counts and collection names may change when the source or chunking logic changes.

The source PDF and generated ChromaDB files are local data and are not included in the repository.

### 7. Start the backend

From `backend`:

```powershell
python manage.py runserver
```

Backend address:

```text
http://127.0.0.1:8000/
```

### 8. Start the frontend

Open a second terminal from the project root:

```powershell
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite.

During development, Vite proxies `/api/` requests to the Django backend.

## Using the Application

1. Register an account.
2. Sign in.
3. Start a new conversation.
4. Ask a question or request a particular section.
5. Expand the source references to inspect the supporting passages.
6. Ask follow-up questions within the same conversation.
7. Reopen saved conversations from the sidebar.

Example questions:

- “Someone secretly took my phone without my permission.”
- “Explain Section 324.”
- “Is there a Section 321?”
- “Explain that in simpler words.”

Retrieval quality varies with the question and available source material.

## API Endpoints

All paths below begin with `/api/`.

| Method | Endpoint | Purpose | Authentication |
|---|---|---|---|
| GET | `health/` | Basic application health response | Public |
| POST | `auth/register/` | Register a user | Public |
| POST | `auth/login/` | Obtain JWT tokens | Public |
| POST | `auth/refresh/` | Refresh an access token | Refresh token in request |
| GET | `auth/me/` | Retrieve the current user | Bearer token |
| POST | `search/` | Retrieve document passages | Public |
| POST | `chat/` | Generate and save an answer | Bearer token |
| GET | `conversations/` | List the user's conversations | Bearer token |
| POST | `conversations/` | Create a conversation | Bearer token |
| GET | `conversations/<uuid>/` | Retrieve a conversation and messages | Bearer token |
| PATCH | `conversations/<uuid>/` | Update a conversation title | Bearer token |
| DELETE | `conversations/<uuid>/` | Delete a conversation | Bearer token |

Protected requests use:

```text
Authorization: Bearer <access_token>
```

### Example chat request

Send a POST request to `/api/chat/`:

```json
{
  "query": "Explain Section 324.",
  "limit": 3
}
```

To continue a conversation, include its returned ID:

```json
{
  "query": "Explain that in simpler words.",
  "limit": 3,
  "conversation_id": "<conversation-uuid>"
}
```

Responses include the answer, conversation ID, and cited source information.

## Tests

From `backend`, with the virtual environment activated:

```powershell
python manage.py test chatbot
```

The existing tests cover selected health, search, chat, and section-lookup behavior. External services are mocked in relevant API tests.

These tests do not establish semantic retrieval accuracy. Broader integration tests and a retrieval evaluation dataset are planned.

## Known Limitations

- The indexed source is a historical IPC document, not a comprehensive current legal database.
- Semantic retrieval can return irrelevant or incomplete results.
- PDF extraction can introduce spacing and formatting errors.
- Some indexed chunks overlap, which can cause repeated text in source passages.
- Follow-up processing uses a limited window of recent messages.
- Citations make supporting passages inspectable but do not guarantee answer correctness.
- Exact lookup depends on the section being correctly extracted and indexed.
- The application currently targets local development; production deployment and hardening remain future work.

## Future Improvements

- Evaluate retrieval against a curated set of questions and expected sections.
- Improve semantic ranking and handling of insufficient evidence.
- Expand the document collection with verified sources and clear version metadata.
- Improve answer formatting and conversation management controls.
- Add broader authentication, ownership, persistence, and failure-handling tests.
- Add production configuration, request limits, and operational monitoring.
- Set up automated CI/CD.
- Deploy the application with persistent database and vector storage.
- Explore PostgreSQL and alternative retrieval approaches as learning extensions.

## Project Status

The core local application is implemented, including authentication, saved conversations, contextual follow-ups, document retrieval, and cited AI answers.

Further retrieval improvements, testing, interface enhancements, and deployment work are planned.