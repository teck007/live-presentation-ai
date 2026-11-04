import { computed, ref, watch } from "vue";

export type ThemeChoice = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "lp-theme";
const MEDIA_QUERY = "(prefers-color-scheme: dark)";

function readStored(): ThemeChoice | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "light" || raw === "dark" || raw === "system") return raw;
    return null;
  } catch {
    return null;
  }
}

function systemIsDark(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia(MEDIA_QUERY).matches;
}

// Module-level singleton: every consumer shares one source of truth.
const theme = ref<ThemeChoice>(readStored() ?? "system");
const systemDark = ref<boolean>(systemIsDark());
let mediaBound = false;

function apply(resolved: ResolvedTheme): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.dataset.theme = resolved;
  root.style.colorScheme = resolved;
}

const resolved = computed<ResolvedTheme>(() => {
  if (theme.value === "system") return systemDark.value ? "dark" : "light";
  return theme.value;
});

function bindMedia(): void {
  if (mediaBound || typeof window === "undefined" || typeof window.matchMedia !== "function") return;
  mediaBound = true;
  const mq = window.matchMedia(MEDIA_QUERY);
  const onChange = (e: MediaQueryListEvent) => {
    systemDark.value = e.matches;
  };
  if (typeof mq.addEventListener === "function") mq.addEventListener("change", onChange);
  else mq.addListener(onChange);
}

// Keep DOM in sync whenever choice or OS preference changes.
watch([theme, systemDark], () => apply(resolved.value), { immediate: true });

export function initTheme(): ResolvedTheme {
  theme.value = readStored() ?? "system";
  systemDark.value = systemIsDark();
  bindMedia();
  apply(resolved.value);
  return resolved.value;
}

export function useTheme() {
  bindMedia();

  function setTheme(next: ThemeChoice): void {
    theme.value = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Private mode: theme still applies for the session.
    }
    apply(resolved.value);
  }

  /** Flip between light and dark based on the resolved value. */
  function toggle(): void {
    setTheme(resolved.value === "dark" ? "light" : "dark");
  }

  return { theme, resolved, setTheme, toggle, initTheme };
}
