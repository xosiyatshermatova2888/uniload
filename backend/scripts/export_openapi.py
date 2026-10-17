"""OpenAPI sxemasini serverni ishga tushirmasdan faylga yozadi (frontend tiplarini generatsiya qilish uchun).

    python backend/scripts/export_openapi.py frontend/openapi.json
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f, ensure_ascii=False, indent=1)
print(f"OpenAPI -> {out}")
