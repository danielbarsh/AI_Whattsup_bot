from typing import get_args
from openai import OpenAI
from models import ExpenseModel, ExpenseCategory

class FinanceAI:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-4o-mini"

    def parse_expense(self, text_message: str) -> ExpenseModel:
        categories = ", ".join(get_args(ExpenseCategory))
        prompt = (
            f'נתח את ההודעה הבאה וחלץ ממנה פרטי הוצאה: "{text_message}".\n'
            f'- item: שם קצר וברור של הפריט/שירות שנרכש.\n'
            f'- amount: הסכום הכספי כמספר בלבד (ללא סימני מטבע).\n'
            f'- category: בחר קטגוריה אחת בלבד, בדיוק כפי שהיא כתובה, מתוך הרשימה הסגורה: {categories}.\n'
            f'  הנחיות סיווג: מזון/ירקות/פירות/סופרמרקט/שוק -> סופר; תדלוק/חנייה/כביש אגרה -> דלק; '
            f'שכירות/חשמל/מים/ארנונה/ועד בית/גז -> בית; מסעדה/בית קפה/הזמנת אוכל/משלוח -> מסעדות; '
            f'תרופות/רופא/קופת חולים/ביטוח בריאות -> בריאות; אוטובוס/רכבת/מונית/נסיעה -> תחבורה; '
            f'קולנוע/הופעה/מסיבה/חופשה/תחביבים -> בילויים; בגדים/נעליים/אקססוריז -> ביגוד; '
            f'כל דבר שלא מתאים בבירור לאחת מהקטגוריות לעיל -> שונות.\n'
            f'- is_expense: קבע false אם ההודעה אינה תיאור של הוצאה כספית שבוצעה בפועל '
            f'(למשל שאלה, בקשת סיכום/דוח, או שיחת חולין).'
        )

        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a strict expense extractor. Respond ONLY with the requested JSON schema."},
                {"role": "user", "content": prompt},
            ],
            response_format=ExpenseModel,
        )
        return completion.choices[0].message.parsed