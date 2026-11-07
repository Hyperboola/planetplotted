"""Configurazione letta dalle variabili d'ambiente.

In locale con Docker i valori arrivano dal file .env.
Senza S3_ENDPOINT il raw viene salvato su disco in data/raw.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Storage del raw: S3/MinIO se configurato, altrimenti cartella locale
S3_ENDPOINT = os.getenv("S3_ENDPOINT")          # es. http://minio:9000
S3_BUCKET = os.getenv("S3_BUCKET", "worldviz-raw")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
LOCAL_RAW_DIR = Path(os.getenv("LOCAL_RAW_DIR", ROOT / "data" / "raw"))

# Database dei dati puliti
PG_DSN = os.getenv(
    "PG_DSN", "postgresql://worldviz:worldviz@localhost:5432/worldviz"
)

# Catalogo degli indicatori
CATALOG_FILE = ROOT / "catalog" / "indicators.yml"

# Anni da scaricare
YEAR_FROM = int(os.getenv("YEAR_FROM", "1990"))
YEAR_TO = int(os.getenv("YEAR_TO", "2030"))
