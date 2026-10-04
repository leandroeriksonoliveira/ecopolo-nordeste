/**
 * Camada de consentimento de cookies — Eco Polo Nordeste.
 *
 * Princípios implementados:
 *  - Opt-in real: nenhuma categoria não essencial é ativada antes da decisão.
 *  - Granularidade por categoria, com rejeição tão fácil quanto a aceitação.
 *  - Registro auditável: id, data/hora ISO, versão do texto e categorias.
 *  - Revogação a qualquer momento pelo botão "Gerenciar cookies" do rodapé.
 *  - Conteúdo incorporado de terceiros (mapas) fica bloqueado até o aceite.
 */
(function () {
  "use strict";

  var CONFIG = window.EPN_CONFIG || {};
  var STORE_KEY = "epn.consent.v1";
  var CATEGORIES = ["preferencias", "estatisticas", "marketing"];

  /* ------------------------------------------------------------ Armazenamento */

  function safeParse(raw) {
    try {
      return JSON.parse(raw);
    } catch (err) {
      return null;
    }
  }

  function readRecord() {
    try {
      return safeParse(window.localStorage.getItem(STORE_KEY));
    } catch (err) {
      return null; // modo privado ou armazenamento bloqueado
    }
  }

  function writeRecord(record) {
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify(record));
    } catch (err) {
      /* Sem persistência: a decisão vale apenas para esta sessão. */
    }
  }

  function newId() {
    try {
      if (window.crypto && window.crypto.randomUUID) {
        return "cns_" + window.crypto.randomUUID();
      }
    } catch (err) {
      /* continua no caminho alternativo */
    }
    return "cns_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  /* --------------------------------------------------------------- API pública */

  var api = {
    get: readRecord,
    allows: function (category) {
      var record = readRecord();
      return !!(record && record.categories && record.categories[category] === true);
    },
    onChange: function (handler) {
      document.addEventListener("epn:consent", function (event) {
        handler(event.detail);
      });
    },
    open: function () {
      openBanner(true);
    },
  };
  window.EPNConsent = api;

  /* ----------------------------------------------- Ativação pós-consentimento */

  var loadedScripts = {};

  function loadCategoryScripts(category) {
    var list = (CONFIG.scripts && CONFIG.scripts[category]) || [];
    list.forEach(function (item, index) {
      var key = category + ":" + index;
      if (loadedScripts[key]) return;
      loadedScripts[key] = true;
      var script = document.createElement("script");
      script.src = item.src;
      script.async = true;
      if (item.attrs) {
        Object.keys(item.attrs).forEach(function (name) {
          script.setAttribute(name, item.attrs[name]);
        });
      }
      document.head.appendChild(script);
    });
  }

  /** Libera iframes marcados com data-consent-src para a categoria autorizada. */
  function releaseEmbeds(categories) {
    var gates = document.querySelectorAll("[data-consent-embed]");
    Array.prototype.forEach.call(gates, function (gate) {
      var category = gate.getAttribute("data-consent-embed") || "marketing";
      if (categories[category] !== true) return;
      var frame = gate.querySelector("[data-consent-src]");
      if (!frame || frame.getAttribute("src")) return;
      frame.setAttribute("src", frame.getAttribute("data-consent-src"));
      var placeholder = gate.querySelector("[data-consent-placeholder]");
      if (placeholder) placeholder.hidden = true;
    });
  }

  function applyRecord(record) {
    if (!record) return;
    CATEGORIES.forEach(function (category) {
      if (record.categories[category]) loadCategoryScripts(category);
    });
    releaseEmbeds(record.categories);
    document.dispatchEvent(new CustomEvent("epn:consent", { detail: record }));
  }

  function persistRemotely(record) {
    if (!CONFIG.consentEndpoint) return;
    try {
      var payload = JSON.stringify(record);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(CONFIG.consentEndpoint, new Blob([payload], { type: "application/json" }));
      } else {
        fetch(CONFIG.consentEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
          keepalive: true,
        }).catch(function () {});
      }
    } catch (err) {
      /* O registro local permanece válido mesmo sem o envio. */
    }
  }

  function decide(categories, how) {
    var previous = readRecord();
    var record = {
      id: (previous && previous.id) || newId(),
      decidedAt: new Date().toISOString(),
      textVersion: CONFIG.consentVersion || "1.0",
      method: how,
      categories: {
        necessarios: true,
        preferencias: categories.preferencias === true,
        estatisticas: categories.estatisticas === true,
        marketing: categories.marketing === true,
      },
      page: location.pathname,
      language: navigator.language || "",
    };
    writeRecord(record);
    persistRemotely(record);
    applyRecord(record);
    closeBanner();
    return record;
  }

  /* ------------------------------------------------------------------ Interface */

  var banner, prefsBox, btnCustomize, btnSave, lastFocused;

  function openBanner(showPrefs) {
    if (!banner) return;
    lastFocused = document.activeElement;
    banner.setAttribute("data-open", "true");
    if (showPrefs) revealPrefs();
    syncCheckboxes();
    var first =
      banner.querySelector("[data-consent-accept-all]") ||
      banner.querySelector("button:not([hidden])");
    if (first) first.focus();
  }

  function closeBanner() {
    if (!banner) return;
    banner.removeAttribute("data-open");
    if (lastFocused && typeof lastFocused.focus === "function") lastFocused.focus();
  }

  function revealPrefs() {
    if (!prefsBox) return;
    prefsBox.hidden = false;
    if (btnCustomize) {
      btnCustomize.setAttribute("aria-expanded", "true");
      btnCustomize.hidden = true;
    }
    if (btnSave) btnSave.hidden = false;
  }

  function syncCheckboxes() {
    var record = readRecord();
    CATEGORIES.forEach(function (category) {
      var box = document.querySelector('[data-consent-category="' + category + '"]');
      if (box) box.checked = !!(record && record.categories[category]);
    });
  }

  function readCheckboxes() {
    var out = {};
    CATEGORIES.forEach(function (category) {
      var box = document.querySelector('[data-consent-category="' + category + '"]');
      out[category] = !!(box && box.checked);
    });
    return out;
  }

  function allTrue() {
    var out = {};
    CATEGORIES.forEach(function (category) {
      out[category] = true;
    });
    return out;
  }

  function init() {
    banner = document.querySelector("[data-consent-banner]");
    prefsBox = document.querySelector("[data-consent-prefs]");
    btnCustomize = document.querySelector("[data-consent-customize]");
    btnSave = document.querySelector("[data-consent-save]");

    if (banner) {
      var acceptAll = banner.querySelector("[data-consent-accept-all]");
      var reject = banner.querySelector("[data-consent-reject]");

      if (acceptAll) {
        acceptAll.addEventListener("click", function () {
          decide(allTrue(), "aceitar-todos");
        });
      }
      if (reject) {
        reject.addEventListener("click", function () {
          decide({}, "rejeitar-nao-essenciais");
        });
      }
      if (btnCustomize) {
        btnCustomize.addEventListener("click", revealPrefs);
      }
      if (btnSave) {
        btnSave.addEventListener("click", function () {
          decide(readCheckboxes(), "personalizado");
        });
      }
      banner.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && readRecord()) closeBanner();
      });
    }

    Array.prototype.forEach.call(
      document.querySelectorAll("[data-open-consent]"),
      function (trigger) {
        trigger.addEventListener("click", function (event) {
          event.preventDefault();
          openBanner(true);
        });
      }
    );

    // Botão "carregar o mapa" dos blocos incorporados: consentimento pontual.
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-consent-embed-load]"),
      function (trigger) {
        trigger.addEventListener("click", function () {
          var gate = trigger.closest("[data-consent-embed]");
          if (!gate) return;
          var category = gate.getAttribute("data-consent-embed") || "marketing";
          var current = readRecord();
          var categories = current ? Object.assign({}, current.categories) : {};
          categories[category] = true;
          decide(categories, "incorporado-" + category);
        });
      }
    );

    var existing = readRecord();
    if (existing && existing.textVersion === (CONFIG.consentVersion || "1.0")) {
      applyRecord(existing);
    } else {
      // Sem decisão válida: nada não essencial é ativado e o aviso aparece.
      openBanner(false);
    }

    renderReceipt();
  }

  /** Comprovante de consentimento visível ao titular (cookies.html). */
  function renderReceipt() {
    var target = document.querySelector("[data-consent-receipt]");
    if (!target) return;

    function paint() {
      var record = readRecord();
      if (!record) {
        target.textContent =
          "Nenhuma decisão registrada neste navegador. Apenas cookies estritamente " +
          "necessários estão em uso.";
        return;
      }
      var on = Object.keys(record.categories)
        .filter(function (key) {
          return record.categories[key];
        })
        .join(", ");
      target.textContent =
        "Identificador do registro: " + record.id + "\n" +
        "Data e hora da decisão: " + new Date(record.decidedAt).toLocaleString("pt-BR") + "\n" +
        "Versão do texto aceito: " + record.textVersion + "\n" +
        "Forma da decisão: " + record.method + "\n" +
        "Categorias autorizadas: " + on;
    }

    paint();
    document.addEventListener("epn:consent", paint);

    var revoke = document.querySelector("[data-consent-revoke]");
    if (revoke) {
      revoke.addEventListener("click", function () {
        decide({}, "revogacao-total");
        paint();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
