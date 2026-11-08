"""Configurazione letta dalle variabili d'ambiente.

In locale con Docker i valori arrivano dal file .env.
Senza S3_ENDPOINT lo strato bronze viene salvato su disco in data/bronze.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Bronze: S3 (o compatibile) se configurato, altrimenti cartella locale
S3_ENDPOINT = os.getenv("S3_ENDPOINT")          # es. https://<account>.r2.cloudflarestorage.com
S3_BUCKET = os.getenv("S3_BUCKET", "worldviz-bronze")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
LOCAL_BRONZE_DIR = Path(os.getenv("LOCAL_BRONZE_DIR", ROOT / "data" / "bronze"))

# Serving: immagini e video generati
RENDERS_DIR = Path(os.getenv("RENDERS_DIR", ROOT / "data" / "renders"))

# Database: schemi silver e gold
PG_DSN = os.getenv(
    "PG_DSN", "postgresql://worldviz:worldviz@localhost:5432/worldviz"
)

# Catalogo degli indicatori
CATALOG_FILE = ROOT / "catalog" / "indicators.yml"

# Anni da scaricare
YEAR_FROM = int(os.getenv("YEAR_FROM", "1990"))
YEAR_TO = int(os.getenv("YEAR_TO", "2030"))
