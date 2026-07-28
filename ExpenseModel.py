from pydantic import BaseModel
from typing import Optional

class ExpenseModel(BaseModel):
    item: str
    amount: float
    category: str
    is_expense: bool
    raw_text: Optional[str] = None
    user: Optional[str] = None