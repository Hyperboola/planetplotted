"""Object storage: bronze (file scaricati) e render (slide e video).

Con S3_ENDPOINT impostato si usa S3 o un servizio compatibile (Cloudflare R2);
senza, tutto resta su disco. I bucket non vengono mai creati dal codice:
li crea Terraform, con i permessi giusti.
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
        _s3().put_object(Bucket=config.S3_BRONZE_BUCKET, Key=key, Body=body)
        return f"s3://{config.S3_BRONZE_BUCKET}/{key}"
    path = Path(config.LOCAL_BRONZE_DIR) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return str(path)


def read_json(key: str):
    if config.S3_ENDPOINT:
        obj = _s3().get_object(Bucket=config.S3_BRONZE_BUCKET, Key=key)
        return json.loads(obj["Body"].read())
    return json.loads((Path(config.LOCAL_BRONZE_DIR) / key).read_text("utf-8"))


def publish_render(local_path: Path, key: str) -> None:
    """Carica una slide o un video nel bucket dei render, se S3 è configurato.
    key è il percorso relativo (es. 2026-11-09/post_1/slide_01.png), uguale
    in locale e nel bucket: è quello salvato in gold.post_queue."""
    if not config.S3_ENDPOINT:
        return
    content_type = "video/mp4" if key.endswith(".mp4") else "image/png"
    _s3().upload_file(str(local_path), config.S3_RENDERS_BUCKET, key,
                      ExtraArgs={"ContentType": content_type})
