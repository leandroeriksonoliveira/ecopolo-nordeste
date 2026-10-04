/**
 * Captura de telas e verificação de console via Chrome DevTools Protocol.
 * Sem dependências npm: usa o WebSocket experimental do Node 20+.
 *
 *   node --experimental-websocket tools/preview.mjs <baseUrl> <dirDeSaida>
 *
 * Para cada página do site, navega, registra erros de console e de rede e
 * grava duas capturas de página inteira — desktop (1440) e móvel (390).
 * A decisão de cookies é pré-aceita via localStorage para que as capturas
 * mostrem a experiência de um visitante recorrente; a captura do aviso de
 * cookies é feita separadamente, em sessão limpa.
 */

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Aceita http(s):// ou file:// — o site é estático e funciona nos dois.
const BASE = process.argv[2] || `file://${process.cwd()}`;

/**
 * Em file:// o navegador bloqueia a leitura do manifest por CORS. É uma
 * limitação do protocolo de arquivo, não um defeito do site, e não ocorre em
 * hospedagem real — por isso a mensagem é ignorada na verificação.
 */
const IGNORED = [/manifest\.webmanifest.*blocked by CORS/i];
const ignorable = (text) => IGNORED.some((re) => re.test(text));
const OUT = process.argv[3] || "/tmp/epn-preview";
const PORT = 9333;

const FULL_PAGE = new Set([
  "index.html",
  "eco-polo.html",
  "contato.html",
  "conformidade.html",
  "cookies.html",
]);

const PAGES = [
  "index.html",
  "quem-somos.html",
  "eco-polo.html",
  "esg.html",
  "investidores.html",
  "trabalhe-conosco.html",
  "contato.html",
  "conformidade.html",
  "privacidade.html",
  "termos.html",
  "cookies.html",
  "acessibilidade.html",
  "404.html",
];

const CHROME_PATHS = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
];

const chromeBin = CHROME_PATHS.find((p) => existsSync(p));
if (!chromeBin) {
  console.error("Chrome não encontrado.");
  process.exit(1);
}

mkdirSync(OUT, { recursive: true });
const profile = join(tmpdir(), `epn-cdp-${Date.now()}`);

const chrome = spawn(
  chromeBin,
  [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--hide-scrollbars",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`,
    "about:blank",
  ],
  { stdio: "ignore" }
);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function targetUrl() {
  for (let i = 0; i < 40; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      const info = await res.json();
      return info.webSocketDebuggerUrl;
    } catch {
      await sleep(250);
    }
  }
  throw new Error("Chrome não expôs a porta de depuração.");
}

class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    this.handlers = new Map();
    ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
      } else if (msg.method) {
        (this.handlers.get(msg.method) || []).forEach((fn) => fn(msg.params));
      }
    });
  }
  /**
   * Envia um comando com tempo limite. O renderizador headless ocasionalmente
   * deixa de responder em capturas grandes; sem o limite, a ferramenta inteira
   * fica pendurada em vez de registrar a falha e seguir para a próxima página.
   */
  send(method, params = {}, sessionId, timeoutMs = 25000) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`tempo limite em ${method}`));
      }, timeoutMs);
      this.pending.set(id, {
        resolve: (value) => {
          clearTimeout(timer);
          resolve(value);
        },
        reject: (err) => {
          clearTimeout(timer);
          reject(err);
        },
      });
      this.ws.send(JSON.stringify({ id, method, params, sessionId }));
    });
  }
  on(method, fn) {
    if (!this.handlers.has(method)) this.handlers.set(method, []);
    this.handlers.get(method).push(fn);
  }
}

const CONSENT_SEED = JSON.stringify({
  id: "cns_preview",
  decidedAt: new Date().toISOString(),
  textVersion: "1.0",
  method: "aceitar-todos",
  categories: { necessarios: true, preferencias: true, estatisticas: true, marketing: true },
  page: "/",
  language: "pt-BR",
});

/**
 * No desktop a captura é de página inteira: o viewport emulado é esticado até a
 * altura do conteúdo. No móvel isso não é usado — com densidade 2x o bitmap
 * resultante é grande o bastante para travar a captura —, então o recorte é de
 * um viewport alto, que é também a forma mais fiel de mostrar a experiência no
 * telefone.
 */
const VIEWPORTS = {
  desktop: { width: 1440, height: 900, scale: 1, mobile: false, maxHeight: 9000, full: true },
  mobile: { width: 390, height: 1100, scale: 2, mobile: true, maxHeight: 1100, full: false },
};

