from __future__ import annotations

import json
import os
import re
import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import streamlit as st
from openai import OpenAI

# -----------------------------
# Configuration
# -----------------------------
MODEL_FEEDBACK = os.getenv("OPENAI_MODEL_FEEDBACK", "gpt-4o-mini")
MODEL_SUMMARY = os.getenv("OPENAI_MODEL_SUMMARY", "gpt-4o-mini")
TEMPERATURE_FEEDBACK = float(os.getenv("OPENAI_TEMPERATURE_FEEDBACK", "0.4"))
TEMPERATURE_SUMMARY = float(os.getenv("OPENAI_TEMPERATURE_SUMMARY", "0.3"))

# -----------------------------
# Data model
# -----------------------------
@dataclass
class Question:
    id: str
    topic: str
    marks: int
    prompt: str
    answer_type: str = "text"

def load_questions(filepath: str) -> List[Question]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Question(**q) for q in data]

# -----------------------------
# Helpers
# -----------------------------
@st.cache_resource
def get_openai_client(api_key: str) -> OpenAI:
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY. Set it in env var or Streamlit secrets.")
    return OpenAI(api_key=api_key)

def youtube_search_link(query: str) -> str:
    q = re.sub(r"\s+", "+", query.strip())
    return f"https://www.youtube.com/results?search_query={q}"

def safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    try:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return None

def save_feedback_to_history(question: Question, answer: str, feedback: Dict[str, Any]):
    """Appends feedback to a local JSON file for history tracking."""
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "question_id": question.id,
        "question_topic": question.topic,
        "question_prompt": question.prompt,
        "student_answer": answer,
        "feedback": feedback
    }
    
    history_file = "feedback_history.json"
    history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
            
    history.append(record)
    
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def save_summary_to_history(summary: Dict[str, Any]):
    """Appends final summary to local JSON file."""
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": "summary",
        "content": summary
    }
    
    history_file = "feedback_history.json"
    history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
            
    history.append(record)
    
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def call_openai_for_feedback(
    client: OpenAI,
    question: Question,
    student_answer: str,
    grade_level: str = "Grade 7 Cambridge",
) -> Dict[str, Any]:
    system = (
        "You are a strict but supportive Cambridge lower-secondary science teacher. "
        "Give accurate chemistry explanations for Grade 7. "
        "Be clear, step-by-step, and correct misconceptions. "
        "Do NOT assume the student has prior knowledge beyond Grade 7."
    )

    user = f"""
Create feedback for a student.

Context:
- Level: {grade_level}
- Topic: {question.topic}
- Question ({question.id}, {question.marks} marks): {question.prompt}
- Student answer: {student_answer}

Output MUST be valid JSON with exactly these keys:
{{
  "verdict": "Correct|Partly correct|Incorrect",
  "score_band": "0-{question.marks} (integer as string)",
  "feedback": "Brief, supportive feedback in 3-6 lines",
  "model_answer": "A clear, exam-style ideal answer",
  "why": "Detailed explanation suitable for Grade 7, step-by-step",
  "misconceptions": ["..."],
  "next_steps": ["..."],
  "video_queries": ["3-5 YouTube search queries the student can use"]
}}

Rules:
- Keep the model answer concise but complete for the marks.
- In 'why', explain the science in detail but in simple language.
- If the student is wrong, correct them clearly and kindly.
- video_queries should be specific (e.g., 'Rutherford gold foil experiment explained for kids').
""".strip()

    resp = client.chat.completions.create(
        model=MODEL_FEEDBACK,
        temperature=TEMPERATURE_FEEDBACK,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    content = resp.choices[0].message.content or ""
    parsed = safe_json_loads(content)

    if not parsed:
        parsed = {
            "verdict": "Partly correct",
            "score_band": "0",
            "feedback": "Feedback could not be parsed as JSON. Showing raw response below.",
            "model_answer": "",
            "why": content,
            "misconceptions": [],
            "next_steps": [],
            "video_queries": [],
        }

    vqs = parsed.get("video_queries", []) or []
    parsed["video_links"] = [{"query": q, "url": youtube_search_link(q)} for q in vqs[:6]]

    return parsed

def call_openai_for_final_summary(
    client: OpenAI,
    qa_log: List[Dict[str, Any]],
    grade_level: str = "Grade 7 Cambridge",
) -> Dict[str, Any]:
    system = (
        "You are an expert Cambridge science tutor and assessment designer. "
        "You will analyze student responses and produce a compact, actionable learning plan."
    )

    user = f"""
Analyze the student's full quiz attempt and produce a summary for {grade_level}.

Here is the attempt log as JSON:
{json.dumps(qa_log, ensure_ascii=False, indent=2)}

Output MUST be valid JSON with exactly these keys:
{{
  "overall_summary": "3-6 lines, plain language",
  "strengths": ["..."],
  "gaps": ["..."],
  "misconceptions_to_fix": ["..."],
  "key_learning_points": ["..."],
  "recommended_next_topics": ["..."]
}}

Rules:
- Be specific: reference patterns in the student's answers (e.g., 'confuses concentration with amount').
""".strip()

    resp = client.chat.completions.create(
        model=MODEL_SUMMARY,
        temperature=TEMPERATURE_SUMMARY,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    content = resp.choices[0].message.content or ""
    parsed = safe_json_loads(content)

    if not parsed:
        parsed = {
            "overall_summary": "Summary could not be parsed as JSON. Raw output provided.",
            "strengths": [],
            "gaps": [],
            "misconceptions_to_fix": [],
            "key_learning_points": [],
            "recommended_next_topics": [],
            "raw": content,
        }

    return parsed
