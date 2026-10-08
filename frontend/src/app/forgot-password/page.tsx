"use client";
import Link from "next/link";
import { useState } from "react";
import { AuthForm, AuthShell } from "@/components/AuthForm";
import { authRequest } from "@/lib/auth";

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  return <AuthShell eyebrow="ACCOUNT RECOVERY" title="A fresh start." description="Enter your email and we’ll send a secure reset link if an account matches." footer={<>Remembered your password? <Link href="/login">Sign in <span>↗</span></Link></>}>
    {sent ? <div className="success-box"><span>✓</span><p>If an account matches that email, reset instructions are on their way.</p></div> : <AuthForm fields={[{name:"email",label:"Email address",type:"email",autoComplete:"email"}]} submitLabel="Send reset link" onSubmit={async data => { await authRequest("/auth/forgot-password",data); setSent(true); }} />}
  </AuthShell>;
}
