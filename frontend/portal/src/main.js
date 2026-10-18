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
  }
}

translations().then(() => {
  const dir = boot().rtl ? "rtl" : "ltr";
  const app = createApp({ render: () => h(ConfigProvider, { dir }, () => h(App)) });
  app.config.globalProperties.__ = __;
  app.use(resourcesPlugin);
  app.use(router);
  app.mount("#app");
});
