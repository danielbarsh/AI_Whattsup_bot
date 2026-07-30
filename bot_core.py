import calendar
import datetime
import random
from database import DatabaseManager

# הודעת פתיחה כשמישהו פשוט מברך את הבוט או שולח הודעה שלא קשורה להוצאות
GREETING_MESSAGE = "היי דניאל ואפרת! 😊 אני העוזר האישי שלכם לניהול ההוצאות. פשוט תכתבו לי מה קניתם ובכמה (למשל: \"חלב וביצים ב-25 ש\"ח\"), ואני ארשום את זה. אפשר גם לבקש ממני \"סיכום\" בכל רגע."

# פידבק חיובי קבוע שדניאל תמיד יקבל כשאפרת רושמת הוצאה - הבוט קצת נוטה לצדה :)
EFRAT_COMPLIMENTS = [
    "איזה תותחית! 💪",
    "אפרתי, קנייה מוצדקת לגמרי! 🙌",
    "ברור שזה היה שווה כל שקל 😍",
]

# סף סכום (בש"ח) שמעליו הוצאה בקטגוריה נחשבת "קצת יקרה". בריאות לא נשפטת בכלל.
CATEGORY_THRESHOLDS = {
    "סופר": 400,
    "דלק": 300,
    "בית": 1000,
    "מסעדות": 150,
    "תחבורה": 100,
    "בילויים": 300,
    "ביגוד": 300,
    "שונות": 200,
}

class BotCore:
    def __init__(self, db_manager, ai_manager):
        """אתחול הבוט עם מנהלי בסיס הנתונים וה-AI שמתקבלים מ-main.py"""
        self.db = db_manager
        self.ai = ai_manager

    def process_message(self, text: str, sender_name: str) -> str:
        """הפונקציה המרכזית שאחראית לנתב בין שמירה לשליפת סיכום"""
        lower_text = text.lower()
        
        # 1. בדיקה אם מדובר בבקשת סיכום
        if "סיכום" in lower_text or "דוח" in lower_text or "כמה הוצאתי" in lower_text:
            # חילוץ חודש נוכחי כברירת מחדל בפורמט YYYY-MM
            current_month = datetime.datetime.now().strftime("%Y-%m")
            
            # זיהוי דינמי בסיסי של חודש ספציפי מתוך ההודעה
            month_to_fetch = current_month
            if "2026-07" in text:
                month_to_fetch = "2026-07"
            elif "2026-08" in text:
                month_to_fetch = "2026-08"
                
            return self._handle_summary_request(month_to_fetch)
            
        # 2. אם זו לא בקשת סיכום -> מדובר בהוצאה חדשה לשמירה
        return self._handle_new_expense(text, sender_name)

    def _handle_new_expense(self, text: str, sender_name: str) -> str:
        """טיפול בהוצאה חדשה: פענוח ב-AI ושמירה ב-Supabase"""
        try:
            # הפעלה של ה-AI האמיתי מתוך ה-ai_engine שלך (מתואם לאובייקט ה-ai_mgr שמועבר ב-main)
            # בהתאם למבנה שלך, הוספנו ל-expense_data את השולח
            expense_data = self.ai.parse_expense(text)

            # אם ה-AI זיהה שזו לא באמת הוצאה (למשל ברכה או שאלה) - לא שומרים, רק מציגים הודעת פתיחה
            if not expense_data.is_expense:
                return GREETING_MESSAGE

            # עדכון שדה המשתמש באובייקט למי ששלח את ההודעה בפועל בוואטסאפ
            expense_data.user = sender_name

            # קריאה לפונקציית השמירה המעודכנת בדאטהבייס (עובד עם user_name ב-SQL)
            self.db.save_expense(expense_data)

            feedback = self._get_expense_feedback(sender_name, expense_data.category, expense_data.amount)
            return f"✅ נרשם: *{expense_data.item}* בסך *{expense_data.amount} ש\"ח* ({expense_data.category})\n{feedback}"
        except Exception as e:
            print(f"❌ שגיאה בעיבוד הוצאה: {e}")
            return "משהו השתבש בניסיון לרשום את ההוצאה."

    def _get_role(self, sender_name: str) -> str:
        """זיהוי בסיסי מי כתב - אפרת, דניאל, או מישהו אחר - לפי השם שמגיע מוואטסאפ"""
        name = (sender_name or "")
        if "אפרת" in name:
            return "efrat"
        if "דניאל" in name:
            return "daniel"
        return "other"

    def _get_expense_feedback(self, sender_name: str, category: str, amount: float) -> str:
        """פידבק קליל על ההוצאה - הבוט קצת נוטה לצד אפרת :)"""
        role = self._get_role(sender_name)

        # לאפרת תמיד יש מחמאה, לא משנה מה קנתה
        if role == "efrat":
            return random.choice(EFRAT_COMPLIMENTS)

        # הוצאות בריאות לא נשפטות בכלל
        if category == "בריאות":
            return "הבריאות שווה כל שקל 🩺"

        threshold = CATEGORY_THRESHOLDS.get(category)
        if threshold is not None and amount > threshold:
            return "קצת יקר 😅" if role != "daniel" else "דניאל... קצת יקר הפעם 😅"

        return "כל הכבוד! 👏"

    def _handle_summary_request(self, month_str: str) -> str:
        """שליפת הנתונים מ-Supabase ובניית הודעת סיכום מעוצבת"""
        expenses = self.db.get_monthly_summary(month_str)
        
        if not expenses:
            return f"לא מצאתי הוצאות רשומות עבור חודש {month_str}."
            
        # בניית הודעת הטקסט בצורה מרוכזת ומעוצבת לוואטסאפ
        response_lines = [f"📊 *סיכום הוצאות לחודש {month_str}:*\n"]
        total_amount = 0.0
        
        for exp in expenses:
            item = exp.get("item", "פריט")
            amount = float(exp.get("amount", 0))
            category = exp.get("category", "כללי")
            user = exp.get("user_name", "לא ידוע")
            
            total_amount += amount
            response_lines.append(f"• *{item}* ({category}): {amount:.2f} ש\"ח | מאת: {user}")
            
        response_lines.append(f"\n💰 *סך הכל החודש:* {total_amount:.2f} ש\"ח")
        response_lines.append(self._get_date_feedback(month_str, total_amount))

        return "\n".join(response_lines)

    def _get_date_feedback(self, month_str: str, total_amount: float) -> str:
        """פידבק קליל ביחס לאיזה שלב אנחנו נמצאים בחודש שסוכם"""
        today = datetime.datetime.now()
        year, month = map(int, month_str.split("-"))
        days_in_month = calendar.monthrange(year, month)[1]

        # אם זה חודש שכבר הסתיים - מתייחסים אליו כאל חודש מלא
        if (year, month) < (today.year, today.month):
            day_of_month = days_in_month
        else:
            day_of_month = min(today.day, days_in_month)

        progress = day_of_month / days_in_month

        if progress < 0.4 and total_amount > 3000:
            return "⚠️ שימו לב, החודש רק התחיל ואתם כבר עם הוצאות גבוהות. כדאי להאט קצת."
        if progress >= 0.85:
            return "🏁 החודש כמעט נגמר - זה כנראה קרוב לסיכום הסופי, כל הכבוד שעברתם אותו!"
        if progress < 0.4:
            return "📅 עדיין מוקדם בחודש, יש זמן לשפר את הקצב אם צריך."
        return "📅 אתם באמצע החודש, תמשיכו לעקוב אחרי ההוצאות."