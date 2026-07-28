from typing import Optional
from pydantic import BaseModel

class ExpenseModel(BaseModel):
    item: str
    amount: float
    category: str
    is_expense: bool
    user: Optional[str] = None