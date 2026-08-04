import os
import requests
from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# יבוא המחלקות מהקבצים השונים בתיקייה
from database import DatabaseManager
from ai_engine import FinanceAI
from bot_core import BotCore

load_dotenv()

app = FastAPI(title="WhatsApp Expense Webhook (Green-API)")

# --- בדיקת תקינות משתני סביבה בסיסיים ---
openai_key = os.environ.get("OPENAI_API_KEY", "")
if not openai_key:
    print("[אזהרה קריטית]: OPENAI_API_KEY אינו מוגדר במערכת! ה-AI לא יעבוד כראוי.")

# --- אתחול הרכיבים ---
db_mgr = DatabaseManager()
ai_mgr = FinanceAI(api_key=openai_key)
bot_core = BotCore(db_manager=db_mgr, ai_manager=ai_mgr)

# משתני הסביבה החדשים של Green-API
GREEN_INSTANCE_ID = os.environ.get("GREEN_INSTANCE_ID", "")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "")

# --- התאמת ה-Pydantic Models למבנה של Green-API ---
class MessageData(BaseModel):
    typeMessage: str
    textMessageData: Optional[dict] = None

class SenderData(BaseModel):
    chatId: str
    sender: str
    senderName: Optional[str] = None  # שם השולח מגיע ישירות כאן ב-Green-API

class GreenWebhookPayload(BaseModel):
    typeWebhook: str
    instanceData: dict
    timestamp: int
    idMessage: str
    senderData: Optional[SenderData] = None
    messageData: Optional[MessageData] = None

# --- ה-Endpoint לקבלת ההודעות ---
@app.post("/webhook")
async def whatsapp_webhook(payload: GreenWebhookPayload, background_tasks: BackgroundTasks, request: Request):
    """נקודת קצה לקבלת הודעות בוואטסאפ מ-Green-API"""
    
    # הדפסת ה-JSON הגולמי ל-Logs ברנדר לצורך בדיקות ודיבאג
    raw_body = await request.json()
    print(f"[Green-API Raw JSON]: {raw_body}")
    
    # מעבדים רק אירועי הודעות נכנסות מסוג טקסט
    if payload.typeWebhook == "incomingMessageReceived" and payload.messageData and payload.senderData:
        msg_data = payload.messageData
        sender_info = payload.senderData
        
        # בדיקה שמדובר בהודעת טקסט
        if msg_data.typeMessage == "textMessage" and msg_data.textMessageData:
            message_text = msg_data.textMessageData.get("textMessage", "")
            chat_id = sender_info.chatId
            
            # שליפת שם השולח
            sender_name = sender_info.senderName if sender_info.senderName else "משתמש וואטסאפ"
            
            print(f"[עיבוד הודעה]: מאת={sender_name}, תוכן={message_text}, צ'אט={chat_id}")
            
            # שליחה לטיפול ברקע (אי סינכרוני)
            background_tasks.add_task(handle_async_response, message_text, sender_name, chat_id)
            
    return {"status": "success"}

def handle_async_response(text: str, sender: str, chat_id: str):
    reply = bot_core.process_message(text, sender)
    
    if reply:
        print(f"[שליחת הודעה לוואטסאפ ל-{chat_id}]:\n{reply}")
        send_whatsapp_message(chat_id, reply)

def send_whatsapp_message(chat_id: str, text: str):
    """שליחת הודעת טקסט חזרה דרך ה-API של Green-API"""
    if not GREEN_INSTANCE_ID or not GREEN_API_TOKEN:
        print("[שגיאה]: פרטי GREEN_INSTANCE_ID או GREEN_API_TOKEN חסרים במערכת.")
        return

    url = f"https://api.green-api.com/waInstance{GREEN_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    
    payload = {
        "chatId": chat_id,
        "message": text
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"שגיאה בשליחת הודעה דרך Green-API: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)