import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from backend.config import (
    get_schedule_file_path,
    get_courses_file_path,
    get_rules_file_path,
)


class DataLoader:
    """Safely loads and queries exam schedules, course details, and exam rules."""

    @staticmethod
    def load_schedule_df() -> tuple[Optional[pd.DataFrame], bool, Optional[str]]:
        """Loads schedule CSV as pandas DataFrame."""
        file_path, is_synthetic = get_schedule_file_path()
        if not file_path.exists():
            return None, is_synthetic, f"Schedule file not found at {file_path}"
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                return None, is_synthetic, "Schedule file is empty."
            # Clean column names
            df.columns = [col.strip().lower() for col in df.columns]
            return df, is_synthetic, None
        except Exception as e:
            return None, is_synthetic, f"Error reading schedule CSV: {str(e)}"

    @staticmethod
    def load_courses_df() -> tuple[Optional[pd.DataFrame], bool, Optional[str]]:
        """Loads course details CSV as pandas DataFrame."""
        file_path, is_synthetic = get_courses_file_path()
        if not file_path.exists():
            return None, is_synthetic, f"Course details file not found at {file_path}"
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                return None, is_synthetic, "Course details file is empty."
            df.columns = [col.strip().lower() for col in df.columns]
            return df, is_synthetic, None
        except Exception as e:
            return None, is_synthetic, f"Error reading course details CSV: {str(e)}"

    @staticmethod
    def load_rules_text() -> tuple[Optional[str], bool, Optional[str]]:
        """Loads exam rules text document."""
        file_path, is_synthetic = get_rules_file_path()
        if not file_path.exists():
            return None, is_synthetic, f"Rules file not found at {file_path}"
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            if not content:
                return None, is_synthetic, "Rules document is empty."
            return content, is_synthetic, None
        except Exception as e:
            return None, is_synthetic, f"Error reading rules document: {str(e)}"


def query_exam_schedule(
    student_id: Optional[str] = None,
    course_code: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    """Search exam schedule CSV by student_id, course_code, or subject keyword."""
    df, is_synthetic, error_msg = DataLoader.load_schedule_df()

    if error_msg or df is None:
        return {
            "status": "error",
            "message": error_msg or "Failed to load schedule dataset.",
            "records": [],
            "count": 0,
            "is_synthetic": is_synthetic,
        }

    # Normalize inputs
    student_id_clean = student_id.strip().lower() if student_id else None
    course_code_clean = course_code.strip().lower() if course_code else None
    subject_clean = subject.strip().lower() if subject else None

    # Filter conditions
    filtered_df = df.copy()

    if student_id_clean:
        if "student_id" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["student_id"].astype(str).str.lower() == student_id_clean
            ]

    if course_code_clean:
        if "course_code" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["course_code"].astype(str).str.lower().str.contains(course_code_clean, regex=False)
            ]

    if subject_clean:
        if "subject" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["subject"].astype(str).str.lower().str.contains(subject_clean, regex=False)
            ]
        elif "course_name" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["course_name"].astype(str).str.lower().str.contains(subject_clean, regex=False)
            ]

    if filtered_df.empty:
        query_desc = []
        if student_id: query_desc.append(f"student_id='{student_id}'")
        if course_code: query_desc.append(f"course_code='{course_code}'")
        if subject: query_desc.append(f"subject='{subject}'")
        search_term = ", ".join(query_desc) if query_desc else "given parameters"
        return {
            "status": "no_results",
            "message": f"No matching exam schedule records found for {search_term}.",
            "records": [],
            "count": 0,
            "is_synthetic": is_synthetic,
        }

    records = filtered_df.to_dict(orient="records")
    return {
        "status": "success",
        "message": f"Found {len(records)} matching schedule record(s).",
        "records": records,
        "count": len(records),
        "is_synthetic": is_synthetic,
    }


def query_course_details(
    course_code: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve available course details from course dataset."""
    df, is_synthetic, error_msg = DataLoader.load_courses_df()

    if error_msg or df is None:
        return {
            "status": "error",
            "message": error_msg or "Failed to load course details dataset.",
            "courses": [],
            "count": 0,
            "is_synthetic": is_synthetic,
        }

    course_code_clean = course_code.strip().lower() if course_code else None
    subject_clean = subject.strip().lower() if subject else None

    filtered_df = df.copy()

    if course_code_clean and "course_code" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["course_code"].astype(str).str.lower().str.contains(course_code_clean, regex=False)
        ]

    if subject_clean:
        subject_mask = pd.Series([False] * len(filtered_df))
        if "subject" in filtered_df.columns:
            subject_mask = subject_mask | filtered_df["subject"].astype(str).str.lower().str.contains(subject_clean, regex=False)
        if "course_name" in filtered_df.columns:
            subject_mask = subject_mask | filtered_df["course_name"].astype(str).str.lower().str.contains(subject_clean, regex=False)
        filtered_df = filtered_df[subject_mask]

    if filtered_df.empty:
        search_str = course_code or subject or "unspecified course"
        return {
            "status": "no_results",
            "message": f"No course details found for '{search_str}'.",
            "courses": [],
            "count": 0,
            "is_synthetic": is_synthetic,
        }

    courses = filtered_df.to_dict(orient="records")
    return {
        "status": "success",
        "message": f"Found {len(courses)} matching course detail(s).",
        "courses": courses,
        "count": len(courses),
        "is_synthetic": is_synthetic,
    }


def query_exam_rules(query: str) -> Dict[str, Any]:
    """Keyword search in the exam rules document."""
    rules_text, is_synthetic, error_msg = DataLoader.load_rules_text()

    if error_msg or not rules_text:
        return {
            "status": "error",
            "message": error_msg or "Failed to load examination rules document.",
            "rules": [],
            "count": 0,
            "is_synthetic": is_synthetic,
        }

    query_keywords = [k.lower() for k in re.findall(r"\w+", query) if len(k) > 2]
    if not query_keywords:
        query_keywords = [query.strip().lower()]

    # Filter out generic stop words to avoid false positive matches on common document terms
    generic_words = {"exam", "examination", "rule", "rules", "policy", "student", "candidates", "section", "hall"}
    specific_keywords = [kw for kw in query_keywords if kw not in generic_words]
    search_keywords = specific_keywords if specific_keywords else query_keywords

    # Split document into sections or rule paragraphs
    paragraphs = [p.strip() for p in rules_text.split("\n\n") if p.strip()]

    matched_rules: List[Dict[str, Any]] = []

    for idx, para in enumerate(paragraphs):
        para_lower = para.lower()
        # Calculate keyword overlap score
        matches = [kw for kw in search_keywords if kw in para_lower]
        if matches:
            matched_rules.append(
                {
                    "section_index": idx + 1,
                    "matched_keywords": list(set(matches)),
                    "match_score": len(matches),
                    "rule_text": para,
                }
            )

    # Sort by match score descending
    matched_rules.sort(key=lambda x: x["match_score"], reverse=True)

    if not matched_rules:
        return {
            "status": "no_results",
            "message": f"No examination rules matching query '{query}' were found in the official rules document.",
            "rules": [],
            "count": 0,
            "is_synthetic": is_synthetic,
        }

    return {
        "status": "success",
        "message": f"Found {len(matched_rules)} relevant rule paragraph(s) for '{query}'.",
        "rules": matched_rules[:3],  # Return top 3 most relevant matches
        "count": len(matched_rules),
        "is_synthetic": is_synthetic,
    }
