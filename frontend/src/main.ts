import { createApp } from "vue";
import { clerkPlugin } from "@clerk/vue";
import App from "./App.vue";
import router from "./router";
import i18n from "./i18n";
import "./style.css";
import { initTheme } from "./composables/useTheme";
import { initLanguage, initialClerkLocalization } from "./composables/useLanguage";
import {
  CLERK_PUBLISHABLE_KEY,
  isClerkConfigured,
  registerApp,
} from "./lib/clerk";

// Apply stored/OS theme and stored/detected language before mount
// to avoid a flash of the wrong theme or <html lang>.
initTheme();
initLanguage();

// App entry point.
const app = createApp(App);
registerApp(app);
app.use(i18n);
if (isClerkConfigured) {
  const localization = initialClerkLocalization() as
    | { [key: string]: unknown }
    | undefined;
  app.use(clerkPlugin, {
    publishableKey: CLERK_PUBLISHABLE_KEY,
    ...(localization ? { localization } : {}),
  });
} else {
  // Dev without env: stay usable, backend fail-opens locally without secret.
  console.warn(
    "[clerk] VITE_CLERK_PUBLISHABLE_KEY is missing: running without auth (dev only).",
  );
}
app.use(router).mount("#app");
