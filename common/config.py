"""Configurazione letta dalle variabili d'ambiente.

In locale con Docker i valori arrivano dal file .env; in produzione dai
segreti gestiti da Terraform. Nel codice non ci sono credenziali.
Senza S3_ENDPOINT i file restano su disco (data/bronze e data/renders).
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Object storage (Cloudflare R2, S3 o compatibile). I bucket li crea Terraform.
S3_ENDPOINT = os.getenv("S3_ENDPOINT")          # es. https://<account>.r2.cloudflarestorage.com
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BRONZE_BUCKET = os.getenv("S3_BRONZE_BUCKET", "planetplotted-bronze")
S3_RENDERS_BUCKET = os.getenv("S3_RENDERS_BUCKET", "planetplotted-renders")

# Cartelle locali: il bronze se S3 non è configurato, i render sempre
# (con S3 vengono anche caricati nel bucket)
LOCAL_BRONZE_DIR = Path(os.getenv("LOCAL_BRONZE_DIR", ROOT / "data" / "bronze"))
RENDERS_DIR = Path(os.getenv("RENDERS_DIR", ROOT / "data" / "renders"))

# Database (schemi silver e gold): obbligatorio, nessun valore predefinito
PG_DSN = os.getenv("PG_DSN")

# Catalogo degli indicatori
CATALOG_FILE = ROOT / "catalog" / "indicators.yml"

# Anni da scaricare
YEAR_FROM = int(os.getenv("YEAR_FROM", "1990"))
YEAR_TO = int(os.getenv("YEAR_TO", "2040"))
