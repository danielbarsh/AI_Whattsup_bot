from datetime import datetime
from typing import Optional
from ai_engine import FinanceAI
from database import DatabaseManager

class ExpenseBotCore:
    def __init__(self, ai_manager: FinanceAI, db_manager: DatabaseManager):
        self.ai = ai_manager
        self.db = db_manager

    def process_message(self, incoming_text: str, sender_name: str) -> Optional[str]:
        text_clean = incoming_text.strip()
        
        if text_clean == "סיכום":
            return self.generate_report()
            
        expense_data = self.ai.analyze_text(text_clean)
        expense_data.user = sender_name
        
        if expense_data.is_expense:
            self.db.save_expense(expense_data)
            return f"✅ נרשם: *{expense_data.item}* בסך *{expense_data.amount} ש\"ח* ({expense_data.category})"
        
        return None

    def generate_report(self, target_month: Optional[str] = None) -> str:
        if not target_month:
            target_month = datetime.now().strftime("%Y-%m")
            
        total, categories = self.db.fetch_monthly_data(target_month)
        
        summary_msg = f"📊 *סיכום הוצאות לחודש {target_month}:*\n"
        summary_msg += f"💰 סך הכל הוצאתם: *{total:.2f} ש\"ח*\n\n"
        
        if categories:
            summary_msg += "📌 *פירוט לפי קטגוריות:*\n"
            for cat, amt in categories:
                summary_msg += f"- {cat}: {amt:.2f} ש\"ח\n"
        else:
            summary_msg += "אין הוצאות רשומות לחודש זה. 🤷‍♂️"
            
        return summary_msg