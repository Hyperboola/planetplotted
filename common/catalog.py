"""Lettura del catalogo degli indicatori."""

import yaml

from common import config


def load(source: str | None = None) -> list[dict]:
    with open(config.CATALOG_FILE, encoding="utf-8") as f:
        items = yaml.safe_load(f)["indicators"]
    if source:
        items = [i for i in items if i["source"] == source]
    return items


def get(indicator_id: str) -> dict:
    for item in load():
        if item["id"] == indicator_id:
            return item
    raise KeyError(f"Indicatore non presente nel catalogo: {indicator_id}")
