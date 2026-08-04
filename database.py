import os
from supabase import create_client, Client

class DatabaseManager:
    def __init__(self):
        # משיכת פרטי ה-API של Supabase ממשתני הסביבה
        self.url = os.environ.get("SUPABASE_URL", "")
        self.key = os.environ.get("SUPABASE_KEY", "")
        
        # אתחול הלקוח רק אם המפתחות קיימים
        if self.url and self.key:
            self.supabase: Client = create_client(self.url, self.key)
        else:
            self.supabase = None
            print("⚠️ אזהרה: מפתחות Supabase לא הוגדרו ב-.env. הבוט יפעל ללא שמירה בענן.")

    def save_expense(self, expense_data):
        """שמירת הוצאה חדשה בענן - ללא שום גישה לשדה תאריך באובייקט הפייתון"""
        if not self.supabase:
            print("❌ שגיאה: בסיס הנתונים לא מחובר.")
            return
            
        try:
            # חילוץ בטוח של השדות הקימיים בלבד. 
            # אם השדה נקרא user, נמפה אותו לעמודת user_name ב-Supabase
            user_val = getattr(expense_data, "user", None) or getattr(expense_data, "user_name", "Unknown")
            
            data = {
                "item": getattr(expense_data, "item", "פריט כללי"),
                "amount": float(getattr(expense_data, "amount", 0)),
                "category": getattr(expense_data, "category", "כללי"),
                "user_name": user_val
            }
            
            # שליחה ל-Supabase. עמודת ה-date תתמלא אוטומטית על ידי השרת בענן (DEFAULT NOW)
            self.supabase.table("expenses").insert(data).execute()
            print(f"💾 ההוצאה נשמרה בהצלחה ב-Supabase: {data['item']}")
        except Exception as e:
            print(f"❌ שגיאה בשמירת הנתונים ב-Supabase: {e}")

    def get_budgets(self):
        """שליפת התקציבים המוגדרים לכל קטגוריה. מחזיר {} בשקט אם הטבלה עדיין לא קיימת/ריקה."""
        if not self.supabase:
            return {}

        try:
            response = self.supabase.table("budgets").select("category, monthly_limit").execute()
            return {row["category"]: float(row["monthly_limit"]) for row in response.data}
        except Exception as e:
            print(f"⚠️ לא ניתן לשלוף תקציבים (ייתכן שהטבלה 'budgets' עדיין לא נוצרה ב-Supabase): {e}")
            return {}

    def upsert_budget(self, category: str, amount: float, updated_by: str) -> None:
        """קביעה/עדכון של תקציב חודשי לקטגוריה (upsert לפי category)."""
        if not self.supabase:
            print("❌ שגיאה: בסיס הנתונים לא מחובר.")
            return

        try:
            data = {
                "category": category,
                "monthly_limit": float(amount),
                "updated_by": updated_by,
            }
            self.supabase.table("budgets").upsert(data).execute()
            print(f"💾 תקציב עודכן בהצלחה ב-Supabase: {category} -> {amount}")
        except Exception as e:
            print(f"❌ שגיאה בעדכון תקציב ב-Supabase: {e}")

    def get_monthly_summary(self, month_str):
        """שליפת כל ההוצאות לחודש מסוים (בפורמט YYYY-MM)"""
        if not self.supabase:
            return []

        # חישוב טווח התאריכים המלא עבור החודש המבוקש
        year, month = map(int, month_str.split("-"))
        start_date = f"{year}-{month:02d}-01T00:00:00Z"
        
        if month == 12:
            end_date = f"{year + 1}-01-01T00:00:00Z"
        else:
            end_date = f"{year}-{month + 1:02d}-01T00:00:00Z"

        try:
            # שליפת נתונים מותאמת לעמודת user_name
            response = self.supabase.table("expenses") \
                .select("item, amount, category, user_name") \
                .gte("date", start_date) \
                .lt("date", end_date) \
                .execute()
                
            return response.data
        except Exception as e:
            print(f"❌ שגיאה בשליפת סיכום חודשי מ-Supabase: {e}")
            return []