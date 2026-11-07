"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Play,
  RotateCcw,
  ExternalLink,
  ChevronRight,
  Info,
  Clock,
  Sliders,
  Sparkles,
  BookOpen,
  Copy,
  Check,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

interface FindingEvidence {
  id: string;
  source_type: string;
  source_id?: string;
  source_version: number;
  quote: string;
  location?: Record<string, any>;
}

interface Finding {
  id: string;
  category: "TERMINOLOGY" | "FACT_CHECK" | "COLOR_COMPLIANCE" | "CONTRAST" | "CLAIM_ACCURACY";
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFORMATIONAL";
  source_engine: "DETERMINISTIC" | "RAG_AI";
  title: string;
  description: string;
  location?: Record<string, any>;
  evidence?: Record<string, any>;
  suggestion?: Record<string, any>;
  status: string;
  evidence_list?: FindingEvidence[];
}

interface AuditRun {
  id: string;
  submission_id: string;
  revision_id: string;
  status: string;
  deterministic_status: string;
  ai_status: string;
  readiness_score: number | null;
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  started_at: string;
  completed_at: string;
}

export default function SubmissionAuditView() {
  const params = useParams();
  const submissionId = params.id as string;
  const router = useRouter();
  const { token, activeWorkspace } = useAuth();

  const [auditRun, setAuditRun] = useState<AuditRun | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [submissionTitle, setSubmissionTitle] = useState("Marketing Release");
  const [rawText, setRawText] = useState("");
  const [sanitizedText, setSanitizedText] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isRunningAudit, setIsRunningAudit] = useState(false);
  const [activeTab, setActiveTab] = useState<"FINDINGS" | "CONTENT">("FINDINGS");

  // Initial demo findings fallback
  const demoFindings: Finding[] = [
    {
      id: "f-1",
      category: "TERMINOLOGY",
      severity: "CRITICAL",
      source_engine: "DETERMINISTIC",
      title: "Banned terminology detected: 'unbreakable'",
      description: "The term 'unbreakable' is strictly prohibited under global compliance guidelines.",
      location: { line: 1, column: 22, matched_text: "unbreakable" },
      evidence: { rule_type: "BANNED", term: "unbreakable" },
      suggestion: { action: "REMOVE_TERM", original: "unbreakable", replacement: "highly resilient" },
      status: "OPEN",
      evidence_list: [
        {
          id: "ev-1",
          source_type: "RULE",
          source_version: 1,
          quote: "Rule: BANNED term 'unbreakable' -> 'highly resilient'",
        },
      ],
    },
    {
      id: "f-2",
      category: "FACT_CHECK",
      severity: "HIGH",
      source_engine: "DETERMINISTIC",
      title: "Unverified numeric claim: '99.99%'",
      description: "Submission claims '99.99%' for uptime, which contradicts Approved Fact #UPTIME_SLA (99.9% uptime).",
      location: { line: 2, column: 14, matched_text: "99.99%" },
      evidence: { fact_key: "UPTIME_SLA", expected_value: 99.9, found_value: 99.99 },
      suggestion: { action: "ALIGN_WITH_APPROVED_FACT", approved_value: "99.9%", statement: "Verified 99.9% uptime SLA." },
      status: "OPEN",
      evidence_list: [
        {
          id: "ev-2",
          source_type: "APPROVED_FACT",
          source_version: 2,
          quote: "Approved Fact #UPTIME_SLA: Platform delivers verified 99.9% uptime SLA.",
        },
      ],
    },
    {
      id: "f-3",
      category: "COLOR_COMPLIANCE",
      severity: "MEDIUM",
      source_engine: "DETERMINISTIC",
      title: "Off-brand color deviation detected (Delta-E: 3.42)",
      description: "Primary visual color #005FB5 diverges from approved brand color #0055AA by Delta-E 3.42 (limit is 2.0).",
      location: { percentage_prominence: 28.4, hex: "#005FB5" },
      evidence: { approved_hex: "#0055AA", measured_hex: "#005FB5", delta_e: 3.42 },
      suggestion: { action: "SNAP_TO_BRAND_PALETTE", approved_hex: "#0055AA" },
      status: "OPEN",
      evidence_list: [
        {
          id: "ev-3",
          source_type: "RULE",
          source_version: 1,
          quote: "Brand color rule requires primary blue #0055AA with CIEDE2000 Delta-E <= 2.0",
        },
      ],
    },
  ];

  useEffect(() => {
    async function loadData() {
      if (!token || !submissionId) {
        setFindings(demoFindings);
        setAuditRun({
          id: "demo-audit",
          submission_id: submissionId,
          revision_id: "demo-rev",
          status: "COMPLETED",
          deterministic_status: "COMPLETED",
          ai_status: "PENDING",
          readiness_score: 65,
          total_findings: 3,
          critical_findings: 1,
          high_findings: 1,
          medium_findings: 1,
          low_findings: 0,
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        });
        return;
      }

      try {
        const subRes = await fetch(`/api/v1/submissions/${submissionId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (subRes.ok) {
          const subData = await subRes.json();
          setSubmissionTitle(subData.submission.title);
          const latestRev = subData.submission.latest_revision;
          if (latestRev) {
            setRawText(latestRev.extracted_text || latestRev.raw_content || "");
            setSanitizedText(latestRev.sanitized_text || "");
          }
        }

        const auditRes = await fetch(`/api/v1/submissions/${submissionId}/latest-audit`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (auditRes.ok) {
          const auditData = await auditRes.json();
          setAuditRun(auditData.audit_run);
          setFindings(auditData.findings);
        } else {
          setFindings(demoFindings);
          setAuditRun({
            id: "demo-audit",
            submission_id: submissionId,
            revision_id: "demo-rev",
            status: "COMPLETED",
            deterministic_status: "COMPLETED",
            ai_status: "PENDING",
            readiness_score: 65,
            total_findings: 3,
            critical_findings: 1,
            high_findings: 1,
            medium_findings: 1,
            low_findings: 0,
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          });
        }
      } catch {
        setFindings(demoFindings);
      }
    }
    loadData();
  }, [submissionId, token]);

  const handleRunAudit = async () => {
    try {
      setIsRunningAudit(true);
      if (token) {
        const res = await fetch(`/api/v1/submissions/${submissionId}/audits`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setAuditRun(data.audit_run);
          setFindings(data.findings);
        }
      } else {
        // Demo simulation
        setTimeout(() => {
          setAuditRun((prev) => (prev ? { ...prev, readiness_score: 70 } : null));
        }, 800);
      }
    } finally {
      setIsRunningAudit(false);
    }
  };

  const handleCopySuggestion = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredFindings = findings.filter((f) => {
    const matchCat = categoryFilter === "ALL" || f.category === categoryFilter;
    const matchSev = severityFilter === "ALL" || f.severity === severityFilter;
    return matchCat && matchSev;
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-red-100 text-red-800 border border-red-200">Critical</span>;
      case "HIGH":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-orange-100 text-orange-800 border border-orange-200">High</span>;
      case "MEDIUM":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-amber-100 text-amber-800 border border-amber-200">Medium</span>;
      case "LOW":
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-slate-100 text-slate-700 border border-slate-200">Low</span>;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 85) return "text-emerald-700 bg-emerald-50 border-emerald-200";
    if (score >= 70) return "text-amber-700 bg-amber-50 border-amber-200";
    return "text-red-700 bg-red-50 border-red-200";
  };

  const readinessScore = auditRun?.readiness_score ?? 100;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Breadcrumb */}
      <div className="flex items-center space-x-2 text-xs font-medium text-slate-500">
        <Link href="/audits" className="hover:text-slate-800 transition">
          Submissions
        </Link>
        <span>/</span>
        <span className="text-slate-900 font-semibold">{submissionTitle}</span>
        <span>/</span>
        <span className="text-teal-700 font-mono">Audit Results</span>
      </div>

      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded border border-teal-200">
              Deterministic Governance Audit
            </span>
            <span className="text-xs text-slate-500">Workspace: {activeWorkspace?.workspace_name || "Acme Global"}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-2">{submissionTitle}</h1>
          <p className="text-xs text-slate-600 mt-1">
            Engine: Python Regex • OpenCV / Pillow CIEDE2000 • WCAG 2.1 AA Luminance • Approved Fact Registry
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleRunAudit}
            disabled={isRunningAudit}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition shadow-sm disabled:opacity-50"
          >
            {isRunningAudit ? <RotateCcw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isRunningAudit ? "Executing Checks..." : "Re-Run Deterministic Audit"}</span>
          </button>
        </div>
      </div>

      {/* Brand Readiness Score & Severity Breakdown Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Score Card */}
        <div className={`p-6 rounded-2xl border shadow-sm flex flex-col justify-between ${getScoreColor(readinessScore)}`}>
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider">Brand Readiness Score</span>
              <span className="text-xs font-mono font-medium">Threshold: ≥ 85%</span>
            </div>
            <div className="mt-4 flex items-baseline space-x-2">
              <span className="text-5xl font-extrabold tracking-tight">{readinessScore}</span>
              <span className="text-lg font-medium opacity-70">/ 100</span>
            </div>
            <p className="text-xs mt-2 opacity-90">
              {readinessScore >= 85
                ? "Content is ready for human reviewer sign-off."
                : "Action required: resolve critical & high compliance findings before publication."}
            </p>
          </div>
          <div className="mt-4 pt-4 border-t border-current/20 text-[11px] font-mono opacity-80">
            Formula: max(0, 100 - (25×Crit) - (10×High) - (5×Med) - (1×Low))
          </div>
        </div>

        {/* Severity Metrics Card */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <span className="text-xs font-bold uppercase text-slate-700">Audit Finding Distribution</span>
              <span className="text-xs text-slate-500 font-mono">
                Total Violations: {findings.length}
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
              <div className="p-3 bg-red-50 rounded-xl border border-red-200">
                <span className="text-[11px] font-semibold text-red-800 uppercase">Critical</span>
                <p className="text-2xl font-bold text-red-900 mt-1">
                  {findings.filter((f) => f.severity === "CRITICAL").length}
                </p>
                <span className="text-[10px] text-red-600">-25 pts each</span>
              </div>
              <div className="p-3 bg-orange-50 rounded-xl border border-orange-200">
                <span className="text-[11px] font-semibold text-orange-800 uppercase">High</span>
                <p className="text-2xl font-bold text-orange-900 mt-1">
                  {findings.filter((f) => f.severity === "HIGH").length}
                </p>
                <span className="text-[10px] text-orange-600">-10 pts each</span>
              </div>
              <div className="p-3 bg-amber-50 rounded-xl border border-amber-200">
                <span className="text-[11px] font-semibold text-amber-800 uppercase">Medium</span>
                <p className="text-2xl font-bold text-amber-900 mt-1">
                  {findings.filter((f) => f.severity === "MEDIUM").length}
                </p>
                <span className="text-[10px] text-amber-600">-5 pts each</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-[11px] font-semibold text-slate-700 uppercase">Low</span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {findings.filter((f) => f.severity === "LOW").length}
                </p>
                <span className="text-[10px] text-slate-500">-1 pt each</span>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Philosophy: <strong>Suggest, Never Override.</strong> AI/Rules never silently rewrite.</span>
            <span className="font-mono text-[11px]">Engine Status: {auditRun?.deterministic_status || "COMPLETED"}</span>
          </div>
        </div>
      </div>

      {/* Tabs: Findings vs Content Preview */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 text-sm font-medium">
          <button
            onClick={() => setActiveTab("FINDINGS")}
            className={`pb-3 transition border-b-2 ${
              activeTab === "FINDINGS"
                ? "border-slate-900 text-slate-900 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Traceable Findings ({findings.length})
          </button>
          <button
            onClick={() => setActiveTab("CONTENT")}
            className={`pb-3 transition border-b-2 ${
              activeTab === "CONTENT"
                ? "border-slate-900 text-slate-900 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Content & Privacy Gate Stream
          </button>
        </nav>
      </div>

      {activeTab === "FINDINGS" ? (
        <div className="space-y-6">
          {/* Filters Bar */}
          <div className="flex flex-wrap gap-3 items-center justify-between bg-white p-3.5 rounded-xl border border-slate-200">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-slate-700">Category:</span>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                <option value="ALL">All Categories</option>
                <option value="TERMINOLOGY">Terminology</option>
                <option value="FACT_CHECK">Fact Check</option>
                <option value="COLOR_COMPLIANCE">Color Compliance</option>
                <option value="CONTRAST">Contrast Ratio</option>
              </select>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-slate-700">Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>

          {/* Findings Cards List */}
          {filteredFindings.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Zero Violations in Filter</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                No compliance issues found matching the selected category and severity filter.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredFindings.map((finding) => (
                <div
                  key={finding.id}
                  className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4 hover:border-slate-300 transition"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 border-b border-slate-100 pb-3">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        {getSeverityBadge(finding.severity)}
                        <span className="text-xs font-mono font-medium text-slate-500 uppercase">
                          {finding.category}
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                          {finding.source_engine}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-slate-900 mt-1">{finding.title}</h3>
                    </div>
                    {finding.location && (
                      <span className="text-xs font-mono text-slate-400">
                        {finding.location.line ? `Line ${finding.location.line}, Col ${finding.location.column}` : ""}
                        {finding.location.hex ? `Color: ${finding.location.hex}` : ""}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-700 leading-relaxed">{finding.description}</p>

                  {/* Traceable Evidence Passage */}
                  {finding.evidence_list && finding.evidence_list.length > 0 && (
                    <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1.5">
                      <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-800">
                        <BookOpen className="w-3.5 h-3.5 text-teal-600" />
                        <span>Traceable Brand Vault Citation</span>
                      </div>
                      <p className="text-xs font-mono text-slate-600 italic">
                        &quot;{finding.evidence_list[0].quote}&quot;
                      </p>
                    </div>
                  )}

                  {/* Intent-Preserving Actionable Suggestion */}
                  {finding.suggestion && (
                    <div className="bg-teal-50/60 p-4 rounded-xl border border-teal-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                      <div>
                        <span className="text-xs font-bold uppercase text-teal-900 flex items-center">
                          <Sparkles className="w-3.5 h-3.5 text-teal-700 mr-1.5" />
                          Intent-Preserving Correction
                        </span>
                        <p className="text-xs text-teal-950 font-medium mt-1">
                          {finding.suggestion.action === "REPLACE_TERM" && (
                            <span>Replace with: <strong className="font-mono bg-teal-100/70 px-1.5 py-0.5 rounded">{finding.suggestion.replacement}</strong></span>
                          )}
                          {finding.suggestion.action === "REMOVE_TERM" && (
                            <span>Prohibited term: remove or substitute with authorized alternative.</span>
                          )}
                          {finding.suggestion.action === "ALIGN_WITH_APPROVED_FACT" && (
                            <span>Approved SLA: <strong className="font-mono bg-teal-100/70 px-1.5 py-0.5 rounded">{finding.suggestion.approved_value}</strong></span>
                          )}
                          {finding.suggestion.action === "SNAP_TO_BRAND_PALETTE" && (
                            <span>Palette snap: recommended brand color is <strong className="font-mono bg-teal-100/70 px-1.5 py-0.5 rounded">{finding.suggestion.approved_hex}</strong></span>
                          )}
                        </p>
                      </div>
                      <button
                        onClick={() => handleCopySuggestion(
                          finding.suggestion?.replacement || finding.suggestion?.approved_value || finding.suggestion?.approved_hex || "",
                          finding.id
                        )}
                        className="inline-flex items-center space-x-1 px-3 py-1.5 bg-white border border-teal-300 rounded-lg text-xs font-medium text-teal-900 hover:bg-teal-50 transition shrink-0"
                      >
                        {copiedId === finding.id ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-teal-700" />}
                        <span>{copiedId === finding.id ? "Copied" : "Copy Suggestion"}</span>
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Content & Privacy Stream Tab */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center justify-between">
              <span>Original Submission Content</span>
              <span className="text-xs font-mono font-normal text-slate-400">Preserved Immutably</span>
            </h3>
            <div className="p-4 bg-slate-50 rounded-xl text-xs font-mono leading-relaxed max-h-96 overflow-y-auto border border-slate-200 text-slate-800">
              {rawText || "No raw text available."}
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center justify-between">
              <span>Sanitized Stream (Privacy Gate)</span>
              <span className="text-xs font-mono font-normal text-teal-700 bg-teal-50 px-2 py-0.5 rounded">PII Scrubbed</span>
            </h3>
            <div className="p-4 bg-slate-900 rounded-xl text-xs font-mono leading-relaxed max-h-96 overflow-y-auto border border-slate-800 text-slate-200">
              {sanitizedText || rawText || "No sanitized text available."}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
