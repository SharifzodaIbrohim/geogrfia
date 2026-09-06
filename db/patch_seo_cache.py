"""SEO: robots/sitemap/favicon routes + meta injection + static cache headers."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# path -> (title, description, indexable)
_SEO = {
    "/": (
        "Geografia.tj — Платформаи ҷуғрофия ва олимпиада",
        "Платформаи ҷуғрофия, олимпиада ва викторина барои хонандагони Тоҷикистон. Кишварҳо, курсҳо, рейтинг ва имтиҳонҳои онлайн.",
        True,
    ),
    "/countries": (
        "Кишварҳо — Geografia.tj",
        "Маълумоти интерактивӣ дар бораи ҳамаи кишварҳои ҷаҳон: аҳолӣ, масоҳат, пойтахт, харита ва ҷустуҷӯ.",
        True,
    ),
    "/courses": (
        "Курсҳо ва китобҳо — Geografia.tj",
        "Китобҳои ҷуғрофия, мақолаҳо ва маводҳои омӯзишӣ барои синфҳои 7–11.",
        True,
    ),
    "/quiz": (
        "Викторинаҳо — Geografia.tj",
        "Викторинаҳои онлайн аз ҷуғрофия. Худсанҷӣ ва омодагии олимпиада.",
        True,
    ),
    "/leaderboard": (
        "Рейтинг — Geografia.tj",
        "Рейтинги беҳтарин иштирокчиёни олимпиада ва викторинаҳои ҷуғрофия.",
        True,
    ),
    "/student": (
        "Хонанда — Олимпиада ва викторина",
        "Портали хонанда барои олимпиада ва викторина.",
        False,
    ),
    "/profile": (
        "Профил — Geografia.tj",
        "Профили корбар дар платформаи Geografia.tj.",
        False,
    ),
    "/admin": (
        "Admin — Geografia.tj",
        "Панели идоракунӣ.",
        False,
    ),
}


def _meta_block(path: str, title: str, description: str, indexable: bool) -> str:
    url = "https://geografia.tj" + (path if path != "/" else "/")
    robots = "index,follow" if indexable else "noindex,nofollow"
    og = ""
    if indexable:
        og = f"""
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Geografia.tj" />
  <meta property="og:locale" content="tg_TJ" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:image" content="https://geografia.tj/favicon.svg" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{description}" />"""
    jsonld = ""
    if path == "/":
        jsonld = """
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"WebSite","name":"Geografia.tj","url":"https://geografia.tj/","description":"Платформаи ҷуғрофия, олимпиада ва викторина барои хонандагони Тоҷикистон.","inLanguage":["tg","ru","en"]}
  </script>"""
    return f"""
  <!-- geo-seo -->
  <title>{title}</title>
  <meta name="description" content="{description}" />
  <meta name="theme-color" content="#0a120e" />
  <meta name="robots" content="{robots}" />
  <link rel="canonical" href="{url}" />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="apple-touch-icon" href="/favicon.svg" />{og}{jsonld}
  <!-- /geo-seo -->
"""


def install(app):
    try:
        from flask import Response, request
    except Exception:
        return

    try:
        paths = set(getattr(app, "config", {}).get("PUBLIC_PATHS") or [])
        for p in ("robots.txt", "sitemap.xml", "favicon.svg", "favicon.ico"):
            paths.add(p)
        app.config["PUBLIC_PATHS"] = paths
    except Exception:
        pass

    @app.route("/robots.txt")
    def seo_robots():
        p = ROOT / "robots.txt"
        if p.is_file():
            body = p.read_text(encoding="utf-8")
        else:
            body = (
                "User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\n"
                "Disallow: /student\nDisallow: /profile\n\n"
                "Sitemap: https://geografia.tj/sitemap.xml\n"
            )
        return Response(body, mimetype="text/plain; charset=utf-8")

    @app.route("/sitemap.xml")
    def seo_sitemap():
        p = ROOT / "sitemap.xml"
        if p.is_file():
            body = p.read_text(encoding="utf-8")
        else:
            body = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://geografia.tj/</loc><priority>1.0</priority></url>
  <url><loc>https://geografia.tj/countries</loc><priority>0.9</priority></url>
  <url><loc>https://geografia.tj/courses</loc><priority>0.8</priority></url>
  <url><loc>https://geografia.tj/quiz</loc><priority>0.8</priority></url>
  <url><loc>https://geografia.tj/leaderboard</loc><priority>0.7</priority></url>
</urlset>
"""
        return Response(body, mimetype="application/xml; charset=utf-8")

    @app.route("/favicon.svg")
    def seo_favicon_svg():
        p = ROOT / "favicon.svg"
        if p.is_file():
            return Response(p.read_bytes(), mimetype="image/svg+xml")
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="14" fill="#0a120e"/>'
            '<circle cx="32" cy="32" r="18" fill="none" stroke="#70db97" stroke-width="3"/>'
            '<text x="32" y="38" text-anchor="middle" font-family="system-ui,sans-serif" '
            'font-weight="800" font-size="16" fill="#70db97">Г</text></svg>'
        )
        return Response(svg, mimetype="image/svg+xml")

    @app.after_request
    def seo_after(resp):
        try:
            path = request.path or "/"
            if path != "/" and path.endswith("/"):
                path = path.rstrip("/") or "/"

            # Cache policy
            pl = path.lower()
            if pl.endswith((".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff2", ".woff")):
                resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
            elif pl in ("/robots.txt", "/sitemap.xml", "/favicon.svg", "/favicon.ico"):
                resp.headers["Cache-Control"] = "public, max-age=86400"
            elif path in _SEO or pl.endswith(".html"):
                resp.headers["Cache-Control"] = "public, max-age=60, must-revalidate"

            # Inject SEO meta into HTML
            ctype = (resp.mimetype or "").lower()
            if "html" in ctype and path in _SEO and resp.status_code == 200:
                data = resp.get_data(as_text=True)
                if data and "<!-- geo-seo -->" not in data and "<head" in data.lower():
                    title, desc, indexable = _SEO[path]
                    block = _meta_block(path, title, desc, indexable)
                    import re
                    data2 = re.sub(r"<title>[^<]*</title>", "", data, count=1, flags=re.I)
                    data2 = re.sub(
                        r"(<head[^>]*>)",
                        r"\1" + block,
                        data2,
                        count=1,
                        flags=re.I,
                    )
                    resp.set_data(data2)
                    resp.headers["Content-Length"] = str(len(resp.get_data()))
        except Exception as e:
            try:
                print("[seo] after_request skip:", e)
            except Exception:
                pass
        return resp

    print("[boot] patch_seo_cache installed (routes+inject+cache)")
