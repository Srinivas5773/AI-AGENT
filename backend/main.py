import logging
import shutil
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import (
    DATA_DIR,
    FRONTEND_ORIGIN,
    GROQ_API_KEY,
    GROQ_MODEL,
    get_schedule_file_path,
    get_courses_file_path,
    get_rules_file_path,
)
from backend.agent import run_agent
from backend.rag import get_rag_engine, DOCS_DIR
from backend.memory import memory_manager
from backend.escalation import (
    get_all_tickets,
    update_ticket_status,
    authenticate_user,
    register_student,
    create_escalation_ticket,
    get_student_tickets,
    mark_ticket_notified,
    MEDIA_DIR,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.main")

app = FastAPI(
    title="NEC Campus Copilot AI API",
    description="Agentic Academic Support & Study Assistant for Narasaraopeta Engineering College (Autonomous).",
    version="3.0.0",
)

@app.get("/", response_model=dict)
def health_check():
    """Simple health check endpoint returning service status."""
    return {"status": "ok", "message": "NEC Campus Copilot API is running"}

origins = [
    FRONTEND_ORIGIN,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static media attachments folder for student file downloads
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media-files", StaticFiles(directory=MEDIA_DIR), name="media-files")


# Pydantic Request & Response Models
class LoginRequest(BaseModel):
    name_or_email: str = Field(..., description="Student Name/Email or Admin VST")
    password: str = Field(..., description="Password (Admin: 577577)")


class RegisterRequest(BaseModel):
    name: str = Field(..., description="Student Name")
    email: str = Field(..., description="Student Email")
    mobile: str = Field(..., description="Mobile Number")
    password: str = Field(..., description="Password")


class ContactAdminRequest(BaseModel):
    student_name: str = Field(..., description="Student Name")
    email: str = Field(..., description="Student Email")
    mobile: str = Field(..., description="Mobile Number")
    question: str = Field(..., description="Query / Issue Description")
    reason: Optional[str] = Field(default="Direct Student Contact Form Submission", description="Reason")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Student's academic question.")
    session_id: Optional[str] = Field(default="default_session", description="Unique session ID for conversation memory.")
    student_name: Optional[str] = Field(default="Student", description="Student Name")
    email: Optional[str] = Field(default="student@nec.edu", description="Student Email")
    mobile: Optional[str] = Field(default="N/A", description="Student Mobile")


class ChatResponse(BaseModel):
    answer: str
    tools_used: List[str]
    citations: List[str] = []
    success: bool
    iterations: int = 1
    session_id: str = "default_session"
    mode: str = "groq_api"
    error: Optional[str] = None


class ResetRequest(BaseModel):
    session_id: str = Field(default="default_session", description="Session ID to clear memory.")


class StudyModeRequest(BaseModel):
    action: str = Field(..., description="Study action: 'explain_simply', 'practical_example', 'practice_questions', 'flashcards', 'summarize_notes'")
    topic: str = Field(..., description="Study topic or subject name.")
    context_text: Optional[str] = Field(default=None, description="Optional RAG context text.")


class TicketStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New status: 'pending', 'reviewed', or 'resolved'")
    resolution_notes: Optional[str] = Field(default="", description="Operator resolution notes")
    media_file: Optional[str] = Field(default=None, description="Media attachment file URL/path")


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint verifying backend status, NEC metadata, RAG index, and SQLite DB."""
    sched_path, sched_synth = get_schedule_file_path()
    course_path, course_synth = get_courses_file_path()
    rules_path, rules_synth = get_rules_file_path()

    rag_engine = get_rag_engine()
    tickets = get_all_tickets()

    is_configured = bool(GROQ_API_KEY and GROQ_API_KEY.strip() not in ["your_actual_groq_api_key", ""])

    return {
        "status": "ok",
        "product_name": "NEC Campus Copilot AI",
        "institution": "Narasaraopeta Engineering College (Autonomous)",
        "groq_model": GROQ_MODEL,
        "groq_configured": is_configured,
        "rag_chunks_count": len(rag_engine.chunks),
        "escalation_tickets_count": len(tickets),
        "admin_credentials": {"admin_name": "VST", "password_hint": "577577"},
        "official_links": {
            "homepage": "https://www.nrtec.in/",
            "academic_calendar": "https://www.nrtec.in/academic-calendar/",
            "notifications": "https://www.nrtec.in/notifications/",
            "syllabi": "https://www.nrtec.in/syllabus-2/",
        },
        "data_files": {
            "exam_schedule": {"path": str(sched_path), "is_synthetic": sched_synth},
            "course_details": {"path": str(course_path), "is_synthetic": course_synth},
            "exam_rules": {"path": str(rules_path), "is_synthetic": rules_synth},
        },
    }


@app.post("/login", status_code=status.HTTP_200_OK)
def login_endpoint(payload: LoginRequest):
    """Authenticates Student or Admin VST (577577) and logs attempt in SQLite."""
    user = authenticate_user(payload.name_or_email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid name/email or password. For Admin use name 'VST' and password '577577'.")
    return {"status": "success", "message": f"Welcome back, {user['name']}!", "user": user}


@app.post("/register", status_code=status.HTTP_200_OK)
def register_endpoint(payload: RegisterRequest):
    """Registers a new student account in SQLite database."""
    res = register_student(payload.name, payload.email, payload.mobile, payload.password)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res


@app.post("/contact-admin", status_code=status.HTTP_200_OK)
def contact_admin_endpoint(payload: ContactAdminRequest):
    """Submits a direct student contact request to Admin (VST) and stores in SQLite DB."""
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    ticket = create_escalation_ticket(
        student_question=payload.question.strip(),
        reason=payload.reason or "Direct Student Contact Form Submission",
        evidence_summary=f"Contact Details: Name: {payload.student_name}, Email: {payload.email}, Mobile: {payload.mobile}",
        student_name=payload.student_name,
        email=payload.email,
        mobile=payload.mobile
    )
    return {"status": "success", "message": "Your query has been submitted to Admin (VST) successfully!", "ticket": ticket}


@app.get("/student-tickets", status_code=status.HTTP_200_OK)
def get_student_tickets_endpoint(email: str = Query(..., description="Student email address")):
    """Retrieves only the tickets belonging to a specific student with unread notification count."""
    tickets = get_student_tickets(student_email=email)
    unread_count = sum(1 for t in tickets if t.get("notified") == 1)
    return {"status": "success", "count": len(tickets), "unread_notifications": unread_count, "tickets": tickets}


@app.post("/mark-ticket-read/{ticket_id}", status_code=status.HTTP_200_OK)
def mark_ticket_read_endpoint(ticket_id: str):
    """Clears notification alert badge for a student ticket."""
    mark_ticket_notified(ticket_id)
    return {"status": "success", "message": "Marked ticket notification as read."}


@app.post("/upload-resolution-media", status_code=status.HTTP_200_OK)
async def upload_resolution_media_endpoint(file: UploadFile = File(...)):
    """Uploads a resolution media attachment file (PDF, Image, DOCX) sent by Admin VST to student."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    filename = f"{int(datetime.now().timestamp())}_{file.filename}"
    target_path = Path(MEDIA_DIR) / filename

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_url = f"/media-files/{filename}"
        return {
            "status": "success",
            "message": f"Media file '{file.filename}' uploaded successfully.",
            "filename": filename,
            "file_url": file_url
        }
    except Exception as e:
        logger.error(f"Error uploading media file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload media file: {str(e)}")


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat_endpoint(payload: ChatRequest):
    """Processes student academic query using Agentic LLM tool calling, RAG, and memory."""
    if not payload.question or not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or blank.",
        )

    session_id = payload.session_id or "default_session"

    try:
        result = run_agent(question=payload.question.strip(), session_id=session_id)
        return ChatResponse(
            answer=result.get("answer", "No content generated."),
            tools_used=result.get("tools_used", []),
            citations=result.get("citations", []),
            success=result.get("success", False),
            iterations=result.get("iterations", 1),
            session_id=session_id,
            mode=result.get("mode", "unknown"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@app.post("/study-mode", status_code=status.HTTP_200_OK)
def study_mode_endpoint(payload: StudyModeRequest):
    """Generates study mode content (Explain Simply, Practical Example, Practice Questions, Flashcards, Summarize Notes)."""
    if not payload.topic or not payload.topic.strip():
        raise HTTPException(status_code=400, detail="Study topic cannot be empty.")

    valid_actions = ["explain_simply", "practical_example", "practice_questions", "flashcards", "summarize_notes"]
    action = payload.action if payload.action in valid_actions else "explain_simply"

    try:
        res = generate_study_mode_content(
            action=action,
            topic=payload.topic.strip(),
            context_text=payload.context_text,
        )
        return res
    except Exception as e:
        logger.error(f"Study mode error: {e}")
        from backend.study_mode import generate_study_mode_fallback
        return generate_study_mode_fallback(action, payload.topic.strip(), payload.context_text or f"Study Topic: {payload.topic}")


@app.post("/reset", status_code=status.HTTP_200_OK)
def reset_session_endpoint(payload: ResetRequest):
    """Resets/clears conversation memory for a specific session."""
    session_id = payload.session_id or "default_session"
    cleared = memory_manager.clear_session(session_id)
    return {
        "status": "success",
        "message": f"Session memory cleared for '{session_id}'.",
        "session_id": session_id,
        "was_cleared": cleared,
    }


@app.post("/upload", status_code=status.HTTP_200_OK)
async def upload_document_endpoint(file: UploadFile = File(...)):
    """Uploads a college document (PDF, TXT, DOCX, CSV) and ingests into RAG vector index."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".txt", ".pdf", ".docx", ".doc", ".csv"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: .pdf, .txt, .docx, .csv",
        )

    target_path = DOCS_DIR / file.filename
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        rag_engine = get_rag_engine()
        new_chunks = rag_engine.ingest_all_documents()

        return {
            "status": "success",
            "message": f"Document '{file.filename}' uploaded and ingested successfully.",
            "filename": file.filename,
            "total_rag_chunks": len(new_chunks),
        }
    except Exception as e:
        logger.error(f"Error uploading file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@app.get("/escalations", status_code=status.HTTP_200_OK)
def get_escalations_endpoint(status_filter: Optional[str] = None):
    """Retrieves all human escalation tickets for operator review."""
    tickets = get_all_tickets(status=status_filter)
    return {"status": "success", "count": len(tickets), "tickets": tickets}


@app.patch("/escalations/{ticket_id}", status_code=status.HTTP_200_OK)
def update_escalation_endpoint(ticket_id: str, payload: TicketStatusUpdateRequest):
    """Updates escalation ticket status, attaches media files, and dispatches email notification log."""
    res = update_ticket_status(
        ticket_id,
        new_status=payload.status,
        resolution_notes=payload.resolution_notes or "",
        media_file=payload.media_file
    )
    if not res or res.get("status") == "error":
        raise HTTPException(status_code=400, detail=f"Ticket '{ticket_id}' not found.")
    return {
        "status": "success",
        "new_status": payload.status,
        "ticket_id": ticket_id,
        "ticket": res
    }
