import calendar
import datetime
import random
from typing import Optional, get_args

from models import ParsedMessage, ExpenseCategory

# מילות מפתח לזיהוי ברכה/פנייה ראשונית (בתוך chitchat) - כדי להציג להן את הודעת ההיכרות המלאה
GREETING_KEYWORDS = [
    "היי", "הי ", "שלום", "מה קורה", "מה נשמע", "מה המצב",
    "בוקר טוב", "ערב טוב", "לילה טוב", "עזרה", "מה אתה יודע",
    "מה אתה עושה", "מה אפשר", "איך זה עובד", "hello", "hi", "help",
]

# גוף הודעת ההיכרות המלאה - מוצג כשמזהים ברכה/פנייה ראשונית, כדי שיהיה ברור מה אפשר לעשות עם הבוט.
# שימו לב: בכל *הדגשה* יש רווח/סימן פיסוק לפני ואחרי הכוכביות (לא צמוד לאות עברית) - אחרת וואטסאפ לא יציג את זה מודגש.
ONBOARDING_BODY = (
    "אני *הבנקאי האישי* שלכם - כאן כדי לנהל את ההוצאות והתקציב של הבית. הנה מה שאני יודע לעשות:\n\n"
    "🧾 *לרשום הוצאה* - תכתבו מה קניתם ובכמה, בשפה חופשית:\n"
    "׳חלב וביצים ב-25 ש\"ח׳ • ׳מילאתי דלק ב-250׳\n\n"
    "📁 *לקבוע תקציב חודשי לקטגוריה*:\n"
    "׳תגדיר תקציב סופר 1500׳ • ׳עדכן את תקציב הדלק ל-400׳\n\n"
    "📊 *לבדוק סטטוס תקציב*:\n"
    "׳כמה נשאר לי בתקציב סופר?׳ • ׳איך אני עומד מול התקציב?׳\n\n"
    "🗓️ *לקבל סיכום חודשי*:\n"
    "׳סיכום׳ • ׳כמה הוצאתי החודש?׳\n\n"
    "💬 *לשאול אותי כל שאלה פיננסית* על ההוצאות וההרגלים שלכם:\n"
    "׳כדאי לנו לצמצם על מסעדות?׳ • ׳יש לנו כסף לחופשה בעוד חודשיים?׳\n\n"
    "אין צורך בפורמט מיוחד - פשוט תכתבו כמו שהייתם מספרים לבן אדם 🙂"
)

# תשובות לשיחת חולין קלה שאינה ברכה (תודה, סתם משפט) - בלי שום עלות AI, מעבר לסיווג שכבר בוצע
CHITCHAT_REPLIES = [
    "בשמחה! 😊 תמיד כאן בשבילכם.",
    "🙌 מוזמנים לרשום הוצאה, לשאול על תקציב, או לבקש \"סיכום\" בכל רגע.",
    "😊 אם צריך תזכורת למה אני יודע לעשות, פשוט תכתבו \"עזרה\".",
]

# תשובות חולין חמות במיוחד לתפקיד ה"אישה" בקבוצה - קצת יותר כיף ואישי מהגרסה הרגילה. {name} מוחלף בשם הרשום שלה.
FEMALE_CHITCHAT_REPLIES = [
    "בשמחה {name}! 😊 תמיד כיף לעזור לך.",
    "🙌 בכל רגע בשבילך, את יודעת.",
    "😍 את והתקציב - הצוות הכי טוב שיש.",
    "💕 תמיד שמח לשמוע ממך.",
]

# פידבק חיובי קבוע שתפקיד ה"אישה" תמיד מקבל כשהיא רושמת הוצאה - הבוט קצת נוטה לצדה :). {name} מוחלף בשם הרשום שלה.
FEMALE_COMPLIMENTS = [
    "איזה תותחית! 💪",
    "{name}, קנייה מוצדקת לגמרי! 🙌",
    "ברור שזה היה שווה כל שקל 😍",
    "טעם מעולה כרגיל 👑",
    "את פשוט יודעת לקנות נכון ✨",
    "הבית הזה בר מזל שיש לו אותך 💖",
    "מאה אחוז שהיה שווה את זה 🥰",
    "קנייה של אלופה! 🏆",
    "אין עליך, כרגיל 😎",
    "החלטה מצוינת, כמו תמיד 🌟",
    "רשמתי בהנאה מיוחדת 😄",
    "וואו, איזה טעם! 👏",
    "זה בדיוק מה שהיה צריך 💯",
    "כל הכבוד יפהפייה 😘",
]

