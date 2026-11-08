"""Bronze: salvataggio e lettura dei file scaricati, così come arrivano.

Lo stesso codice funziona con MinIO in locale, con S3 nel cloud
o con una semplice cartella su disco.
"""

import json
from pathlib import Path

from common import config


def _s3():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
    )


def bronze_key(source: str, dataset: str, run_date: str) -> str:
    """Percorso standard: <fonte>/<dataset>/run_date=<data>/data.json"""
    return f"{source}/{dataset}/run_date={run_date}/data.json"


def write_json(key: str, payload) -> str:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if config.S3_ENDPOINT:
        s3 = _s3()
        try:
            s3.head_bucket(Bucket=config.S3_BUCKET)
        except Exception:
            s3.create_bucket(Bucket=config.S3_BUCKET)
        s3.put_object(Bucket=config.S3_BUCKET, Key=key, Body=body)
        return f"s3://{config.S3_BUCKET}/{key}"
    path = Path(config.LOCAL_BRONZE_DIR) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return str(path)


def read_json(key: str):
    if config.S3_ENDPOINT:
        obj = _s3().get_object(Bucket=config.S3_BUCKET, Key=key)
        return json.loads(obj["Body"].read())
    return json.loads((Path(config.LOCAL_BRONZE_DIR) / key).read_text("utf-8"))
