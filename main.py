import os
import random
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# יבוא המחלקות מהקבצים השונים בתיקייה
from database import DatabaseManager
from ai_engine import FinanceAI
from bot_core import BotCore

load_dotenv()

# --- בדיקת תקינות משתני סביבה בסיסיים ---
openai_key = os.environ.get("OPENAI_API_KEY", "")
if not openai_key:
    print("[אזהרה קריטית]: OPENAI_API_KEY אינו מוגדר במערכת! ה-AI לא יעבוד כראוי.")

# --- אתחול הרכיבים ---
db_mgr = DatabaseManager()
ai_mgr = FinanceAI(api_key=openai_key)
bot_core = BotCore(db_manager=db_mgr, ai_manager=ai_mgr)

WHAPI_TOKEN = os.environ.get("WHAPI_TOKEN", "YOUR_WHAPI_TOKEN_HERE")

# --- תזכורת יומית יזומה (לא בתגובה להודעה נכנסת) ---
# chat_id של קבוצת הוואטסאפ המשותפת של דניאל ואפרת עם הבוט
REMINDER_CHAT_ID = os.environ.get("REMINDER_CHAT_ID", "")

DAILY_REMINDER_MESSAGES = [
    "📝 דניאל ואפרת, תזכורת ידידותית מהבנקאי האישי שלכם - יש הוצאות של היום לרשום? 😊",
    "👋 היי לשניכם! רגע לפני שהיום נגמר - מה קניתם היום?",
    "💰 תזכורת יומית: אל תשכחו לעדכן אותי בהוצאות של היום, כדי שהסיכום יישאר מדויק.",
]

def send_daily_reminder():
    """נשלח פעם ביום ע\"י ה-scheduler (לא כתגובה להודעה נכנסת) לקבוצת הוואטסאפ המשותפת"""
    if not REMINDER_CHAT_ID:
        print("⚠️ REMINDER_CHAT_ID לא מוגדר ב-.env - מדלג על שליחת התזכורת היומית.")
        return

    message = random.choice(DAILY_REMINDER_MESSAGES)
    print(f"[תזכורת יומית] שולח ל-{REMINDER_CHAT_ID}: {message}")
    send_whatsapp_message(REMINDER_CHAT_ID, message)

# ה-timezone מוגדר במפורש ל-Asia/Jerusalem (לא לפי שעון השרת) - כדי שהתזכורת תמיד תישלח ב-15:00
# לפי השעון הישראלי, כולל התאמה נכונה לשעון קיץ/חורף בישראל (שלא תמיד חופף לשעון הקיץ בארה"ב).
scheduler = BackgroundScheduler(timezone="Asia/Jerusalem")

@asynccontextmanager
async def lifespan(app: FastAPI):
    job = scheduler.add_job(
        send_daily_reminder,
        CronTrigger(hour=15, minute=10, timezone="Asia/Jerusalem"),
        id="daily_expense_reminder",
        replace_existing=True,
    )
    scheduler.start()
    # לוג ניתן לבדיקה מיד אחרי דיפלוי - בלי להמתין לשעת השליחה ובלי לבצע שליחה בפועל
    print(f"[תזמון פעיל] התזכורת היומית תישלח הבא ב-{job.next_run_time} (שעון ישראל)")
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(title="WhatsApp Expense Webhook", lifespan=lifespan)

# --- התאמת ה-Pydantic Models למבנה המדויק והמלא של Whapi ---
class TextObject(BaseModel):
    body: str

class MessageItem(BaseModel):
    id: str
    chat_id: str
    from_me: bool
    type: str
    text: Optional[TextObject] = None
    # השדה האמיתי שמחזיר Whapi עבור שם השולח (ה-pushname מוואטסאפ)
    from_name: Optional[str] = None

class WhapiWebhookPayload(BaseModel):
    messages: Optional[List[MessageItem]] = None

# --- ה-Endpoint לקבלת ההודעות ---
@app.post("/webhook")
async def whatsapp_webhook(payload: WhapiWebhookPayload, background_tasks: BackgroundTasks, request: Request):
    """נקודת קצה לקבלת הודעות בוואטסאפ מ-Whapi"""

    # הדפסת ה-JSON הגולמי לתוך ה-Logs של Render כדי שנוכל לדבג במקרה הצורך
    raw_body = await request.json()
    print(f"[Whapi Webhook Received Raw JSON]: {raw_body}")

    if not payload.messages:
        return {"status": "success", "detail": "No messages in payload"}

    for msg in payload.messages:
        if msg.from_me:
            continue

        if msg.type == "text" and msg.text:
            message_text = msg.text.body
            chat_id = msg.chat_id

            # שליפת שם השולח מהשדה האמיתי שמחזיר Whapi
            sender_name = msg.from_name or "משתמש וואטסאפ"

            print(f"[עיבוד הודעה]: מאת={sender_name}, תוכן={message_text}, צ'אט={chat_id}")

            # שליחה לטיפול ברקע
            background_tasks.add_task(handle_async_response, message_text, sender_name, chat_id)

    return {"status": "success"}

@app.get('/health')
async def health_check():
    return {"status": "healthy"}

def handle_async_response(text: str, sender: str, chat_id: str):
    reply = bot_core.process_message(text, sender)

    if reply:
        print(f"[שליחת הודעה לוואטסאפ ל-{chat_id}]:\n{reply}")
        send_whatsapp_message(chat_id, reply)

def send_whatsapp_message(chat_id: str, text: str):
    url = "https://gate.whapi.cloud/messages/text"
    headers = {
        "Authorization": f"Bearer {WHAPI_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": chat_id,
        "body": text
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"שגיאה בשליחת הודעה לוואטסאפ: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
