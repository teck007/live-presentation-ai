import { createI18n } from "vue-i18n";
import en from "./locales/en.json";
import es from "./locales/es.json";

export type SupportedLocale = "es" | "en";

export const SUPPORTED_LOCALES: SupportedLocale[] = ["es", "en"];
export const FALLBACK_LOCALE: SupportedLocale = "en";

// Global (non-scoped) messages: every component uses useI18n({ useScope: "global" })
// or $t so the LanguageSwitcher flips the whole app without reload.
const i18n = createI18n({
  legacy: false,
  locale: "es",
  fallbackLocale: FALLBACK_LOCALE,
  messages: { es, en },
});

export default i18n;
