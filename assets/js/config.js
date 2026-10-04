/**
 * Configuração de ambiente do site da Eco Polo Nordeste.
 *
 * Este é o único arquivo que precisa ser editado no deploy. Não coloque
 * segredos aqui: tudo neste arquivo é público e visível no navegador.
 */
window.EPN_CONFIG = {
  /**
   * Endpoint HTTPS que recebe os formulários (contato, currículo, newsletter e
   * requisições de titular de dados). Deve aceitar POST de multipart/form-data
   * e responder 2xx em caso de sucesso.
   *
   * Enquanto estiver vazio, os formulários validam normalmente e oferecem ao
   * visitante um encaminhamento por e-mail, sem perder o preenchimento.
   * Exemplo: "https://forms.ecopolonordeste.com.br/api/v1/submit"
   */
  formEndpoint: "",

  /**
   * Endpoint que armazena o registro auditável de consentimento de cookies
   * (art. 8º, §1º, da LGPD: o ônus da prova do consentimento é do controlador).
   * Vazio = o registro é mantido apenas no navegador do titular e exibido a ele
   * em cookies.html. Recomenda-se configurar antes do go-live.
   */
  consentEndpoint: "",

  /** E-mails de destino do encaminhamento alternativo dos formulários. */
  contactEmail: "contato@ecopolonordeste.com.br",
  legalEmail: "juridico@ecopolonordeste.com.br",

  /** Versão do texto de consentimento de cookies registrada em cada decisão. */
  consentVersion: "1.0",

  /**
   * Scripts de medição. Só são carregados depois do consentimento da categoria
   * correspondente. Deixe vazio para não carregar nada.
   * Ex.: { estatisticas: [{ src: "https://.../script.js", attrs: { "data-domain": "ecopolonordeste.com.br" } }] }
   */
  scripts: {
    preferencias: [],
    estatisticas: [],
    marketing: [],
  },
};
