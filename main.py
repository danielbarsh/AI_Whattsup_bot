import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

# יבוא המחלקות מהקבצים השונים בתיקייה
from database import DatabaseManager
from ai_engine import FinanceAI
from bot_core import ExpenseBotCore

load_dotenv()

app = FastAPI(title="WhatsApp Expense Webhook")

# אתחול
db_mgr = DatabaseManager()
ai_mgr = FinanceAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
bot_core = ExpenseBotCore(ai_manager=ai_mgr, db_manager=db_mgr)

# --- הגדרת המבנה עבור ה-Swagger וה-FastAPI ---
class MessagePayload(BaseModel):
    text: str

class SenderPayload(BaseModel):
    name: str

class WebhookPayload(BaseModel):
    message: MessagePayload
    sender: SenderPayload

# --- עדכון ה-Endpoint לקבלת המבנה החדש ---
@app.post("/webhook")
async def whatsapp_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """נקודת קצה לקבלת הודעות בוואטסאפ"""
    message_text = payload.message.text
    sender_name = payload.sender.name
    
    if message_text:
        background_tasks.add_task(handle_async_response, message_text, sender_name)
        
    return {"status": "success"}

def handle_async_response(text: str, sender: str):
    reply = bot_core.process_message(text, sender)
    if reply:
        print(f"[שליחת הודעה לוואטסאפ]:\n{reply}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)