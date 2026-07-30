from typing import Literal, Optional
from pydantic import BaseModel

# רשימה סגורה של קטגוריות - כדי שה-AI יסווג באופן עקבי ולא ימציא קטגוריות חדשות בכל פעם
ExpenseCategory = Literal[
    "סופר", "דלק", "בית", "מסעדות", "בריאות", "תחבורה", "בילויים", "ביגוד", "שונות"
]

class ExpenseModel(BaseModel):
    item: str
    amount: float
    category: ExpenseCategory
    is_expense: bool
    user: Optional[str] = None