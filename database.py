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
        """שמירת הוצאה חדשה בענן דרך ה-API של Supabase"""
        if not self.supabase:
            print("❌ שגיאה: בסיס הנתונים לא מחובר.")
            return
            
        # יצירת המילון להתאמה מלאה מול עמודות הטבלה
        data = {
            "date": expense_data["date"],
            "item": expense_data["item"],
            "amount": float(expense_data["amount"]),
            "category": expense_data["category"],
            "user": expense_data["user"]
        }
        
        try:
            # הכנסת הנתונים לטבלה בענן
            self.supabase.table("expenses").insert(data).execute()
            print(f"💾 ההוצאה נשמרה בהצלחה ב-Supabase: {expense_data['item']}")
        except Exception as e:
            print(f"❌ שגיאה בשמירת הנתונים ב-Supabase: {e}")

    def get_monthly_summary(self, month_str):
        """שליפת כל ההוצאות לחודש מסוים (בפורמט YYYY-MM)"""
        if not self.supabase:
            return []

        # חישוב טווח התאריכים המלא עבור החודש המבוקש (למשל מ-2026-07-01 עד 2026-08-01)
        # זה מבטיח שליפה מדויקת מתוך עמודת TIMESTAMPTZ
        year, month = map(int, month_str.split("-"))
        start_date = f"{year}-{month:02d}-01T00:00:00Z"
        
        if month == 12:
            end_date = f"{year + 1}-01-01T00:00:00Z"
        else:
            end_date = f"{year}-{month + 1:02d}-01T00:00:00Z"

        try:
            # שליפת נתונים באמצעות פילטרים מובנים של גדול-שווה וקטן-מ
            response = self.supabase.table("expenses") \
                .select("item, amount, category, user") \
                .gte("date", start_date) \
                .lt("date", end_date) \
                .execute()
                
            return response.data
        except Exception as e:
            print(f"❌ שגיאה בשליפת סיכום חודשי מ-Supabase: {e}")
            return []