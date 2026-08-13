from typing import List, Literal, Optional
from pydantic import BaseModel

# רשימה סגורה של קטגוריות - כדי שה-AI יסווג באופן עקבי ולא ימציא קטגוריות חדשות בכל פעם
ExpenseCategory = Literal[
    "סופר", "דלק", "בית", "מסעדות", "בריאות", "תחבורה", "בילויים", "ביגוד", "שונות"
]

# כוונת ההודעה - לפי זה בוט_קור מנתב לטיפול המתאים
IntentType = Literal["expense", "budget_set", "budget_query", "general_question", "chitchat", "help"]

class ExpenseItem(BaseModel):
    """פריט הוצאה בודד - הודעה אחת יכולה להכיל כמה מהם (למשל "לחם ב-10 ועוד דלק ב-200")"""
    item: str
    amount: float
    category: ExpenseCategory

class ParsedMessage(BaseModel):
    intent: IntentType
    # רלוונטי ל-expense בלבד - רשימה כי הודעה אחת עשויה לתאר כמה הוצאות שונות
    expenses: Optional[List[ExpenseItem]] = None
    amount: Optional[float] = None
    # רלוונטי ל-budget_set/budget_query (None ב-budget_query = כל הקטגוריות)
    category: Optional[ExpenseCategory] = None
    # טקסט השאלה המנוקה, רלוונטי ל-general_question בלבד
    question: Optional[str] = None
    user: Optional[str] = None
