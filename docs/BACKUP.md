# Backup — PostgreSQL (Geografia)

Мақсад: пеш аз кӯчиш ба Ubuntu / пеш аз тағйироти калон нусхаи DB нигоҳ доред.

## 1) Аз Render (ё ҳар ҷое DATABASE_URL ҳаст)

Дар компютери худ (Windows/Linux) бо `psql` / `pg_dump`:

```bash
# DATABASE_URL-ро аз Render Dashboard → Environment нусха кунед
export DATABASE_URL="postgresql://USER:PASS@HOST:5432/DBNAME"

mkdir -p backups
pg_dump "$DATABASE_URL" --no-owner --no-acl -F c -f "backups/geografia_$(date +%Y%m%d_%H%M).dump"

# ё SQL оддӣ (хондан осонтар):
pg_dump "$DATABASE_URL" --no-owner --no-acl -f "backups/geografia_$(date +%Y%m%d_%H%M).sql"
```

**Windows (PowerShell):**

```powershell
$env:DATABASE_URL = "postgresql://..."
New-Item -ItemType Directory -Force -Path backups | Out-Null
$ts = Get-Date -Format "yyyyMMdd_HHmm"
pg_dump $env:DATABASE_URL --no-owner --no-acl -f "backups/geografia_$ts.sql"
```

Агар `pg_dump` нест: [PostgreSQL client tools](https://www.postgresql.org/download/) насб кунед.

## 2) Барқарор кардан (restore)

```bash
# ба DB-и нав (Ubuntu ва ғ.)
export DATABASE_URL="postgresql://geografia:PASSWORD@127.0.0.1:5432/geografia"

# аз .sql:
psql "$DATABASE_URL" -f backups/geografia_YYYYMMDD_HHMM.sql

# аз custom format (-F c):
pg_restore --no-owner --no-acl -d "$DATABASE_URL" backups/geografia_YYYYMMDD_HHMM.dump
```

## 3) Ҷойи нигоҳдорӣ

| Ҷой | Тавсия |
|-----|--------|
| Компютери шумо `backups/` | ҳамеша |
| USB / диск | нусхаи дуюм |
| **На** танҳо диски сервер | агар диск вайрон шавад |

Файлҳои dump-ро ба git **commit накунед** (маълумоти шахсӣ).

## 4) Пеш аз кӯчиш ба Ubuntu — рӯйхат

1. `pg_dump` аз Render (ё DB-и ҳозира)
2. Файлро ба PC нигоҳ доред
3. Дар Ubuntu Postgres + DB созед
4. `psql` / `pg_restore`
5. App-ро бо ҳамон `DATABASE_URL` оғоз кунед
6. `/api/health` → `"ok": true`

## 5) Backup мунтазам (Ubuntu, баъд)

```bash
# мисол: ҳар рӯз соати 3:00 (crontab -e)
0 3 * * * pg_dump "$DATABASE_URL" --no-owner --no-acl -f /var/backups/geografia/$(date +\%Y\%m\%d).sql
```
