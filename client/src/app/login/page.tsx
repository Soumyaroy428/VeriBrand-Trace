"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ShieldCheck, ArrowRight, Lock, Mail, AlertCircle, UserCheck } from "lucide-react";
import { useAuth, RoleType } from "@/context/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { login, switchDemoRole, user, activeWorkspace } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const result = await login(email, password);
    setIsSubmitting(false);

    if (result.success) {
      router.push("/");
    } else {
      setError(result.error || "Authentication failed");
    }
  };

  const handleDemoSelect = (role: RoleType) => {
    switchDemoRole(role);
    router.push("/");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-white">VeriBrand Trace</span>
        </div>
        <h2 className="text-center text-xl font-semibold tracking-tight text-slate-200">
          Sign in to your brand workspace
        </h2>
        <p className="mt-1 text-center text-xs text-slate-400">
          Deterministic compliance & AI claim verification governance
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 sm:p-8 shadow-xl">
          {error && (
            <div className="mb-5 p-3 rounded-lg bg-rose-950/60 border border-rose-800/80 text-rose-200 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 py-2.5 px-4 bg-teal-500 hover:bg-teal-400 active:bg-teal-600 disabled:opacity-50 text-slate-950 font-medium text-sm rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              {isSubmitting ? "Authenticating..." : "Sign In with Credentials"}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-800">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold tracking-wide text-slate-400 uppercase">
                Instant Role Switching (Development)
              </span>
              <UserCheck className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Select a pre-seeded persona to test workspace role-based governance:
            </p>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleDemoSelect("CREATOR")}
                className="p-2.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition-colors group"
              >
                <div className="text-[11px] font-semibold text-sky-400 group-hover:text-sky-300">Creator</div>
                <div className="text-[10px] text-slate-400 truncate">Alice</div>
              </button>

              <button
                type="button"
                onClick={() => handleDemoSelect("REVIEWER")}
                className="p-2.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition-colors group"
              >
                <div className="text-[11px] font-semibold text-amber-400 group-hover:text-amber-300">Reviewer</div>
                <div className="text-[10px] text-slate-400 truncate">Bob</div>
              </button>

              <button
                type="button"
                onClick={() => handleDemoSelect("GOVERNANCE_ADMIN")}
                className="p-2.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition-colors group"
              >
                <div className="text-[11px] font-semibold text-emerald-400 group-hover:text-emerald-300">Admin</div>
                <div className="text-[10px] text-slate-400 truncate">Carol</div>
              </button>
            </div>
          </div>

          <div className="mt-6 text-center text-xs text-slate-400">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-teal-400 hover:text-teal-300 font-medium">
              Create a new user account
            </Link>
          </div>
        </div>

        {user && activeWorkspace && (
          <div className="mt-4 p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs text-slate-400 flex items-center justify-between">
            <span>
              Currently signed in as: <strong className="text-slate-200">{user.full_name}</strong> ({activeWorkspace.role})
            </span>
            <Link href="/" className="text-teal-400 hover:underline">
              Return to app &rarr;
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

