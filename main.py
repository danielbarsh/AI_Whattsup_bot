import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv

# יבוא המחלקות מהקבצים השונים בתיקייה
from database import DatabaseManager
from ai_engine import FinanceAI
from bot_core import BotCore
from whatsapp_client import WhatsAppClient
from webhook_router import WebhookRouter
from reminder_service import ReminderService


def create_app() -> FastAPI:
    """בונה ומחברת יחד את כל רכיבי המערכת: DB, AI, ניתוב Webhook ותזכורת יומית"""
    load_dotenv()

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        print("[אזהרה קריטית]: OPENAI_API_KEY אינו מוגדר במערכת! ה-AI לא יעבוד כראוי.")

    db_mgr = DatabaseManager()
    ai_mgr = FinanceAI(api_key=openai_key)
    bot_core = BotCore(db_manager=db_mgr, ai_manager=ai_mgr)

    whatsapp_client = WhatsAppClient(
        instance_id=os.environ.get("GREEN_INSTANCE_ID", ""),
        api_token=os.environ.get("GREEN_API_TOKEN", ""),
    )

    webhook_router = WebhookRouter(bot_core=bot_core, whatsapp_client=whatsapp_client)
    reminder_service = ReminderService(
        whatsapp_client=whatsapp_client,
        chat_id=os.environ.get("REMINDER_CHAT_ID", ""),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        reminder_service.start()
        yield
        reminder_service.stop()

    fastapi_app = FastAPI(title="WhatsApp Expense Webhook (Green-API)", lifespan=lifespan)
    fastapi_app.include_router(webhook_router.router)
    return fastapi_app


app = create_app()


def main():
    """מפעיל את השרת - זו האחריות היחידה של main"""
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
