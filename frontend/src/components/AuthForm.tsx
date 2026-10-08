"use client";

import Link from "next/link";
import Image from "next/image";
import { Brand } from "@/components/Brand";
import { FormEvent, ReactNode, useState } from "react";
import { ThemeControls } from "@/components/ThemeProvider";

export function AuthShell({ eyebrow, title, description, children, footer }: { eyebrow: string; title: string; description: string; children: ReactNode; footer: ReactNode }) {
  return <main className="auth-layout"><div className="auth-aside"><div className="auth-aside-top"><Brand /><ThemeControls /></div><Image src="/gnk-algo-brand.jpg" width={1672} height={943} alt="GNK ALGO bull and bear brand artwork" className="auth-brand-art" priority sizes="(max-width: 800px) 100vw, 50vw" /><div className="aside-copy"><p className="gnk-eyebrow">INTELLIGENCE BEHIND EVERY TRADE</p><h1>A clearer view.<br/><em>A considered decision.</em></h1><p>Research and risk planning. Live execution disabled.</p></div></div><section className="auth-panel"><div className="auth-card"><p className="eyebrow green">{eyebrow}</p><h2>{title}</h2><p className="muted">{description}</p>{children}<div className="auth-footer">{footer}</div></div><p className="legal">© 2026 GNK ALGO <span>SECURE ACCESS</span></p></section></main>;
}

export function AuthForm({ fields, submitLabel, onSubmit, links }: { fields: { name: string; label: string; type: string; autoComplete: string; required?: boolean }[]; submitLabel: string; onSubmit: (data: Record<string, string>) => Promise<void>; links?: ReactNode }) {
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    const data = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>;
    try { await onSubmit(data); } catch (cause) { setError(cause instanceof Error ? cause.message : "Something went wrong."); } finally { setBusy(false); }
  }
  return <form className="auth-form" onSubmit={submit}>{fields.map(field => <label key={field.name}>{field.label}<span className="password-field"><input aria-label={field.label} name={field.name} type={field.type === "password" && visible[field.name] ? "text" : field.type} autoComplete={field.autoComplete} required={field.required ?? true} maxLength={field.type === "password" ? 128 : undefined} />{field.type === "password" && <button type="button" aria-label={`${visible[field.name] ? "Hide" : "Show"} ${field.label}`} aria-pressed={!!visible[field.name]} onClick={() => setVisible({ ...visible, [field.name]: !visible[field.name] })}>{visible[field.name] ? "Hide" : "Show"}</button>}</span></label>)}{error && <p className="error-message" role="alert">{error}</p>}{links}<button className="button button-dark" disabled={busy}>{busy ? "Please wait…" : submitLabel}<span>↗</span></button></form>;
}
