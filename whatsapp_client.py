import random

import requests

# טווח משך "מקליד..." (במילישניות) שמוצג בוואטסאפ לפני כל הודעה יוצאת - נותן תחושה טבעית יותר
# ומרווח קל בין קליטת ההודעה לתשובה, כדי לא "להציף" את הצ'אט בתשובה מיידית מדי
_MIN_TYPING_MS = 1000
_MAX_TYPING_MS = 2000


class WhatsAppClient:
    """עטיפה פשוטה לשליחת הודעות וואטסאפ החוצה דרך Green-API"""

    def __init__(self, instance_id: str, api_token: str, api_server: str = "7107"):
        self.instance_id = instance_id
        self.api_token = api_token
        self.api_server = api_server

    def send_message(self, chat_id: str, text: str):
        """שליחת הודעת טקסט לצ'אט נתון דרך Green-API, עם אינדיקציית 'מקליד...' קצרה לפניה"""
        if not self.instance_id or not self.api_token:
            print("[שגיאה]: פרטי GREEN_INSTANCE_ID או GREEN_API_TOKEN חסרים במערכת.")
            return

        url = f"https://{self.api_server}.api.greenapi.com/waInstance{self.instance_id}/sendMessage/{self.api_token}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "chatId": chat_id,
            "message": text,
            "typingTime": random.randint(_MIN_TYPING_MS, _MAX_TYPING_MS),
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except Exception as e:
            print(f"שגיאה בשליחת הודעה לוואטסאפ דרך Green-API: {e}")
