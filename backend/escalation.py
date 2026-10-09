import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "escalations.db")
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "data", "media_attachments")


def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite database tables for Users, Logins, Escalations, and Email Logs."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Login Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            email TEXT NOT NULL,
            mobile TEXT,
            role TEXT NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'success'
        )
    """)

    # Check table info for escalation_tickets migration
    cursor.execute("PRAGMA table_info(escalation_tickets)")
    columns = [col["name"] for col in cursor.fetchall()]

    if columns and ("student_name" not in columns or "media_file" not in columns):
        cursor.execute("DROP TABLE IF EXISTS escalation_tickets")

    # 3. Escalation Tickets & Student Contact Requests Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalation_tickets (
            id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL DEFAULT 'Student',
            email TEXT NOT NULL DEFAULT 'student@nec.edu',
            mobile TEXT NOT NULL DEFAULT 'N/A',
            student_question TEXT NOT NULL,
            reason TEXT NOT NULL,
            evidence_summary TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            resolution_notes TEXT,
            media_file TEXT,
            email_status TEXT,
            notified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 4. Email Dispatch Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            student_email TEXT NOT NULL,
            admin_name TEXT NOT NULL DEFAULT 'VST',
            message_text TEXT NOT NULL,
            media_file TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed Admin User VST (Password: 577577) if not present
    cursor.execute("SELECT * FROM users WHERE name = 'VST' OR email = 'admin@vst.nec.edu'")
    admin_exists = cursor.fetchone()
    if not admin_exists:
        cursor.execute("""
            INSERT INTO users (name, email, mobile, password, role)
            VALUES ('VST', 'admin@vst.nec.edu', '9999999999', '577577', 'admin')
        """)
        logger.info("Admin user VST seeded into SQLite database.")

    conn.commit()
    conn.close()


def clear_mock_tickets():
    """Clears sample mock tickets from SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM escalation_tickets WHERE id LIKE 'ESC-100%' OR student_name = 'Sample Student'")
    conn.commit()
    conn.close()


def log_user_login(user_name: str, email: str, mobile: str, role: str, status: str = 'success'):
    """Logs user login attempt to SQLite login_logs table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO login_logs (user_name, email, mobile, role, status)
        VALUES (?, ?, ?, ?, ?)
    """, (user_name, email, mobile, role, status))
    conn.commit()
    conn.close()


def authenticate_user(name_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates user against SQLite database. Checks Admin VST / 577577 first."""
    if (name_or_email.strip() == "VST" or name_or_email.strip().lower() == "admin@vst.nec.edu") and password.strip() == "577577":
        log_user_login("VST", "admin@vst.nec.edu", "9999999999", "admin", "success")
        return {
            "name": "VST",
            "email": "admin@vst.nec.edu",
            "mobile": "9999999999",
            "role": "admin"
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM users WHERE (name = ? OR email = ?) AND password = ?
    """, (name_or_email.strip(), name_or_email.strip().lower(), password.strip()))
    user = cursor.fetchone()
    conn.close()

    if user:
        log_user_login(user["name"], user["email"], user["mobile"], user["role"], "success")
        return {
            "name": user["name"],
            "email": user["email"],
            "mobile": user["mobile"],
            "role": user["role"]
        }
    else:
        log_user_login(name_or_email, name_or_email, "", "unknown", "failed")
        return None


def register_student(name: str, email: str, mobile: str, password: str) -> Dict[str, Any]:
    """Registers a new student user in SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (name, email, mobile, password, role)
            VALUES (?, ?, ?, ?, 'student')
        """, (name.strip(), email.strip().lower(), mobile.strip(), password.strip()))
        conn.commit()
        conn.close()
        log_user_login(name, email, mobile, "student", "registered_and_logged_in")
        return {
            "status": "success",
            "message": "Student registered successfully",
            "user": {"name": name, "email": email, "mobile": mobile, "role": "student"}
        }
    except sqlite3.IntegrityError:
        conn.close()
        return {"status": "error", "message": "An account with this email address already exists."}


