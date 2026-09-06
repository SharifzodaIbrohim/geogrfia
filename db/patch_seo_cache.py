"""SEO Phase 1+2: robots/sitemap/favicon/og + meta injection + Google verify."""
from __future__ import annotations

import base64 as _b64mod
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Embedded 48x48 PNG favicon (Bing/Google prefer PNG/ICO over SVG)
_FAVICON_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAABoElEQVR42u2aMW7DMAxFZUJThw69Qg7QMejQqeglegDP2YKiaxafIICLniQn8Ji5yEWCJO6kQE4sWaJJhUqt1bL1n0iRlOTi4emxVY5WNpWS0Or50vms6AOQIjwE5ArgUryPPkUb0tMBsDvfWrgPxNZ2BjAdpAl3gRidINnnQ0BAkr9jFjLkOPu2FYrF77qlnn3fpFCNY8bQKUSHRBNs0xzCfcLs/hSRT1OJDxVh9zPvl02FhtCphPtgyqZCWwNuJX7IKmwAXDkD+z3AzD5XwrNdihwgVa0UC6EpB5+9P6u31Ye3T3s6qe+XT7IxQdLsY6ygOYX8vH6p4/7ACgsq8wbS3CfWje7fAhPABDABZA6AKbAot6hD4Tt7C5CWErvNVu02W3lrILUbxWT//xOFUlkhtvaKsgA3BKZwhLGDUYtnT2RjjkBCxMeW7agwSnEgNVY4SR6o58vO8WCImNizVPZE1rewQ12LYpd3vh+g3DZy3w/Y39e2G1DvZ1Psm4EzNHLmik4YzeFyz2Xl+7nodpkoq18NpK+FoJ89JIL4vOAPxeTjKbNUgO4AAAAASUVORK5CYII="


def _og_png_bytes():
    p = ROOT / "og-default.png"
    if p.is_file():
        return p.read_bytes()
    for candidate in (ROOT / "db" / "_og_png_b64.txt", ROOT / "_og_png_b64.txt"):
        if candidate.is_file() and candidate.stat().st_size > 1000:
            try:
                return _b64mod.b64decode(candidate.read_text(encoding="ascii").strip())
            except Exception:
                pass
    parts = sorted((ROOT / "db").glob("_og_png_b64_*.txt"))
    if not parts:
        parts = sorted(ROOT.glob("_og_png_b64_*.txt"))
    if parts:
        try:
            joined = "".join(x.read_text(encoding="ascii").strip() for x in parts)
            if len(joined) > 1000:
                return _b64mod.b64decode(joined)
        except Exception:
            pass
    return b""


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

_OG_IMAGE = "https://geografia.tj/og-default.png"
_FAVICON_SVG = "https://geografia.tj/favicon.svg"
_FAVICON_PNG = "https://geografia.tj/favicon.png"
_GSC_VERIFY = "OAUh0qgRBDH2IJCC7bg0nRG3MiNVWI9RZhrWXEaHc4U"


def _meta_block(path: str, title: str, description: str, indexable: bool) -> str:
    url = "https://geografia.tj" + (path if path != "/" else "/")
    robots = "index,follow" if indexable else "noindex,nofollow"
    hreflang = f"""
  <link rel="alternate" hreflang="tg" href="{url}" />
  <link rel="alternate" hreflang="ru" href="{url}" />
  <link rel="alternate" hreflang="en" href="{url}" />
  <link rel="alternate" hreflang="x-default" href="{url}" />"""
    og = ""
    if indexable:
        og = f"""
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Geografia.tj" />
  <meta property="og:locale" content="tg_TJ" />
  <meta property="og:locale:alternate" content="ru_RU" />
  <meta property="og:locale:alternate" content="en_US" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:image" content="{_OG_IMAGE}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content="Geografia.tj" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{description}" />
  <meta name="twitter:image" content="{_OG_IMAGE}" />"""
    jsonld = ""
    if path == "/":
        jsonld = f"""
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@graph":[
    {{"@type":"WebSite","name":"Geografia.tj","url":"https://geografia.tj/","description":"Платформаи ҷуғрофия, олимпиада ва викторина барои хонандагони Тоҷикистон.","inLanguage":["tg","ru","en"],"potentialAction":{{"@type":"SearchAction","target":"https://geografia.tj/countries?q={{search_term_string}}","query-input":"required name=search_term_string"}}}},
    {{"@type":"Organization","name":"Geografia.tj","url":"https://geografia.tj/","logo":"{_FAVICON_PNG}"}}
  ]}}
  </script>"""
    return f"""
  <!-- geo-seo -->
  <title>{title}</title>
  <meta name="description" content="{description}" />
  <meta name="theme-color" content="#0a120e" />
  <meta name="robots" content="{robots}" />
  <meta name="google-site-verification" content="{_GSC_VERIFY}" />
  <link rel="canonical" href="{url}" />
  <link rel="icon" href="{_FAVICON_SVG}" type="image/svg+xml" />
  <link rel="icon" href="{_FAVICON_PNG}" type="image/png" sizes="48x48" />
  <link rel="shortcut icon" href="{_FAVICON_PNG}" />
  <link rel="apple-touch-icon" href="{_FAVICON_PNG}" />{hreflang}{og}{jsonld}
  <!-- /geo-seo -->
"""


