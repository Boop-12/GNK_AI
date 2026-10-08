"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AuthForm, AuthShell } from "@/components/AuthForm";
import { authRequest } from "@/lib/auth";

function ResetForm() {
  const search = useSearchParams(); const [token, setToken] = useState(""); const [done, setDone] = useState(false);
  useEffect(() => {
    const fragmentToken = new URLSearchParams(window.location.hash.slice(1)).get("token");
    setToken(fragmentToken ?? search.get("token") ?? "");
    if (fragmentToken) window.history.replaceState(null, "", window.location.pathname);
  }, [search]);
  return <AuthShell eyebrow="SECURE RESET" title="Choose a new password." description="Set a new password to secure your account." footer={<>Back to sign in <Link href="/login">Sign in <span>↗</span></Link></>}>
    {done ? <div className="success-box"><span>✓</span><p>Your password has been updated. You can now sign in.</p><Link href="/login">Continue to sign in ↗</Link></div> : <AuthForm fields={[{name:"new_password",label:"New password",type:"password",autoComplete:"new-password"},{name:"confirm_password",label:"Confirm password",type:"password",autoComplete:"new-password"}]} submitLabel="Update password" onSubmit={async data => { if (data.new_password !== data.confirm_password) throw new Error("Passwords do not match."); await authRequest("/auth/reset-password",{new_password:data.new_password,token}); setDone(true); }} />}
  </AuthShell>;
}
export default function ResetPasswordPage() { return <Suspense><ResetForm /></Suspense>; }
