# ☕ Roast & Co. — AI Support & Ordering Chatbot Platform
### Hackathon Project Specification & Documentation

---

## 1. Project Goal

**Roast & Co.** is a full-stack AI-driven e-commerce assistant built for a specialty coffee roastery that sells bags of freshly roasted coffee online.

### Primary Objectives:
1. **Grounded FAQ Support via RAG:** Answer customer inquiries about shipping, return policies, and coffee brewing methods accurately using document retrieval without hallucinating.
2. **Conversational E-Commerce:** Enable customers to seamlessly browse products, place orders, check order statuses, and cancel active orders in natural conversation.
3. **Single-turn Tool Calling Architecture:** Eliminate rigid intent classifiers in favor of native LLM tool calling (function calling), allowing the model to naturally transition between answering questions and executing actions in a single turn.
4. **Transparency & Cost Observability:** Provide store administrators with token usage statistics, cost breakdowns (per-user, per-chat), and audit visibility into every AI decision and customer conversation.

---

## 2. System Architecture & Design Decisions

```
                           ┌────────────────────────┐
                           │   Web Client (Jinja2   │
                           │   + Vanilla JS Fetch)  │
                           └───────────┬────────────┘
                                       │ HTTP / JSON
                                       ▼
                           ┌────────────────────────┐
                           │   Flask App Factory    │
                           │   Blueprints & Auth    │
                           └───────────┬────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
  ┌───────────────────────────┐                 ┌───────────────────────────┐
  │  services/chat_agent.py   │                 │     services/rag.py       │
  │  - Gemini SDK Integration │                 │  - Sentence Chunking      │
  │  - Function Declarations  │                 │  - Local E5-Small Embed   │
  │  - DB Tool Handlers       │◄───────────────┤  - Cosine Vector Search   │
  │  - Write-time Cost Calc   │  (Search Tool)  │  - PDF/TXT/MD Parser      │
  └─────────────┬─────────────┘                 └─────────────┬─────────────┘
                │                                             │
                ▼                                             ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                           SQLAlchemy Database                           │
  │  - User & Admin (Dual Auth)          - Document & DocumentChunk         │
  │  - Chat & Message (with Token Logs)  - Order (Scoped User Operations)   │
  └─────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions:

1. **Tool Calling Over Classifier Routers:**
   - *Why:* Keyword or classifier routers ("is this an FAQ or an order?") add latency, create brittle edge cases, and break multi-intent user queries (e.g., *"How long does shipping take, and can I get 2 bags of House Blend?"*).
   - *Implementation:* The LLM (`gemini-3.5-flash-lite`) is provided 4 function declarations on every request:
     - `search_knowledge_base(query)`
     - `create_order(items, shipping_address)`
     - `track_order(order_id)`
     - `cancel_order(order_id)`
   - The model inspects the conversation context, triggers tools autonomously when needed, receives structured tool responses, and crafts grounded replies.

2. **Hand-Rolled RAG Pipeline (No Heavy Frameworks):**
   - *Why:* LangChain/LlamaIndex add unnecessary abstraction layers and heavy dependency footprints. A hand-rolled RAG pipeline (~80 lines) is fast, deterministic, easy to inspect, and completely transparent to judges.
   - *Implementation:* 
     - **Embedding Model:** `intfloat/multilingual-e5-small` (384 dimensions) running locally with zero external API costs or rate limits.
     - **Retrieval:** Cosine similarity search over text chunks.
     - **Cascade Delete:** Document chunks are tied to parent documents with `cascade="all, delete-orphan"`. When an admin deletes a document, all chunk vectors are purged from the retrieval index immediately.

3. **User-Scoped Security on Tools:**
   - Tools like `track_order` and `cancel_order` enforce database queries scoped to `current_user.id`. A user can never inspect or manipulate another customer's order through the AI assistant.

4. **Write-Time Cost Calculation:**
   - Message costs (`cost_usd`) and token counts (`prompt_tokens`, `completion_tokens`) are calculated at creation time from the model's token usage metadata and saved to the database. Historical financial analytics remain accurate even if pricing rates change later.

---

## 3. What Was Implemented

| Feature Area | Implementation Details |
|---|---|
| **App Factory & Blueprints** | Modular architecture with `auth`, `chat`, `admin`, and `orders` blueprints. |
| **Authentication** | `Flask-Login` session auth with a custom compound user loader supporting both customer `User` and store `Admin` accounts. |
| **Chat Management** | Multi-conversation sidebar, chat creation, chat deletion, message history persistence, automatic title generation from first message. |
| **AI Tool Agent** | `google-genai` SDK integration with function calling, automatic multi-turn message handling, tool execution, and token accumulation. |
| **E-Commerce Order Flow** | Catalog validation (SKUs, weights, pricing), database order creation, status checks, and cancellation safeguards (can only cancel `placed` orders). |
| **RAG Knowledge Base** | Ingestion for PDF (`pypdf`), Markdown, and plain text files with sentence-aware chunking and local embeddings. |
| **Admin Dashboard** | Token analytics, cost summaries, interactive Chart.js bar chart for user usage, document upload/delete interface. |
| **Admin Audit & "View As"** | Ability for admins to view any customer's list of conversations and inspect the full message history (including tool call payloads). |
| **Seed Data** | Automated database seeding with 3 demo customers, sample orders, pre-existing chat histories, and 3 FAQ documents (shipping, returns, brewing). |

---

## 4. What Is Remaining / Future Roadmap

For production deployment beyond the hackathon scope:
1. **Live Payment Integration:** Add Stripe or PayPal webhook verification before setting order status to `placed`.
2. **Email & SMS Notifications:** Automated order confirmations and tracking updates via SendGrid / Twilio.
3. **Response Streaming:** Implement Server-Sent Events (SSE) or WebSockets to stream LLM responses token-by-token to the chat UI.
4. **PostgreSQL + pgvector Migration:** Transition from the local SQLite storage layer to PostgreSQL with the `pgvector` extension and HNSW indexing for scaling to millions of document chunks.
5. **Rate Limiting:** Implement token bucket rate limiting on chat endpoints to prevent API abuse.

---

## 5. Demo Accounts

| Role | Email | Password | Access / Role |
|---|---|---|---|
| **Customer** | `maria@example.com` | `demo123` | Active customer with past orders and chat history |
| **Customer** | `james.chen@example.com` | `demo123` | Customer with tracking inquiry history |
| **Customer** | `sarah.k@example.com` | `demo123` | Fresh customer account |
| **Admin** | `admin@roastandco.com` | `admin123` | Access to `/admin/dashboard` & `/admin/documents` |

---

## 6. How to Run the Project

### Prerequisites:
- Python 3.10+ (Python 3.11 recommended)

### Setup & Run:
```powershell
# 1. Navigate to project folder
cd "C:\Users\Student\Desktop\hackathon project"

