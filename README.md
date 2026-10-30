# Appeal Management

REST API, web frontend and Telegram bot for submitting, processing, tracking and analyzing appeals.

**Stack:** FastAPI · SQLAlchemy 2 (async) · PostgreSQL · aiogram 3 · JWT

## Features

- Appeal submission from the web or the Telegram bot (phone, description 10–2000 chars, category)
- Each appeal is routed to the responsible user of its category
- Workflow with validated transitions: `NEW → IN_PROGRESS → CLOSED`, `NEW/IN_PROGRESS → REJECTED`
- Full status history (who, when, previous/new status, comment)
- Notifications on every status change (web + Telegram)
- Role-based access: Appealer, Manager (responsible user), Administrator
- Statistics for the administrator

## Quick start (Docker)

```bash
cp .env.example .env        # then fill in JWT_SECRET and TELEGRAM_BOT_TOKEN
docker compose up -d --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:8000        |
| Swagger  | http://localhost:8000/docs   |

The Telegram bot starts automatically as the `bot` service.

## Create an administrator

```bash
docker compose exec api python -m app.create_admin --phone +998901234567 --name "Admin"
```

You will be asked for a password (min 8 characters). It is not echoed or stored in shell history.

Without Docker: `python -m app.create_admin --phone +998901234567 --name "Admin"`

As admin you can then create managers (Users page) and categories (Categories page).

## Environment variables

| Variable             | Description                                   |
|----------------------|-----------------------------------------------|
| `DATABASE_URL`       | PostgreSQL URL (`postgresql+asyncpg://...`)   |
| `POSTGRES_USER/PASSWORD/DB` | Credentials for the `db` container     |
| `JWT_SECRET`         | Secret for signing tokens (use a long random value) |
| `JWT_ALGORITHM`      | Default `HS256`                               |
| `JWT_EXPIRE_MINUTES` | Token lifetime, default `720`                 |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather                         |

## Roles

| Role      | Can do |
|-----------|--------|
| Appealer  | Create appeals, see own appeals, history and notifications |
| Manager   | See and process appeals in categories they are responsible for (accept, reject, close, change category) |
| Admin     | Everything above for all appeals, manage users and categories, view statistics |

## Appeal workflow

| Action          | From              | To            | Comment   |
|-----------------|-------------------|---------------|-----------|
| Accept          | NEW               | IN_PROGRESS   | optional  |
| Reject          | NEW, IN_PROGRESS  | REJECTED      | required  |
| Close           | IN_PROGRESS       | CLOSED        | required  |
| Change category | NEW               | NEW           | optional  |

Any other transition returns `409 Conflict`. Concurrent updates are protected with a row lock.

## Telegram bot

1. `/start` → share your phone number (only your own contact is accepted).
2. The Telegram account is linked to the user with that phone number, or a new user is created.
3. Submit appeals and check their status from the menu.
4. Status changes are delivered as Telegram messages.

The same account works on the website: register there with the same phone number to set a password.
