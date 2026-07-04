#!/bin/sh
set -e

echo "[entrypoint] aguardando o Postgres..."
python - <<'PY'
import os, time, psycopg2
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
for i in range(60):
    try:
        psycopg2.connect(url).close()
        print("[entrypoint] banco OK")
        break
    except Exception as e:
        print(f"[entrypoint] tentativa {i+1}/60: {e}")
        time.sleep(2)
else:
    raise SystemExit("[entrypoint] banco nunca respondeu")
PY

echo "[entrypoint] aplicando migrações..."
alembic upgrade head

echo "[entrypoint] subindo a API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
