# ☕ Roast & Co. — Specialty Coffee AI Concierge Platform

## Problem Statement
> **Build a website for a business that has a chatbot handling two things: customer support (FAQ) and order placement/tracking/cancellation. The system should feel like a real product, not a demo script.**

---

**Roast & Co.** is a production-grade specialty coffee roastery web application combining grounded customer support via RAG with conversational e-commerce order management via LLM native tool calling, backed by full administrator observability into token consumption, financial costs, and audit logs.

> 📖 **Full Specification & Architecture Document:** See [PROJECT_DOCS.md](PROJECT_DOCS.md) for detailed architectural diagrams, design decisions, and demo scripts.

---

## Quick Start

### 1. Set Your Gemini API Key
Edit the `.env` file in this directory:
```env
SECRET_KEY=roast-and-co-secret-key-12345
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 2. Run the Application
```powershell
.\venv\Scripts\python.exe run.py
```
Open your browser at **http://127.0.0.1:5000**.

---

## Demo Accounts

| Role | Email | Password | URL |
|---|---|---|---|
| Customer | `maria@example.com` | `demo123` | [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login) |
| Customer | `james.chen@example.com` | `demo123` | [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login) |
| Admin | `admin@roastandco.com` | `admin123` | [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login) |

---

## Core Product Capabilities

- **Single-Model Native Tool Calling:** Powered by Google Gemini with tools (`search_knowledge_base`, `create_order`, `track_order`, `cancel_order`) without rigid intent classifiers.
- **Local RAG Pipeline:** Sentence chunking + local HuggingFace embeddings (`intfloat/multilingual-e5-small`) with exact `passage:` / `query:` prefixing for fast, cost-free vector similarity search.
- **True Cascade Deletion:** Deleting a document from the admin panel removes all related vector chunks from the retrieval index immediately.
- **Admin Observability & Audit:** Real-time token usage, per-user/per-chat write-time cost metrics, Chart.js visualizations, document manager, and "View-As" user conversation inspection.
- **Bespoke Artisanal UI:** Fraunces serif + Space Grotesk typography, warm coffee roastery palette (`#F5EFE6`, `#3B2A20`, `#C1652F`), fixed viewport layout, collapsible sidebar, and micro-animations.
