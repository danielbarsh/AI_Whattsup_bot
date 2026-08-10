import os
import random
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, BackgroundTasks, Request
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

# משתני הסביבה של Green-API
GREEN_INSTANCE_ID = os.environ.get("GREEN_INSTANCE_ID", "")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "")

# --- תזכורת יומית יזומה (לא בתגובה להודעה נכנסת) ---
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

scheduler = BackgroundScheduler(timezone="Asia/Jerusalem")

@asynccontextmanager
async def lifespan(app: FastAPI):
    job = scheduler.add_job( 
        send_daily_reminder,
        CronTrigger(hour=15, minute=18, timezone="Asia/Jerusalem"),
        id="daily_expense_reminder",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[תזמון פעיל] התזכורת היומית תישלח הבא ב-{job.next_run_time} (שעון ישראל)")
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(title="WhatsApp Expense Webhook (Green-API)", lifespan=lifespan)

# --- ה-Endpoint לקבלת ההודעות מ-Green-API ---
@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """נקודת קצה לקבלת הודעות בוואטסאפ מ-Green-API"""
    try:
        body = await request.json()
    except Exception as e:
        print(f"[שגיאת פילוס JSON]: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    print(f"[Green-API Webhook Received Raw JSON]: {body}")

    type_webhook = body.get("typeWebhook")

    # מעבדים רק אירועי הודעות נכנסות
    if type_webhook == "incomingMessageReceived":
        message_data = body.get("messageData", {})
        sender_data = body.get("senderData", {})

        # בדיקה שמדובר בהודעת טקסט נכנסת
        type_message = message_data.get("typeMessage")
        if type_message == "textMessage":
            text_data = message_data.get("textMessageData", {})
            message_text = text_data.get("textMessage", "")
            chat_id = sender_data.get("chatId", "")
            sender_name = sender_data.get("senderName") or "משתמש וואטסאפ"

            if message_text and chat_id:
                print(f"[עיבוד הודעה]: מאת={sender_name}, תוכן={message_text}, צ'אט={chat_id}")
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
    """שליחת הודעה דרך Green-API (שרת 7107)"""
    if not GREEN_INSTANCE_ID or not GREEN_API_TOKEN:
        print("[שגיאה]: פרטי GREEN_INSTANCE_ID או GREEN_API_TOKEN חסרים במערכת.")
        return

    url = f"https://7107.api.greenapi.com/waInstance{GREEN_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "chatId": chat_id,
        "message": text
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"שגיאה בשליחת הודעה לוואטסאפ דרך Green-API: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)