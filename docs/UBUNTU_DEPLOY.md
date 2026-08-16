# Ubuntu deploy (кӯтоҳ) — пеш аз Cloudflare Tunnel

## 1. Clone

```bash
sudo mkdir -p /opt/geogrfia
sudo chown "$USER":"$USER" /opt/geogrfia
cd /opt/geogrfia
git clone https://github.com/SharifzodaIbrohim/geogrfia.git .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Environment

```bash
cp .env.example .env   # агар ҳаст
nano .env
```

Ҳадди ақал:

```env
DATABASE_URL=postgresql://geografia:PASSWORD@127.0.0.1:5432/geografia
# JWT / SECRET калиди дароз (≥32 рамз)
```

## 3. Гӯш кардан (тест)

```bash
source .venv/bin/activate
gunicorn server:app -b 127.0.0.1:8000 --workers 2
# дигар терминал:
curl http://127.0.0.1:8000/api/health
```

## 4. Systemd (мисол)

Файл: `/etc/systemd/system/geografia.service`

```ini
[Unit]
Description=Geografia gunicorn
After=network.target postgresql.service

[Service]
User=YOUR_USER
Group=YOUR_USER
WorkingDirectory=/opt/geogrfia
EnvironmentFile=/opt/geogrfia/.env
ExecStart=/opt/geogrfia/.venv/bin/gunicorn server:app -b 127.0.0.1:8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now geografia
```

## 5. Навсозӣ пас аз git push

```bash
cd /opt/geogrfia
./scripts/deploy.sh
```

## 6. Баъд

- Nginx (ихтиёрӣ) → `127.0.0.1:8000`
- Cloudflare Tunnel → мактаб аз интернет
- `docs/BACKUP.md` → dump мунтазам
