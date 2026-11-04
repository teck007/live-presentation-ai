import { computed, ref, watch } from "vue";
import { enUS, esES } from "@clerk/localizations";
import { updateClerkOptions } from "@clerk/vue";
import i18n, { SUPPORTED_LOCALES, type SupportedLocale } from "../i18n";
import { isClerkConfigured } from "../lib/clerk";

const STORAGE_KEY = "lp-locale";

function readStored(): SupportedLocale | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw === "es" || raw === "en" ? raw : null;
  } catch {
    return null;
  }
}

function detectFromNavigator(): SupportedLocale {
  try {
    const lang = (navigator.language ?? "").toLowerCase();
    // Spanish (any region) -> es. Everything else (including any third
    // language) -> en by decision: the catalog only ships es/en.
    return lang.startsWith("es") ? "es" : "en";
  } catch {
    return "es";
  }
}

function resolveClerkLocalization(locale: SupportedLocale): unknown | undefined {
  // @clerk/localizations ships esES/enUS dictionaries. Clerk reads them at
  // the plugin level (no per-<SignIn/> localization prop in @clerk/vue v2),
  // so the language switch pushes them via updateClerkOptions.
  if (!isClerkConfigured) return undefined;
  return locale === "es" ? esES : enUS;
}

function pushClerkLocalization(locale: SupportedLocale): void {
  if (!isClerkConfigured) return;
  const localization = resolveClerkLocalization(locale);
  if (!localization) return;
  try {
    updateClerkOptions({ localization } as Parameters<typeof updateClerkOptions>[0]);
  } catch {
    // Clerk not loaded yet (slow network): the plugin install in main.ts
    // already sets the initial dictionary.
  }
}

// Module-level singleton: mirrors useTheme (one source of truth, persisted,
// applied before mount to avoid a flash of the wrong language in <html>).
const locale = ref<SupportedLocale>(readStored() ?? detectFromNavigator());

function applyMeta(next: SupportedLocale): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.lang = next;
  const t = i18n.global.t.bind(i18n.global);
  const title = t("meta.title");
  const description = t("meta.description");
  document.title = title;
  const descTag = document.querySelector('meta[name="description"]');
  if (descTag) descTag.setAttribute("content", description);
  const ogTitle = document.querySelector('meta[property="og:title"]');
  if (ogTitle) ogTitle.setAttribute("content", t("meta.ogTitle"));
  const ogDesc = document.querySelector('meta[property="og:description"]');
  if (ogDesc) ogDesc.setAttribute("content", t("meta.ogDescription"));
  const ogLocale = document.querySelector('meta[property="og:locale"]');
  if (ogLocale) ogLocale.setAttribute("content", t("meta.locale"));
}

// Keep <html lang>, title and meta in sync on every switch.
watch(locale, (next) => applyMeta(next));

export function initLanguage(): SupportedLocale {
  locale.value = readStored() ?? detectFromNavigator();
  i18n.global.locale.value = locale.value;
  applyMeta(locale.value);
  return locale.value;
}

/** Dictionary for the Clerk plugin install (main.ts). Undefined when unconfigured. */
export function initialClerkLocalization(): unknown | undefined {
  return resolveClerkLocalization(locale.value);
}

export function useLanguage() {
  const current = computed(() => locale.value);

  function setLanguage(next: SupportedLocale): void {
    if (!SUPPORTED_LOCALES.includes(next) || next === locale.value) return;
    locale.value = next;
    i18n.global.locale.value = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Private mode: language still applies for the session.
    }
    applyMeta(next);
    pushClerkLocalization(next);
  }

  return { locale: current, supported: SUPPORTED_LOCALES, setLanguage, initLanguage };
}
