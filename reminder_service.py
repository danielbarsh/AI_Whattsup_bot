import random

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from whatsapp_client import WhatsAppClient

# גוף התזכורת היומית היזומה (לא בתגובה להודעה נכנסת) שנשלחת לקבוצת הוואטסאפ המשותפת
DAILY_REMINDER_MESSAGES = [
    "📝 דניאל ואפרת, תזכורת ידידותית מהבנקאי האישי שלכם - יש הוצאות של היום לרשום? 😊",
    "👋 היי לשניכם! רגע לפני שהיום נגמר - מה קניתם היום?",
    "💰 תזכורת יומית: אל תשכחו לעדכן אותי בהוצאות של היום, כדי שהסיכום יישאר מדויק.",
]


class ReminderService:
    """אחראי על תזמון ושליחת התזכורת היומית היזומה לקבוצת הוואטסאפ"""

    def __init__(self, whatsapp_client: WhatsAppClient, chat_id: str):
        self.whatsapp_client = whatsapp_client
        self.chat_id = chat_id
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
        """נשלח פעם ביום ע\"י ה-scheduler (לא כתגובה להודעה נכנסת) לקבוצת הוואטסאפ המשותפת"""
        if not self.chat_id:
            print("⚠️ REMINDER_CHAT_ID לא מוגדר ב-.env - מדלג על שליחת התזכורת היומית.")
            return

        message = random.choice(DAILY_REMINDER_MESSAGES)
        print(f"[תזכורת יומית] שולח ל-{self.chat_id}: {message}")
        self.whatsapp_client.send_message(self.chat_id, message)
