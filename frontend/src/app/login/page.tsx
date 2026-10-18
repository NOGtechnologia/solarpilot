"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Logo } from "@/components/logo";
import { useApp } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/form";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function LoginPage() {
  const { t } = useI18n();
  const { auth, refreshAuth } = useApp();
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const setup = auth ? !auth.has_users : false;

  useEffect(() => {
    if (auth?.authenticated) router.replace("/");
  }, [auth, router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post(setup ? "/api/auth/setup" : "/api/auth/login", { username, password });
      await refreshAuth();
      router.replace("/");
    } catch (err) {
      setError((err as Error).message || t("login.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto mt-10 max-w-sm">
      <div className="rounded-[24px] border border-border bg-card p-6 sm:p-8">
        <div className="mb-6 flex flex-col items-center text-center">
          <Logo size={48} />
          <h1 className="mt-4 text-xl font-semibold tracking-tight">{setup ? t("login.setup_title") : t("login.title")}</h1>
          {setup && <p className="mt-2 text-sm text-muted">{t("login.setup_text")}</p>}
        </div>
        <form onSubmit={submit} className="space-y-4">
          <Field label={t("login.username")} htmlFor="username">
            <Input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </Field>
          <Field label={t("login.password")} htmlFor="password" hint={setup ? t("login.password_hint") : undefined}>
            <Input
              id="password"
              type="password"
              autoComplete={setup ? "new-password" : "current-password"}
              value={password}
              minLength={setup ? 8 : 1}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>
          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}
          <Button type="submit" variant="primary" className="w-full" size="lg" disabled={busy || !auth}>
            {setup ? t("login.create") : t("login.submit")}
          </Button>
        </form>
      </div>
    </div>
  );
}
