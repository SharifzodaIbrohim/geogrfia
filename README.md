# Географияи ҷаҳон

Interactive geography web app with country search, filters, detailed country cards, quiz mode, local user authentication, and downloadable geography books.

## Features

- Country search by name, capital, or region
- Filters for region and subregion
- Sorting by country name, population, or area
- Country detail modal with geographic and demographic data
- Language selection (Tajik, Russian, English)
- Dark/light theme toggle
- Quiz and friend quiz modes
- Local registration/login via Flask backend
- Included country data files and PDF book resources

## Project Structure

- `index.html` — main frontend page
- `css/style.css` — application styles
- `js/app.js` — application logic and UI behavior
- `data/` — country data and user storage
  - `countries.json` — country metadata for app display
  - `countries-full.json` — extended country dataset
  - `country-names-tg.json` — Tajik country name translations
  - `users.json` — stored user accounts (created automatically)
- `books/` — geography book PDFs
- `server.py` — Flask backend for authentication and static file serving

## Requirements

- Python 3.8+
- Flask

## Getting Started

1. Install Flask:

```bash
pip install flask
```

2. Run the server from the project root:

```bash
python server.py
```

3. Open the app in your browser:

```text
http://127.0.0.1:5000
```

## Notes

- `server.py` serves the frontend and handles `/api/register` and `/api/login`.
- User accounts are stored in `data/users.json`.
- If you open `index.html` directly in the browser, some features may not work due to CORS and API routing.

## License

This project is provided as-is. Feel free to adapt and extend it for learning and educational use.
