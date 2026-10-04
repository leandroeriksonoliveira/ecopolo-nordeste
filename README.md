# Site institucional — Eco Polo Nordeste

Site institucional estático da **Eco Polo Nordeste LTDA** (CNPJ 44.185.321/0001-83),
em português do Brasil, construído para substituir ecopolonordeste.com.br com o
padrão de conformidade, acessibilidade, SEO e desempenho exigido pelo diagnóstico
de conformidade digital.

Sem framework, sem dependência npm, sem etapa de build obrigatória no servidor.
São arquivos HTML, CSS, JS e SVG que podem ser abertos direto do disco ou
publicados em qualquer hospedagem estática.

---

## Como abrir para revisão

**Opção 1 — direto do disco (offline).** Abra `index.html` no navegador.
Tudo funciona, incluindo o aviso de cookies e a validação de formulários.
A única exceção é o `manifest.webmanifest`, que o navegador bloqueia por CORS no
protocolo `file://` e registra um aviso no console — isso não acontece em
hospedagem real.

**Opção 2 — servidor local (recomendado).** Elimina a limitação acima:

```bash
cd site-novo
python3 -m http.server 8000
# abra http://localhost:8000
```

---

## Estrutura

```
site-novo/
├── index.html                 Home: hero, pilares, Delmiro Gouveia, unidades,
│                              iniciativas, ODS, atualizações, jornadas, CTA
├── quem-somos.html            Dados cadastrais, missão/visão, valores, governança
├── eco-polo.html              O complexo: PUE/WUE/ESG, unidades, nota de números
├── esg.html                   Programa ESG e operação dos ODS, legado social
├── investidores.html          Tese, estágio, status de parcerias, canal de RI
├── trabalhe-conosco.html      Banco de talentos com retenção/descarte declarados
├── contato.html               Canais com finalidade, endereços, mapa, formulário
├── conformidade.html          Central: DPO, direitos do titular, canais, versões
├── privacidade.html           Política de Privacidade (LGPD)
├── termos.html                Termos de Uso
├── cookies.html               Política de Cookies + comprovante de consentimento
├── acessibilidade.html        Declaração de Acessibilidade
├── 404.html                   Página de erro (noindex)
├── sitemap.xml                Gerado por tools/build.py
├── robots.txt                 Indexação liberada, inclui agentes de IA
├── manifest.webmanifest       Identidade de aplicativo e ícones
│
├── assets/
│   ├── css/site.css           Folha única: tokens, componentes, utilitários
│   ├── js/config.js           ÚNICO arquivo a editar no deploy (ver abaixo)
│   ├── js/consent.js          Camada de consentimento de cookies
│   ├── js/site.js             Menu, revelação na rolagem, validação de formulário
│   └── img/                   Logo e ícones em SVG + bitmaps derivados
│
├── _src/                      Fontes do gerador — NÃO publicar
│   ├── layout.html            Esqueleto comum (head, header, footer, scripts)
│   ├── partials/              Cabeçalho, rodapé, aviso de cookies, logo, ícones
│   └── pages/                 Conteúdo de cada página + metadados de SEO
│
├── tools/                     Ferramentas de autoria — NÃO publicar
│   ├── build.py               Gera os HTML da raiz e o sitemap.xml
│   ├── check.py               Verificação automática (links, SEO, acessibilidade)
│   ├── make-images.py         Gera ícones e o cartão de compartilhamento
│   └── preview.mjs            Capturas de tela e checagem de console via CDP
│
└── deploy/                     Configuração de hospedagem — NÃO publicar como está
    ├── _headers                Netlify / Cloudflare Pages
    ├── vercel.json             Vercel
    └── .htaccess               Apache / cPanel
```

### O que publicar

Publique **apenas a raiz** — os `.html`, `sitemap.xml`, `robots.txt`,
`manifest.webmanifest` e a pasta `assets/`. As pastas `_src/`, `tools/` e
`deploy/` são de autoria e não devem ir ao ar (o `.htaccess` de exemplo já
bloqueia esses caminhos por precaução).

---

## Como editar o conteúdo

Há dois caminhos, e os dois são válidos:

**A. Editar os HTML da raiz diretamente.** Funciona e é o caminho mais simples
para uma correção pontual de texto. O risco é o cabeçalho e o rodapé saírem de
sincronia entre as 13 páginas.

**B. Editar os fontes e regerar** (recomendado para qualquer mudança
estrutural, de identidade legal ou de navegação):

```bash
python3 tools/build.py      # só biblioteca padrão do Python 3
```

O conteúdo de cada página fica em `_src/pages/<nome>.html`, começando por um
cabeçalho de metadados terminado por `---`:

```
slug: contato.html
nav: contato.html
title: Contato — Eco Polo Nordeste | canais oficiais, endereços e formulário
description: Fale com a Eco Polo Nordeste. Telefones…
---
<section>…</section>
```

