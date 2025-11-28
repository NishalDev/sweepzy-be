#!/usr/bin/env python3
import os
import sys
import shutil
import hashlib
import urllib.request
import time
import subprocess

MODEL_URL = os.environ.get("MODEL_URL", "").strip()
MODEL_PATH = os.environ.get("MODEL_PATH", "/home/appuser/.models/best.onnx")
UVICORN_CMD = os.environ.get("UVICORN_CMD", "uvicorn main:app --host 0.0.0.0 --port 8080")

def download(url, dest, max_retries=3):
    tmp = dest + ".tmp"
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                with open(tmp, "wb") as f:
                    shutil.copyfileobj(r, f)
            os.replace(tmp, dest)
            return True
        except Exception as e:
            print(f"[prestart] download attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(2 * attempt)
    return False

if MODEL_URL:
    print(f"[prestart] MODEL_URL provided. Downloading to {MODEL_PATH} ...")
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    if not os.path.exists(MODEL_PATH):
        ok = download(MODEL_URL, MODEL_PATH)
        if not ok:
            print("[prestart] Failed to download model. Exiting.", file=sys.stderr)
            sys.exit(1)
    else:
        print("[prestart] Model already exists; skipping download.")
else:
    print("[prestart] No MODEL_URL provided; running without model (if code handles this).")

# Exec uvicorn (replace this process)
args = UVICORN_CMD.split()
print(f"[prestart] Exec: {args}")
os.execvp(args[0], args)
