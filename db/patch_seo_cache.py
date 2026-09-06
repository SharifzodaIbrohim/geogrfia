"""SEO static files + cache headers for CSS/JS/favicon."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def install(app):
    try:
        from flask import Response, request, send_from_directory
    except Exception:
        return

    # Ensure robots / sitemap / favicon are public
    try:
        paths = set(getattr(app, "config", {}).get("PUBLIC_PATHS") or [])
        for p in ("robots.txt", "sitemap.xml", "favicon.svg", "favicon.ico"):
            paths.add(p)
        app.config["PUBLIC_PATHS"] = paths
    except Exception:
        pass

    # Explicit routes (work even if static middleware differs)
    @app.route("/robots.txt")
    def seo_robots():
        p = ROOT / "robots.txt"
        if p.is_file():
            return Response(p.read_text(encoding="utf-8"), mimetype="text/plain; charset=utf-8")
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
            return Response(p.read_text(encoding="utf-8"), mimetype="application/xml; charset=utf-8")
        return Response("<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'></urlset>",
                        mimetype="application/xml; charset=utf-8")

    @app.route("/favicon.svg")
    def seo_favicon_svg():
        p = ROOT / "favicon.svg"
        if p.is_file():
            return Response(p.read_bytes(), mimetype="image/svg+xml")
        return Response("", status=404)

    @app.after_request
    def seo_cache_headers(resp):
        try:
            path = (request.path or "").lower()
            # Long cache for versioned-ish static assets
            if path.endswith((".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff2", ".woff")):
                if "cache-control" not in {k.lower() for k in resp.headers.keys()} or "no-cache" in (resp.headers.get("Cache-Control") or "").lower():
                    resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
            elif path in ("/robots.txt", "/sitemap.xml", "/favicon.svg", "/favicon.ico"):
                resp.headers["Cache-Control"] = "public, max-age=86400"
            elif path.endswith(".html") or path in ("/",):
                # HTML stays relatively fresh
                resp.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
        except Exception:
            pass
        return resp

    print("[boot] patch_seo_cache installed")
