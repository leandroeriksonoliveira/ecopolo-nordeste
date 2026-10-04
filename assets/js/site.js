/**
 * Comportamento do site institucional da Eco Polo Nordeste.
 *
 * Progressive enhancement: todo o conteúdo e a navegação funcionam sem este
 * arquivo. Aqui ficam apenas melhorias — menu móvel, revelação na rolagem,
 * barra de progresso, ano dinâmico e validação acessível de formulários.
 */
(function () {
  "use strict";

  var CONFIG = window.EPN_CONFIG || {};
  var reduceMotion =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function each(list, fn) {
    Array.prototype.forEach.call(list, fn);
  }

  /* ------------------------------------------------------------- Ano dinâmico */
  each(document.querySelectorAll("[data-current-year]"), function (node) {
    node.textContent = String(new Date().getFullYear());
  });

  /* ---------------------------------------------------------------- Cabeçalho */
  var header = document.querySelector("[data-site-header]");
  var nav = document.querySelector("[data-nav]");
  var navToggle = document.querySelector("[data-nav-toggle]");
  var navToggleLabel = document.querySelector("[data-nav-toggle-label]");

  if (navToggle && nav) {
    var setNav = function (open) {
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
      nav.setAttribute("data-open", open ? "true" : "false");
      if (navToggleLabel) navToggleLabel.textContent = open ? "Fechar" : "Menu";
      document.documentElement.style.overflow = open ? "hidden" : "";
    };

    navToggle.addEventListener("click", function () {
      setNav(navToggle.getAttribute("aria-expanded") !== "true");
    });

    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) setNav(false);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && navToggle.getAttribute("aria-expanded") === "true") {
        setNav(false);
        navToggle.focus();
      }
    });

    window.addEventListener("resize", function () {
      // Mesmo limite do CSS (76rem): acima dele o menu móvel não existe.
      if (window.innerWidth > 1216 && navToggle.getAttribute("aria-expanded") === "true") {
        setNav(false);
      }
    });
  }

  /* ------------------------------------------- Rolagem: sombra e progresso */
  var progressBar = document.querySelector("[data-scroll-progress]");
  var ticking = false;

  function onScroll() {
    if (header) {
      header.setAttribute("data-scrolled", window.scrollY > 12 ? "true" : "false");
    }
    if (progressBar) {
      var height = document.documentElement.scrollHeight - window.innerHeight;
      var ratio = height > 0 ? Math.min(1, Math.max(0, window.scrollY / height)) : 0;
      progressBar.style.width = (ratio * 100).toFixed(2) + "%";
    }
    ticking = false;
  }

  window.addEventListener(
    "scroll",
    function () {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(onScroll);
      }
    },
    { passive: true }
  );
  onScroll();

  /* ---------------------------------------------------- Revelação na rolagem */
  var revealables = document.querySelectorAll("[data-reveal]");
  if (!revealables.length) {
    /* nada a fazer */
  } else if (reduceMotion || !("IntersectionObserver" in window)) {
    each(revealables, function (node) {
      node.setAttribute("data-shown", "true");
    });
  } else {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.setAttribute("data-shown", "true");
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );
    each(revealables, function (node, index) {
      var group = node.getAttribute("data-reveal");
      if (group === "stagger") {
        node.style.setProperty("--reveal-delay", (index % 6) * 70 + "ms");
      }
      observer.observe(node);
    });
  }

  /* -------------------------------------- Índice de seção ativa (documentos) */
  var tocLinks = document.querySelectorAll("[data-toc] a[href^='#']");
  if (tocLinks.length && "IntersectionObserver" in window) {
    var byId = {};
    var targets = [];
    each(tocLinks, function (link) {
      var id = link.getAttribute("href").slice(1);
      var section = document.getElementById(id);
      if (!section) return;
      byId[id] = link;
      targets.push(section);
    });
    var tocObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          var link = byId[entry.target.id];
          if (!link) return;
          if (entry.isIntersecting) {
            each(tocLinks, function (other) {
              other.removeAttribute("aria-current");
            });
            link.setAttribute("aria-current", "true");
          }
        });
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );
    targets.forEach(function (section) {
      tocObserver.observe(section);
    });
  }

  /* ----------------------------------------------------------- Formulários */
  var MESSAGES = {
    required: "Este campo é obrigatório.",
    email: "Informe um e-mail válido, como nome@empresa.com.br.",
    tel: "Informe um telefone com DDD, como (82) 99999-0000.",
    consent: "É necessário autorizar o tratamento para prosseguir.",
    file: "Anexe um arquivo PDF, DOC ou DOCX de até 2 MB.",
  };

  var MAX_FILE_BYTES = 2 * 1024 * 1024;
  var ALLOWED_EXT = ["pdf", "doc", "docx"];

  function fieldError(form, name) {
    return form.querySelector('[data-error-for="' + name + '"]');
  }

  function setError(form, control, message) {
    var holder = fieldError(form, control.name);
    if (holder) {
      holder.textContent = message || "";
      holder.setAttribute("data-visible", message ? "true" : "false");
      if (message) {
        control.setAttribute("aria-invalid", "true");
        if (holder.id) control.setAttribute("aria-describedby", holder.id);
      } else {
        control.removeAttribute("aria-invalid");
      }
    }
    return !message;
  }

  function validateControl(form, control) {
    var value = (control.value || "").trim();

    if (control.type === "checkbox") {
      if (control.required && !control.checked) {
        return setError(
          form,
          control,
          control.hasAttribute("data-consent-field") ? MESSAGES.consent : MESSAGES.required
        );
      }
      return setError(form, control, "");
    }

    if (control.type === "file") {
      var file = control.files && control.files[0];
      if (control.required && !file) return setError(form, control, MESSAGES.file);
      if (file) {
        var ext = (file.name.split(".").pop() || "").toLowerCase();
        if (ALLOWED_EXT.indexOf(ext) === -1 || file.size > MAX_FILE_BYTES) {
          return setError(form, control, MESSAGES.file);
        }
      }
      return setError(form, control, "");
    }

    if (control.required && !value) return setError(form, control, MESSAGES.required);
    if (value && control.type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) {
      return setError(form, control, MESSAGES.email);
    }
    if (value && control.type === "tel" && value.replace(/\D/g, "").length < 10) {
      return setError(form, control, MESSAGES.tel);
    }
    return setError(form, control, "");
  }

  function controlsOf(form) {
    return form.querySelectorAll(
      "input[name]:not([type=hidden]), select[name], textarea[name]"
    );
  }

  function showStatus(form, state, message) {
    var box = form.querySelector("[data-form-status]");
    if (!box) return;
    box.setAttribute("data-state", state);
    box.textContent = message;
  }

  function mailtoFallback(form) {
    var to =
      form.getAttribute("data-form-mailto") || CONFIG.contactEmail || "contato@ecopolonordeste.com.br";
    var subject = "[Site] " + (form.getAttribute("data-form-name") || "Mensagem");
    var lines = [];
    each(controlsOf(form), function (control) {
      if (control.type === "file") return;
      if (control.type === "checkbox" && !control.checked) return;
      var label = form.querySelector('label[for="' + control.id + '"]');
      var name = label ? label.textContent.replace(/\s*\*\s*/g, "").trim() : control.name;
      if (control.type === "radio" && !control.checked) return;
      lines.push(name + ": " + (control.type === "checkbox" ? "sim" : control.value));
    });
    return (
      "mailto:" +
      to +
      "?subject=" +
      encodeURIComponent(subject) +
      "&body=" +
      encodeURIComponent(lines.join("\n"))
    );
  }

  each(document.querySelectorAll("form[data-form]"), function (form) {
    each(controlsOf(form), function (control) {
      control.addEventListener("blur", function () {
        if (control.value || control.type === "checkbox") validateControl(form, control);
      });
      control.addEventListener("input", function () {
        if (control.getAttribute("aria-invalid") === "true") validateControl(form, control);
      });
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      var firstInvalid = null;
      each(controlsOf(form), function (control) {
        if (!validateControl(form, control) && !firstInvalid) firstInvalid = control;
      });

      if (firstInvalid) {
        showStatus(form, "error", "Revise os campos destacados e envie novamente.");
        firstInvalid.focus();
        return;
      }

      var record = {
        formulario: form.getAttribute("data-form-name") || form.getAttribute("data-form"),
        enviadoEm: new Date().toISOString(),
        versaoPolitica: form.getAttribute("data-policy-version") || "1.0",
      };

      if (!CONFIG.formEndpoint) {
        showStatus(
          form,
          "info",
          "O envio automático ainda não está configurado neste ambiente. " +
            "Abrimos seu programa de e-mail com os dados preenchidos para que " +
            "a mensagem não se perca."
        );
        window.location.href = mailtoFallback(form);
        return;
      }

      var payload = new FormData(form);
      Object.keys(record).forEach(function (key) {
        payload.append(key, record[key]);
      });
      var consent = window.EPNConsent && window.EPNConsent.get();
      if (consent) payload.append("registroConsentimentoCookies", consent.id);

      var submitBtn = form.querySelector("button[type=submit]");
      if (submitBtn) submitBtn.disabled = true;
      showStatus(form, "info", "Enviando…");

      fetch(CONFIG.formEndpoint, { method: "POST", body: payload })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          form.reset();
          showStatus(
            form,
            "ok",
            "Recebido. A Eco Polo Nordeste responde em até 5 dias úteis no " +
              "e-mail informado. Requisições de titular de dados têm prazo de 15 dias."
          );
        })
        .catch(function () {
          showStatus(
            form,
            "error",
            "Não foi possível enviar agora. Tente novamente ou escreva para " +
              (CONFIG.contactEmail || "contato@ecopolonordeste.com.br") + "."
          );
        })
        .finally(function () {
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  });
})();
