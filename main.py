# backend/main.py
import os
import uuid
import json
import sqlite3
import requests
from datetime import datetime
from typing import Dict, Optional, List

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("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")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

# Initialize app
app = FastAPI(title="Advanced Medical AI", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Serve frontend
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), "medical.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    user TEXT,
    message TEXT,
    bot TEXT,
    timestamp TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS vitals (
    id TEXT PRIMARY KEY,
    blood_pressure TEXT,
    blood_sugar TEXT,
    pulse TEXT,
    timestamp TEXT,
    notes TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    title TEXT,
    time TEXT,
    notes TEXT
)
""")
conn.commit()

# Local symptom rules
SYMPTOM_MAP = {
    "fever": ["Viral infection", "COVID-19", "Heat-related illness"],
    "cough": ["Common cold", "Bronchitis", "COVID-19", "Allergic reaction"],
    "headache": ["Tension headache", "Migraine", "Dehydration", "High blood pressure"],
    "stomach pain": ["Gastritis", "Food poisoning", "IBS"],
    "chest pain": ["Could be serious: heart attack, angina — seek immediate care"],
    "shortness of breath": ["Asthma, pneumonia, heart-related — seek immediate care"],
    "dizziness": ["Low BP", "Dehydration", "Inner ear problem"],
}

def local_symptom_check(text: str) -> str:
    text_low = text.lower()
    found = {s: conds for s, conds in SYMPTOM_MAP.items() if s in text_low}
    if not found:
        return "I couldn't match symptoms locally. Please provide more details."
    urgent = any("care" in c.lower() for conds in found.values() for c in conds)
    result = "\n".join(f"{s}: {', '.join(conds)}" for s, conds in found.items())
    if urgent:
        result += "\n⚠️ Some symptoms may be serious. Seek medical attention."
    return result + "\nDisclaimer: This is not medical advice."

def save_chat(user: str, message: str, bot: str):
    cursor.execute("INSERT INTO chats VALUES (?, ?, ?, ?, ?)", 
                   (str(uuid.uuid4()), user, message, bot, datetime.utcnow().isoformat()))
    conn.commit()

@app.post("/chat")
async def chat(data: Dict):
    message = data.get("message", "").strip()
    user = data.get("user", "anonymous")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    if GROQ_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a friendly medical assistant..."},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.6
            }
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            ai_text = resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            ai_text = f"(AI API failed: {e})\n\n" + local_symptom_check(message)
    else:
        ai_text = local_symptom_check(message)

    save_chat(user, message, ai_text)
    return {"reply": ai_text}

@app.post("/vitals")
async def save_vitals(vitals: Dict):
    cursor.execute("INSERT INTO vitals VALUES (?, ?, ?, ?, ?, ?)", (
        str(uuid.uuid4()),
        vitals.get("blood_pressure"),
        vitals.get("blood_sugar"),
        vitals.get("pulse"),
        vitals.get("timestamp", datetime.utcnow().isoformat()),
        vitals.get("notes")
    ))
    conn.commit()
    return {"ok": True}

@app.get("/vitals")
async def get_vitals():
    cursor.execute("SELECT * FROM vitals")
    rows = cursor.fetchall()
    return {"vitals": rows}

@app.post("/reminder")
async def add_reminder(reminder: Dict, background_tasks: BackgroundTasks):
    cursor.execute("INSERT INTO reminders VALUES (?, ?, ?, ?)", (
        str(uuid.uuid4()), reminder["title"], reminder["time"], reminder.get("notes")
    ))
    conn.commit()
    # Here you could trigger a background task to send notifications
    return {"ok": True}

@app.get("/reminders")
async def list_reminders():
    cursor.execute("SELECT * FROM reminders")
    return {"reminders": cursor.fetchall()}
