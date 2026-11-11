"""Reel: ogni formato ha il suo video, ogni scena si disegna, ffmpeg produce un MP4 valido."""

import json
import subprocess

import pytest
import yaml

from gold.copywriting import values
from gold.copywriting.generate import TEMPLATES_FILE, make_copy, resolve
from serving.render import carousel, reel
from serving.render.base import REEL, Slide
from tests.unit.test_copy_and_render import PAYLOADS


def texts_and_values(fmt):
    templates = yaml.safe_load(open(TEMPLATES_FILE, encoding="utf-8"))
    v = values.build(fmt, PAYLOADS[fmt])
    return resolve(make_copy(templates, fmt, PAYLOADS[fmt], 1, "technology"), v), v


def test_every_reel_has_images_and_only_the_globe_has_no_reel():
    assert set(reel.BUILDERS) <= set(carousel.BUILDERS)
    assert set(carousel.BUILDERS) - set(reel.BUILDERS) == {"globe"}


@pytest.mark.parametrize("fmt", sorted(set(PAYLOADS) & set(reel.BUILDERS)))
def test_every_scene_draws(fmt):
    t, v = texts_and_values(fmt)
    duration, draw = reel.BUILDERS[fmt](t, v, PAYLOADS[fmt])
    assert 8 <= duration <= 25           # un reel breve, adatto a Instagram
    for second in (0.5, 3, duration * 0.5, duration * 0.7, duration - 0.5):
        s = Slide(size=REEL)
        draw(s, second)
        assert len(s.rgba()) == REEL[0] * REEL[1] * 4


def test_ffmpeg_produces_a_vertical_mp4(tmp_path):
    t, v = texts_and_values("ranked")

    def short(t_, v_, p_):          # stesso montaggio, ma 1 secondo: test veloce
        _, draw = reel.ranked(t_, v_, p_)
        return 1.0, draw

    out = reel.render_video(short, t, v, PAYLOADS["ranked"], tmp_path / "reel.mp4")
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height",
         "-of", "json", str(out)], capture_output=True, text=True, check=True).stdout)
    codecs = {s["codec_name"]: s for s in info["streams"]}
    assert codecs["h264"]["width"] == 1080 and codecs["h264"]["height"] == 1920
    assert "aac" in codecs          # traccia audio muta: richiesta da alcune piattaforme