# מחמאות ספציפיות לתפקיד ה"אישה" לפי קטגוריה - עדיפות על פני הרשימה הכללית כשיש התאמה
FEMALE_CATEGORY_COMPLIMENTS = {
    "ביגוד": [
        "בגד חדש = אושר מיידי! 👗✨",
        "תמיד יודעת לבחור הכי טוב 👠",
        "וואו, סטייל ברמה אחרת 😍",
    ],
    "בילויים": [
        "מגיע לך כל רגע כיף! 🎉",
        "לפנק את עצמך זו תמיד החלטה נכונה 💃",
        "תיהני, מגיע לך! 🥳",
    ],
    "מסעדות": [
        "ערב טוב = החלטה מעולה 🍽️😋",
        "מגיע לך לפנק את עצמך 🥂",
        "בתיאבון יפהפייה 😍",
    ],
}

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

    def process_message(self, text: str, sender_name: Optional[str], chat_id: str, sender_phone: Optional[str] = None) -> str:
        """הפונקציה המרכזית שאחראית לנתב בין כל סוגי ההודעות. chat_id הוא חובה - כל שמירה/שליפה מה-DB מבודדת לפי הקבוצה השולחת"""
        role, sender_name = self._identify_sender(sender_name, chat_id, sender_phone)
        lower_text = text.lower()

        # שכבה 0 (חינם): בדיקה אם מדובר בבקשת סיכום, בלי לגעת ב-AI בכלל
        if "סיכום" in lower_text or "דוח" in lower_text or "כמה הוצאתי" in lower_text:
            current_month = datetime.datetime.now().strftime("%Y-%m")

            # זיהוי דינמי בסיסי של חודש ספציפי מתוך ההודעה
            month_to_fetch = current_month
            if "2026-07" in text:
                month_to_fetch = "2026-07"
            elif "2026-08" in text:
                month_to_fetch = "2026-08"

            return self._handle_summary_request(month_to_fetch, chat_id)

        # שכבה 1: קריאת AI אחת שמסווגת כוונה ומחלצת שדות
        try:
            parsed = self.ai.understand_message(text)
        except Exception as e:
            print(f"❌ שגיאה בניתוח ההודעה ב-AI: {e}")
            return "משהו השתבש בהבנת ההודעה, אפשר לנסות לנסח מחדש?"

        parsed.user = sender_name

        if parsed.intent == "expense":
            return self._handle_new_expense(parsed, chat_id, role)
        if parsed.intent == "budget_set":
            return self._handle_budget_set(parsed, chat_id)
        if parsed.intent == "budget_query":
            return self._handle_budget_query(parsed, chat_id)
        if parsed.intent == "general_question":
            return self._handle_general_question(parsed, chat_id, role)
        return self._handle_chitchat(text, role, sender_name)

    def _spend_by_category(self, month_str: str, chat_id: str) -> dict:
        """סך ההוצאות של חודש נתון, מקובץ לפי קטגוריה - מבוסס על אותה שליפה שמשרתת גם את הסיכום"""
        expenses = self.db.get_monthly_summary(month_str, chat_id)
        totals: dict = {}
        for exp in expenses:
            category = exp.get("category", "שונות")
            amount = float(exp.get("amount", 0))
            totals[category] = totals.get(category, 0.0) + amount
        return totals

    def _budget_status_emoji(self, spent: float, limit: float) -> str:
        if limit <= 0:
            return "⚪"
        ratio = spent / limit
        if ratio >= 1:
            return "🔴"
        if ratio >= 0.7:
            return "🟡"
        return "🟢"

    # ---------- הוצאה חדשה ----------

    def _handle_new_expense(self, parsed: ParsedMessage, chat_id: str, role: str) -> str:
        """טיפול בהוצאה חדשה: שמירה ב-DB, פידבק אישי, ותזכורת תקציב אם רלוונטי - תומך בכמה פריטים באותה הודעה"""
        if not parsed.expenses:
            return "לא הצלחתי להבין את פרטי ההוצאה. אפשר לנסח מחדש? (למשל: \"חלב וביצים ב-25 ש\"ח\")"

        try:
            lines = []
            notified_categories = set()

            for expense in parsed.expenses:
                self.db.save_expense(expense.item, expense.amount, expense.category, parsed.user, chat_id)

                lines.append(f"✅ נרשם: *{expense.item}* בסך *{expense.amount} ש\"ח* ({expense.category})")
                lines.append(self._get_expense_feedback(role, parsed.user, expense.category, expense.amount))

                if expense.category not in notified_categories:
                    budget_nudge = self._get_budget_nudge(expense.category, role, chat_id)
                    if budget_nudge:
                        lines.append(budget_nudge)
                    notified_categories.add(expense.category)

            return "\n".join(lines)
        except Exception as e:
            print(f"❌ שגיאה בעיבוד הוצאה: {e}")
            return "משהו השתבש בניסיון לרשום את ההוצאה."

    def _get_budget_nudge(self, category: str, role: str, chat_id: str) -> Optional[str]:
        """תזכורת יזומה כשמתקרבים/חורגים מהתקציב - חישוב Python בלבד, בלי עלות AI נוספת"""
        budgets = self.db.get_budgets(chat_id)
        limit = budgets.get(category)
        if not limit:
            return None

        current_month = datetime.datetime.now().strftime("%Y-%m")
        spent = self._spend_by_category(current_month, chat_id).get(category, 0.0)
        ratio = spent / limit if limit else 0

        if ratio >= 1:
            if role == "female":
                return f'🌸 סטטוס: כבר {spent:.0f} מתוך {limit:.0f} ש"ח בתקציב {category} החודש - אבל את שווה את זה בכל מקרה 😘'
            return f"🔴 שימו לב: חרגתם מהתקציב ל{category} החודש ({spent:.0f}/{limit:.0f} ש\"ח)."
        if ratio >= 0.9:
            if role == "female":
                return f'💕 עוד קצת ומיצינו את התקציב ל{category} ({spent:.0f}/{limit:.0f} ש"ח) - אבל מגיע לך 😉'
            return f"🔴 שימו לב: זה כבר {ratio * 100:.0f}% מהתקציב ל{category} החודש ({spent:.0f}/{limit:.0f} ש\"ח)."
        if ratio >= 0.7:
            if role == "female":
                return f'🙂 {ratio * 100:.0f}% מהתקציב ל{category} נוצל החודש ({spent:.0f}/{limit:.0f} ש"ח) - קצב מעולה!'
            return f"🟡 {ratio * 100:.0f}% מהתקציב ל{category} כבר נוצל החודש ({spent:.0f}/{limit:.0f} ש\"ח)."
        return None

    def _identify_sender(self, sender_name: Optional[str], chat_id: Optional[str], sender_phone: Optional[str]):
        """מזהה את השולח מול group_settings לפי מספר טלפון (ר' group_setup.py) - אין הסתמכות על שם קבוע מראש.
        מחזיר (role, display_name): role הוא 'male'/'female'/'other', ו-display_name הוא השם הרשום אם נמצאה התאמה, אחרת שם השולח מוואטסאפ"""
        if chat_id and sender_phone:
            setup = self.db.get_group_setup(chat_id)
            if setup:
                if setup.get("male_phone") == sender_phone:
                    return "male", setup.get("male_name") or sender_name
                if setup.get("female_phone") == sender_phone:
                    return "female", setup.get("female_name") or sender_name

        return "other", sender_name

    def _get_expense_feedback(self, role: str, display_name: Optional[str], category: str, amount: float) -> str:
        """פידבק קליל על ההוצאה - הבוט קצת נוטה לצד תפקיד ה'אישה' בקבוצה"""
        # לתפקיד ה"אישה" תמיד יש מחמאה, לא משנה מה קנתה - עם עדיפות למחמאה ספציפית לקטגוריה אם יש
        if role == "female":
            category_options = FEMALE_CATEGORY_COMPLIMENTS.get(category)
            if category_options:
                return random.choice(category_options)
            return random.choice(FEMALE_COMPLIMENTS).format(name=display_name or "")

        # הוצאות בריאות לא נשפטות בכלל
        if category == "בריאות":
            return "הבריאות שווה כל שקל 🩺"

        threshold = CATEGORY_THRESHOLDS.get(category)
        if threshold is not None and amount > threshold:
            if role == "male" and display_name:
                return f"{display_name}... קצת יקר הפעם 😅"
            return "קצת יקר 😅"

        return "כל הכבוד! 👏"

    # ---------- תקציבים ----------

    def _handle_budget_set(self, parsed: ParsedMessage, chat_id: str) -> str:
        if not parsed.category or parsed.amount is None:
            return "לא הצלחתי להבין באיזו קטגוריה ובאיזה סכום לקבוע את התקציב. אפשר לכתוב למשל: \"תגדיר תקציב סופר 1500\"?"

        try:
            self.db.upsert_budget(parsed.category, parsed.amount, parsed.user, chat_id)
            return f'✅ התקציב עבור *{parsed.category}* עודכן ל- *{parsed.amount:.0f} ש"ח* לחודש.'
        except Exception as e:
            print(f"❌ שגיאה בעדכון תקציב: {e}")
            return "משהו השתבש בניסיון לעדכן את התקציב."

    def _handle_budget_query(self, parsed: ParsedMessage, chat_id: str) -> str:
        budgets = self.db.get_budgets(chat_id)
        if not budgets:
            return "עדיין לא הוגדרו תקציבים. אפשר להתחיל למשל עם: \"תגדיר תקציב סופר 1500\"."

        current_month = datetime.datetime.now().strftime("%Y-%m")
        spend_by_category = self._spend_by_category(current_month, chat_id)

        if parsed.category:
            limit = budgets.get(parsed.category)
            if not limit:
                return f"לא הוגדר תקציב לקטגוריית *{parsed.category}*. אפשר להגדיר עם: \"תגדיר תקציב {parsed.category} <סכום>\"."

            spent = spend_by_category.get(parsed.category, 0.0)
            remaining = limit - spent
            emoji = self._budget_status_emoji(spent, limit)
            status_line = f'נותרו {remaining:.0f} ש"ח.' if remaining >= 0 else f'חרגתם ב-{abs(remaining):.0f} ש"ח.'
            return f'{emoji} *{parsed.category}*: הוצאתם {spent:.0f} מתוך {limit:.0f} ש"ח החודש.\n{status_line}'

        # אין קטגוריה ספציפית - סקירה כוללת
        lines = ["📊 *סטטוס תקציבים לחודש הנוכחי:*\n"]
        for category, limit in budgets.items():
            spent = spend_by_category.get(category, 0.0)
            emoji = self._budget_status_emoji(spent, limit)
            lines.append(f"{emoji} {category}: {spent:.0f}/{limit:.0f} ש\"ח")

        undefined_categories = [c for c in get_args(ExpenseCategory) if c not in budgets]
        if undefined_categories:
            lines.append(f"\nללא תקציב מוגדר: {', '.join(undefined_categories)}")

        return "\n".join(lines)

    # ---------- סיכום חודשי ----------

    def _handle_summary_request(self, month_str: str, chat_id: str) -> str:
        """שליפת הנתונים מ-Supabase ובניית הודעת סיכום מעוצבת, כולל השוואה לתקציב שהוגדר"""
        expenses = self.db.get_monthly_summary(month_str, chat_id)

        if not expenses:
            return f"לא מצאתי הוצאות רשומות עבור חודש {month_str}."

        budgets = self.db.get_budgets(chat_id)
        spend_by_category: dict = {}

        response_lines = [f"📊 *סיכום הוצאות לחודש {month_str}:*\n"]
        total_amount = 0.0

        for exp in expenses:
            item = exp.get("item", "פריט")
            amount = float(exp.get("amount", 0))
            category = exp.get("category", "כללי")
            user = exp.get("user_name", "לא ידוע")

            total_amount += amount
            spend_by_category[category] = spend_by_category.get(category, 0.0) + amount
            response_lines.append(f"• *{item}* ({category}): {amount:.2f} ש\"ח | מאת: {user}")

        if budgets:
            budget_lines = []
            for category, spent in spend_by_category.items():
                limit = budgets.get(category)
                if limit:
                    emoji = self._budget_status_emoji(spent, limit)
                    budget_lines.append(f"{emoji} {category}: {spent:.0f} מתוך {limit:.0f} ש\"ח")
            if budget_lines:
                response_lines.append("\n📁 *לפי קטגוריה מול תקציב:*")
                response_lines.extend(budget_lines)

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

    # ---------- שאלות פיננסיות כלליות ----------

    def _build_finance_context(self, chat_id: str) -> str:
        """מחרוזת עובדות אמיתיות (מספרים מה-DB בלבד) שמוזרקת לפרומפט - כדי שה-AI לעולם לא ימציא סכומים"""
        current_month = datetime.datetime.now().strftime("%Y-%m")
        spend_by_category = self._spend_by_category(current_month, chat_id)
        budgets = self.db.get_budgets(chat_id)
        total_spent = sum(spend_by_category.values())

        lines = [f"חודש נוכחי: {current_month}", f'סך הוצאות החודש: {total_spent:.0f} ש"ח']
        if spend_by_category:
            lines.append("הוצאות לפי קטגוריה:")
            for category, spent in spend_by_category.items():
                limit = budgets.get(category)
                if limit:
                    lines.append(f'- {category}: {spent:.0f} ש"ח (תקציב: {limit:.0f} ש"ח, נותרו {limit - spent:.0f} ש"ח)')
                else:
                    lines.append(f'- {category}: {spent:.0f} ש"ח (אין תקציב מוגדר)')
        else:
            lines.append("אין הוצאות רשומות החודש עדיין.")

        return "\n".join(lines)

    def _handle_general_question(self, parsed: ParsedMessage, chat_id: str, role: str) -> str:
        try:
            context = self._build_finance_context(chat_id)
            question = parsed.question or ""
            return self.ai.answer_finance_question(question, context, sender_name=parsed.user or "", is_female=(role == "female"))
        except Exception as e:
            print(f"❌ שגיאה במענה על שאלה פיננסית: {e}")
            return "משהו השתבש בניסיון לענות. אפשר לנסות שוב?"

    # ---------- שיחת חולין ----------

    def _build_onboarding_message(self, role: str, display_name: Optional[str]) -> str:
        if role == "female":
            name_part = f"{display_name} המהממת" if display_name else "מהממת"
            intro = f"היי {name_part}! 😍💕 איזה כיף שאת כאן."
        elif role == "male" and display_name:
            intro = f"היי {display_name}! 👋"
        else:
            intro = "היי! 👋"
        return f"{intro} {ONBOARDING_BODY}"

    def _handle_chitchat(self, text: str, role: str, display_name: Optional[str]) -> str:
        normalized = (text or "").strip().lower()
        if any(keyword in normalized for keyword in GREETING_KEYWORDS):
            return self._build_onboarding_message(role, display_name)

        # שכבה 2 חלופית: הודעה לא-כספית (כולל גסויות/הקנטות) - AI עונה עם קצת חוצפה, לא תגובה מתוקתקת
        try:
            return self.ai.answer_chitchat(text, sender_name=display_name or "", is_female=(role == "female"))
        except Exception as e:
            print(f"❌ שגיאה במענה לשיחת חולין, נופלים חזרה לתשובה קבועה: {e}")
            if role == "female":
                return random.choice(FEMALE_CHITCHAT_REPLIES).format(name=display_name or "")
            return random.choice(CHITCHAT_REPLIES)