async function main() {
  const wsUrl = await targetUrl();
  const ws = new WebSocket(wsUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve);
    ws.addEventListener("error", reject);
  });
  const cdp = new CDP(ws);

  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });

  const issues = [];
  let current = "";

  cdp.on("Runtime.consoleAPICalled", ({ type, args }) => {
    if (type === "error" || type === "warning") {
      const text = (args || []).map((a) => a.value ?? a.description ?? "").join(" ");
      if (!ignorable(text)) issues.push(`${current} [console.${type}] ${text}`);
    }
  });
  cdp.on("Runtime.exceptionThrown", ({ exceptionDetails }) => {
    issues.push(`${current} [exceção] ${exceptionDetails.text} ${exceptionDetails.exception?.description ?? ""}`);
  });
  cdp.on("Log.entryAdded", ({ entry }) => {
    if (entry.level === "error" && !ignorable(entry.text)) {
      issues.push(`${current} [${entry.source}] ${entry.text}`);
    }
  });
  cdp.on("Network.loadingFailed", ({ type, errorText }) => {
    if (!ignorable(errorText)) {
      issues.push(`${current} [rede] falha ao carregar ${type}: ${errorText}`);
    }
  });
  cdp.on("Network.responseReceived", ({ response, type }) => {
    if (response.status >= 400) {
      issues.push(`${current} [rede] HTTP ${response.status} em ${response.url} (${type})`);
    }
  });

  for (const domain of ["Page", "Runtime", "Log", "Network", "DOM"]) {
    await cdp.send(`${domain}.enable`, {}, sessionId);
  }
  await cdp.send(
    "Page.addScriptToEvaluateOnNewDocument",
    { source: `try{localStorage.setItem("epn.consent.v1", ${JSON.stringify(CONSENT_SEED)});}catch(e){}` },
    sessionId
  );

  async function goto(url) {
    current = url.replace(BASE, "");
    process.stderr.write(`→ ${current}\n`);
    await cdp.send("Page.navigate", { url }, sessionId);
    await sleep(900);
    // Rola até o fim para disparar a revelação na rolagem e o carregamento lazy.
    const revealPending = await cdp.send(
      "Runtime.evaluate",
      {
        // scroll-behavior: smooth impediria a varredura instantânea, por isso
        // é desligado durante a captura e restaurado ao final.
        expression: `(async()=>{const root=document.documentElement;
          const previous=root.style.scrollBehavior;root.style.scrollBehavior='auto';
          const step=window.innerHeight*0.8;
          for(let y=0;y<root.scrollHeight;y+=step){root.scrollTop=y;
            await new Promise(r=>setTimeout(r,70));}
          root.scrollTop=0;await new Promise(r=>setTimeout(r,900));
          root.style.scrollBehavior=previous;
          return document.querySelectorAll('[data-reveal]:not([data-shown])').length;})()`,
        awaitPromise: true,
      },
      sessionId
    );
    if (Number(revealPending?.result?.value) > 0) {
      issues.push(`${current} [reveal] ${revealPending.result.value} blocos não revelados após a varredura`);
    }
    await sleep(400);
  }

  let currentViewport = null;

  async function setViewport(name) {
    currentViewport = name;
    const v = VIEWPORTS[name];
    await cdp.send(
      "Emulation.setDeviceMetricsOverride",
      {
        width: v.width,
        height: v.height,
        deviceScaleFactor: v.scale,
        mobile: v.mobile,
      },
      sessionId
    );
  }

  /**
   * Captura a página. Para a página inteira, o viewport emulado é esticado até
   * a altura real do conteúdo e depois restaurado — captureBeyondViewport não é
   * confiável quando há device metrics override ativo.
   */
  async function shoot(file, fullPage = true) {
    if (fullPage && VIEWPORTS[currentViewport].full) {
      const metrics = await cdp.send("Page.getLayoutMetrics", {}, sessionId);
      const height = Math.ceil(
        metrics.cssContentSize?.height || metrics.contentSize?.height || 0
      );
      const v = VIEWPORTS[currentViewport];
      await cdp.send(
        "Emulation.setDeviceMetricsOverride",
        {
          width: v.width,
          height: Math.max(v.height, Math.min(height, v.maxHeight)),
          deviceScaleFactor: v.scale,
          mobile: v.mobile,
        },
        sessionId
      );
      await sleep(500);
    }
    const { data } = await cdp.send(
      "Page.captureScreenshot",
      { format: "png", optimizeForSpeed: false },
      sessionId
    );
    writeFileSync(join(OUT, file), Buffer.from(data, "base64"));
    if (fullPage && VIEWPORTS[currentViewport].full) await setViewport(currentViewport);
  }

  // --- rolagem horizontal no móvel: sempre ANTES das capturas de página
  // inteira, porque captureBeyondViewport altera o viewport emulado.
  await setViewport("mobile");
  const overflow = [];
  for (const page of PAGES) {
    await goto(`${BASE}/${page}`);
    const { result } = await cdp.send(
      "Runtime.evaluate",
      {
        expression: `(()=>{const d=document.documentElement;
          const wide=[...document.querySelectorAll('body *')]
            .filter(el=>{const r=el.getBoundingClientRect();return r.right>d.clientWidth+1||r.left<-1;})
            .slice(0,5).map(el=>el.tagName.toLowerCase()+(el.className?'.'+String(el.className).split(' ')[0]:''));
          return JSON.stringify({scrollW:d.scrollWidth,clientW:d.clientWidth,wide});})()`,
        returnByValue: true,
      },
      sessionId
    );
    const data = JSON.parse(result.value);
    if (data.scrollW > data.clientW + 1) {
      overflow.push(`${page}: scrollWidth ${data.scrollW} > ${data.clientW} — ${data.wide.join(", ")}`);
    }
  }

  // ---------------------------------------------- páginas: desktop e móvel
  for (const page of PAGES) {
    for (const viewport of ["desktop", "mobile"]) {
      const name = page.replace(".html", "");
      try {
        await setViewport(viewport);
        await goto(`${BASE}/${page}`);
        await shoot(`${name}-${viewport}.png`, FULL_PAGE.has(page));
        process.stderr.write(`  · ${name} ${viewport}\n`);
      } catch (err) {
        issues.push(`${page} (${viewport}) [captura] ${err.message}`);
        process.stderr.write(`  ! ${name} ${viewport}: ${err.message}\n`);
      }
    }
  }

  // ------------------------------- aviso de cookies em sessão limpa (prova)
  await cdp.send("Page.addScriptToEvaluateOnNewDocument", { source: "" }, sessionId);
  const { targetId: cleanId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId: cleanSession } = await cdp.send("Target.attachToTarget", {
    targetId: cleanId,
    flatten: true,
  });
  for (const domain of ["Page", "Runtime"]) {
    await cdp.send(`${domain}.enable`, {}, cleanSession);
  }
  await cdp.send(
    "Emulation.setDeviceMetricsOverride",
    { width: 1440, height: 950, deviceScaleFactor: 1, mobile: false },
    cleanSession
  );
  await cdp.send("Page.navigate", { url: `${BASE}/index.html` }, cleanSession);
  await sleep(1200);
  let shot = await cdp.send(
    "Page.captureScreenshot",
    { format: "png", captureBeyondViewport: false },
    cleanSession
  );
  writeFileSync(join(OUT, "cookie-banner-desktop.png"), Buffer.from(shot.data, "base64"));

  // Painel de personalização aberto
  await cdp.send(
    "Runtime.evaluate",
    { expression: "document.querySelector('[data-consent-customize]').click()" },
    cleanSession
  );
  await sleep(500);
  shot = await cdp.send(
    "Page.captureScreenshot",
    { format: "png", captureBeyondViewport: false },
    cleanSession
  );
  writeFileSync(join(OUT, "cookie-prefs-desktop.png"), Buffer.from(shot.data, "base64"));

  // Verifica que nada não essencial foi autorizado antes da decisão
  const { result: before } = await cdp.send(
    "Runtime.evaluate",
    { expression: "JSON.stringify(window.EPNConsent.get())", returnByValue: true },
    cleanSession
  );

  // Rejeita e confere o registro
  await cdp.send(
    "Runtime.evaluate",
    { expression: "document.querySelector('[data-consent-reject]').click()" },
    cleanSession
  );
  await sleep(300);
  const { result: after } = await cdp.send(
    "Runtime.evaluate",
    { expression: "JSON.stringify(window.EPNConsent.get())", returnByValue: true },
    cleanSession
  );

  // ----------------------------------------------- menu móvel por teclado
  await setViewport("mobile");
  await goto(`${BASE}/index.html`);
  const keyboardCall = await cdp.send(
    "Runtime.evaluate",
    {
      expression: `(()=>{const t=document.querySelector('[data-nav-toggle]');
        t.click();const open=document.querySelector('[data-nav]').dataset.open==='true';
        t.click();const closed=document.querySelector('[data-nav]').dataset.open!=='true';
        const focusables=document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])');
        return JSON.stringify({open,closed,focusables:focusables.length});})()`,
      returnByValue: true,
    },
    sessionId
  );

  // ---------------------------------------------------------------- saída
  const report = {
    base: BASE,
    saida: OUT,
    paginas: PAGES.length,
    consentimentoAntesDaDecisao: JSON.parse(before.value || "null"),
    consentimentoAposRejeitar: JSON.parse(after.value || "null"),
    menuMovel: keyboardCall.result?.value
      ? JSON.parse(keyboardCall.result.value)
      : { erro: keyboardCall.exceptionDetails?.text || "sem retorno" },
    rolagemHorizontal: overflow,
    problemas: issues,
  };
  console.log(JSON.stringify(report, null, 2));

  ws.close();
  chrome.kill("SIGTERM");
  await sleep(400);
  try {
    rmSync(profile, { recursive: true, force: true });
  } catch {}
  process.exit(issues.length || overflow.length ? 2 : 0);
}

main().catch((err) => {
  console.error(err);
  chrome.kill("SIGKILL");
  process.exit(1);
});
