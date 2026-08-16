# Ubuntu deploy — Geografia (версияи ҳозира)

Ҳадаф: ҳамон код, ки дар Render кор мекунад (`server:app` + PostgreSQL), дар сервери Ubuntu.

## Ҷузъҳои boot (муҳим)

| Файл | Нақш |
|------|------|
| `server.py` | Entry: `.env` → `server_core.py` → patch-ҳо |
| `server_core.py` | Асоси Flask (Phase A, plain source) |
| `db/connection.py` | `DATABASE_URL` → SQLAlchemy pool |
| `requirements.txt` | Flask, gunicorn, psycopg2, dotenv, … |
| `.env` | Секретҳо (на дар git) |
| HTML/CSS/JS дар root + `css/` + `js/` | Static (PUBLIC_PATHS) |

## 1. PostgreSQL

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo -u postgres createuser -P geografia          # парол гузоред
sudo -u postgres createdb -O geografia geografia
```

## 2. Clone + venv

```bash
sudo mkdir -p /opt/geogrfia
sudo chown "$USER":"$USER" /opt/geogrfia
cd /opt/geogrfia
git clone https://github.com/SharifzodaIbrohim/geogrfia.git .
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 3. `.env`

```bash
cp .env.example .env
nano .env
chmod 600 .env
```

Ҳадди ақал:

```env
DATABASE_URL=postgresql://geografia:PASSWORD@127.0.0.1:5432/geografia
JWT_SECRET=<ҳадди ақал 32 рамзи тасодуфӣ>
FLASK_ENV=production
ALLOW_JSON_BACKEND=0
```

## 4. Preflight + тест

```bash
source .venv/bin/activate
set -a && source .env && set +a
python scripts/preflight_check.py
gunicorn server:app -b 127.0.0.1:8000 --workers 2
# терминали дигар:
curl -s http://127.0.0.1:8000/api/health
# интизор: {"ok":true,"database":{"backend":"postgresql",...}}
```

## 5. Static files

Алоҳида `static/` нест — файлҳо дар решаи репо:

- Саҳифаҳо: `index.html`, `admin.html`, `student.html`, `quiz.html`, …
- CSS: `css/`, `css.css`
- JS: `js/`, `js.js`

`server.py` онҳоро ба `PUBLIC_PATHS` илова мекунад. Nginx метавонад фақат proxy кунад ба gunicorn (ё static-ро худаш диҳад).

## 6. Systemd

```bash
sudo cp scripts/geografia.service.example /etc/systemd/system/geografia.service
# User=, WorkingDirectory=, EnvironmentFile= ро ислоҳ кунед
sudo systemctl daemon-reload
sudo systemctl enable --now geografia
sudo systemctl status geografia
```

Мисоли ExecStart:

```text
/opt/geogrfia/.venv/bin/gunicorn server:app -b 127.0.0.1:8000 --workers 2 --timeout 120
```

## 7. Навсозӣ пас аз `git push`

```bash
cd /opt/geogrfia
./scripts/deploy.sh
```

## 8. Backup

Пеш аз кӯчиш ва ҳар ҳафта: `docs/BACKUP.md` (`pg_dump`).

## 9. Интернет (мактаб)

IP-и LAN аз берун намерасад. Баъд:

1. Cloudflare Tunnel (тавсия)
2. Nginx + port forward
3. Домен `geografia.tj`

## server_core.py

Аз Phase A дар git ҳамчун **манбаи оддӣ** аст. Boot:

1. `server_core.py` (агар >10KB) → exec
2. агар нест → аз `_srv_b64_*.txt` materialize

Барои Ubuntu **ҳатман** `server_core.py`-и пурра дар clone бошад (`git pull`).
