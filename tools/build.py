#!/usr/bin/env python3
"""
Gerador estático do site institucional da Eco Polo Nordeste.

Somente biblioteca padrão do Python 3. Uso:

    python3 tools/build.py

Lê `_src/layout.html`, os parciais de `_src/partials/` e as páginas de
`_src/pages/*.html`, e escreve os arquivos HTML finais na raiz do projeto,
junto com `sitemap.xml`. O resultado é HTML estático puro: o site publicado
não depende deste script nem de qualquer etapa de build em tempo de execução.

Cada página em `_src/pages/` começa com um cabeçalho `chave: valor`,
terminado por uma linha `---`.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
PAGES = SRC / "pages"
PARTIALS = SRC / "partials"

# --------------------------------------------------------------------------
# Dados institucionais — fonte única de verdade para todo o site.
# Alterar aqui e reconstruir propaga para todas as páginas, JSON-LD e rodapé.
# --------------------------------------------------------------------------
SITE = {
    "origin": "https://www.ecopolonordeste.com.br",
    "name": "Eco Polo Nordeste",
    "legal_name": "Eco Polo Nordeste LTDA",
    "trade_name": "Polo Eco Green",
    "cnpj": "44.185.321/0001-83",
    "cnpj_digits": "44185321000183",
    "founded": "2021-11",
    "founded_label": "Novembro de 2021",
    "size_label": "Microempresa (ME)",
    "email": "contato@ecopolonordeste.com.br",
    "email_legal": "juridico@ecopolonordeste.com.br",
    "phone_1": "(82) 2122-3318",
    "phone_1_tel": "+558221223318",
    "phone_2": "(82) 2159-0100",
    "phone_2_tel": "+558221590100",
    "hq_street": "Av. Venerável João Vieira Chagas, 13, Sala 09",
    "hq_district": "Mangabeiras",
    "hq_city": "Maceió",
    "hq_state": "AL",
    "hq_zip": "57037-035",
    "com_name": "Norcon Empresarial",
    "com_street": "Av. Comendador Gustavo Paiva",
    "com_district": "Mangabeiras",
    "com_city": "Maceió",
    "com_state": "AL",
    # Perfis sociais oficiais — verificados em 04/10/2026.
    "linkedin": "https://www.linkedin.com/company/ecopolonordeste/posts/",
    "linkedin_handle": "/company/ecopolonordeste",
    "instagram": "https://www.instagram.com/ecopolonordeste/",
    "instagram_handle": "@ecopolonordeste",
    "policy_version": "1.0",
    "policy_date": "04/10/2026",
    "policy_date_iso": "2026-10-04",
    "consent_version": "1.0",
}

SITE["hq_full"] = (
    f'{SITE["hq_street"]} – {SITE["hq_district"]}, {SITE["hq_city"]} - '
    f'{SITE["hq_state"]}, CEP {SITE["hq_zip"]}'
)
SITE["com_full"] = (
    f'{SITE["com_name"]} — {SITE["com_street"]}, {SITE["com_district"]}, '
    f'{SITE["com_city"]} - {SITE["com_state"]}'
)
SITE["sameas"] = [SITE["linkedin"], SITE["instagram"]]

# Navegação principal: (arquivo, rótulo)
NAV = [
    ("index.html", "Início"),
    ("quem-somos.html", "Quem somos"),
    ("eco-polo.html", "O complexo"),
    ("esg.html", "ESG e ODS"),
    ("investidores.html", "Investidores"),
    ("trabalhe-conosco.html", "Carreiras"),
    ("conformidade.html", "Conformidade"),
]

# Prioridade e frequência para o sitemap
SITEMAP_HINTS = {
    "index.html": ("1.0", "weekly"),
    "eco-polo.html": ("0.9", "monthly"),
    "quem-somos.html": ("0.8", "monthly"),
    "esg.html": ("0.8", "monthly"),
    "investidores.html": ("0.8", "monthly"),
    "contato.html": ("0.8", "monthly"),
    "trabalhe-conosco.html": ("0.7", "monthly"),
    "conformidade.html": ("0.7", "monthly"),
    "privacidade.html": ("0.5", "yearly"),
    "termos.html": ("0.4", "yearly"),
    "cookies.html": ("0.4", "yearly"),
    "acessibilidade.html": ("0.4", "yearly"),
}

NOINDEX = {"404.html"}


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_page(text: str) -> tuple[dict, str]:
    """Separa o cabeçalho `chave: valor` do corpo HTML."""
    meta: dict[str, str] = {}
    lines = text.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            body_start = i + 1
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise SystemExit(f"Cabeçalho inválido na linha {i + 1}: {line!r}")
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    else:
        raise SystemExit("Cabeçalho sem a linha separadora '---'.")
    return meta, "\n".join(lines[body_start:]).strip()


def render_nav(active: str) -> str:
    items = []
    for href, label in NAV:
        current = ' aria-current="page"' if href == active else ""
        items.append(
            f'<li><a class="nav__link" href="{href}"{current}>{html.escape(label)}</a></li>'
        )
    return "\n          ".join(items)


def organization_jsonld() -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": f'{SITE["origin"]}/#organizacao',
        "name": SITE["name"],
        "legalName": SITE["legal_name"],
        "alternateName": [SITE["trade_name"], "Eco Green"],
        "url": f'{SITE["origin"]}/',
        "logo": {
            "@type": "ImageObject",
            "url": f'{SITE["origin"]}/assets/img/logo-mark.svg',
            "caption": f'Logotipo da {SITE["legal_name"]}',
        },
        "image": f'{SITE["origin"]}/assets/img/og-default.png',
        "description": (
            "Plataforma de desenvolvimento verde de hiperescala no Nordeste do Brasil: "
            "parques tecnológicos e data centers sustentáveis, energia renovável off-grid, "
            "gestão hídrica em ciclo fechado e desenvolvimento industrial regional."
        ),
        "taxID": SITE["cnpj"],
        "vatID": SITE["cnpj"],
        "identifier": [
            {
                "@type": "PropertyValue",
                "propertyID": "CNPJ",
                "name": "Cadastro Nacional da Pessoa Jurídica",
                "value": SITE["cnpj"],
            }
        ],
        "foundingDate": SITE["founded"],
        "foundingLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Maceió",
                "addressRegion": "AL",
                "addressCountry": "BR",
            },
        },
        "address": {
            "@type": "PostalAddress",
            "streetAddress": SITE["hq_street"],
            "addressLocality": SITE["hq_city"],
            "addressRegion": SITE["hq_state"],
            "postalCode": SITE["hq_zip"],
            "addressCountry": "BR",
        },
        "location": [
            {
                "@type": "Place",
                "name": "Sede e base operacional",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": SITE["hq_street"],
                    "addressLocality": SITE["hq_city"],
                    "addressRegion": SITE["hq_state"],
                    "postalCode": SITE["hq_zip"],
                    "addressCountry": "BR",
                },
            },
            {
                "@type": "Place",
                "name": f'Escritório comercial — {SITE["com_name"]}',
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": SITE["com_street"],
                    "addressLocality": SITE["com_city"],
                    "addressRegion": SITE["com_state"],
                    "addressCountry": "BR",
                },
            },
        ],
        "email": SITE["email"],
        "telephone": SITE["phone_1_tel"],
        "contactPoint": [
            {
                "@type": "ContactPoint",
                "contactType": "customer support",
                "name": "Atendimento institucional e comercial",
                "telephone": SITE["phone_1_tel"],
                "email": SITE["email"],
                "areaServed": "BR",
                "availableLanguage": ["pt-BR"],
            },
            {
                "@type": "ContactPoint",
                "contactType": "sales",
                "name": "Relacionamento com investidores e parceiros",
                "telephone": SITE["phone_2_tel"],
                "email": SITE["email"],
                "areaServed": "BR",
                "availableLanguage": ["pt-BR"],
            },
            {
                "@type": "ContactPoint",
                "contactType": "legal",
                "name": "Encarregado pelo Tratamento de Dados Pessoais (LGPD)",
                "email": SITE["email_legal"],
                "areaServed": "BR",
                "availableLanguage": ["pt-BR"],
            },
        ],
        "sameAs": SITE["sameas"],
        "knowsLanguage": "pt-BR",
        "areaServed": {"@type": "Country", "name": "Brasil"},
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def website_jsonld() -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": f'{SITE["origin"]}/#site',
        "url": f'{SITE["origin"]}/',
        "name": f'{SITE["name"]} — site institucional',
        "inLanguage": "pt-BR",
        "publisher": {"@id": f'{SITE["origin"]}/#organizacao'},
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def breadcrumb_jsonld(slug: str, label: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Início",
                "item": f'{SITE["origin"]}/',
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": label,
                "item": f'{SITE["origin"]}/{slug}',
            },
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def substitute(text: str, values: dict[str, str]) -> str:
    """Substitui {{chave}} de forma literal (sem reinterpretar o conteúdo inserido)."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key not in values:
            raise SystemExit(f"Token desconhecido no template: {{{{{key}}}}}")
        return values[key]

    return re.sub(r"\{\{([a-z0-9_]+)\}\}", repl, text)


