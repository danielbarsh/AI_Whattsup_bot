import os
import requests  # לצורך שליחת התשובה חזרה לוואטסאפ דרך ה-API של Whapi
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# יבוא המחלקות מהקבצים השונים בתיקייה
from database import DatabaseManager
from ai_engine import FinanceAI
from bot_core import BotCore

load_dotenv()

app = FastAPI(title="WhatsApp Expense Webhook")

# --- אתחול הרכיבים ---
db_mgr = DatabaseManager()
ai_mgr = FinanceAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# מעבירים ל-bot_core את המנהלים כדי שיוכל להשתמש ב-db וב-AI בפנים
bot_core = BotCore(db_manager=db_mgr, ai_manager=ai_mgr)

# משיכת הטוקן ממשתני הסביבה (מוגדר בלוח הבקרה של Render)
WHAPI_TOKEN = os.environ.get("WHAPI_TOKEN", "YOUR_WHAPI_TOKEN_HERE")

# --- התאמת ה-Pydantic Models למבנה גמיש וחסין קריסות של Whapi ---
class TextObject(BaseModel):
    body: str

class MessageItem(BaseModel):
    id: str
    chat_id: str  # מזהה הצ'אט - קריטי כדי לדעת למי לענות!
    from_me: bool
    name: Optional[str] = None  # הפיכה ל-Optional מלא למניעת שגיאות Pydantic בהודעות יוצאות
    type: str
    text: Optional[TextObject] = None

class WhapiWebhookPayload(BaseModel):
    # שימוש ב-Optional למקרה ש-Whapi שולחת איוונט סטטוס/קריאה ללא מערך הודעות
    messages: Optional[List[MessageItem]] = None

# --- ה-Endpoint לקבלת ההודעות ---
@app.post("/webhook")
async def whatsapp_webhook(payload: WhapiWebhookPayload, background_tasks: BackgroundTasks):
    """נקודת קצה לקבלת הודעות בוואטסאפ מ-Whapi"""
    
    # אם קיבלנו איוונט מערכת/סטטוס ללא הודעות, נתעלם באלגנטיות בלי לקרוס
    if not payload.messages:
        return {"status": "success", "detail": "No messages in payload"}
    
    for msg in payload.messages:
        # מתעלמים מהודעות שהבוט עצמו שלח כדי למנוע לופ אינסופי
        if msg.from_me:
            continue
            
        # ודא שמדובר בהודעת טקסט ויש בה תוכן
        if msg.type == "text" and msg.text:
            message_text = msg.text.body
            sender_name = msg.name if msg.name else "משתמש וואטסאפ"
            chat_id = msg.chat_id
            
            # שליחה לטיפול ברקע - הוספנו את chat_id כדי שנדע לאן להחזיר תשובה
            background_tasks.add_task(handle_async_response, message_text, sender_name, chat_id)
        
    return {"status": "success"}

def handle_async_response(text: str, sender: str, chat_id: str):
    # הפונקציה ב-bot_core מעבדת את ההודעה מול OpenAI ו-Supabase
    reply = bot_core.process_message(text, sender)
    
    if reply:
        print(f"[שליחת הודעה לוואטסאפ ל-{chat_id}]:\n{reply}")
        send_whatsapp_message(chat_id, reply)

def send_whatsapp_message(chat_id: str, text: str):
    """פונקציית עזר לשליחת הודעת טקסט חזרה למשתמש דרך Whapi"""
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