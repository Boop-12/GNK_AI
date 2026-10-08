"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm, AuthShell } from "@/components/AuthForm";
import { authRequest, setAccessToken, type AuthUser } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  return <AuthShell eyebrow="WELCOME BACK" title="Good to see you." description="Sign in to your GNK Algo account." footer={<>New to GNK Algo? <Link href="/register">Create an account <span>↗</span></Link></>}>
    <AuthForm fields={[{name:"email",label:"Email address",type:"email",autoComplete:"email"},{name:"password",label:"Password",type:"password",autoComplete:"current-password"}]} submitLabel="Sign in" links={<div className="form-link"><Link href="/forgot-password">Forgot password?</Link></div>} onSubmit={async data => { const result = await authRequest<{access_token:string;user:AuthUser}>("/auth/login",data); setAccessToken(result.access_token); router.push("/broker"); }} />
  </AuthShell>;
}

