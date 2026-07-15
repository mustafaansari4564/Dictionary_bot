import os
from dotenv import load_dotenv

load_dotenv()

# ── Credentials ───────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GUILD_ID  = int(os.getenv("GUILD_ID", "0"))

# ── Access control ────────────────────────────────────────────────────────────
COD_ROLE_ID          = int(os.getenv("COD_ROLE_ID",          "0"))
LIBRARY_PASS_ROLE_ID = int(os.getenv("LIBRARY_PASS_ROLE_ID", "0"))
LIBRARY_CHANNEL_ID   = int(os.getenv("LIBRARY_CHANNEL_ID",   "0"))

# ── Arabic dictionaries ───────────────────────────────────────────────────────
DICTIONARIES = {
    "Lisan al-Arab (لسان العرب)":      "/home/container/lughat_bot/data/lisan_index.db",
    "Qamus al-Muhit (القاموس المحيط)": "/home/container/lughat_bot/data/qamus_al_muhit_index.db",
}

# Individual dict paths (for single-dict commands)
LISAN_DB = "/home/container/lughat_bot/data/lisan_index.db"
QAMUS_DB = "/home/container/lughat_bot/data/qamus_al_muhit_index.db"

# ── English dictionaries ──────────────────────────────────────────────────────
ENGLISH_DICTS = {
    "Lane's Lexicon— E.W. Lane (1863–1893)": "/home/container/lughat_bot/data/lane_lexicon.db",
}

# ── ejtaal scan dictionaries (/lughat-scan) ───────────────────────────────────
# SQLite index built by setup_ejtaal.py — contains page numbers for 44 dicts.
EJTAAL_DB = "/home/container/lughat_bot/data/ejtaal_index.db"

# Base URL for page images.
# Phase 1 (hotlink from ejtaal.net — no download needed):
EJTAAL_IMAGE_BASE = "https://ejtaal.net/aa/img"
# Phase 2 (self-hosted — swap to this after uploading images to your server):
# EJTAAL_IMAGE_BASE = "/home/container/lughat_bot/data/img"

# Dicts shown by default when no language filter is chosen.
# Full code list: umj uqw umr ums ulq uqa uqq lqn hw4 ll ls sg ha br pr vi la amj kz mn ...
EJTAAL_DEFAULT_DICTS = ['umj', 'uqw', 'umr', 'hw4', 'll']

# ── Embed colors ──────────────────────────────────────────────────────────────
EMBED_COLOR         = 0x1B6B3A   # dark green  — Arabic
ENGLISH_EMBED_COLOR = 0x1A5276   # dark blue   — English
SCAN_EMBED_COLOR    = 0x6C3483   # purple      — ejtaal scan
EMBED_LIMIT         = 3800