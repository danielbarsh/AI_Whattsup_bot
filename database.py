import sqlite3
from datetime import datetime
from typing import List, Tuple
from models import ExpenseModel

class DatabaseManager:
    def __init__(self, db_path: str = "expenses.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    item TEXT,
                    amount REAL,
                    category TEXT,
                    user TEXT
                )
            ''')
            conn.commit()

    def save_expense(self, expense: ExpenseModel) -> None:
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO expenses (date, item, amount, category, user) VALUES (?, ?, ?, ?, ?)",
                (current_date, expense.item, expense.amount, expense.category, expense.user)
            )
            conn.commit()

    def fetch_monthly_data(self, month_str: str) -> Tuple[float, List[Tuple[str, float]]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(amount) FROM expenses WHERE date LIKE ?", (f"{month_str}%",))
            total = cursor.fetchone()[0] or 0.0
            
            cursor.execute("""
                SELECT category, SUM(amount) 
                FROM expenses 
                WHERE date LIKE ? 
                GROUP BY category 
                ORDER BY SUM(amount) DESC
            """, (f"{month_str}%",))
            categories = cursor.fetchall()
            
            return total, categories