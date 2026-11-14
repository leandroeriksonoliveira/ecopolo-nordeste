#!/usr/bin/env python3
"""
Gerador estático do site institucional da Eco Polo Nordeste (PT-BR e EN).

Somente biblioteca padrão do Python 3. Uso:

    python3 tools/build.py

Lê `_src/layout.html`, os parciais de `_src/partials/` (com overrides em
`_src/partials/en/` para o inglês) e as páginas de `_src/pages/*.html` e
`_src/pages/en/*.html`, minifica `assets/css/site.css` em
`assets/css/site.min.css`, e escreve os HTML finais na raiz e em `en/`,
junto com `sitemap.xml`.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
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
    "founded_label_en": "November 2021",
    "size_label": "Microempresa (ME)",
    "size_label_en": "Micro-enterprise (ME)",
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
    "policy_date_en": "October 4, 2026",
    "policy_date_iso": "2026-10-04",
    "consent_version": "1.0",
}

SITE["hq_full"] = (
    f'{SITE["hq_street"]} – {SITE["hq_district"]}, {SITE["hq_city"]} - '
    f'{SITE["hq_state"]}, CEP {SITE["hq_zip"]}'
)
SITE["hq_full_en"] = (
    f'{SITE["hq_street"]} – {SITE["hq_district"]}, {SITE["hq_city"]} - '
    f'{SITE["hq_state"]}, ZIP {SITE["hq_zip"]}, Brazil'
)
SITE["com_full"] = (
    f'{SITE["com_name"]} — {SITE["com_street"]}, {SITE["com_district"]}, '
    f'{SITE["com_city"]} - {SITE["com_state"]}'
)
SITE["sameas"] = [SITE["linkedin"], SITE["instagram"]]

NAV_BY_LANG = {
    "pt": [
        ("index.html", "Início"),
        ("quem-somos.html", "Quem somos"),
        ("eco-polo.html", "O complexo"),
        ("esg.html", "ESG e ODS"),
        ("investidores.html", "Investidores"),
        ("trabalhe-conosco.html", "Carreiras"),
        ("conformidade.html", "Conformidade"),
    ],
    "en": [
        ("index.html", "Home"),
        ("quem-somos.html", "About"),
        ("eco-polo.html", "The Complex"),
        ("esg.html", "ESG & SDGs"),
        ("investidores.html", "Investors"),
        ("trabalhe-conosco.html", "Careers"),
        ("conformidade.html", "Compliance"),
    ],
}

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


def minify_css(css: str) -> str:
    """Minificação leve e segura de CSS preservando strings e expressões calc/clamp."""
    out: list[str] = []
    i = 0
    n = len(css)
    while i < n:
        ch = css[i]
        # Preserva strings literais sem alterar conteúdo interno
        if ch in ('"', "'"):
            quote = ch
            j = i + 1
            while j < n:
                if css[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if css[j] == quote:
                    j += 1
                    break
                j += 1
            out.append(css[i:j])
            i = j
            continue
        # Remove comentários /* ... */
        if ch == "/" and i + 1 < n and css[i + 1] == "*":
            end = css.find("*/", i + 2)
            if end == -1:
                break
            i = end + 2
            continue
        # Colapsa whitespace consecutivo em um único espaço
        if ch.isspace():
            if out and not out[-1].endswith(" "):
                out.append(" ")
            i += 1
            while i < n and css[i].isspace():
                i += 1
            continue
        out.append(ch)
        i += 1

    compact = "".join(out).strip()
    # Remove espaços redundantes ao redor de delimitadores seguros
    compact = re.sub(r"\s*([{};,])\s*", r"\1", compact)
    compact = re.sub(r":\s+", ":", compact)
    compact = compact.replace(";}", "}")
    return compact + "\n"


def write_min_css() -> None:
    raw = read(ROOT / "assets/css/site.css")
    minified = minify_css(raw)
    (ROOT / "assets/css/site.min.css").write_text(minified, encoding="utf-8")


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


def render_nav(active: str, lang: str) -> str:
    items = []
    for href, label in NAV_BY_LANG[lang]:
        current = ' aria-current="page"' if href == active else ""
        items.append(
            f'<li><a class="nav__link" href="{href}"{current}>{html.escape(label)}</a></li>'
        )
    return "\n          ".join(items)


def canonical_url(slug: str, lang: str) -> str:
    if lang == "en":
        return f'{SITE["origin"]}/en/{slug}'
    return f'{SITE["origin"]}/' if slug == "index.html" else f'{SITE["origin"]}/{slug}'


def organization_jsonld(lang: str) -> str:
    is_en = lang == "en"
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": f'{SITE["origin"]}/#organizacao',
        "name": SITE["name"],
        "legalName": SITE["legal_name"],
        "alternateName": [SITE["trade_name"], "Eco Green"],
        "url": canonical_url("index.html", lang),
        "logo": {
            "@type": "ImageObject",
            "url": f'{SITE["origin"]}/assets/img/logo-mark.svg',
            "caption": (
                f'{SITE["legal_name"]} logo'
                if is_en
                else f'Logotipo da {SITE["legal_name"]}'
            ),
        },
        "image": f'{SITE["origin"]}/assets/img/og-default.png',
        "description": (
            "Hyperscale green development platform in Northeast Brazil: "
            "sustainable technology parks and data centers, off-grid renewable "
            "energy, closed-loop water management, and regional industrial development."
            if is_en
            else "Plataforma de desenvolvimento verde de hiperescala no Nordeste do Brasil: "
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
                "name": "Headquarters and operations base" if is_en else "Sede e base operacional",
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
                "name": (
                    f'Commercial office — {SITE["com_name"]}'
                    if is_en
                    else f'Escritório comercial — {SITE["com_name"]}'
                ),
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
                "name": (
                    "Institutional and commercial support"
                    if is_en
                    else "Atendimento institucional e comercial"
                ),
                "telephone": SITE["phone_1_tel"],
                "email": SITE["email"],
                "areaServed": "BR",
                "availableLanguage": ["pt-BR", "en"],
            },
            {
                "@type": "ContactPoint",
                "contactType": "sales",
                "name": (
                    "Investor and partner relations"
                    if is_en
                    else "Relacionamento com investidores e parceiros"
                ),
                "telephone": SITE["phone_2_tel"],
                "email": SITE["email"],
                "areaServed": "BR",
                "availableLanguage": ["pt-BR", "en"],
            },
            {
                "@type": "ContactPoint",
                "contactType": "legal",
                "name": (
                    "Data Protection Officer (LGPD)"
                    if is_en
                    else "Encarregado pelo Tratamento de Dados Pessoais (LGPD)"
                ),
                "email": SITE["email_legal"],
                "areaServed": "BR",
                "availableLanguage": ["pt-BR", "en"],
            },
        ],
        "sameAs": SITE["sameas"],
        "knowsLanguage": ["pt-BR", "en"],
        "areaServed": {"@type": "Country", "name": "Brazil" if is_en else "Brasil"},
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def website_jsonld(lang: str) -> str:
    is_en = lang == "en"
    data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": f'{SITE["origin"]}/#site' if not is_en else f'{SITE["origin"]}/en/#site',
        "url": canonical_url("index.html", lang),
        "name": (
            f'{SITE["name"]} — institutional website'
            if is_en
            else f'{SITE["name"]} — site institucional'
        ),
        "inLanguage": "en" if is_en else "pt-BR",
        "publisher": {"@id": f'{SITE["origin"]}/#organizacao'},
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def breadcrumb_jsonld(slug: str, label: str, lang: str) -> str:
    is_en = lang == "en"
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home" if is_en else "Início",
                "item": canonical_url("index.html", lang),
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": label,
                "item": canonical_url(slug, lang),
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


def asset_version() -> str:
    """Fingerprint dos arquivos estáticos referenciados no layout."""
    digest = hashlib.sha256()
    for relative in (
        "assets/css/site.min.css",
        "assets/js/site.js",
        "assets/js/consent.js",
        "assets/js/config.js",
    ):
        digest.update((ROOT / relative).read_bytes())
    return digest.hexdigest()[:10]


def load_partials(lang: str) -> dict[str, str]:
    partials = {p.stem: read(p) for p in sorted(PARTIALS.glob("*.html"))}
    if lang == "en" and (PARTIALS / "en").is_dir():
        for p in sorted((PARTIALS / "en").glob("*.html")):
            partials[p.stem] = read(p)
    return partials


def build_lang(lang: str, layout: str, site_tokens: dict[str, str], year: str, assets: str) -> list[str]:
    is_en = lang == "en"
    src_dir = PAGES / "en" if is_en else PAGES
    out_dir = ROOT / "en" if is_en else ROOT
    out_dir.mkdir(parents=True, exist_ok=True)
    partials = load_partials(lang)

    written: list[str] = []
    for page_path in sorted(src_dir.glob("*.html")):
        meta, body = parse_page(read(page_path))
        slug = meta.get("slug") or page_path.name
        nav_active = meta.get("nav", slug)
        label = meta.get("nav_label") or meta.get("short_title") or meta["title"]

        jsonld_items = [organization_jsonld(lang), website_jsonld(lang)] if slug == "index.html" else []
        if slug not in ("index.html", "404.html"):
            jsonld_items.append(breadcrumb_jsonld(slug, label, lang))
        jsonld = "\n".join(
            f'    <script type="application/ld+json">\n{item}\n    </script>'
            for item in jsonld_items
        )

        canonical = canonical_url(slug, lang)
        pt_url = canonical_url(slug, "pt")
        en_url = canonical_url(slug, "en")
        hreflang_links = (
            ""
            if slug in NOINDEX
            else (
                f'    <link rel="alternate" hreflang="pt-BR" href="{pt_url}" />\n'
                f'    <link rel="alternate" hreflang="en" href="{en_url}" />\n'
                f'    <link rel="alternate" hreflang="x-default" href="{pt_url}" />'
            )
        )
        og_image = meta.get("og_image", "assets/img/og-default.png")
        robots = (
            "noindex, nofollow"
            if slug in NOINDEX
            else "index, follow, max-image-preview:large, max-snippet:-1"
        )

        values = dict(site_tokens)
        values.update(
            {
                "html_lang": "en" if is_en else "pt-BR",
                "og_locale": "en_US" if is_en else "pt_BR",
                "og_locale_alt": "pt_BR" if is_en else "en_US",
                "asset_prefix": "../" if is_en else "",
                "skip_label": "Skip to main content" if is_en else "Ir para o conteúdo principal",
                "lang_switch_label": "Language selection" if is_en else "Seleção de idioma",
                "pt_href": f"../{slug}" if is_en else slug,
                "en_href": slug if is_en else f"en/{slug}",
                "pt_current_attr": "" if is_en else ' aria-current="true"',
                "en_current_attr": ' aria-current="true"' if is_en else "",
                "hreflang_links": hreflang_links,
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
                "nav_items": render_nav(nav_active, lang),
                "jsonld": jsonld,
                "body_class": meta.get("body_class", ""),
                "year": year,
                "asset_v": assets,
                "head_extra": substitute(meta.get("head_extra", ""), {
                    **site_tokens,
                    "asset_prefix": "../" if is_en else "",
                }),
                "body": "",
            }
        )

        # O corpo é resolvido antes de entrar no layout: tokens inseridos por
        # substituição não são reprocessados numa segunda passada.
        values["body"] = substitute(expand_partials(body, partials), values)
        out = substitute(expand_partials(layout, partials), values)

        (out_dir / slug).write_text(out.rstrip() + "\n", encoding="utf-8")
        rel = f"en/{slug}" if is_en else slug
        written.append(slug)
        print(f"  ✓ {rel}")
    return written


def build() -> int:
    write_min_css()
    print("  ✓ assets/css/site.min.css")

    layout = read(SRC / "layout.html")
    site_tokens = {f"site_{k}": (v if isinstance(v, str) else "") for k, v in SITE.items()}
    year = str(_dt.date.today().year)
    assets = asset_version()

    pt_slugs = build_lang("pt", layout, site_tokens, year, assets)
    en_slugs = build_lang("en", layout, site_tokens, year, assets)

    write_sitemap(pt_slugs, en_slugs)
    print(f"\n{len(pt_slugs)} páginas PT + {len(en_slugs)} páginas EN geradas em {ROOT}")
    return 0


def write_sitemap(pt_slugs: list[str], en_slugs: list[str]) -> None:
    today = _dt.date.today().isoformat()
    en_set = set(en_slugs)
    entries = []

    for lang, slugs in (("pt", pt_slugs), ("en", en_slugs)):
        for slug in slugs:
            if slug in NOINDEX:
                continue
            priority, freq = SITEMAP_HINTS.get(slug, ("0.6", "monthly"))
            loc = canonical_url(slug, lang)
            pt_alt = canonical_url(slug, "pt")
            en_alt = canonical_url(slug, "en")
            alts = ""
            if slug in en_set:
                alts = (
                    f'    <xhtml:link rel="alternate" hreflang="pt-BR" href="{pt_alt}" />\n'
                    f'    <xhtml:link rel="alternate" hreflang="en" href="{en_alt}" />\n'
                    f'    <xhtml:link rel="alternate" hreflang="x-default" href="{pt_alt}" />\n'
                )
            entries.append(
                "  <url>\n"
                f"    <loc>{loc}</loc>\n"
                f"{alts}"
                f"    <lastmod>{today}</lastmod>\n"
                f"    <changefreq>{freq}</changefreq>\n"
                f"    <priority>{priority}</priority>\n"
                "  </url>"
            )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print("  ✓ sitemap.xml")


if __name__ == "__main__":
    print("Gerando o site da Eco Polo Nordeste (PT + EN)…\n")
    sys.exit(build())
