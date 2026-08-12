from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import secrets
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from db.connection import health_check as db_health_check
from db import repo
from db.google_auth import google_configured, GOOGLE_CLIENT_ID, verify_google_id_token

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
ADMINS_FILE = DATA_DIR / "admins.json"
STUDENTS_FILE = DATA_DIR / "students.json"
OLYMPIADS_FILE = DATA_DIR / "olympiads.json"
RESULTS_FILE = DATA_DIR / "results.json"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# PLACEHOLDER_PART0_CONTINUE — full content in next commits if truncated
