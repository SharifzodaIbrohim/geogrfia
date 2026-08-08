# Phase 1 — Database Architecture

## Ҳадаф
JSON-ро бо PostgreSQL иваз кардан **бе вайрон кардани** Countries / Books / Quiz UI-и ҳозира.

## Стратегияи dual-backend

| Маълумот | Ҳоло | Phase 1 | Баъдтар |
|----------|------|---------|--------|
| Countries, names TG | JSON файл | **ҳамон JSON** (static) | ихтиёрӣ PG |
| Books (PDF) | диск | **ҳамон** | — |
| Admins, Students, Olympiads, Results | JSON | schema + migrate script | server → PG |
| Users (legacy) | JSON | schema + migrate | + Google OAuth |

`server.py` **ҳоло ҳам JSON** мехонад. PostgreSQL танҳо вақте фаъол мешавад, ки:

```bash
DATABASE_URL=postgresql://...
```

ва API-ро ба ORM пайваст кунем (Phase 1.5 / Phase 2).

## Файлҳо

```
db/
  schema.sql      # DDL пурра
  models.py       # SQLAlchemy models
  connection.py   # engine / session / health
scripts/
  migrate_json_to_pg.py
docs/
  PHASE1_DATABASE.md
```

## Schema (ҳулоса)

```
users              ← Google + legacy email
schools
students           ← student_code = long ID
admins             ← role enum (RBAC ready)

quizzes / quiz_questions / quiz_options
olympiads / olympiad_questions / olympiad_options
olympiad_participants

attempts / attempt_answers
audit_logs
notifications
```

### Identity model (lock)

```
Google Account  →  users
Student ID      →  students.student_code
Link            →  students.user_id → users.id
Olympiad access →  olympiad_participants + time window + is_active
Admin           →  admins.role (super_admin, …)
```

## Чӣ тавр schema-ро дар PostgreSQL ҷорӣ кунем

### 1. Локалӣ (Docker мисол)

```bash
docker run -d --name geo-pg \
  -e POSTGRES_PASSWORD=geo \
  -e POSTGRES_DB=geografia \
  -p 5432:5432 postgres:16

export DATABASE_URL="postgresql://postgres:geo@localhost:5432/geografia"
psql "$DATABASE_URL" -f db/schema.sql
python scripts/migrate_json_to_pg.py
```

### 2. Render

1. New → PostgreSQL
2. `DATABASE_URL` -ро ба Web Service environment илова кунед
3. One-off shell:

```bash
psql $DATABASE_URL -f db/schema.sql
python scripts/migrate_json_to_pg.py
```

### 3. Аз JSON бе талафи маълумот

`migrate_json_to_pg.py`:
- `admins.json` → `admins`
- `users.json` → `users`
- `students.json` → `schools` + `students`
- `olympiads.json` → `olympiads` + questions/options
- `results.json` → `attempts`

Idempotent: login / student_code / email такрор намешавад.

## Чӣ тағйир намеёбад (Phase 1)

- `https://geografia-19tf.onrender.com` — ҳамон JSON backend
- Admin / Student panel — кор мекунад
- Countries / Books — бе тағйир

## Қадами навбатӣ (Phase 1.5 / 2)

1. `server.py`-ро dual-mode: агар `DATABASE_URL` → PG, вагарна JSON
2. Google OAuth (`users.google_id`)
3. Student ↔ Google link
4. RBAC enforcement дар admin API

## Dependencies

```
psycopg2-binary
sqlalchemy>=2.0
```

Дар `requirements.txt` илова шудаанд; Render бе `DATABASE_URL` ҳам боз бо Flask кор мекунад.
