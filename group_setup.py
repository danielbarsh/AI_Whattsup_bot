import re
from typing import Optional

from bot_core import ONBOARDING_BODY
from database import DatabaseManager

# מספר טלפון תקין: ספרות בלבד (אחרי ניקוי), עם או בלי + מוביל, 9-15 ספרות
_PHONE_RE = re.compile(r"^\+?\d{9,15}$")

# כל הסטטוסים התקינים של הזרימה הנוכחית (טלפון -> שם, לכל אחד מבני הזוג)
_KNOWN_STATUSES = {
    "awaiting_male_phone",
    "awaiting_male_name",
    "awaiting_female_phone",
    "awaiting_female_name",
    "complete",
}

INTRO_MESSAGE = (
    "היי! 👋 אני *הבנקאי האישי* שלכם - בוט לניהול הוצאות ותקציב הבית בקבוצה הזו.\n\n"
    "לפני שמתחילים, אני צריך להכיר את שני בני הזוג כדי שאדע להתאים לכל אחד את הפידבק שלו 🙂\n\n"
    "📱 בואו נתחיל - מה *מספר הטלפון* של הגבר?"
)

LEGACY_RESET_MESSAGE = (
    "עדכנו קצת את תהליך ההרשמה - בואו נעשה את זה שוב, זה ייקח רק רגע 🙂\n\n" + INTRO_MESSAGE
)

INVALID_NAME_MESSAGE = (
    "הממ, זה לא נראה לי כמו שם 🤔\n"
    "אפשר לכתוב רק את השם?"
)

INVALID_PHONE_MESSAGE = (
    "הממ, זה לא נראה כמו מספר טלפון תקין 🤔\n"
    "אפשר לשלוח שוב? (למשל: 0501234567 או +972501234567)"
)

DUPLICATE_PHONE_MESSAGE = (
    "המספר הזה כבר נשמר בתור המספר של הגבר - אפשר לשלוח מספר אחר עבור האישה?"
)


class GroupSetupService:
    """שער הרשמה: קבוצה חדשה חייבת לספק מספר טלפון ושם עבור כל אחד משני בני הזוג לפני שהבוט מתחיל לפעול בה"""

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
            self.db.upsert_group_setup(chat_id, status="awaiting_male_phone")
            return INTRO_MESSAGE

        status = setup.get("status")

        if status not in _KNOWN_STATUSES:
            # קבוצה שנרשמה תחת גרסה קודמת של הזרימה (סדר אחר, או בלי שמות בכלל) - מתחילים מחדש בבטחה.
            # מספרים/שמות שכבר נשמרו בעמודות הישנות לא נמחקים - רק ה-status מתאפס לתחילת הזרימה הנוכחית.
            self.db.upsert_group_setup(chat_id, status="awaiting_male_phone")
            return LEGACY_RESET_MESSAGE

        if status == "awaiting_male_phone":
            phone = self._normalize_phone(text)
            if not phone:
                return INVALID_PHONE_MESSAGE
            self.db.upsert_group_setup(chat_id, male_phone=phone, status="awaiting_male_name")
            return "קיבלתי, תודה! ✅\n\n🙋‍♂️ ואיך קוראים לו?"

        if status == "awaiting_male_name":
            name = self._normalize_name(text)
            if not name:
                return INVALID_NAME_MESSAGE
            self.db.upsert_group_setup(chat_id, male_name=name, status="awaiting_female_phone")
            return f"נעים להכיר, {name}! 😊\n\n📱 עכשיו מה *מספר הטלפון* של האישה?"

        if status == "awaiting_female_phone":
            phone = self._normalize_phone(text)
            if not phone:
                return INVALID_PHONE_MESSAGE
            if phone == setup.get("male_phone"):
                return DUPLICATE_PHONE_MESSAGE
            self.db.upsert_group_setup(chat_id, female_phone=phone, status="awaiting_female_name")
            return "מעולה, קיבלתי! ✅\n\n🙋‍♀️ ואיך קוראים לה?"

        if status == "awaiting_female_name":
            name = self._normalize_name(text)
            if not name:
                return INVALID_NAME_MESSAGE
            self.db.upsert_group_setup(chat_id, female_name=name, status="complete")
            return self._build_completion_message(setup.get("male_name"), name)

        return None  # status == "complete" - ההרשמה כבר בוצעה

    @staticmethod
    def _build_completion_message(male_name: Optional[str], female_name: Optional[str]) -> str:
        names = " ו".join(name for name in (male_name, female_name) if name)
        greeting = f"מושלם, הכל מוכן {names}! 🎉" if names else "מושלם, הכל מוכן! 🎉"
        return f"{greeting} מעכשיו אני פה בשבילכם.\n\n{ONBOARDING_BODY}"

    @staticmethod
    def _normalize_name(text: str) -> Optional[str]:
        """ולידציה בסיסית לשם: לא ריק, לא ארוך מדי, ולא בטעות מספר טלפון"""
        name = (text or "").strip()
        if not name or len(name) > 40:
            return None
        if GroupSetupService._normalize_phone(name) is not None:
            return None
        return name

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
