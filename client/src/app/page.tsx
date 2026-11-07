"use client";

import React, { useState, useEffect, useMemo } from "react";
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
  Lock,
  Boxes,
  BarChart3,
  Search,
  Eye,
  Check,
  RotateCcw,
  Sliders,
  ChevronRight,
  ShieldAlert,
  Fingerprint,
  Zap,
  History,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

interface HealthStatus {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

// Sample presets for the Live Interactive Audit Playground
const PLAYGROUND_PRESETS = [
  {
    id: "greenwashing",
    title: "Eco Greenwashing Claim",
    badge: "Critical Claim Violation",
    badgeColor: "text-rose-400 bg-rose-500/10 border-rose-500/30",
    text: "Our new FalconCore engine delivers 100% zero carbon footprint across all operations. Guaranteed completely eco-friendly and eco-safe.",
    confidentialTerms: ["FalconCore"],
    expectedScore: 45,
    findings: [
      {
        category: "CLAIM_ACCURACY",
        severity: "CRITICAL",
        title: "Unsubstantiated Absolute Environmental Claim",
        desc: "Claims '100% zero carbon footprint' without validated lifecycle assessment citations.",
        replacement: "reduces carbon emissions by up to 34% compared to baseline (verified by ISO 14064)",
      },
      {
        category: "TERMINOLOGY",
        severity: "HIGH",
        title: "Banned Broad Superlative",
        desc: "Term 'completely eco-friendly' violates greenwashing disclosure standards.",
        replacement: "engineered for improved resource efficiency",
      },
      {
        category: "CONFIDENTIAL",
        severity: "HIGH",
        title: "Unannounced Codename Detected",
        desc: "Codename 'FalconCore' is restricted prior to Q4 keynote release.",
        replacement: "[CONFIDENTIAL_PROJECT_1]",
      },
    ],
  },
  {
    id: "pii_leak",
    title: "PII & Executive Contact Leak",
    badge: "Privacy Gate Triggered",
    badgeColor: "text-amber-400 bg-amber-500/10 border-amber-500/30",
    text: "For early access to Project Titan, direct partner queries to sarah.connor@veribrand.io or phone +1 (555) 234-5678 immediately.",
    confidentialTerms: ["Project Titan"],
    expectedScore: 65,
    findings: [
      {
        category: "PRIVACY",
        severity: "HIGH",
        title: "PII Scrubbed: Direct Corporate Email",
        desc: "Unmasked personal work email 'sarah.connor@veribrand.io' redacted before AI processing.",
        replacement: "[REDACTED_EMAIL]",
      },
      {
        category: "PRIVACY",
        severity: "MEDIUM",
        title: "PII Scrubbed: Direct Phone Number",
        desc: "Personal contact number '+1 (555) 234-5678' masked.",
        replacement: "[REDACTED_PHONE]",
      },
      {
        category: "CONFIDENTIAL",
        severity: "HIGH",
        title: "Secret Project Codename",
        desc: "'Project Titan' masked to prevent LLM memory poisoning.",
        replacement: "[CONFIDENTIAL_PROJECT_2]",
      },
    ],
  },
  {
    id: "compliant",
    title: "Certified Compliant Copy",
    badge: "Ready for Publication",
    badgeColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    text: "The VeriBrand enterprise governance system enables real-time deterministic policy enforcement and cryptographic audit logging under ISO-27001 standards.",
    confidentialTerms: [],
    expectedScore: 98,
    findings: [],
  },
];

export default function HomePage() {
  const { switchDemoRole, activeWorkspace } = useAuth();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  // Live Playground State
  const [activePreset, setActivePreset] = useState(PLAYGROUND_PRESETS[0]);
  const [playgroundText, setPlaygroundText] = useState(PLAYGROUND_PRESETS[0].text);
  const [playgroundConfidential, setPlaygroundConfidential] = useState<string[]>(
    PLAYGROUND_PRESETS[0].confidentialTerms
  );
  const [privacyGateEnabled, setPrivacyGateEnabled] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [scanCompleted, setScanCompleted] = useState(true);

  // Fetch health status
  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((data) => {
        setHealth(data);
        setLoadingHealth(false);
      })
      .catch((err) => {
        console.error("Health fetch error:", err);
        setLoadingHealth(false);
      });
  }, []);

  const selectPreset = (preset: (typeof PLAYGROUND_PRESETS)[0]) => {
    setActivePreset(preset);
    setPlaygroundText(preset.text);
    setPlaygroundConfidential(preset.confidentialTerms);
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
      setScanCompleted(true);
    }, 400);
  };

  // Instant Privacy Gate simulation
  const sanitizationResult = useMemo(() => {
    if (!privacyGateEnabled) {
      return { sanitized: playgroundText, piiCount: 0, termsCount: 0 };
    }

    let text = playgroundText;
    let piiCount = 0;
    let termsCount = 0;

    // Detect and scrub emails
    const emailRegex = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;
    const emails = text.match(emailRegex) || [];
    if (emails.length > 0) {
      piiCount += emails.length;
      text = text.replace(emailRegex, "[REDACTED_EMAIL]");
    }

    // Detect and scrub phones
    const phoneRegex = /(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g;
    const phones = text.match(phoneRegex) || [];
    if (phones.length > 0) {
      piiCount += phones.length;
      text = text.replace(phoneRegex, "[REDACTED_PHONE]");
    }

    // Scrub confidential terms
    playgroundConfidential.forEach((term, idx) => {
      if (!term.trim()) return;
      const regex = new RegExp(`\\b${term}\\b`, "gi");
      const matches = text.match(regex);
      if (matches) {
        termsCount += matches.length;
        text = text.replace(regex, `[CONFIDENTIAL_PROJECT_${idx + 1}]`);
      }
    });

    return { sanitized: text, piiCount, termsCount };
  }, [playgroundText, playgroundConfidential, privacyGateEnabled]);

  // Dynamic calculated score
  const liveScore = useMemo(() => {
    if (activePreset.id === "compliant") return 98;
    if (activePreset.id === "pii_leak") {
      return privacyGateEnabled ? 92 : 65;
    }
    return 48;
  }, [activePreset, privacyGateEnabled]);

  const handleSimulateScan = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
      setScanCompleted(true);
    }, 600);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-16">
      {/* Hero Header Section */}
      <section className="relative pt-4 sm:pt-8 pb-4 text-center sm:text-left">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
          <div className="space-y-4 max-w-3xl">
            {/* Ambient status pill */}
            <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs font-mono font-medium">
              <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
              <span>Sovereign Pre-Publication Brand Governance</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-400">Gemini 2.5 Flash + pgvector</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.1]">
              Where Brand Integrity Meets{" "}
              <span className="bg-gradient-to-r from-teal-400 via-cyan-300 to-emerald-400 bg-clip-text text-transparent">
                Mathematical Certainty.
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-300 leading-relaxed font-sans max-w-2xl">
              Audit marketing copy, creative assets, and sustainability claims before release.
              Deterministic zero-hallucination rules, citation-grounded AI claim verification, and side-by-side human diffing with cryptographic sign-off.
            </p>

            {/* Core Principle Callout */}
            <div className="p-3.5 rounded-xl bg-[#0e1320] border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center space-x-2.5 text-slate-300">
                <Scale className="h-4 w-4 text-teal-400 shrink-0" />
                <span className="font-semibold text-white">Guiding Law:</span>
                <span>Suggest, Never Override. AI assists and cites sources; human reviewers retain final publishing authority.</span>
              </div>
              <span className="font-mono text-teal-400/90 uppercase tracking-widest text-[10px] shrink-0">
                Team Last of Us
              </span>
            </div>

            {/* Hero Quick Action Buttons */}
            <div className="pt-2 flex flex-wrap items-center gap-3">
              <Link
                href="/audits/new"
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-sm flex items-center space-x-2 transition shadow-[0_0_20px_rgba(20,184,166,0.3)] hover:scale-[1.02]"
              >
                <FileText className="w-4 h-4" />
                <span>Start New Content Audit</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Link>
              <Link
                href="/review"
                className="px-5 py-2.5 rounded-xl bg-[#141b2d] hover:bg-[#1c253d] text-slate-200 border border-slate-700 font-semibold text-sm flex items-center space-x-2 transition"
              >
                <History className="w-4 h-4 text-amber-400" />
                <span>Reviewer Queue</span>
              </Link>
              <a
                href="#interactive-playground"
                className="px-4 py-2.5 rounded-xl text-teal-300 hover:text-teal-200 border border-teal-500/20 hover:border-teal-500/40 text-sm font-medium transition flex items-center gap-1.5"
              >
                <Sparkles className="w-4 h-4 text-teal-400" />
                <span>Try Live Simulator</span>
              </a>
            </div>
          </div>

          {/* Quick Engine Telemetry Blueprint Card */}
          <div className="w-full lg:w-96 rounded-2xl bg-[#0e1320] border border-slate-800 p-6 shadow-2xl relative overflow-hidden text-left">
            <div className="absolute top-0 right-0 -mr-16 -mt-16 w-48 h-48 rounded-full bg-teal-500/10 blur-3xl pointer-events-none" />

            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <span className="text-xs font-mono font-bold text-teal-400 uppercase tracking-wider flex items-center gap-1.5">
                <Fingerprint className="w-4 h-4" />
                <span>Readiness Target</span>
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-300 rounded border border-emerald-500/30">
                Target ≥ 85%
              </span>
            </div>

            <div className="mt-4 flex items-baseline space-x-3">
              <span className="text-5xl font-extrabold text-white font-mono tracking-tight font-tabular">
                96
              </span>
              <span className="text-slate-400 font-mono text-sm">/ 100</span>
              <span className="ml-auto text-xs font-semibold px-2 py-1 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                PUBLISH READY
              </span>
            </div>

            <p className="mt-3 text-xs text-slate-400 leading-relaxed font-mono">
              Formula: <code className="text-teal-300">max(0, 100 - 25(Crit) - 10(High) - 5(Med) - 1(Low))</code>
            </p>

            <div className="mt-4 pt-4 border-t border-slate-800/80 space-y-2 text-xs font-mono">
              <div className="flex justify-between items-center text-slate-300">
                <span>Deterministic Rules:</span>
                <span className="text-emerald-400 font-semibold">Zero-Hallucination</span>
              </div>
              <div className="flex justify-between items-center text-slate-300">
                <span>Visual CIEDE2000:</span>
                <span className="text-emerald-400 font-semibold">&Delta;E &lt; 2.0</span>
              </div>
              <div className="flex justify-between items-center text-slate-300">
                <span>Privacy Boundary:</span>
                <span className="text-teal-400 font-semibold">Pre-AI PII Scrubbing</span>
              </div>
              <div className="flex justify-between items-center text-slate-300">
                <span>Cryptographic Ledger:</span>
                <span className="text-purple-400 font-semibold">SHA-256 Hash Chain</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SHOWSTOPPER: LIVE INTERACTIVE AUDIT PLAYGROUND */}
      <section id="interactive-playground" className="space-y-6 scroll-mt-24">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="inline-flex items-center space-x-2 text-xs font-mono uppercase tracking-widest text-teal-400 mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Interactive Evaluation Sandbox</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Live Governance & Claim Verification Engine
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Experience deterministic policy checks, pre-LLM Privacy Gate scrubbing, and explainable claim verification directly in your browser.
            </p>
          </div>

          {/* Quick preset selector buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 font-mono mr-1">Load Preset:</span>
            {PLAYGROUND_PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => selectPreset(preset)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                  activePreset.id === preset.id
                    ? "bg-teal-500/20 text-teal-300 border-teal-500/40 shadow-sm"
                    : "bg-[#0e1320] text-slate-400 border-slate-800 hover:text-white hover:border-slate-700"
                }`}
              >
                {preset.title}
              </button>
            ))}
          </div>
        </div>

        {/* Playground Sandbox Interface */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Input Pane: Copy Editor & Privacy Controls */}
          <div className="lg:col-span-7 space-y-4">
            <div className="rounded-2xl bg-[#0e1320] border border-slate-800 p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs">
                <div className="flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-teal-400" />
                  <span className="font-semibold text-white">Marketing Copy Input</span>
                  <span className="text-slate-500">({playgroundText.length} chars)</span>
                </div>

                {/* Privacy Gate Toggle */}
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] font-mono text-slate-400">Privacy Gate:</span>
                  <button
                    onClick={() => setPrivacyGateEnabled(!privacyGateEnabled)}
                    className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      privacyGateEnabled ? "bg-teal-500" : "bg-slate-700"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition duration-200 ease-in-out ${
                        privacyGateEnabled ? "translate-x-4" : "translate-x-0"
                      }`}
                    />
                  </button>
                  <span
                    className={`text-[10px] font-mono font-semibold ${
                      privacyGateEnabled ? "text-teal-400" : "text-slate-500"
                    }`}
                  >
                    {privacyGateEnabled ? "ON" : "OFF"}
                  </span>
                </div>
              </div>

              {/* Textarea */}
              <div className="relative">
                <textarea
                  value={playgroundText}
                  onChange={(e) => setPlaygroundText(e.target.value)}
                  rows={4}
                  className="w-full rounded-xl bg-[#080c14] border border-slate-800 p-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-teal-500/60 font-sans leading-relaxed transition"
                  placeholder="Paste marketing copy, product specs, or creative claims to audit..."
                />
              </div>

              {/* Confidential Terms Tokens */}
              <div className="pt-1 flex flex-wrap items-center gap-2 text-xs">
                <span className="text-[11px] font-mono text-slate-400">Confidential Codewords:</span>
                {playgroundConfidential.length > 0 ? (
                  playgroundConfidential.map((term, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-purple-500/15 border border-purple-500/30 text-purple-300 font-mono text-[11px]"
                    >
                      <Lock className="w-3 h-3 text-purple-400" />
                      <span>{term}</span>
                    </span>
                  ))
                ) : (
                  <span className="text-[11px] text-slate-500 italic">None configured</span>
                )}
              </div>

              {/* Privacy Gate Scrubbing Output Preview */}
              {privacyGateEnabled && (
                <div className="p-3.5 rounded-xl bg-[#141b2d]/60 border border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-teal-300 font-semibold flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
                      <span>Privacy Gate Scrubbed Text (Sent to AI):</span>
                    </span>
                    <span className="text-slate-400 text-[11px]">
                      {sanitizationResult.piiCount} PII masked • {sanitizationResult.termsCount} terms masked
                    </span>
                  </div>
                  <p className="text-xs font-mono text-slate-300 bg-[#080c14] p-3 rounded-lg border border-slate-800/80 leading-relaxed whitespace-pre-wrap">
                    {sanitizationResult.sanitized}
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 flex items-center justify-between">
                <button
                  onClick={handleSimulateScan}
                  disabled={isScanning}
                  className="px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs flex items-center gap-2 transition disabled:opacity-50 shadow-[0_0_15px_rgba(20,184,166,0.25)]"
                >
                  <Zap className={`w-3.5 h-3.5 ${isScanning ? "animate-spin" : ""}`} />
                  <span>{isScanning ? "Evaluating Rules & AI..." : "Re-Scan Copy"}</span>
                </button>

                <Link
                  href="/audits/new"
                  className="text-xs font-medium text-slate-400 hover:text-teal-300 flex items-center gap-1 transition"
                >
                  <span>Create formal audit file</span>
                  <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </div>

          {/* Right Output Pane: Live Brand Readiness Gauge & Findings */}
          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-2xl bg-[#0e1320] border border-slate-800 p-5 shadow-xl space-y-5">
              {/* Readiness Score Card */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div>
                  <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
                    Brand Readiness Score
                  </div>
                  <div className="mt-1 flex items-baseline space-x-2">
                    <span
                      className={`text-4xl font-extrabold font-mono tracking-tight font-tabular ${
                        liveScore >= 85
                          ? "text-emerald-400"
                          : liveScore >= 60
                          ? "text-amber-400"
                          : "text-rose-400"
                      }`}
                    >
                      {liveScore}
                    </span>
                    <span className="text-sm font-mono text-slate-500">/ 100</span>
                  </div>
                </div>

                {/* Score Status Badge */}
                <div className="text-right">
                  <span
                    className={`inline-block px-3 py-1 rounded-lg text-xs font-mono font-bold border ${
                      liveScore >= 85
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                        : liveScore >= 60
                        ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                        : "bg-rose-500/15 text-rose-300 border-rose-500/30"
                    }`}
                  >
                    {liveScore >= 85
                      ? "PASS (≥ 85%)"
                      : liveScore >= 60
                      ? "NEEDS REVIEW"
                      : "BLOCKED (< 60%)"}
                  </span>
                  <p className="text-[10px] text-slate-500 mt-1 font-mono">
                    {liveScore >= 85
                      ? "Eligible for Reviewer Sign-Off"
                      : "Critical Findings Block Approval"}
                  </p>
                </div>
              </div>

              {/* Progress bar visual */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-[11px] font-mono text-slate-400">
                  <span>Compliance Threshold</span>
                  <span>Target: 85%</span>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${
                      liveScore >= 85
                        ? "bg-emerald-400"
                        : liveScore >= 60
                        ? "bg-amber-400"
                        : "bg-rose-500"
                    }`}
                    style={{ width: `${liveScore}%` }}
                  />
                </div>
              </div>

              {/* Live Findings List */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                  <span className="font-semibold text-white">Detected Findings:</span>
                  <span>{activePreset.findings.length} total</span>
                </div>

                {activePreset.findings.length === 0 ? (
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center space-y-1">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 mx-auto" />
                    <p className="text-xs font-semibold text-emerald-300">
                      Zero Policy Violations Detected
                    </p>
                    <p className="text-[11px] text-slate-400">
                      Copy adheres to all brand guidelines and cited benchmark facts.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                    {activePreset.findings.map((f, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-xl bg-[#141b2d]/70 border border-slate-800 space-y-1.5 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                              f.severity === "CRITICAL"
                                ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                                : "bg-amber-500/15 text-amber-300 border-amber-500/30"
                            }`}
                          >
                            {f.severity}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500 uppercase">
                            {f.category}
                          </span>
                        </div>
                        <h4 className="font-semibold text-white">{f.title}</h4>
                        <p className="text-slate-400 text-[11px] leading-relaxed">{f.desc}</p>
                        <div className="pt-1 text-[11px] font-mono">
                          <span className="text-teal-400 font-medium">Suggested Fix: </span>
                          <span className="text-slate-300 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                            {f.replacement}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4-Stage Sovereign Governance Architecture Visualizer */}
      <section className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <div className="inline-flex items-center space-x-2 text-xs font-mono uppercase tracking-widest text-teal-400">
            <Layers className="w-3.5 h-3.5" />
            <span>Cryptographic Pipeline</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            How VeriBrand Trace Enforces Brand Truth
          </h2>
          <p className="text-sm text-slate-400">
            A 4-tier pipeline combining deterministic rule execution, privacy sandboxing, grounded AI verification, and sovereign human authority.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4">
          {/* Stage 1 */}
          <div className="rounded-2xl bg-[#0e1320] border border-slate-800 p-5 space-y-3 relative overflow-hidden group hover:border-teal-500/40 transition">
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-400 flex items-center justify-center font-mono font-bold text-xs">
              01
            </div>
            <h3 className="text-sm font-bold text-white group-hover:text-teal-300 transition">
              Privacy Gate Redaction
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Every document is scrubbed locally before AI exposure. PII (emails, phones) and confidential codenames are replaced with masked tokens.
            </p>
            <div className="text-[10px] font-mono text-teal-400/80 pt-1">
              Zero PII Transmission
            </div>
          </div>

          {/* Stage 2 */}
          <div className="rounded-2xl bg-[#0e1320] border border-slate-800 p-5 space-y-3 relative overflow-hidden group hover:border-teal-500/40 transition">
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-400 flex items-center justify-center font-mono font-bold text-xs">
              02
            </div>
            <h3 className="text-sm font-bold text-white group-hover:text-sky-300 transition">
              Deterministic Rules
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Banned words via regex boundary matchers, WCAG 2.1 contrast, and visual hex compliance calculated with CIEDE2000 Delta-E &lt; 2.0.
            </p>
            <div className="text-[10px] font-mono text-sky-400/80 pt-1">
              Zero-Hallucination
            </div>
          </div>

          {/* Stage 3 */}
          <div className="rounded-2xl bg-[#0e1320] border border-slate-800 p-5 space-y-3 relative overflow-hidden group hover:border-teal-500/40 transition">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-400 flex items-center justify-center font-mono font-bold text-xs">
              03
            </div>
            <h3 className="text-sm font-bold text-white group-hover:text-purple-300 transition">
              Grounded AI Verification
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Gemini 2.5 Flash semantically verifies sustainability, performance, and legal claims against approved Brand Vault vectors in PostgreSQL pgvector.
            </p>
            <div className="text-[10px] font-mono text-purple-400/80 pt-1">
              Mandatory Source Citations
            </div>
          </div>

          {/* Stage 4 */}
          <div className="rounded-2xl bg-[#0e1320] border border-slate-800 p-5 space-y-3 relative overflow-hidden group hover:border-teal-500/40 transition">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center font-mono font-bold text-xs">
              04
            </div>
            <h3 className="text-sm font-bold text-white group-hover:text-emerald-300 transition">
              Human-in-the-Loop Sign-off
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Side-by-side diff workspace allows reviewers to accept/reject edits and issue official compliance certificates chained with SHA-256 ledger hashes.
            </p>
            <div className="text-[10px] font-mono text-emerald-400/80 pt-1">
              Cryptographic Proof
            </div>
          </div>
        </div>
      </section>

      {/* Core Platform Workflows Grid */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Command Modules & Core Workflows
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              Access the complete suite of brand verification and governance tools.
            </p>
          </div>
          <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>All 8 Modules Active</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Card 1: New Audit */}
          <Link
            href="/audits/new"
            className="group p-5 rounded-2xl bg-[#0e1320] border border-slate-800 hover:border-teal-500/40 transition flex flex-col justify-between shadow-lg glow-card"
          >
            <div>
              <div className="h-10 w-10 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-400 flex items-center justify-center mb-4 group-hover:scale-105 transition">
                <FileText className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-base text-white group-hover:text-teal-300 transition">
                New Content Audit
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Upload text, DOCX, PDF, PNG, or JPG for pre-publication validation through Privacy Gate sanitization.
              </p>
            </div>
            <div className="mt-6 flex items-center text-xs font-semibold text-teal-400 group-hover:translate-x-1 transition">
              <span>Start audit</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </div>
          </Link>

          {/* Card 2: Brand Vault */}
          <Link
            href="/brand-vault"
            className="group p-5 rounded-2xl bg-[#0e1320] border border-slate-800 hover:border-purple-500/40 transition flex flex-col justify-between shadow-lg glow-card"
          >
            <div>
              <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400 flex items-center justify-center mb-4 group-hover:scale-105 transition">
                <Layers className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-base text-white group-hover:text-purple-300 transition">
                Brand Vault
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Manage corporate guidelines, approved facts, forbidden claims, terminology dictionaries, and visual color tokens.
              </p>
            </div>
            <div className="mt-6 flex items-center text-xs font-semibold text-purple-400 group-hover:translate-x-1 transition">
              <span>Explore Vault</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </div>
          </Link>

          {/* Card 3: Review Queue */}
          <Link
            href="/review"
            className="group p-5 rounded-2xl bg-[#0e1320] border border-slate-800 hover:border-amber-500/40 transition flex flex-col justify-between shadow-lg glow-card"
          >
            <div>
              <div className="h-10 w-10 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center justify-center mb-4 group-hover:scale-105 transition">
                <History className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-base text-white group-hover:text-amber-300 transition">
                Review Queue & Diffing
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Side-by-side human-in-the-loop diff editor, creator exception reviews, and official cryptographic compliance sign-off.
              </p>
            </div>
            <div className="mt-6 flex items-center text-xs font-semibold text-amber-400 group-hover:translate-x-1 transition">
              <span>Open Review Queue</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </div>
          </Link>

          {/* Card 4: Campaign Batches */}
          <Link
            href="/batches"
            className="group p-5 rounded-2xl bg-[#0e1320] border border-slate-800 hover:border-cyan-500/40 transition flex flex-col justify-between shadow-lg glow-card"
          >
            <div>
              <div className="h-10 w-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center mb-4 group-hover:scale-105 transition">
                <Boxes className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-base text-white group-hover:text-cyan-300 transition">
                Campaign Batch Auditing
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Audit 50+ omni-channel assets simultaneously with asynchronous parallel queuing and aggregated readiness scorecards.
              </p>
            </div>
            <div className="mt-6 flex items-center text-xs font-semibold text-cyan-400 group-hover:translate-x-1 transition">
              <span>View Batches</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </div>
          </Link>

          {/* Card 5: Governance Intelligence */}
          <Link
            href="/governance"
            className="group p-5 rounded-2xl bg-[#0e1320] border border-slate-800 hover:border-rose-500/40 transition flex flex-col justify-between shadow-lg glow-card"
          >
            <div>
              <div className="h-10 w-10 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center justify-center mb-4 group-hover:scale-105 transition">
                <BarChart3 className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-base text-white group-hover:text-rose-300 transition">
                Governance Analytics
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Workspace telemetry, recurring rule drift diagnostics, exception approval rates, and executive compliance reports.
              </p>
            </div>
            <div className="mt-6 flex items-center text-xs font-semibold text-rose-400 group-hover:translate-x-1 transition">
              <span>View Analytics</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </div>
          </Link>

          {/* Card 6: Tamper-Evident Ledger */}
          <Link
            href="/audit-trail"
            className="group p-5 rounded-2xl bg-[#0e1320] border border-slate-800 hover:border-emerald-500/40 transition flex flex-col justify-between shadow-lg glow-card"
          >
            <div>
              <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mb-4 group-hover:scale-105 transition">
                <Lock className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-base text-white group-hover:text-emerald-300 transition">
                Tamper-Evident Ledger
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Cryptographic SHA-256 hash-chained ledger verifying the immutable sequence of every brand modification and approval.
              </p>
            </div>
            <div className="mt-6 flex items-center text-xs font-semibold text-emerald-400 group-hover:translate-x-1 transition">
              <span>Inspect Ledger</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </div>
          </Link>
        </div>
      </section>

      {/* Role Personas Quick Simulator */}
      <section className="rounded-2xl bg-[#0e1320] border border-slate-800 p-6 sm:p-8 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-teal-400" />
              <span>Multi-Role Governance Experience</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Test how different team members interact with the platform based on enterprise permission boundaries.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">
            Current: <strong className="text-teal-400">{activeWorkspace?.role || "CREATOR"}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Creator Persona */}
          <button
            onClick={() => switchDemoRole("CREATOR")}
            className={`p-4 rounded-xl border text-left transition ${
              activeWorkspace?.role === "CREATOR"
                ? "bg-sky-500/15 border-sky-500/50 text-white shadow-md"
                : "bg-[#141b2d]/60 border-slate-800 text-slate-300 hover:bg-[#141b2d]"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-sm text-sky-400">Alice (Creator)</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/20 text-sky-300">
                Authoring
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Uploads creative assets, tests drafts against Privacy Gate, and submits formal exception requests with justifications.
            </p>
          </button>

          {/* Reviewer Persona */}
          <button
            onClick={() => switchDemoRole("REVIEWER")}
            className={`p-4 rounded-xl border text-left transition ${
              activeWorkspace?.role === "REVIEWER"
                ? "bg-amber-500/15 border-amber-500/50 text-white shadow-md"
                : "bg-[#141b2d]/60 border-slate-800 text-slate-300 hover:bg-[#141b2d]"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-sm text-amber-400">Bob (Reviewer)</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">
                Authority
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Inspects side-by-side diffs, adjudicates exception requests, and signs official compliance certificates when score ≥ 85%.
            </p>
          </button>

          {/* Admin Persona */}
          <button
            onClick={() => switchDemoRole("GOVERNANCE_ADMIN")}
            className={`p-4 rounded-xl border text-left transition ${
              activeWorkspace?.role === "GOVERNANCE_ADMIN"
                ? "bg-emerald-500/15 border-emerald-500/50 text-white shadow-md"
                : "bg-[#141b2d]/60 border-slate-800 text-slate-300 hover:bg-[#141b2d]"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-sm text-emerald-400">Carol (Admin)</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                Governance
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Manages Brand Vault documents, updates forbidden terms, edits color palettes, and accesses full audit export reports.
            </p>
          </button>
        </div>
      </section>
    </div>
  );
}
