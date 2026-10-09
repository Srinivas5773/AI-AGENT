# NEC Campus Copilot AI

**Narasaraopeta Engineering College (Autonomous), Andhra Pradesh**
*AI-Powered Academic Support, Study Assistant, RAG Document Retrieval, Memory & Human Escalation System*

---

## 🌟 Overview & Key Capabilities

**NEC Campus Copilot AI** is a competition-ready AI application tailored for Narasaraopeta Engineering College (NEC), Andhra Pradesh. It combines genuine **Groq Tool Calling** (`llama-3.1-8b-instant`), **RAG Document Vector Retrieval**, **Session Memory**, **Interactive Study Mode**, and a **Persistent SQLite Human Escalation Portal**.

### 🚀 Key Features

1. **NEC Official Resources & RAG Vector Engine**:
   - Ingests official NEC academic documents:
     - `https://www.nrtec.in/` (College Profile, NAAC A+ Accreditation, AICTE Approval, EAPCET Code: `NSPE`)
     - `https://www.nrtec.in/academic-calendar/` (Official R20/R23 Academic Calendar)
     - `https://www.nrtec.in/syllabus-2/` (Autonomous Regulations R20/R23 Syllabi, CS301 DBMS Units 1-5)
     - `https://www.nrtec.in/notifications/` (Exam Guidelines, Attendance Rules & Calculator Policies)
   - Returns explicit **Source Citations** with page numbers and clickable links.
2. **Interactive Study Mode Hub**:
   - 💡 **Explain Simply**: Explains complex topics in easy, plain language.
   - 🛠️ **Practical Example**: Provides real-world engineering applications.
   - 📝 **5 Practice Questions**: Generates 5 practice questions with answer keys (labeled clearly as Practice Questions, not official exam papers).
   - 🎴 **Flashcards**: Generates front/back concept revision cards.
   - 📌 **Summarize Notes**: Condenses retrieved material into 4 key bullet points.
3. **Conversational Intent Handling**:
   - Responds to greetings ("hi", "hello"), thanks, and chit-chat with **0 tool executions** and **0 escalation tickets created**.
4. **Session Conversation Memory**:
   - Preserves academic context across follow-up queries (e.g. *"Explain DBMS syllabus"* followed by *"What about Unit 3?"*).
5. **Persistent Human Escalation (SQLite DB)**:
   - Escalates queries requiring bursar authorization, financial aid waivers, or explicit human representative requests.
   - Prevents duplicate ticket creation.
   - Includes Operator Admin Portal with ticket status filter (`pending`, `reviewed`, `resolved`).
6. **100% Automated Test Suite (40 Passing Tests)**:
   - Comprehensive pytest suite covering tools, RAG, memory, escalation, study mode, intent routing, and API endpoints.

---

## 📁 Final Project Architecture

```
student-exam-assistant/
├── backend/
│   ├── main.py                # FastAPI server (/health, /chat, /study-mode, /upload, /reset, /escalations)
│   ├── agent.py               # Groq LLM tool-calling loop, RAG citations, Intent router
│   ├── study_mode.py          # Study Mode Content Generator (5 Actions)
│   ├── intent.py               # Conversational Intent Classifier (Greetings, Thanks)
│   ├── tools.py               # 5 custom tools + Groq JSON schema definitions
│   ├── rag.py                 # Document Ingestion, PDF/DOCX/TXT/CSV parsers, Vector Store
│   ├── memory.py              # Isolated Session Memory Manager
│   ├── escalation.py          # SQLite DB Human Escalation Module
│   ├── data_loader.py         # CSV & TXT dataset loader
│   ├── config.py              # Environment configuration & path resolver
│   ├── requirements.txt       # Python dependencies
│   ├── .env                   # Environment config with active Groq API Key
│   └── data/                  # Persistent data directory
│       ├── docs/              # NEC Documents (nec_college_info.txt, nec_academic_calendar.txt, nec_syllabi_r20_r23.txt)
│       ├── escalations.db     # SQLite DB for Escalation Tickets
│       └── vector_store.json  # RAG Vector Store metadata
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # NEC Campus Copilot AI React Dashboard
│   │   ├── App.css            # Responsive Navy/Cyan styling & sidebar navigation
│   │   └── main.jsx           # Vite React entry point
│   ├── index.html             # HTML Shell
│   ├── package.json           # Node dependencies
│   └── vite.config.js         # Vite dev server configuration
├── tests/
│   ├── test_study_mode.py     # Unit tests for 5 Study Mode actions
│   ├── test_regression_fixes.py # Regression tests for intent routing, memory, escalation deduplication
│   ├── test_tools.py          # Unit tests for 5 tools
│   ├── test_rag.py            # Unit tests for RAG parsing & citations
│   ├── test_memory.py         # Unit tests for session memory
│   ├── test_escalation.py     # Unit tests for SQLite ticket creation
│   ├── test_agent.py          # Multi-step agent loop tests
│   └── test_api.py            # Integration tests for FastAPI endpoints
├── .gitignore                 # Git ignore rules
└── README.md                  # System Documentation
```

---

## 🚀 How to Run Locally

### 1. Start Backend Server
```bash
cd backend
python -m uvicorn backend.main:app --reload --port 8000
```
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Start Frontend Dashboard
In a second terminal:
```bash
cd frontend
npm run dev
```
- Access Portal: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Automated Test Execution (40 Passed Tests)

Run pytest:
```bash
python -m pytest tests/ -v
```

**Result**: `40 passed, 1 warning in 48.63s` (100% Pass Rate).
