#!/usr/bin/env python3
"""
Verificação automática do site gerado.

    python3 tools/check.py

Checa, sem rede: links internos e âncoras, unicidade de título e descrição,
presença de canonical / Open Graph / JSON-LD, identidade legal e perfis sociais
em todas as páginas, rótulo de cada campo de formulário, atributos de segurança
em links externos, alternativa textual de imagem, hierarquia de títulos,
referências a ícones do sprite e itens do sitemap.
"""

from __future__ import annotations

import html.parser
import json
import pathlib
import re
import sys
from urllib.parse import urldefrag, urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = sorted(p for p in ROOT.glob("*.html"))

CNPJ = "44.185.321/0001-83"
LINKEDIN = "linkedin.com/company/ecopolonordeste"
INSTAGRAM = "instagram.com/ecopolonordeste"

problems: list[str] = []
notes: list[str] = []


def fail(page: str, message: str) -> None:
    problems.append(f"{page}: {message}")


class Doc(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[dict] = []
        self.images: list[dict] = []
        self.headings: list[tuple[int, str]] = []
        self.labels_for: set[str] = set()
        self.controls: list[dict] = []
        self.uses: list[str] = []
        self.symbols: set[str] = set()
        self.iframes: list[dict] = []
        self._heading: int | None = None
        self._text: list[str] = []
        self._in_label = False
        self._label_text: list[str] = []
        self._label_wraps: list[dict] = []

    def handle_starttag(self, tag, attrs_list):
        attrs = dict(attrs_list)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a":
            self.links.append(attrs)
        elif tag == "img":
            self.images.append(attrs)
        elif tag == "iframe":
            self.iframes.append(attrs)
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading = int(tag[1])
            self._text = []
        elif tag == "label":
            self._in_label = True
            self._label_text = []
            self._label_wraps = []
            if attrs.get("for"):
                self.labels_for.add(attrs["for"])
        elif tag in ("input", "select", "textarea"):
            record = dict(attrs, _tag=tag)
            self.controls.append(record)
            if self._in_label:
                self._label_wraps.append(record)
        elif tag == "use":
            ref = attrs.get("href") or attrs.get("xlink:href") or ""
            if ref.startswith("#"):
                self.uses.append(ref[1:])
        elif tag == "symbol" and attrs.get("id"):
            self.symbols.add(attrs["id"])

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._heading:
            self.headings.append((self._heading, "".join(self._text).strip()))
            self._heading = None
        elif tag == "label":
            text = "".join(self._label_text).strip()
            for control in self._label_wraps:
                control["_wrapped_label"] = text
            self._in_label = False

    def handle_data(self, data):
        if self._heading:
            self._text.append(data)
        if self._in_label:
            self._label_text.append(data)


def parse(path: pathlib.Path) -> tuple[Doc, str]:
    raw = path.read_text(encoding="utf-8")
    doc = Doc()
    doc.feed(raw)
    return doc, raw


def meta(raw: str, pattern: str) -> str | None:
    match = re.search(pattern, raw, re.I)
    return match.group(1) if match else None


def main() -> int:
    if not PAGES:
        print("Nenhum HTML encontrado. Rode tools/build.py primeiro.")
        return 1

    titles: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    ids_by_page: dict[str, set[str]] = {}
    docs: dict[str, tuple[Doc, str]] = {}

    for path in PAGES:
        docs[path.name] = parse(path)
        ids_by_page[path.name] = docs[path.name][0].ids

    for path in PAGES:
        name = path.name
        doc, raw = docs[name]

        # ---------------------------------------------------- metadados
        title = meta(raw, r"<title>(.*?)</title>")
        description = meta(raw, r'<meta name="description" content="(.*?)"')
        canonical = meta(raw, r'<link rel="canonical" href="(.*?)"')

        if not title:
            fail(name, "sem <title>")
        elif title in titles:
            fail(name, f"título duplicado com {titles[title]}")
        else:
            titles[title] = name

        if not description:
            fail(name, "sem meta description")
        elif description in descriptions:
            fail(name, f"descrição duplicada com {descriptions[description]}")
        else:
            descriptions[description] = name
            if len(description) < 70 or len(description) > 320:
                notes.append(f"{name}: descrição com {len(description)} caracteres")

        if not canonical:
            fail(name, "sem link canonical")

        for prop in ("og:title", "og:description", "og:image", "og:url", "og:type"):
            if f'property="{prop}"' not in raw:
                fail(name, f"sem {prop}")
        if 'name="twitter:card"' not in raw:
            fail(name, "sem cartão twitter")
        if 'name="robots"' not in raw:
            fail(name, "sem diretiva robots")
        if 'lang="pt-BR"' not in raw:
            fail(name, "sem idioma pt-BR no <html>")

        # ---------------------------------------------------------- JSON-LD
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', raw, re.S
        )
        if not blocks and name not in ("404.html",):
            fail(name, "sem dados estruturados JSON-LD")
        org_found = False
        for block in blocks:
            try:
                data = json.loads(block)
            except json.JSONDecodeError as err:
                fail(name, f"JSON-LD inválido: {err}")
                continue
            if data.get("@type") == "Organization":
                org_found = True
                if data.get("taxID") != CNPJ:
                    fail(name, "Organization sem taxID com o CNPJ correto")
                same_as = data.get("sameAs") or []
                if not any(LINKEDIN in s for s in same_as):
                    fail(name, "Organization sem LinkedIn em sameAs")
                if not any(INSTAGRAM in s for s in same_as):
                    fail(name, "Organization sem Instagram em sameAs")
        if name == "index.html" and not org_found:
            fail(name, "home sem JSON-LD Organization")

        # -------------------------------------------- identidade e perfis
        if CNPJ not in raw:
            fail(name, "CNPJ ausente na página")
        if "Eco Polo Nordeste LTDA" not in raw:
            fail(name, "razão social ausente na página")
        if LINKEDIN not in raw:
            fail(name, "link do LinkedIn ausente")
        if INSTAGRAM not in raw:
            fail(name, "link do Instagram ausente")

        # ------------------------------------------- estrutura e acesso
        if raw.count("<h1") != 1:
            fail(name, f"deveria ter exatamente um h1, tem {raw.count('<h1')}")
        if 'class="skip-link"' not in raw:
            fail(name, "sem link de atalho para o conteúdo")
        if 'id="conteudo"' not in raw:
            fail(name, "sem landmark principal #conteudo")

        levels = [level for level, _ in doc.headings]
        for before, after in zip(levels, levels[1:]):
            if after > before + 1:
                fail(name, f"salto de título h{before} → h{after}")

        for image in doc.images:
            if "alt" not in image:
                fail(name, f"imagem sem alt: {image.get('src', '?')}")

        for frame in doc.iframes:
            if not frame.get("title"):
                fail(name, "iframe sem title")

        # ----------------------------------------------------- formulários
        for control in doc.controls:
            if control.get("type") in ("hidden", "submit", "button"):
                continue
            control_id = control.get("id")
            has_label = (
                (control_id and control_id in doc.labels_for)
                or control.get("_wrapped_label")
                or control.get("aria-label")
                or control.get("aria-labelledby")
            )
            if not has_label:
                fail(
                    name,
                    f"campo sem rótulo: <{control['_tag']} name={control.get('name')!r}>",
                )

        # --------------------------------------------- links e referências
        for link in doc.links:
            href = link.get("href", "").strip()
            if not href:
                fail(name, "link sem href")
                continue
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue

            parsed = urlparse(href)
            if parsed.scheme in ("http", "https"):
                rel = (link.get("rel") or "").lower()
                if link.get("target") == "_blank" and "noopener" not in rel:
                    fail(name, f"link externo em nova aba sem noopener: {href}")
                continue

            target, fragment = urldefrag(href)
            if not target:
                if fragment and fragment not in doc.ids:
                    fail(name, f"âncora inexistente nesta página: #{fragment}")
                continue
            if not (ROOT / target).exists():
                fail(name, f"link interno quebrado: {href}")
            elif fragment and target.endswith(".html"):
                if fragment not in ids_by_page.get(target, set()):
                    fail(name, f"âncora inexistente em {target}: #{fragment}")

        # ----------------------------------------------- sprite de ícones
        missing = {ref for ref in doc.uses if ref not in doc.symbols}
        if missing:
            fail(name, f"ícones referenciados e ausentes do sprite: {sorted(missing)}")

    # ------------------------------------------------------ arquivos de apoio
    for required in (
        "sitemap.xml",
        "robots.txt",
        "manifest.webmanifest",
        "assets/css/site.css",
        "assets/js/site.js",
        "assets/js/consent.js",
        "assets/js/config.js",
        "assets/img/favicon.svg",
        "assets/img/og-default.png",
        "assets/img/apple-touch-icon.png",
        "README.md",
    ):
        if not (ROOT / required).exists():
            problems.append(f"arquivo obrigatório ausente: {required}")

    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for path in PAGES:
        if path.name == "404.html":
            if path.name in sitemap:
                problems.append("sitemap.xml não deveria listar 404.html")
            continue
        slug = "/" if path.name == "index.html" else f"/{path.name}"
        if f"<loc>https://www.ecopolonordeste.com.br{slug}</loc>" not in sitemap:
            problems.append(f"sitemap.xml sem a página {path.name}")

    # --------------------------------------------------------------- saída
    print(f"Páginas verificadas: {len(PAGES)}")
    if notes:
        print(f"\nObservações ({len(notes)}):")
        for note in notes:
            print(f"  · {note}")
    if problems:
        print(f"\nProblemas ({len(problems)}):")
        for problem in problems:
            print(f"  ✗ {problem}")
        return 1
    print("\nTudo certo: nenhum problema encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
