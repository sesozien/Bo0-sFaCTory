#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

VENV=".venv"
PYTHON="$VENV/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "[1/2] إنشاء بيئة التشغيل لأول مرة..."
  python3 -m venv "$VENV"
  echo "[2/2] تثبيت المكتبات مرة واحدة فقط..."
  "$PYTHON" -m pip install -r requirements.txt
  echo "تم التثبيت. لن يتم تنزيل المكتبات في التشغيلات القادمة."
fi

export BO0_OFFLINE_MODE=1
echo "تشغيل Bo0 Factory محليًا بدون إعادة تثبيت المكتبات..."
exec "$PYTHON" -m streamlit run app.py --server.headless false