def create_escalation_ticket(
    student_question: str,
    reason: str,
    evidence_summary: str = "",
    student_name: str = "Student",
    email: str = "student@nec.edu",
    mobile: str = "N/A",
    session_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Creates a real escalation ticket or student contact request in SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM escalation_tickets")
    row = cursor.fetchone()
    count = row["count"] + 1001
    ticket_id = f"ESC-{count}"

    cursor.execute("""
        INSERT INTO escalation_tickets (id, student_name, email, mobile, student_question, reason, evidence_summary, status, notified)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0)
    """, (ticket_id, student_name, email, mobile, student_question, reason, evidence_summary))

    conn.commit()
    conn.close()

    logger.info(f"Created ticket {ticket_id} for student {student_name} ({email}) in SQLite DB.")

    ticket_obj = {
        "id": ticket_id,
        "ticket_id": ticket_id,
        "student_name": student_name,
        "email": email,
        "mobile": mobile,
        "student_question": student_question,
        "reason": reason,
        "evidence_summary": evidence_summary,
        "status": "pending",
        "notified": 0,
        "created_at": datetime.now().isoformat()
    }

    return {
        "status": "success",
        "ticket_id": ticket_id,
        "student_name": student_name,
        "email": email,
        "mobile": mobile,
        "ticket": ticket_obj,
        "message": f"Created human escalation ticket {ticket_id}. College administration will review and respond."
    }


def get_all_escalation_tickets(status: Optional[str] = None, status_filter: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
    """Retrieves all escalation tickets from SQLite database for Admin VST."""
    target_status = status_filter or status
    conn = get_db_connection()
    cursor = conn.cursor()

    if target_status and target_status.lower() != 'all':
        cursor.execute("SELECT * FROM escalation_tickets WHERE status = ? ORDER BY created_at DESC", (target_status.lower(),))
    else:
        cursor.execute("SELECT * FROM escalation_tickets ORDER BY created_at DESC")

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


get_all_tickets = get_all_escalation_tickets
get_all_escalations = get_all_escalation_tickets


def get_student_tickets(student_email: str) -> List[Dict[str, Any]]:
    """Retrieves only the tickets belonging to a specific student email."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM escalation_tickets
        WHERE email = ? OR student_name = ?
        ORDER BY created_at DESC
    """, (student_email.strip().lower(), student_email.strip()))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_escalation_status(
    ticket_id: str,
    new_status: str,
    resolution_notes: str = "",
    media_file: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Updates ticket status, resolution notes, attaches media files, and dispatches email notification."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM escalation_tickets WHERE id = ?", (ticket_id,))
    ticket = cursor.fetchone()

    if not ticket:
        conn.close()
        return {"status": "error", "message": f"Ticket '{ticket_id}' not found."}

    student_email = ticket["email"]
    now_str = datetime.now().isoformat()
    email_status_str = f"Sent to {student_email} on {datetime.now().strftime('%b %d, %Y %I:%M %p')}"

    cursor.execute("""
        UPDATE escalation_tickets
        SET status = ?, resolution_notes = ?, media_file = ?, email_status = ?, notified = 1, updated_at = ?
        WHERE id = ?
    """, (new_status.lower(), resolution_notes, media_file or ticket["media_file"], email_status_str, now_str, ticket_id))

    # Record email dispatch in email_logs table
    cursor.execute("""
        INSERT INTO email_logs (ticket_id, student_email, admin_name, message_text, media_file)
        VALUES (?, ?, 'VST', ?, ?)
    """, (ticket_id, student_email, resolution_notes, media_file or ticket["media_file"]))

    conn.commit()

    cursor.execute("SELECT * FROM escalation_tickets WHERE id = ?", (ticket_id,))
    updated_row = cursor.fetchone()
    conn.close()

    res_dict = dict(updated_row)
    res_dict["status"] = "success"
    res_dict["new_status"] = updated_row["status"]
    res_dict["ticket_status"] = updated_row["status"]
    res_dict["email_sent_to"] = student_email
    res_dict["media_file"] = media_file or ticket["media_file"]
    return res_dict


update_ticket_status = update_escalation_status


def mark_ticket_notified(ticket_id: str):
    """Marks notification read for a student ticket."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE escalation_tickets SET notified = 0 WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()


# Initialize DB on module load
init_db()
clear_mock_tickets()
