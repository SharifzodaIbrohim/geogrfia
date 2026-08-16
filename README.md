# Geografia

Платформаи география / олимпиада / викторина (Тоҷикистон).

## Ҳолати ҳозира

| Қисм | Ҷой |
|------|-----|
| Код | GitHub `SharifzodaIbrohim/geogrfia` |
| Demo/prod cloud | Render: https://geografia-19tf.onrender.com |
| DB | PostgreSQL (`DATABASE_URL`) |
| Boot | Phase A: plain `server_core.py` |

## Хусусиятҳо

- Admin: хонандагон (ID дароз), олимпиада, натиҷаҳо
- Student: login бо ID, оғоз/супоридани олимпиада (як attempt)
- Leaderboard, кишварҳо, курсҳо, profile (Gmail ихтиёрӣ)
- Дастрасӣ: Student ID ҳатмӣ; агар рӯйхати иштирокчии олимпиада холӣ бошад — ҳамаи хонандагони фаъол

## Local / Ubuntu (кӯтоҳ)

```bash
git clone https://github.com/SharifzodaIbrohim/geogrfia.git /opt/geogrfia
cd /opt/geogrfia
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL + JWT_SECRET
python scripts/preflight_check.py
gunicorn server:app -b 127.0.0.1:8000 --workers 2
```

Муфассал:

- `docs/UBUNTU_DEPLOY.md` — clone, systemd, deploy
- `docs/BACKUP.md` — `pg_dump` / restore
- `scripts/deploy.sh` — `git pull` + restart
- `scripts/geografia.service.example` — systemd unit
- `scripts/nginx-geografia.conf.example` — Nginx

### Systemd

```bash
sudo cp scripts/geografia.service.example /etc/systemd/system/geografia.service
# User= ва роҳҳоро иваз кунед
sudo systemctl daemon-reload
sudo systemctl enable --now geografia
```

### Навсозӣ пас аз `git push`

```bash
cd /opt/geogrfia && ./scripts/deploy.sh
```

### Дастрасӣ аз интернет (мактаб)

IP-и LAN (`192.168.x.x`) аз берун намерасад. Вариантҳо:

1. **Cloudflare Tunnel** (тавсия) — бе port forward
2. Port forwarding 80/443 + домен
3. Домени ниҳоӣ: `geografia.tj`

## Requirements

- Python 3.10+
- PostgreSQL (prod)
- бастаҳо: `requirements.txt`

## License

Educational use — as-is.