Dados institucionais — razão social, CNPJ, endereços, telefones, e-mails, perfis
sociais, versão das políticas — ficam **em um único lugar**: o dicionário `SITE`
no topo de `tools/build.py`. Alterar ali e reconstruir propaga para as 13
páginas, para o rodapé, para os dados estruturados e para o sitemap. É isso que
evita o endereço desatualizado em uma página só.

A lista `NAV`, logo abaixo, define a navegação principal e o rótulo de cada
item. O rótulo do menu é independente do título da página: “Carreiras” no menu
aponta para a página “Trabalhe conosco”, porque a navegação completa só cabe em
uma linha até cerca de 1.160 px de conteúdo.

---

## Verificação

```bash
python3 tools/check.py
```

Checa, sem rede, em todas as páginas: links internos e âncoras, unicidade de
título e descrição, presença de canonical/Open Graph/JSON-LD, CNPJ e razão
social, perfis do LinkedIn e do Instagram, `sameAs` nos dados estruturados,
rótulo de cada campo de formulário, `noopener` em link externo, `alt` em imagem,
hierarquia de títulos sem salto, ícones do sprite e cobertura do sitemap.

Capturas de tela e verificação de console (opcional, requer Chrome e Node 20+):

```bash
node --experimental-websocket tools/preview.mjs "file://$PWD" /tmp/epn-preview
```

Gera desktop (1440) e móvel (390) de página inteira para cada página, mais a
prova do aviso de cookies, e reporta erro de console, falha de rede, rolagem
horizontal no móvel e o registro de consentimento antes e depois da decisão.

Ícones e cartão de compartilhamento, apenas quando a identidade mudar:

```bash
python3 tools/make-images.py
```

---

## Configuração de deploy

### 1. Endpoint dos formulários — obrigatório antes do go-live

Edite `assets/js/config.js`:

```js
window.EPN_CONFIG = {
  formEndpoint: "https://…/submit",     // recebe POST multipart/form-data
  consentEndpoint: "https://…/consent", // registro auditável de consentimento
  …
};
```

Enquanto `formEndpoint` estiver vazio, os formulários validam normalmente e
abrem o programa de e-mail do visitante com os dados preenchidos — nada se
perde, mas **não há captura estruturada**. Com `consentEndpoint` vazio, o
registro de consentimento de cookies existe apenas no navegador do titular;
configurá-lo é o que permite à companhia **provar** o consentimento diante da
ANPD, como exige o art. 8º, §1º, da LGPD.

Nunca coloque segredo nesse arquivo: ele é público.

O endpoint precisa receber quatro formulários — `newsletter`, `comercial`,
`curriculo` (com anexo de até 2 MB em PDF/DOC/DOCX) e `titular` — e deve gravar,
junto de cada envio, a versão da política aceita e o carimbo de tempo, que já
são enviados no corpo da requisição.

### 2. Cabeçalhos de resposta — obrigatório

Copie o arquivo correspondente de `deploy/` para a raiz publicada:

| Hospedagem | Arquivo |
| --- | --- |
| Netlify, Cloudflare Pages | `deploy/_headers` |
| Vercel | `deploy/vercel.json` |
| Apache, cPanel | `deploy/.htaccess` |

Eles aplicam HSTS, Content-Security-Policy, `X-Content-Type-Options`,
`X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, políticas de origem
cruzada e cache longo para `assets/`. A CSP permite apenas `openstreetmap.org`
como origem de quadro, usada pelo mapa opcional da página de contato.

Em Nginx, os mesmos valores vão em `add_header` dentro do `server`.

### 3. HTTPS e domínio

O site é HTTPS-ready e usa apenas caminhos relativos. Requisitos no servidor:
certificado válido com renovação monitorada, redirecionamento 301 de `http://`
para `https://`, escolha de um host canônico (com ou sem `www`) com redirect do
outro, e `404.html` configurado como página de erro.

Se o domínio canônico mudar, atualize `SITE["origin"]` em `tools/build.py`,
regere e ajuste a linha `Sitemap:` em `robots.txt`.

### 4. Pós-publicação

- Enviar `sitemap.xml` no Google Search Console e no Bing Webmaster Tools.
- Validar os dados estruturados no teste de resultados aprimorados do Google.
- Conferir o cartão de compartilhamento no LinkedIn Post Inspector.
- Preencher o site oficial e os dados de contato no perfil do LinkedIn e no
  Instagram, usando exatamente os mesmos dados do rodapé.
- Medir Core Web Vitals com dado de campo após uma semana de tráfego.

---

## Decisões de conteúdo embutidas no site

Três critérios editoriais foram aplicados e convém conhecê-los antes de editar
textos:

1. **Nenhuma alegação absoluta.** Expressões como “descarbonização garantida”,
   “mitigação total” e “principal plataforma do país” não aparecem. No lugar
   delas há descrição de projeto com qualificador. Isso é o que protege a
   companhia da acusação de publicidade enganosa e de *greenwashing*.
2. **Números são metas de projeto.** Potência, área, número de empresas e
   indicadores de eficiência estão rotulados como planejamento, com nota
   metodológica própria em `eco-polo.html#numeros`. Números ainda em
   reconciliação interna não foram publicados.
