from fastapi import APIRouter, BackgroundTasks, Request

from bot_core import BotCore
from whatsapp_client import WhatsAppClient


class WebhookRouter:
    """אחראי על ניתוב וטיפול בבקשות ה-Webhook הנכנסות מ-Green-API"""

    def __init__(self, bot_core: BotCore, whatsapp_client: WhatsAppClient):
        self.bot_core = bot_core
        self.whatsapp_client = whatsapp_client

        self.router = APIRouter()
        self.router.add_api_route("/webhook", self.handle_webhook, methods=["POST"])
        self.router.add_api_route("/health", self.health_check, methods=["GET"])

    async def handle_webhook(self, request: Request, background_tasks: BackgroundTasks):
        """נקודת קצה לקבלת הודעות בוואטסאפ מ-Green-API"""
        try:
            body = await request.json()
        except Exception as e:
            print(f"[שגיאת פילוס JSON]: {e}")
            return {"status": "error", "message": "Invalid JSON"}

        print(f"[Green-API Webhook Received Raw JSON]: {body}")

        if body.get("typeWebhook") == "incomingMessageReceived":
            self._route_incoming_message(body, background_tasks)

        return {"status": "success"}

    async def health_check(self):
        return {"status": "healthy"}

    def _route_incoming_message(self, body: dict, background_tasks: BackgroundTasks):
        """שולף מהודעה נכנסת את הפרטים הרלוונטיים ומעביר לטיפול ברקע, אם מדובר בהודעת טקסט תקינה"""
        message_data = body.get("messageData", {})
        sender_data = body.get("senderData", {})

        if message_data.get("typeMessage") != "textMessage":
            return

        text_data = message_data.get("textMessageData", {})
        message_text = text_data.get("textMessage", "")
        chat_id = sender_data.get("chatId", "")
        sender_name = sender_data.get("senderName") or "משתמש וואטסאפ"

        if not message_text or not chat_id:
            return

        print(f"[עיבוד הודעה]: מאת={sender_name}, תוכן={message_text}, צ'אט={chat_id}")
        background_tasks.add_task(self._process_and_reply, message_text, sender_name, chat_id)

    def _process_and_reply(self, text: str, sender: str, chat_id: str):
        reply = self.bot_core.process_message(text, sender)
        if reply:
            print(f"[שליחת הודעה לוואטסאפ ל-{chat_id}]:\n{reply}")
            self.whatsapp_client.send_message(chat_id, reply)
