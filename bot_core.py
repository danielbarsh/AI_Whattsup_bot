import datetime
from database import DatabaseManager

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
            
            # עדכון שדה המשתמש באובייקט למי ששלח את ההודעה בפועל בוואטסאפ
            expense_data.user = sender_name
            
            # קריאה לפונקציית השמירה המעודכנת בדאטהבייס (עובד עם user_name ב-SQL)
            self.db.save_expense(expense_data)
            
            return f"✅ נרשם: *{expense_data.item}* בסך *{expense_data.amount} ש\"ח* ({expense_data.category})"
        except Exception as e:
            print(f"❌ שגיאה בעיבוד הוצאה: {e}")
            return "משהו השתבש בניסיון לרשום את ההוצאה."

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
        
        return "\n".join(response_lines)