3. **Estágio real das parcerias.** Em `investidores.html`, cada relação aparece
   com o estágio declarado — apresentação, designação ou projeto anunciado — e
   não como contrato vigente.

---

## Pendências que dependem do cliente

Estes pontos estão marcados no próprio site com texto provisório honesto, e
precisam de decisão para serem fechados:

| Pendência | Onde aparece | O que falta |
| --- | --- | --- |
| **Nome do Encarregado de Dados (DPO)** | `conformidade.html#encarregado`, `privacidade.html` | Ato formal de nomeação. O canal `juridico@` já opera com os prazos legais; falta a identificação nominal exigida pelo art. 41 da LGPD. |
| **Data book técnico** | `eco-polo.html#numeros`, `investidores.html#documentos` | Congelar a fonte de cada número quantitativo (potência, área, empresas, PUE/WUE) com escopo, período e responsável. Divergências internas conhecidas não foram publicadas. |
| **Estrutura societária e liderança** | `quem-somos.html#governanca`, `investidores.html#documentos` | Autorização para publicar nomes de conselho e diretoria, e definição do canal de denúncia. |
| **Escritório de Londres** | não publicado | O endereço do Reino Unido que constava no site antigo tem grafia de logradouro e código postal divergentes entre as fontes. Foi omitido até conferência no registro oficial. |
| **Indicadores ESG** | `esg.html` | Metas, linha de base e período de apuração para publicar resultado, não só compromisso. |
| **Fotografia real** | todo o site | O site não usa nenhuma foto. Toda a imagem é SVG gerado ou a própria marca. Para incluir fotografia do sítio, da equipe ou do lançamento é preciso o arquivo em alta e a comprovação de direito de uso e de autorização de imagem das pessoas retratadas. |
| **Direitos sobre a marca gráfica** | `assets/img/` | O logotipo foi vetorizado a partir do site atual para ganhar nitidez e escala. O arquivo vetorial original da marca, se existir, deve substituir o traçado. |
| **Vagas abertas** | `trabalhe-conosco.html` | A página declara que não há vaga publicada. Assim que houver, incluir no lugar do aviso. |
| **Versão em inglês** | declarada como limitação | O público investidor e industrial é internacional; a versão em inglês está registrada como pendência em `acessibilidade.html`. |
| **Hospedagem e medição** | `deploy/`, `assets/js/config.js` | Escolher a hospedagem, aplicar os cabeçalhos e decidir a ferramenta de medição de audiência — que só pode ser ativada após consentimento e precisa ser declarada no inventário de `cookies.html`. |
| **Auditoria externa de acessibilidade** | `acessibilidade.html#limitacoes` | A verificação AA desta versão foi interna. A declaração prevê avaliação independente com relatório publicável. |

---

## Conformidade coberta por esta versão

- **Identidade legal** — razão social, CNPJ, constituição, porte e os dois
  endereços no rodapé de todas as páginas, mais quadro cadastral completo em
  `quem-somos.html`.
- **LGPD** — Política de Privacidade versionada; aviso de privacidade no próprio
  ponto de coleta, com finalidade, base legal, retenção, compartilhamento e
  transferência internacional; consentimento opt-in por categoria com registro
  auditável; canal do Encarregado; formulário de direitos do titular com prazo
  de 15 dias; política de retenção e descarte do banco de currículos.
- **CDC** — identificação do fornecedor em todas as páginas e remoção das
  alegações absolutas de desempenho ambiental.
- **LBI e WCAG 2.2 AA** — semântica, link de atalho, foco visível, contraste
  verificado, `alt` real, operação por teclado, rótulo em todo campo, erro
  descritivo, respeito a `prefers-reduced-motion` e Declaração de
  Acessibilidade com canal de reporte.
- **SEO técnico** — título e descrição únicos por página, canonical, Open Graph
  e cartão de compartilhamento com imagem própria, JSON-LD `Organization` com
  CNPJ e `sameAs`, `WebSite`, `BreadcrumbList`, `sitemap.xml` e `robots.txt`.
- **Desempenho** — nenhuma requisição externa em tempo de execução: sem fonte
  remota, sem biblioteca de terceiros, sem fotografia. Uma folha de estilo e
  três arquivos de script pequenos, todos com `defer`. Imagens vetoriais.
- **Canais** — ícones e links apontam para os perfis reais no LinkedIn e no
  Instagram, com `target="_blank"`, `rel="noopener noreferrer"` e `aria-label`,
  e os identificadores legíveis aparecem no cabeçalho, no hero, na página de
  contato e no rodapé. Matriz de canais oficiais publicada em
  `conformidade.html#canais`.
- **Sem recurso quebrado** — o mapa é opcional e consentido, com o endereço
  sempre disponível em texto; não há chamada de API que possa exibir mensagem de
  erro de configuração ao visitante.

---

Eco Polo Nordeste LTDA · CNPJ 44.185.321/0001-83 · Maceió — AL
Documentos do site na versão 1.0, vigentes desde 04/10/2026.
