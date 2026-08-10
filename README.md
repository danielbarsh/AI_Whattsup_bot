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
- **Daily reminder** — a proactive nudge sent to every active WhatsApp group (per `group_settings`) every day at 15:00 Israel time, scheduled independently of the server's own timezone.
- **Group onboarding gate** — the first time the bot sees a message in a new WhatsApp group, it introduces itself and asks for each partner's name and phone number before doing anything else. Nothing else works in that group until both are registered.
- **Personality** — the bot recognizes who's writing (by phone number, matched against the group's registration - not a hardcoded name) and responds accordingly, including a gentle bias in the registered woman's favor 😉.
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
main.py             # App wiring only: builds all components and starts the server
webhook_router.py   # Routes/parses incoming Green-API webhooks, dispatches replies
whatsapp_client.py  # Thin Green-API client for sending WhatsApp messages
group_setup.py       # Onboarding gate: registers a new group's two phone numbers before it becomes active
reminder_service.py  # APScheduler wrapper for the daily reminder job
bot_core.py          # Core logic: intent routing, all handlers, and personality
ai_engine.py         # OpenAI integration - intent classification + financial answers
database.py          # Supabase access layer (expenses, budgets, group setup)
models.py            # Pydantic models (ParsedMessage, categories)
```

## 🚀 Running locally

**Requirements**: Python 3.11+, a Supabase account, an OpenAI API key, a Green-API account.

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
GREEN_INSTANCE_ID=...
GREEN_API_TOKEN=...
```

No env var is needed for the daily reminder's target - it's read dynamically from every `group_settings` row with `status = 'complete'`, so it automatically covers every group that finished onboarding.

And in Supabase, an `expenses` table (item, amount, category, user_name, date, chat_id), a `budgets` table, and a `group_settings` table (tracks each group's onboarding progress plus the registered name and phone number of each partner). All expense/budget data is scoped by `chat_id`, so multiple WhatsApp groups can share the same bot deployment without their data mixing, and the bot's personality (e.g. the flirtier "female" feedback) is driven by whichever phone number is registered as male/female per group, never by a hardcoded name:

```sql
create table expenses (
  id bigint generated always as identity primary key,
  item text not null,
  amount numeric not null,
  category text not null,
  user_name text,
  chat_id text not null,
  date timestamptz default now()
);

create table budgets (
  category text not null,
  monthly_limit numeric not null,
  updated_by text,
  chat_id text not null,
  updated_at timestamptz default now(),
  primary key (chat_id, category)
);

create table group_settings (
  chat_id text primary key,
  male_name text,
  male_phone text,
  female_name text,
  female_phone text,
  status text not null default 'pending_male_name',  -- pending_male_name | pending_male_phone | pending_female_name | pending_female_phone | complete
  updated_at timestamptz default now()
);
```

**Migrating an existing install** (adding `chat_id` to `expenses`/`budgets` without losing existing data): see the "Adding multi-group support" migration script in the project's history, or run:

```sql
-- expenses: add the column, backfill existing rows with your current group's chat_id, then require it going forward
alter table expenses add column chat_id text;
update expenses set chat_id = '<YOUR_GROUP_CHAT_ID>' where chat_id is null;
alter table expenses alter column chat_id set not null;

-- budgets: same, plus widen the primary key from `category` alone to `(chat_id, category)`
alter table budgets add column chat_id text;
update budgets set chat_id = '<YOUR_GROUP_CHAT_ID>' where chat_id is null;
alter table budgets alter column chat_id set not null;
alter table budgets drop constraint budgets_pkey;
alter table budgets add primary key (chat_id, category);
```

Find `<YOUR_GROUP_CHAT_ID>` by running `select chat_id from group_settings;` if you've already completed the group onboarding flow, or from the server logs (`[עיבוד הודעה]: ... צ'אט=...`) — it looks like `1203630XXXXXXXXXX@g.us`.

**Adding names to an existing `group_settings` table** (the onboarding flow now also asks for each partner's name, not just their phone number - no data is lost, existing rows just pick up two new nullable columns):

```sql
alter table group_settings add column male_name text;
alter table group_settings add column female_name text;
alter table group_settings alter column status set default 'pending_male_name';
```

Any group that was mid-registration under the old phone-only flow (`status` still `pending_male` or `pending_female`) gets automatically restarted through the new name+phone flow the next time it sends a message - handled in code, no manual fix needed.

```bash
# Run the server
uv run uvicorn main:app --reload
```

Make sure to point Green-API's webhook settings at your `/webhook` URL so incoming messages reach the bot.

## 🩺 Monitoring

`GET /health` — basic health check endpoint (suitable for an uptime monitor).
