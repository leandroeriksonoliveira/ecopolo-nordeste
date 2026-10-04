#!/usr/bin/env python3
"""
Gera os bitmaps derivados da identidade: ícones de aplicativo e cartão de
compartilhamento (Open Graph).

Executar apenas quando a identidade visual mudar:

    python3 tools/make-images.py

Requisitos: Google Chrome instalado (usado em modo headless para rasterizar os
SVG e o cartão) e Pillow (redimensionamento e conversão).
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "img"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]


def chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if candidate and pathlib.Path(candidate).exists():
            return candidate
    raise SystemExit("Chrome ou Chromium não encontrado — necessário para rasterizar.")


def shot(html: pathlib.Path, out: pathlib.Path, width: int, height: int) -> None:
    subprocess.run(
        [
            chrome(),
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out}",
            f"--window-size={width},{height}",
            html.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
    )


def build_icons() -> None:
    from PIL import Image

    favicon = (IMG / "favicon.svg").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        page = pathlib.Path(tmp) / "icon.html"
        page.write_text(
            "<!doctype html><meta charset=utf-8>"
            "<style>html,body{margin:0;width:512px;height:512px;overflow:hidden}"
            "svg{display:block;width:512px;height:512px}</style>" + favicon,
            encoding="utf-8",
        )
        raw = pathlib.Path(tmp) / "icon-512.png"
        shot(page, raw, 512, 512)

        base = Image.open(raw).convert("RGBA")
        base.save(IMG / "icon-512.png", optimize=True)
        base.resize((192, 192), Image.LANCZOS).save(IMG / "icon-192.png", optimize=True)
        base.resize((180, 180), Image.LANCZOS).save(IMG / "apple-touch-icon.png", optimize=True)
        base.resize((32, 32), Image.LANCZOS).save(
            IMG / "favicon.ico", sizes=[(16, 16), (32, 32)]
        )
    print("  ✓ ícones de aplicativo")


OG_TEMPLATE = """<!doctype html>
<meta charset="utf-8" />
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; width: 1200px; height: 630px; overflow: hidden; }
  body {
    position: relative;
    background:
      radial-gradient(70rem 36rem at 86% -24%, rgba(19,138,72,.55), transparent 62%),
      linear-gradient(162deg, #06190f 0%, #04120a 55%, #020a06 100%);
    color: #eef4ee;
    font-family: "Inter Tight", "Inter", -apple-system, "Segoe UI", Roboto, sans-serif;
    padding: 72px 80px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .mesh {
    position: absolute; inset: 0; opacity: .42;
    background-image:
      linear-gradient(transparent 59px, rgba(238,244,238,.1) 59px),
      linear-gradient(90deg, transparent 59px, rgba(238,244,238,.1) 59px);
    background-size: 60px 60px;
    mask-image: radial-gradient(75% 75% at 70% 25%, #000 15%, transparent 85%);
    -webkit-mask-image: radial-gradient(75% 75% at 70% 25%, #000 15%, transparent 85%);
  }
  .watermark {
    position: absolute; right: -120px; top: -60px;
    width: 720px; color: rgba(94,194,137,.11);
  }
  .watermark svg { width: 100%; height: auto; display: block; }
  .top { position: relative; display: flex; align-items: center; gap: 20px; }
  .top .mark { width: 74px; color: #fff; }
  .top .mark svg { width: 100%; height: auto; display: block; }
  .top .word { width: 300px; color: #fff; }
  .top .word svg { width: 100%; height: auto; display: block; }
  h1 {
    position: relative;
    font-size: 72px; line-height: 1.02; letter-spacing: -.034em;
    font-weight: 680; margin: 0 0 22px; max-width: 17ch;
  }
  h1 em { font-style: normal; color: #e8c977; }
  p.sub {
    position: relative; margin: 0;
    font-size: 25px; line-height: 1.42; color: #bdcdc1; max-width: 30ch;
    font-family: "Inter", -apple-system, "Segoe UI", Roboto, sans-serif;
  }
  .foot {
    position: relative; display: flex; align-items: center; gap: 28px;
    font-size: 17px; color: #8fa394; letter-spacing: .02em;
    border-top: 1px solid rgba(238,244,238,.16); padding-top: 24px;
    font-family: "Inter", -apple-system, "Segoe UI", Roboto, sans-serif;
  }
  .foot b { color: #e8c977; font-weight: 620; letter-spacing: .14em; font-size: 14px; }
</style>
<div class="mesh"></div>
<div class="watermark">__MARK__</div>
<div class="top">
  <span class="mark">__MARK__</span>
  <span class="word">__WORD__</span>
</div>
<div>
  <h1>Infraestrutura verde de <em>hiperescala</em> no Nordeste</h1>
  <p class="sub">
    Energia renovável off-grid, gestão hídrica em ciclo fechado e
    desenvolvimento industrial regional.
  </p>
</div>
<div class="foot">
  <b>ECOPOLONORDESTE.COM.BR</b>
  <span>Alagoas · Paraíba · Ceará</span>
  <span>CNPJ 44.185.321/0001-83</span>
</div>
"""


def build_og() -> None:
    from PIL import Image

    def inline(name: str) -> str:
        svg = (IMG / name).read_text(encoding="utf-8")
        return re.sub(r'\s(?:role|aria-label)="[^"]*"', "", svg)

    html = OG_TEMPLATE.replace("__MARK__", inline("logo-mark.svg")).replace(
        "__WORD__", inline("logo-wordmark.svg")
    )
    with tempfile.TemporaryDirectory() as tmp:
        page = pathlib.Path(tmp) / "og.html"
        page.write_text(html, encoding="utf-8")
        raw = pathlib.Path(tmp) / "og.png"
        shot(page, raw, 1200, 630)
        Image.open(raw).convert("RGB").save(
            IMG / "og-default.png", optimize=True, quality=92
        )
    print("  ✓ cartão de compartilhamento (1200×630)")


if __name__ == "__main__":
    print("Gerando bitmaps da identidade…\n")
    build_icons()
    build_og()
    print("\nConcluído.")
    sys.exit(0)
