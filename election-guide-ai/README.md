# 🗳️ Election Guide AI

A chat-based AI assistant that helps citizens understand the election process, check eligibility, register to vote, prepare documents, and cast their ballot. Built with **FastAPI**, powered by **Google Gemini 1.5 Flash**, and deployable on **Google Cloud Run**.

## ✨ Features

- 🤖 **AI-Powered Chat** — Natural language Q&A about elections via Google Gemini
- 🧭 **Guided Voting Wizard** — Interactive 4-step flow (Eligibility → Registration → Documents → Voting)
- 📅 **Election Timeline** — Visual timeline of key election milestones
- 🔒 **Security** — Input sanitisation, rate limiting, SQL injection protection, security headers
- ♿ **Accessibility** — WCAG compliant, keyboard navigable, ARIA labels, skip-to-content
- 📱 **Responsive** — Mobile-first design with sidebar (desktop) / tabs (mobile)
- 🌐 **Multilingual Ready** — Language selector with localStorage persistence

## 📁 Project Structure

```
election-guide-ai/
├── main.py                    # FastAPI entry point
├── routes/
│   ├── chat.py                # POST /api/chat, POST /api/guided-step
│   └── health.py              # GET /health
├── controllers/
│   └── chat_controller.py     # Request orchestration logic
├── services/
│   ├── gemini_service.py      # Google Gemini API integration
│   └── intent_service.py      # Intent detection + guided wizard
├── utils/
│   ├── sanitizer.py           # Multi-layer input sanitisation
│   └── response_formatter.py  # Response formatting utilities
├── static/
│   └── index.html             # Complete chat UI (single file)
├── tests/
│   ├── test_chat.py           # API + integration tests
│   └── test_sanitizer.py      # Sanitiser unit tests
├── Dockerfile                 # Cloud Run deployment image
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── README.md
```

## 🚀 Local Setup

### Prerequisites
- Python 3.11+
- A Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### Steps

```bash
# 1. Clone the repository
git clone <repo-url> && cd election-guide-ai

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run the development server
uvicorn main:app --reload --port 8080

# 6. Open http://localhost:8080 in your browser
```

## 📡 API Endpoints

### `POST /api/chat`
Send a chat message and receive an AI response.

**Request:**
```json
{
  "message": "How do I register to vote?",
  "session_id": "test123",
  "lang": "en"
}
```

**Response:**
```json
{
  "reply": "📋 How to Register to Vote\n1. Visit your local election commission...",
  "intent": "registration",
  "guided_step": null
}
```

### `POST /api/guided-step`
Get a specific guided wizard step.

**Request:** `{ "step": 2 }`

### `GET /health`
**Response:** `{ "status": "ok", "version": "1.0.0" }`

### cURL Examples

```bash
# Chat message
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I register to vote?", "session_id": "test123", "lang": "en"}'

# Guided step
curl -X POST http://localhost:8080/api/guided-step \
  -H "Content-Type: application/json" \
  -d '{"step": 1}'

# Health check
curl http://localhost:8080/health
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --tb=short
```

### Test Coverage
| Test | Description |
|------|-------------|
| Valid message → 200 | POST /api/chat returns reply |
| Empty message → 422 | Pydantic validation rejects empty input |
| Message > 500 chars → 422 | Length validation enforced |
| XSS payload sanitised | `<script>alert(1)</script>` is stripped |
| Health check → 200 | GET /health returns `{"status": "ok"}` |
| HTML stripping | `<b>hello</b>` → `hello` |
| Intent detection | "how do I vote" → `voting_process` |
| SQL injection blocked | `DROP TABLE` raises ValueError |
| Guided steps 1-4 | Each step returns correct content |
| Security headers | X-Content-Type-Options, X-Frame-Options present |

## ☁️ Google Cloud Run Deployment

```bash
# Step 1: Set up project
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com

# Step 2: Build and push Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/election-guide-ai

# Step 3: Deploy to Cloud Run
gcloud run deploy election-guide-ai \
  --image gcr.io/YOUR_PROJECT_ID/election-guide-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key_here \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10

# Step 4: Get your live URL
gcloud run services describe election-guide-ai --format='value(status.url)'
```

## 🔐 Security Features

- **Input Sanitisation** — HTML tag stripping (bleach), SQL injection detection, character escaping
- **Rate Limiting** — 20 requests/minute per IP via slowapi
- **CORS** — Configurable allowed origins via environment variable
- **Security Headers** — X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy
- **No Hardcoded Secrets** — All sensitive values from environment variables

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11 + FastAPI |
| AI | Google Gemini 1.5 Flash (REST API) |
| Frontend | Vanilla HTML/CSS/JS (single file) |
| Security | bleach, slowapi, Pydantic validation |
| Testing | pytest + pytest-asyncio |
| Deployment | Docker + Google Cloud Run |

## 📄 License

MIT
