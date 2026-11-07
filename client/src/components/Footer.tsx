"use client";

import React from "react";
import Link from "next/link";
import { ShieldCheck, Scale, Lock, ExternalLink, Activity, Sparkles, Terminal } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-slate-800/80 bg-[#060910] text-slate-400 mt-20 relative z-10">
      {/* Top Banner: Core Ethos */}
      <div className="border-b border-slate-800/60 bg-[#090d16]/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2 text-slate-300">
            <Scale className="w-4 h-4 text-teal-400 shrink-0" />
            <span className="font-semibold text-white">Ethos:</span>
            <span>Suggest, Never Override. AI assists and cites sources; human reviewers retain final publishing authority.</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-400">
            <span className="flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-emerald-400">Systems Normal</span>
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">pgvector v0.7</span>
            <span className="text-slate-600">|</span>
            <span className="text-teal-400">SHA-256 Ledger</span>
          </div>
        </div>
      </div>

      {/* Main Footer Links */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Info */}
          <div className="space-y-4 md:col-span-1">
            <div className="flex items-center space-x-2.5">
              <div className="h-8 w-8 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <span className="font-bold text-white tracking-tight">
                VeriBrand <span className="text-teal-400 font-mono text-xs font-semibold">TRACE</span>
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              High-integrity pre-publication brand governance designed with cryptographic rigor, zero-hallucination deterministic rules, and human-in-the-loop diff editing.
            </p>
            <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-500">
              <Terminal className="w-3.5 h-3.5 text-teal-400" />
              <span>Press <kbd className="px-1 py-0.5 bg-slate-800 rounded border border-slate-700 text-slate-300">⌘K</kbd> anywhere for commands</span>
            </div>
          </div>

          {/* Core Platform */}
          <div>
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-200 mb-3">
              Governance Core
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/audits/new" className="hover:text-teal-400 transition">
                  New Content Audit
                </Link>
              </li>
              <li>
                <Link href="/audits" className="hover:text-teal-400 transition">
                  Submissions & Revisions
                </Link>
              </li>
              <li>
                <Link href="/review" className="hover:text-teal-400 transition">
                  Reviewer Queue & Diffing
                </Link>
              </li>
              <li>
                <Link href="/brand-vault" className="hover:text-teal-400 transition">
                  Brand Vault (Rules & Facts)
                </Link>
              </li>
              <li>
                <Link href="/batches" className="hover:text-teal-400 transition">
                  Campaign Batches
                </Link>
              </li>
            </ul>
          </div>

          {/* Trust & Cryptography */}
          <div>
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-200 mb-3">
              Trust & Architecture
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/audit-trail" className="hover:text-teal-400 transition flex items-center gap-1.5">
                  <Lock className="w-3 h-3 text-teal-400" />
                  <span>Tamper-Evident Ledger</span>
                </Link>
              </li>
              <li>
                <Link href="/governance" className="hover:text-teal-400 transition">
                  Governance Analytics & Drift
                </Link>
              </li>
              <li>
                <Link href="/operations" className="hover:text-teal-400 transition flex items-center gap-1.5">
                  <Activity className="w-3 h-3 text-emerald-400" />
                  <span>System Ops & Health</span>
                </Link>
              </li>
              <li>
                <Link href="/verify/CERT-DEMO-001" className="hover:text-teal-400 transition">
                  Public Certificate Validator
                </Link>
              </li>
            </ul>
          </div>

          {/* Engine Specs */}
          <div>
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-200 mb-3">
              Engine Specifications
            </h4>
            <div className="space-y-2 text-[11px] font-mono text-slate-400">
              <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-teal-400 font-semibold block">Privacy Gate</span>
                <span>PII Redaction & Term Masking before AI</span>
              </div>
              <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-emerald-400 font-semibold block">Deterministic Scan</span>
                <span>Regex boundary scanner & CIEDE2000 ΔE</span>
              </div>
              <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-purple-400 font-semibold block">Grounded AI Verification</span>
                <span>Gemini 2.5 Flash + pgvector RAG</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom copyright line */}
        <div className="mt-12 pt-6 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-3">
          <p>
            VeriBrand Trace &copy; {new Date().getFullYear()} Team Last of Us. Explainable Brand Governance Platform.
          </p>
          <div className="flex items-center space-x-4">
            <span className="text-[11px] font-mono text-slate-400">v1.0.0 Production Release</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
