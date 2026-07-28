import os
from fastapi import FastAPI, Request, BackgroundTasks
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

@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    message_text = data.get("message", {}).get("text", "")
    sender_name = data.get("sender", {}).get("name", "Unknown")
    
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