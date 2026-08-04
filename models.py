from typing import Literal, Optional
from pydantic import BaseModel

# רשימה סגורה של קטגוריות - כדי שה-AI יסווג באופן עקבי ולא ימציא קטגוריות חדשות בכל פעם
ExpenseCategory = Literal[
    "סופר", "דלק", "בית", "מסעדות", "בריאות", "תחבורה", "בילויים", "ביגוד", "שונות"
]

# כוונת ההודעה - לפי זה בוט_קור מנתב לטיפול המתאים
IntentType = Literal["expense", "budget_set", "budget_query", "general_question", "chitchat"]

class ParsedMessage(BaseModel):
    intent: IntentType
    item: Optional[str] = None
    amount: Optional[float] = None
    # רלוונטי גם ל-expense וגם ל-budget_set/budget_query (None ב-budget_query = כל הקטגוריות)
    category: Optional[ExpenseCategory] = None
    # טקסט השאלה המנוקה, רלוונטי ל-general_question בלבד
    question: Optional[str] = None
    user: Optional[str] = None
