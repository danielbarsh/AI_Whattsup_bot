import random

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import DatabaseManager
from whatsapp_client import WhatsAppClient

# גוף התזכורת היומית היזומה (לא בתגובה להודעה נכנסת) שנשלחת לכל קבוצת וואטסאפ פעילה בנפרד
DAILY_REMINDER_MESSAGES = [
    "📝 תזכורת ידידותית מהבנקאי האישי שלכם - יש הוצאות של היום לרשום? 😊",
    "👋 היי לשניכם! רגע לפני שהיום נגמר - מה קניתם היום?",
    "💰 תזכורת יומית: אל תשכחו לעדכן אותי בהוצאות של היום, כדי שהסיכום יישאר מדויק.",
]


class ReminderService:
    """אחראי על תזמון ושליחת התזכורת היומית היזומה לכל קבוצה שסיימה הרשמה (status='complete' ב-group_settings)"""

    def __init__(self, whatsapp_client: WhatsAppClient, db_manager: DatabaseManager):
        self.whatsapp_client = whatsapp_client
        self.db = db_manager
        self.scheduler = BackgroundScheduler(timezone="Asia/Jerusalem")

    def start(self):
        job = self.scheduler.add_job(
            self.send_daily_reminder,
            CronTrigger(hour=15, minute=18, timezone="Asia/Jerusalem"),
            id="daily_expense_reminder",
            replace_existing=True,
        )
        self.scheduler.start()
        print(f"[תזמון פעיל] התזכורת היומית תישלח הבא ב-{job.next_run_time} (שעון ישראל)")

    def stop(self):
        self.scheduler.shutdown(wait=False)

    def send_daily_reminder(self):
        """נשלח פעם ביום ע\"י ה-scheduler (לא כתגובה להודעה נכנסת) - בלולאה על כל הקבוצות הפעילות בנפרד"""
        chat_ids = self.db.get_active_group_chat_ids()
        if not chat_ids:
            print("⚠️ אין קבוצות פעילות ב-group_settings - מדלג על שליחת התזכורת היומית.")
            return

        for chat_id in chat_ids:
            message = random.choice(DAILY_REMINDER_MESSAGES)
            print(f"[תזכורת יומית] שולח ל-{chat_id}: {message}")
            self.whatsapp_client.send_message(chat_id, message)
