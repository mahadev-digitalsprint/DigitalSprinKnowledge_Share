export const SETTINGS_STORAGE_KEY = "rag-ui-settings";

export type ThemeMode = "dark" | "light";

export function isThemeMode(value: unknown): value is ThemeMode {
  return value === "dark" || value === "light";
}

export function applyTheme(theme: ThemeMode): void {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

export function persistTheme(theme: ThemeMode): void {
  if (typeof window === "undefined") return;

  try {
    const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) as Record<string, unknown> : {};
    window.localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        ...parsed,
        theme,
      }),
    );
  } catch {
    window.localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({ theme }),
    );
  }
}
