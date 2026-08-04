import os
import requests
from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# יבוא המחלקות מהקבצים השונים בתיקייה
from database import DatabaseManager
from ai_engine import FinanceAI
from bot_core import BotCore

load_dotenv()

app = FastAPI(title="WhatsApp Expense Webhook")

# --- בדיקת תקינות משתני סביבה בסיסיים ---
openai_key = os.environ.get("OPENAI_API_KEY", "")
if not openai_key:
    print("[אזהרה קריטית]: OPENAI_API_KEY אינו מוגדר במערכת! ה-AI לא יעבוד כראוי.")

# --- אתחול הרכיבים ---
db_mgr = DatabaseManager()
ai_mgr = FinanceAI(api_key=openai_key)
bot_core = BotCore(db_manager=db_mgr, ai_manager=ai_mgr)

WHAPI_TOKEN = os.environ.get("WHAPI_TOKEN", "YOUR_WHAPI_TOKEN_HERE")

# --- התאמת ה-Pydantic Models למבנה המדויק והמלא של Whapi ---
class TextObject(BaseModel):
    body: str

class MessageItem(BaseModel):
    id: str
    chat_id: str
    from_me: bool
    type: str
    text: Optional[TextObject] = None
    # Whapi משתמשת לעיתים קרובות ב-push_name עבור השם הפרטי של השולח
    push_name: Optional[str] = None  
    name: Optional[str] = None
    sender_name: Optional[str] = None

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
            
            # לוגיקת שליפת שם מתקדמת וחסינת תקלות
            sender_name = None
            if msg.push_name:
                sender_name = msg.push_name
            elif msg.sender_name:
                sender_name = msg.sender_name
            elif msg.name:
                sender_name = msg.name
            else:
                sender_name = "משתמש וואטסאפ"
                
            print(f"[עיבוד הודעה]: מאת={sender_name}, תוכן={message_text}, צ'אט={chat_id}")
            
            # שליחה לטיפול ברקע
            background_tasks.add_task(handle_async_response, message_text, sender_name, chat_id)
        
    return {"status": "success"}

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