def expand_partials(text: str, partials: dict[str, str], depth: int = 6) -> str:
    """Expande {{partial:nome}}, permitindo parciais aninhados."""
    for _ in range(depth):
        if "{{partial:" not in text:
            return text
        for name, content in partials.items():
            text = text.replace(f"{{{{partial:{name}}}}}", content)
        leftover = re.search(r"\{\{partial:([a-z0-9_-]+)\}\}", text)
        if leftover and leftover.group(1) not in partials:
            raise SystemExit(f"Parcial não encontrado: {leftover.group(1)}")
    raise SystemExit("Parciais aninhados além da profundidade máxima (possível ciclo).")


def build() -> int:
    layout = read(SRC / "layout.html")
    partials = {p.stem: read(p) for p in sorted(PARTIALS.glob("*.html"))}

    site_tokens = {f"site_{k}": (v if isinstance(v, str) else "") for k, v in SITE.items()}
    year = str(_dt.date.today().year)

    written: list[str] = []
    for page_path in sorted(PAGES.glob("*.html")):
        meta, body = parse_page(read(page_path))
        slug = meta.get("slug") or page_path.name
        nav_active = meta.get("nav", slug)
        label = meta.get("nav_label") or meta.get("short_title") or meta["title"]

        jsonld_items = [organization_jsonld(), website_jsonld()] if slug == "index.html" else []
        if slug not in ("index.html", "404.html"):
            jsonld_items.append(breadcrumb_jsonld(slug, label))
        jsonld = "\n".join(
            f'    <script type="application/ld+json">\n{item}\n    </script>'
            for item in jsonld_items
        )

        canonical = f'{SITE["origin"]}/' if slug == "index.html" else f'{SITE["origin"]}/{slug}'
        og_image = meta.get("og_image", "assets/img/og-default.png")
        robots = (
            "noindex, nofollow"
            if slug in NOINDEX
            else "index, follow, max-image-preview:large, max-snippet:-1"
        )

        values = dict(site_tokens)
        values.update(
            {
                "title": html.escape(meta["title"], quote=True),
                "description": html.escape(meta["description"], quote=True),
                "canonical": canonical,
                "slug": slug,
                "og_image_url": f'{SITE["origin"]}/{og_image}',
                "og_image_path": og_image,
                "og_type": meta.get("og_type", "website"),
                "og_image_alt": html.escape(
                    meta.get("og_image_alt", f'{SITE["name"]} — {meta["title"]}'), quote=True
                ),
                "robots": robots,
                "nav_items": render_nav(nav_active),
                "jsonld": jsonld,
                "body_class": meta.get("body_class", ""),
                "year": year,
                "head_extra": meta.get("head_extra", ""),
                "body": "",
            }
        )

        # O corpo é resolvido antes de entrar no layout: tokens inseridos por
        # substituição não são reprocessados numa segunda passada.
        values["body"] = substitute(expand_partials(body, partials), values)
        out = substitute(expand_partials(layout, partials), values)

        (ROOT / slug).write_text(out.rstrip() + "\n", encoding="utf-8")
        written.append(slug)
        print(f"  ✓ {slug}")

    write_sitemap(written)
    print(f"\n{len(written)} páginas geradas em {ROOT}")
    return 0


def write_sitemap(slugs: list[str]) -> None:
    today = _dt.date.today().isoformat()
    entries = []
    for slug in slugs:
        if slug in NOINDEX:
            continue
        priority, freq = SITEMAP_HINTS.get(slug, ("0.6", "monthly"))
        loc = f'{SITE["origin"]}/' if slug == "index.html" else f'{SITE["origin"]}/{slug}'
        entries.append(
            "  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            "  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print("  ✓ sitemap.xml")


if __name__ == "__main__":
    print("Gerando o site da Eco Polo Nordeste…\n")
    sys.exit(build())
