# 💰 The Personal Banker — WhatsApp Expense & Budget Bot

A WhatsApp bot that manages a household's shared expenses and budget. Send it a plain message in Hebrew — it understands, saves, and talks back.

```
"קניתי חלב וביצים ב-25 ש"ח"        →  ✅ Logged, with personal feedback and a budget nudge if needed
"תגדיר תקציב סופר 1500"            →  📁 Monthly budget for a category, updatable anytime
"כמה נשאר לי בתקציב סופר?"          →  🟢🟡🔴 Exact status against real data
"כדאי לנו לצמצם על מסעדות?"         →  💬 Financial answer grounded in real data, never a guess
"סיכום"                            →  📊 Full monthly report, including budget comparison
```

## ✨ Features

- **Free-form expense logging** — AI extracts item, amount, and category from any phrasing, no fixed format required.
- **Per-category budgets** — set and updated directly over WhatsApp, no external dashboard needed.
- **Proactive nudges** — when an expense pushes you to 70%/90%+ of a category's budget, the bot flags it immediately in the confirmation, not just when a report is requested.
- **Financial Q&A** — tips, spending-habit analysis, and recommendations, always grounded in the household's real data, never invented.
- **Monthly summary** — full expense breakdown against budget, with feedback tuned to how far into the month you are.
- **Daily reminder** — a proactive nudge sent to the household's WhatsApp group every day at 15:00 Israel time, scheduled independently of the server's own timezone.
- **Personality** — the bot recognizes who's writing and responds accordingly (including a gentle bias in Efrat's favor 😉).
- **Fault-tolerant** — an unclear message, an off-topic question, or an AI hiccup never breaks the bot — it always replies with something sensible.

## 🧠 How it works

```
WhatsApp ──► Whapi Webhook ──► FastAPI (main.py)
                                     │
                                     ▼
                              BotCore.process_message
                                     │
                    ┌────────────────┼─────────────────┐
                    ▼                ▼                  ▼
             Free keyword       One AI call          Result: reply
             match ("סיכום")    that classifies      always composed
                                intent                in Python from
                                (gpt-4o-mini)          real DB data
                                     │                 (never by AI)
        ┌───────────┬───────────────┼──────────────┐
        ▼           ▼               ▼              ▼
     expense    budget set/     general finance   chitchat
                 query          question (2nd,
                                 short AI call)
```

**Core principle — keeping AI costs down:** most messages (expense, budget, summary) go through **exactly one AI call**, and every money figure in a reply (amount, remaining budget, summary total) is always computed in Python straight from the DB — the AI never "invents" numbers. A second call only happens for genuinely open-ended financial questions, and even then the reply is short and focused.

## 🛠️ Tech stack

| Component | Technology |
|---|---|
| Webhook server | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Natural language understanding | [OpenAI](https://platform.openai.com/) `gpt-4o-mini` (structured outputs) |
| Database | [Supabase](https://supabase.com/) (Postgres) |
| WhatsApp gateway | [Whapi](https://whapi.cloud/) |
| Validation & models | [Pydantic](https://docs.pydantic.dev/) |
| Scheduled reminder | [APScheduler](https://apscheduler.readthedocs.io/) (timezone-aware cron trigger) |

## 📁 Project structure

```
main.py         # FastAPI server, WhatsApp webhook intake and reply sending
bot_core.py      # Core logic: intent routing, all handlers, and personality
ai_engine.py     # OpenAI integration - intent classification + financial answers
database.py      # Supabase access layer (expenses and budgets)
models.py        # Pydantic models (ParsedMessage, categories)
```

## 🚀 Running locally

**Requirements**: Python 3.11+, a Supabase account, an OpenAI API key, a Whapi account.

```bash
# Install dependencies (the project is managed with uv)
uv sync

# Set up environment variables
cp .env.example .env   # then fill in real values
```

Required in `.env`:

```
OPENAI_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
WHAPI_TOKEN=...
REMINDER_CHAT_ID=...   # the shared WhatsApp group's chat_id, for the 15:00 daily reminder
```

And in Supabase, an `expenses` table (item, amount, category, user_name, date) and a `budgets` table:

```sql
create table budgets (
  category text primary key,
  monthly_limit numeric not null,
  updated_by text,
  updated_at timestamptz default now()
);
```

```bash
# Run the server
uv run uvicorn main:app --reload
```

Make sure to point Whapi's webhook settings at your `/webhook` URL so incoming messages reach the bot.

## 🩺 Monitoring

`GET /health` — basic health check endpoint (suitable for an uptime monitor).
