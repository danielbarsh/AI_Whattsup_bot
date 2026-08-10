import re
from typing import Optional

from bot_core import ONBOARDING_BODY
from database import DatabaseManager

# מספר טלפון תקין: ספרות בלבד (אחרי ניקוי), עם או בלי + מוביל, 9-15 ספרות
_PHONE_RE = re.compile(r"^\+?\d{9,15}$")

INTRO_MESSAGE = (
    "היי! 👋 אני *הבנקאי האישי* שלכם - בוט לניהול הוצאות ותקציב הבית בקבוצה הזו.\n\n"
    "לפני שנתחיל, אני צריך להכיר את שני בני הזוג כדי שאוכל להתאים לכל אחד את הפידבק שלו 🙂\n\n"
    "📱 מה *מספר הטלפון של הגבר*? (למשל: 0501234567)"
)

ASK_FEMALE_MESSAGE = (
    "קיבלתי, מעולה! ✅\n\n"
    "📱 ועכשיו - מה *מספר הטלפון של האישה*? (למשל: 0501234567)"
)

INVALID_PHONE_MESSAGE = (
    "הממ, זה לא נראה כמו מספר טלפון תקין 🤔\n"
    "אפשר לשלוח שוב? (למשל: 0501234567 או +972501234567)"
)

DUPLICATE_PHONE_MESSAGE = (
    "המספר הזה כבר נשמר בתור המספר של הגבר - אפשר לשלוח מספר אחר עבור האישה?"
)

SETUP_COMPLETE_MESSAGE = f"מושלם, הכל מוכן! 🎉 מעכשיו אני פה בשבילכם.\n\n{ONBOARDING_BODY}"


class GroupSetupService:
    """שער הרשמה: קבוצה חדשה חייבת לספק את מספרי הטלפון של שני בני הזוג לפני שהבוט מתחיל לפעול בה"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    @staticmethod
    def is_group_chat(chat_id: str) -> bool:
        return bool(chat_id) and chat_id.endswith("@g.us")

    def intercept(self, chat_id: str, text: str) -> Optional[str]:
        """
        מטפל בהודעה כחלק מתהליך ההרשמה אם הקבוצה עדיין לא הושלמה, ומחזיר את התשובה לשליחה.
        אם ההרשמה כבר הושלמה - לא נוגע בכלום ומחזיר None, כדי שההודעה תמשיך לטיפול הרגיל.
        """
        setup = self.db.get_group_setup(chat_id)

        if setup is None:
            self.db.upsert_group_setup(chat_id, status="pending_male")
            return INTRO_MESSAGE

        status = setup.get("status")

        if status == "pending_male":
            phone = self._normalize_phone(text)
            if not phone:
                return INVALID_PHONE_MESSAGE
            self.db.upsert_group_setup(chat_id, male_phone=phone, status="pending_female")
            return ASK_FEMALE_MESSAGE

        if status == "pending_female":
            phone = self._normalize_phone(text)
            if not phone:
                return INVALID_PHONE_MESSAGE
            if phone == setup.get("male_phone"):
                return DUPLICATE_PHONE_MESSAGE
            self.db.upsert_group_setup(chat_id, female_phone=phone, status="complete")
            return SETUP_COMPLETE_MESSAGE

        return None  # status == "complete" - ההרשמה כבר בוצעה

    @staticmethod
    def _normalize_phone(text: str) -> Optional[str]:
        """מנקה את הטקסט למספר עם ספרות בלבד, ומנרמל 05... ל-972 (קידומת ישראל) כדי להתאים לפורמט sender של Green-API"""
        candidate = re.sub(r"[\s-]", "", (text or "").strip())
        if not _PHONE_RE.match(candidate):
            return None

        digits = candidate.lstrip("+")
        if digits.startswith("0"):
            digits = "972" + digits[1:]
        return digits
