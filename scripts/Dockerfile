# Archiver: nightly GitHub stars fetch -> append-only stars.json -> Postgres mirror.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STARS_JSON=/data/stars.json \
    STARS_MD=/data/STARS.md \
    TODAY_MD=/data/TODAY.md \
    SEED_JSON=/seed/stars.json \
    SCHEMA_SQL=/app/db/schema.sql

RUN pip install "psycopg[binary]>=3.2,<4"

WORKDIR /app
COPY db/schema.sql /app/db/schema.sql
COPY scripts/archive_stars.py scripts/sync_to_postgres.py scripts/archiver_loop.py /app/scripts/

VOLUME ["/data"]
CMD ["python", "/app/scripts/archiver_loop.py"]
