// The portal (onedesk/one/portal.py): frappe-ui's app frame, its resources
// through frappe's API, and frappe's translations in the reader's language,
// fetched as the desk fetches them (cached by their version) before it draws.
import { createApp, h } from "vue";
import { frappeRequest, resourcesPlugin, setConfig } from "frappe-ui";
import { ConfigProvider } from "reka-ui";

import App from "./App.vue";
import router from "./router";
import { __, boot } from "./words";
import "./index.css";

setConfig("resourceFetcher", frappeRequest);

async function translations() {
  const { lang, translations_version } = boot();
  if (!lang || lang === "en") return;
  const query = new URLSearchParams({ lang, v: translations_version || "" });
  try {
    const response = await fetch(`/api/method/frappe.translate.get_boot_translations?${query}`);
    window.frappe.boot.__messages = (await response.json()).message || {};
  } catch {
    // In English, then: a page in the wrong language beats no page.
  }
}

translations().then(() => {
  // frappe-ui's parts read their direction from reka-ui, which says left to
  // right unless told: the page's own, for Arabic.
  const dir = boot().rtl ? "rtl" : "ltr";
  const app = createApp({ render: () => h(ConfigProvider, { dir }, () => h(App)) });
  app.config.globalProperties.__ = __;
  app.use(resourcesPlugin);
  app.use(router);
  app.mount("#app");
});