# 2. Configure your Gemini API key in .env
# Edit .env and ensure GOOGLE_API_KEY is set:
# GOOGLE_API_KEY=your_actual_key_here

# 3. Run the development server
.\venv\Scripts\python.exe run.py
```

Open your browser at:
- **Customer Store & Chat:** [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)
- **Admin Management Portal:** [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login)

---

## 7. 2-Minute Hackathon Demo Script

1. **Login as Customer (`maria@example.com` / `demo123`):**
   - Show existing conversation history in the left sidebar.
   - **Test RAG FAQ:** Type *"What's your return policy for coffee?"* -> Notice how the bot answers using the grounded returns policy FAQ.
   - **Test Order Placement:** Type *"I'd like to order 1 bag of Ethiopian Yirgacheffe to 123 Main St, Seattle WA."* -> The bot calls `create_order`, places order `#3`, and returns the confirmation.
   - **Test Order Tracking:** Type *"Can you track order #3 for me?"* -> The bot calls `track_order` and confirms status is `placed`.
2. **Switch to Admin Portal (`admin@roastandco.com` / `admin123`):**
   - Open `/admin/dashboard`: Show live token consumption, estimated USD costs, and the Chart.js breakdown.
   - Open `/admin/documents`: Show the active FAQ files. Upload a new text file or delete an existing one to demonstrate real-time vector index updates.
   - Open `/admin/users`: Click "View Chats" for Maria to demonstrate the read-only audit log.
