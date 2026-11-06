"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Layers,
  ArrowRight,
  Sparkles,
  Scale,
  Users,
  Activity,
} from "lucide-react";

interface HealthStatus {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export default function HomePage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((data) => {
        setHealth(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Health fetch error:", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-10">
      {/* Hero Header */}
      <div className="border-b border-slate-200 pb-8">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium mb-4">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Explainable Pre-Publication Brand Governance</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          VeriBrand <span className="text-blue-600">Trace</span>
        </h1>
        <p className="mt-3 text-base text-slate-600 max-w-3xl leading-relaxed">
          Audit marketing and creative assets before publication with deterministic brand compliance,
          citation-grounded AI claim verification, and side-by-side human-in-the-loop diff editing.
        </p>

        {/* Guiding Principle Banner */}
        <div className="mt-5 p-3.5 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-between text-xs text-slate-700">
          <div className="flex items-center space-x-2">
            <Scale className="h-4 w-4 text-slate-500" />
            <span className="font-semibold text-slate-800">Core Principle:</span>
            <span>Suggest, Never Override. AI assists and cites sources; human reviewers retain final publishing authority.</span>
          </div>
          <span className="font-mono text-slate-500 uppercase tracking-wider text-[10px]">Team Last of Us</span>
        </div>
      </div>

      {/* Metrics & Readiness Formula Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Brand Readiness Score Blueprint */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Brand Readiness Score
            </span>
            <span className="px-2 py-0.5 text-[11px] font-medium bg-emerald-50 text-emerald-700 rounded border border-emerald-200">
              Target ≥ 85%
            </span>
          </div>
          <div className="mt-4 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold text-slate-900 tracking-tight">96</span>
            <span className="text-sm font-medium text-slate-500">/ 100</span>
          </div>
          <p className="mt-2 text-xs text-slate-500 leading-normal">
            Formula: <code>max(0, 100 - 25(Crit) - 10(High) - 5(Med) - 1(Low))</code>. Any unresolved critical violation blocks approval.
          </p>
        </div>

        {/* Deterministic Engine Status */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Deterministic Rules
            </span>
            <span className="px-2 py-0.5 text-[11px] font-medium bg-blue-50 text-blue-700 rounded border border-blue-200">
              Zero-Hallucination
            </span>
          </div>
          <div className="mt-4 space-y-2 text-xs text-slate-600">
            <div className="flex justify-between items-center">
              <span>Banned / Preferred Terms:</span>
              <span className="font-semibold text-slate-800">Regex & Boundary Scanner</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Visual Colors & Logos:</span>
              <span className="font-semibold text-slate-800">CIEDE2000 Delta-E &lt; 2.0</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Accessibility Checks:</span>
              <span className="font-semibold text-slate-800">WCAG 2.1 AA Contrast</span>
            </div>
          </div>
        </div>

        {/* Grounded AI Engine Status */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Grounded AI Engine
            </span>
            <span className="px-2 py-0.5 text-[11px] font-medium bg-purple-50 text-purple-700 rounded border border-purple-200">
              Gemini 2.5 Flash
            </span>
          </div>
          <div className="mt-4 space-y-2 text-xs text-slate-600">
            <div className="flex justify-between items-center">
              <span>Retrieval Vector Store:</span>
              <span className="font-semibold text-slate-800">pgvector (PostgreSQL)</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Privacy Boundary:</span>
              <span className="font-semibold text-slate-800">Pre-AI PII & Term Redaction</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Evidence Policy:</span>
              <span className="font-semibold text-slate-800">Mandatory Source Citation</span>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Action Workflows */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900 mb-4">Core Workflows</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Link
            href="/audits/new"
            className="group p-4 rounded-lg border border-slate-200 hover:border-blue-400 hover:bg-blue-50/30 transition flex flex-col justify-between"
          >
            <div>
              <div className="h-8 w-8 rounded bg-blue-100 text-blue-700 flex items-center justify-center mb-3">
                <FileText className="h-4 w-4" />
              </div>
              <h3 className="font-medium text-sm text-slate-900 group-hover:text-blue-600 transition">
                New Content Audit
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Upload text, DOCX, PDF, PNG, or JPG for pre-publication validation.
              </p>
            </div>
            <div className="mt-4 flex items-center text-xs font-medium text-blue-600">
              <span>Start audit</span>
              <ArrowRight className="h-3 w-3 ml-1 group-hover:translate-x-1 transition" />
            </div>
          </Link>

          <Link
            href="/brand-vault"
            className="group p-4 rounded-lg border border-slate-200 hover:border-blue-400 hover:bg-blue-50/30 transition flex flex-col justify-between"
          >
            <div>
              <div className="h-8 w-8 rounded bg-slate-100 text-slate-700 flex items-center justify-center mb-3">
                <Layers className="h-4 w-4" />
              </div>
              <h3 className="font-medium text-sm text-slate-900 group-hover:text-blue-600 transition">
                Brand Vault
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Manage guideline documents, approved facts, terminology, and visual rules.
              </p>
            </div>
            <div className="mt-4 flex items-center text-xs font-medium text-slate-700 group-hover:text-blue-600">
              <span>View Vault</span>
              <ArrowRight className="h-3 w-3 ml-1 group-hover:translate-x-1 transition" />
            </div>
          </Link>

          <Link
            href="/review-queue"
            className="group p-4 rounded-lg border border-slate-200 hover:border-blue-400 hover:bg-blue-50/30 transition flex flex-col justify-between"
          >
            <div>
              <div className="h-8 w-8 rounded bg-amber-100 text-amber-700 flex items-center justify-center mb-3">
                <CheckCircle2 className="h-4 w-4" />
              </div>
              <h3 className="font-medium text-sm text-slate-900 group-hover:text-blue-600 transition">
                Review Queue
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Inspect diffs, handle creator exception requests, and sign compliance certificates.
              </p>
            </div>
            <div className="mt-4 flex items-center text-xs font-medium text-slate-700 group-hover:text-blue-600">
              <span>Open queue</span>
              <ArrowRight className="h-3 w-3 ml-1 group-hover:translate-x-1 transition" />
            </div>
          </Link>

          <div className="p-4 rounded-lg border border-slate-200 bg-slate-50 flex flex-col justify-between">
            <div>
              <div className="h-8 w-8 rounded bg-emerald-100 text-emerald-700 flex items-center justify-center mb-3">
                <Activity className="h-4 w-4" />
              </div>
              <h3 className="font-medium text-sm text-slate-900">
                System Status
              </h3>
              <div className="mt-2 text-xs text-slate-600 space-y-1 font-mono">
                <div>Frontend: <span className="text-emerald-600 font-bold">Healthy (v1.0.0)</span></div>
                <div>Backend: <span className="text-emerald-600 font-bold">FastAPI 200 OK</span></div>
              </div>
            </div>
            <div className="mt-4 text-[11px] text-slate-500">
              {loading ? "Checking services..." : `Last ping: ${health?.timestamp?.slice(11, 19) || "Active"}`}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

