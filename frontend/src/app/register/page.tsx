"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm, AuthShell } from "@/components/AuthForm";
import { authRequest, setAccessToken, type AuthUser } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  return <AuthShell eyebrow="YOUR NEXT CHAPTER" title="Let’s get started." description="Create your account and make your next move." footer={<>Already have an account? <Link href="/login">Sign in <span>↗</span></Link></>}>
    <AuthForm fields={[{name:"name",label:"Your name",type:"text",autoComplete:"name"},{name:"email",label:"Email address",type:"email",autoComplete:"email"},{name:"password",label:"Create password",type:"password",autoComplete:"new-password"},{name:"confirm_password",label:"Confirm password",type:"password",autoComplete:"new-password"}]} submitLabel="Create account" onSubmit={async data => { if (data.password !== data.confirm_password) throw new Error("Passwords do not match."); const { confirm_password, ...payload } = data; const result = await authRequest<{access_token:string;user:AuthUser}>("/auth/register",payload); setAccessToken(result.access_token); router.push("/broker"); }} />
    <p className="password-hint">Use 12+ characters with uppercase, lowercase, a number, and a symbol.</p>
  </AuthShell>;
}

