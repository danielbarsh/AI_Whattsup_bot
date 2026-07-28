from openai import OpenAI
from models import ExpenseModel

class FinanceAI:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-4o-mini"

    def analyze_text(self, text_message: str) -> ExpenseModel:
        prompt = f'Analyze: "{text_message}". Extract item, amount, category (e.g. סופר, דלק, בית, מסעדות, שונות). If not an expense, set is_expense=false.'
        
        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a strict expense extractor. Respond ONLY with the requested JSON schema."},
                {"role": "user", "content": prompt},
            ],
            response_format=ExpenseModel,
        )
        return completion.choices[0].message.parsed