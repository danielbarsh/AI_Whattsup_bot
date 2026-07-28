import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

# יבוא המחלקות מהקבצים השונים בתיקייה
from database import DatabaseManager
from ai_engine import FinanceAI
from bot_core import BotCore

load_dotenv()

app = FastAPI(title="WhatsApp Expense Webhook")

# --- אתחול נכון של הרכיבים ---
db_mgr = DatabaseManager()
ai_mgr = FinanceAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# מעבירים ל-bot_core את המנהלים כדי שיוכל להשתמש ב-db וב-AI בפנים
bot_core = BotCore(db_manager=db_mgr, ai_manager=ai_mgr)

# --- הגדרת המבנה עבור ה-Swagger וה-FastAPI ---
class MessagePayload(BaseModel):
    text: str

class SenderPayload(BaseModel):
    name: str

class WebhookPayload(BaseModel):
    message: MessagePayload
    sender: SenderPayload

# --- ה-Endpoint לקבלת המבנה החדש ---
@app.post("/webhook")
async def whatsapp_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """נקודת קצה לקבלת הודעות בוואטסאפ"""
    message_text = payload.message.text
    sender_name = payload.sender.name
    
    if message_text:
        background_tasks.add_task(handle_async_response, message_text, sender_name)
        
    return {"status": "success"}

def handle_async_response(text: str, sender: str):
    # הפונקציה ב-bot_core מקבלת את הטקסט ואת שם השולח הפיזיים מה-JSON
    reply = bot_core.process_message(text, sender)
    if reply:
        print(f"[שליחת הודעה לוואטסאפ]:\n{reply}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)