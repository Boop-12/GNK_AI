"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
type ThemeMode = "carbon" | "classic-dark" | "classic-light" | "system";
type AccentColor = "green" | "blue" | "purple" | "orange" | "red" | "yellow" | "pink" | "cyan";
type Settings = { theme: ThemeMode; accent: AccentColor; setTheme: (theme: ThemeMode) => void; setAccent: (accent: AccentColor) => void };
const Context = createContext<Settings | null>(null);
const themes: { value: ThemeMode; label: string }[] = [{ value: "carbon", label: "Carbon Black" }, { value: "classic-dark", label: "Dark" }, { value: "classic-light", label: "Light" }, { value: "system", label: "System" }];
const accents: AccentColor[] = ["green", "blue", "purple", "orange", "red", "yellow", "pink", "cyan"];
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeMode>("carbon");
  const [accent, setAccent] = useState<AccentColor>("green");
  const [ready, setReady] = useState(false);
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem("gnk-theme");
      const savedAccent = localStorage.getItem("gnk-accent");
      if (themes.some(item => item.value === savedTheme)) setTheme(savedTheme as ThemeMode);
      if (accents.includes(savedAccent as AccentColor)) setAccent(savedAccent as AccentColor);
    } catch { /* Preferences remain usable without storage. */ }
    setReady(true);
  }, []);
  useEffect(() => {
    if (!ready) return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      document.documentElement.dataset.theme = theme === "system" ? (media.matches ? "classic-dark" : "classic-light") : theme;
      document.documentElement.dataset.accent = accent;
    };
    apply(); media.addEventListener("change", apply);
    try { localStorage.setItem("gnk-theme", theme); localStorage.setItem("gnk-accent", accent); } catch { /* No secrets are stored here. */ }
    return () => media.removeEventListener("change", apply);
  }, [theme, accent, ready]);
  return <Context.Provider value={{ theme, accent, setTheme, setAccent }}>{children}</Context.Provider>;
}
export function ThemeControls() {
  const settings = useContext(Context); if (!settings) return null;
  return <div className="theme-controls" aria-label="Appearance settings"><label><span>Theme</span><select aria-label="Theme" value={settings.theme} onChange={event => settings.setTheme(event.target.value as ThemeMode)}>{themes.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label><label><span>Accent</span><select aria-label="Accent color" value={settings.accent} onChange={event => settings.setAccent(event.target.value as AccentColor)}>{accents.map(item => <option key={item} value={item}>{item[0].toUpperCase() + item.slice(1)}</option>)}</select></label></div>;
}
