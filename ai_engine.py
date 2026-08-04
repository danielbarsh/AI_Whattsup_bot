from typing import get_args
from openai import OpenAI
from models import ParsedMessage, ExpenseCategory

class FinanceAI:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-4o-mini"

    def understand_message(self, text_message: str) -> ParsedMessage:
        """קריאת AI אחת שמסווגת את כוונת ההודעה ומחלצת את השדות הרלוונטיים - שכבה 1 בזרימה."""
        categories = ", ".join(get_args(ExpenseCategory))
        prompt = (
            f'נתח את הודעת הוואטסאפ הבאה וקבע את כוונת השולח (intent), מתוך חמש אפשרויות בלבד:\n'
            f'- "expense": תיאור של הוצאה כספית שבוצעה בפועל (משהו שקנו/שילמו עליו). חלץ item, amount, category.\n'
            f'- "budget_set": בקשה מפורשת לקבוע/לעדכן תקציב חודשי לקטגוריה (מילים כמו "תקציב", "הגדר", "עדכן" יחד עם קטגוריה וסכום). '
            f'חלץ category ו-amount. אם חסר category או amount באופן ודאי - אל תנחש, סווג כ-"general_question" במקום.\n'
            f'- "budget_query": שאלה עובדתית על מצב תקציב/יתרה/כמה נשאר בפועל (למשל "כמה נשאר לי בתקציב סופר", "איך אני עומד מול התקציב החודש"). '
            f'חלץ category אם הוזכרה קטגוריה ספציפית, אחרת השאר category ריק (משמע כל הקטגוריות). '
            f'שים לב: אם השאלה מבקשת דעה/ייעוץ/המלצה (כמו "כדאי לצמצם?", "האם אני מוציא יותר מדי?") - זו "general_question", לא "budget_query", גם אם מוזכרת קטגוריה.\n'
            f'- "general_question": שאלה או בקשה פיננסית כללית - ייעוץ, דעה, טיפים לחיסכון, ניתוח הרגלי הוצאה. חלץ את השאלה לשדה question.\n'
            f'- "chitchat": ברכה, תודה, שיחת חולין, או כל דבר שלא קשור לכסף/הוצאות/תקציב.\n\n'
            f'קטגוריות אפשריות (לשדה category): {categories}.\n'
            f'הנחיות סיווג קטגוריה: מזון/ירקות/פירות/סופרמרקט/שוק -> סופר; תדלוק/חנייה/כביש אגרה -> דלק; '
            f'שכירות/חשמל/מים/ארנונה/ועד בית/גז -> בית; מסעדה/בית קפה/הזמנת אוכל/משלוח -> מסעדות; '
            f'תרופות/רופא/קופת חולים/ביטוח בריאות -> בריאות; אוטובוס/רכבת/מונית/נסיעה -> תחבורה; '
            f'קולנוע/הופעה/מסיבה/חופשה/תחביבים -> בילויים; בגדים/נעליים/אקססוריז -> ביגוד; '
            f'כל דבר שלא מתאים בבירור לאחת מהקטגוריות לעיל -> שונות.\n\n'
            f'דוגמאות למקרי גבול:\n'
            f'- "קניתי חלב וביצים ב-25 ש\"ח" -> expense (item=חלב וביצים, amount=25, category=סופר)\n'
            f'- "כמה עלה לי החלב הפעם?" -> general_question (זו שאלה, לא רישום הוצאה, למרות שיש בה "חלב")\n'
            f'- "תגדיר תקציב סופר 1500" -> budget_set (category=סופר, amount=1500)\n'
            f'- "עדכן את תקציב הדלק ל-400 ש\"ח" -> budget_set (category=דלק, amount=400)\n'
            f'- "התקציב שלנו לבית קצת מוגזם השנה" -> general_question (יש כאן את המילה "תקציב" אבל זו לא בקשה מפורשת לקבוע סכום)\n'
            f'- "כמה נשאר לי בתקציב סופר החודש?" -> budget_query (category=סופר)\n'
            f'- "איך אני עומד מול התקציב?" -> budget_query (category ריק)\n'
            f'- "כדאי לנו לצמצם הוצאות על מסעדות?" -> general_question (שאלת דעה/ייעוץ, לא בקשה למצב תקציב בפועל)\n'
            f'- "יש לי כסף לחופשה בעוד חודשיים?" -> general_question\n'
            f'- "היי, מה קורה" -> chitchat\n'
            f'- "תודה רבה!" -> chitchat\n\n'
            f'ההודעה לניתוח: "{text_message}"'
        )

        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a strict intent classifier and data extractor for a household finance WhatsApp bot. Respond ONLY with the requested JSON schema."},
                {"role": "user", "content": prompt},
            ],
            response_format=ParsedMessage,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("ה-AI לא החזיר ניתוח תקין להודעה")
        return parsed

    def answer_finance_question(self, question: str, context: str, sender_name: str = "") -> str:
        """שכבה 2: קריאת AI שנייה, רק לשאלות פיננסיות כלליות. מנוסחת חופשית אך מבוססת אך ורק על context אמיתי."""
        personalization = ""
        if "אפרת" in (sender_name or ""):
            personalization = (
                " הפעם פונה אליך אפרת - היה חם, מחמיא ותומך במיוחד, גם אם התשובה כוללת מספרים פחות נעימים."
            )

        system_prompt = (
            "אתה 'הבנקאי האישי' של דניאל ואפרת - עוזר פיננסי חם ומקצועי בוואטסאפ שמנהל את ההוצאות והתקציבים המשותפים שלהם. "
            "ענה בעברית, בקצרה (2-4 משפטים, בהתאם לאורך הודעת וואטסאפ), בטון ידידותי אך מקצועי." + personalization + " "
            "התבסס אך ורק על המספרים שסופקו לך בהמשך - אסור לך להמציא או להעריך סכומים שלא ניתנו לך. "
            "אם השאלה לא קשורה לכסף, הוצאות, תקציב או חיסכון - הסבר בנימוס שאתה מתמקד בניהול הכספים שלהם והפנה אותם בחזרה לנושא. "
            'אם אתה מדגיש מילה ב-*כוכביות* (בולד לוואטסאפ) - תמיד השאר רווח או סימן פיסוק לפני הכוכבית הפותחת ואחרי הסוגרת, ולעולם אל תצמיד כוכבית ישירות לאות עברית (למשל לא "ל*מסעדות*" אלא "ל-*מסעדות*" או "עבור *מסעדות*"), אחרת ההדגשה לא תוצג בוואטסאפ.'
        )
        user_prompt = f'נתונים פיננסיים עדכניים של הבית:\n{context}\n\nהשאלה: "{question}"'

        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=220,
        )
        content = completion.choices[0].message.content
        if not content:
            return "מצטער, לא הצלחתי לנסח תשובה כרגע. אפשר לנסות לשאול שוב?"
        return content.strip()