def install(app):
    try:
        from flask import Response, request
    except Exception:
        return

    try:
        paths = set(getattr(app, "config", {}).get("PUBLIC_PATHS") or [])
        for p in (
            "robots.txt", "sitemap.xml", "favicon.svg", "favicon.ico", "favicon.png",
            "og-default.png", "db/_og_png_b64.txt", "_og_png_b64.txt",
        ):
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

    @app.route("/favicon.png")
    def seo_favicon_png():
        p = ROOT / "favicon.png"
        if p.is_file():
            return Response(p.read_bytes(), mimetype="image/png")
        try:
            return Response(_b64mod.b64decode(_FAVICON_PNG_B64), mimetype="image/png")
        except Exception:
            return Response(b"", status=404)

    @app.route("/favicon.ico")
    def seo_favicon_ico():
        p = ROOT / "favicon.ico"
        if p.is_file():
            return Response(p.read_bytes(), mimetype="image/x-icon")
        try:
            return Response(_b64mod.b64decode(_FAVICON_PNG_B64), mimetype="image/png")
        except Exception:
            return Response(b"", status=404)

    @app.route("/og-default.png")
    def seo_og_image():
        data = _og_png_bytes()
        if data:
            return Response(data, mimetype="image/png")
        try:
            return Response(_b64mod.b64decode(_FAVICON_PNG_B64), mimetype="image/png")
        except Exception:
            return Response(b"", status=404)

    @app.after_request
    def seo_after(resp):
        try:
            path = request.path or "/"
            if path != "/" and path.endswith("/"):
                path = path.rstrip("/") or "/"

            pl = path.lower()
            if pl.endswith((".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff2", ".woff", ".ico")):
                resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
            elif pl in ("/robots.txt", "/sitemap.xml", "/favicon.svg", "/favicon.ico", "/favicon.png", "/og-default.png"):
                resp.headers["Cache-Control"] = "public, max-age=86400"
            elif path in _SEO or pl.endswith(".html"):
                resp.headers["Cache-Control"] = "public, max-age=60, must-revalidate"

            ctype = (resp.mimetype or "").lower()
            if "html" in ctype and path in _SEO and resp.status_code == 200:
                try:
                    if getattr(resp, "direct_passthrough", False):
                        resp.direct_passthrough = False
                except Exception:
                    pass
                data = resp.get_data(as_text=True)
                if data and "<!-- geo-seo -->" not in data and "<head" in data.lower():
                    title, desc, indexable = _SEO[path]
                    block = _meta_block(path, title, desc, indexable)
                    data2 = re.sub(r"<title>[^<]*</title>", "", data, count=1, flags=re.I)
                    data2 = re.sub(r"(<head[^>]*>)", r"\1" + block, data2, count=1, flags=re.I)
                    resp.set_data(data2)
                    try:
                        resp.headers["Content-Length"] = str(len(resp.get_data()))
                    except Exception:
                        pass
        except Exception as e:
            try:
                print("[seo] after_request skip:", e)
            except Exception:
                pass
        return resp

    print("[boot] patch_seo_cache installed (GSC verify + favicon png/svg)")
