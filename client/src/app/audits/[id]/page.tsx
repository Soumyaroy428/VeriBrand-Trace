"use client";

import React, { useState, useEffect, useRef } from "react";
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
  Split,
  Edit3,
  HelpCircle,
  X,
  History,
  ArrowRight,
  Save,
  CheckSquare,
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

interface DiffChunk {
  type: "equal" | "delete" | "insert";
  text: string;
}

interface DiffLine {
  line_number_orig: number | null;
  line_number_rev: number | null;
  type: "equal" | "modified" | "delete" | "insert";
  original_text: string | null;
  revised_text: string | null;
}

interface DiffResponse {
  submission_id: string;
  from_revision_number: number;
  to_revision_number: number;
  original_text: string;
  revised_text: string;
  chunks: DiffChunk[];
  lines: DiffLine[];
  stats: {
    additions: number;
    deletions: number;
    modifications: number;
    unchanged: number;
  };
}

interface RevisionItem {
  id: string;
  revision_number: number;
  content_hash: string;
  created_at: string;
}

export default function SubmissionAuditView() {
  const params = useParams();
  const submissionId = params.id as string;
  const router = useRouter();
  const { token, activeWorkspace } = useAuth();

  const [auditRun, setAuditRun] = useState<AuditRun | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [submissionTitle, setSubmissionTitle] = useState("Marketing Release");
  const [revisions, setRevisions] = useState<RevisionItem[]>([]);
  const [rawText, setRawText] = useState("");
  const [sanitizedText, setSanitizedText] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isRunningAudit, setIsRunningAudit] = useState(false);
  const [activeTab, setActiveTab] = useState<"FINDINGS" | "DIFF_WORKSPACE" | "CONTENT">("DIFF_WORKSPACE");

  // Diff Workspace State
  const [fromRev, setFromRev] = useState<number>(1);
  const [toRev, setToRev] = useState<number>(1);
  const [diffData, setDiffData] = useState<DiffResponse | null>(null);
  const [isLoadingDiff, setIsLoadingDiff] = useState(false);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [applyingFindingId, setApplyingFindingId] = useState<string | null>(null);

  // Manual Edit State
  const [isManualEditMode, setIsManualEditMode] = useState(false);
  const [manualEditText, setManualEditText] = useState("");
  const [isSavingManual, setIsSavingManual] = useState(false);

  // Exception Modal State
  const [exceptionModalFinding, setExceptionModalFinding] = useState<Finding | null>(null);
  const [exceptionReason, setExceptionReason] = useState("");
  const [isSubmittingException, setIsSubmittingException] = useState(false);

  // Toast Banner
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const findingRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // Fallback demo data
  const demoOriginalText = "Our cloud platform delivers unbreakable security and guaranteed 99.99% uptime across all data centers.";
  const demoRevisedText = "Our cloud platform delivers highly resilient security and guaranteed 99.9% uptime SLA across all data centers.";

  const demoFindings: Finding[] = [
    {
      id: "f-1",
      category: "TERMINOLOGY",
      severity: "CRITICAL",
      source_engine: "DETERMINISTIC",
      title: "Banned terminology detected: 'unbreakable'",
      description: "The term 'unbreakable' is strictly prohibited under global compliance guidelines.",
      location: { line: 1, column: 27, matched_text: "unbreakable" },
      evidence: { rule_type: "BANNED", term: "unbreakable" },
      suggestion: { action: "REPLACE_TERM", original: "unbreakable", replacement: "highly resilient" },
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
      location: { line: 1, column: 55, matched_text: "99.99%" },
      evidence: { fact_key: "UPTIME_SLA", expected_value: 99.9, found_value: 99.99 },
      suggestion: { action: "ALIGN_WITH_APPROVED_FACT", approved_value: "99.9% uptime SLA", statement: "Verified 99.9% uptime SLA." },
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
  ];

  const fetchDiffData = async (fRev: number, tRev: number) => {
    setIsLoadingDiff(true);
    try {
      if (token && submissionId) {
        const res = await fetch(`/api/v1/submissions/${submissionId}/diff?from_rev=${fRev}&to_rev=${tRev}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setDiffData(data);
          return;
        }
      }
      // Demo simulated diff fallback
      setDiffData({
        submission_id: submissionId,
        from_revision_number: fRev,
        to_revision_number: tRev,
        original_text: demoOriginalText,
        revised_text: demoRevisedText,
        chunks: [
          { type: "equal", text: "Our cloud platform delivers " },
          { type: "delete", text: "unbreakable" },
          { type: "insert", text: "highly resilient" },
          { type: "equal", text: " security and guaranteed " },
          { type: "delete", text: "99.99%" },
          { type: "insert", text: "99.9% uptime SLA" },
          { type: "equal", text: " across all data centers." },
        ],
        lines: [
          {
            line_number_orig: 1,
            line_number_rev: 1,
            type: "modified",
            original_text: demoOriginalText,
            revised_text: demoRevisedText,
          },
        ],
        stats: { additions: 2, deletions: 2, modifications: 1, unchanged: 0 },
      });
    } catch {
      // Demo fallback
    } finally {
      setIsLoadingDiff(false);
    }
  };

  const loadData = async () => {
    if (!token || !submissionId) {
      setFindings(demoFindings);
      setRawText(demoOriginalText);
      setManualEditText(demoRevisedText);
      setAuditRun({
        id: "demo-audit",
        submission_id: submissionId,
        revision_id: "demo-rev-1",
        status: "COMPLETED",
        deterministic_status: "COMPLETED",
        ai_status: "COMPLETED",
        readiness_score: 65,
        total_findings: 2,
        critical_findings: 1,
        high_findings: 1,
        medium_findings: 0,
        low_findings: 0,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      });
      setRevisions([
        { id: "rev-1", revision_number: 1, content_hash: "hash_1", created_at: new Date().toISOString() },
        { id: "rev-2", revision_number: 2, content_hash: "hash_2", created_at: new Date().toISOString() },
      ]);
      setFromRev(1);
      setToRev(2);
      fetchDiffData(1, 2);
      return;
    }

    try {
      const subRes = await fetch(`/api/v1/submissions/${submissionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (subRes.ok) {
        const subData = await subRes.json();
        setSubmissionTitle(subData.submission.title);
        const revList = subData.revisions || [];
        setRevisions(revList);

        if (revList.length > 0) {
          const firstRev = revList[0];
          const latestRev = revList[revList.length - 1];
          setRawText(firstRev.extracted_text || firstRev.raw_content || "");
          setSanitizedText(latestRev.sanitized_text || "");
          setManualEditText(latestRev.extracted_text || latestRev.raw_content || "");
          setFromRev(firstRev.revision_number);
          setToRev(latestRev.revision_number);
          fetchDiffData(firstRev.revision_number, latestRev.revision_number);
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
      }
    } catch {
      setFindings(demoFindings);
    }
  };

  useEffect(() => {
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
          setToastMessage("Audit re-run completed. Brand Readiness Score updated.");
        }
      } else {
        setTimeout(() => {
          setAuditRun((prev) => (prev ? { ...prev, readiness_score: 85 } : null));
          setToastMessage("Audit re-run completed (Simulation).");
        }, 800);
      }
    } finally {
      setIsRunningAudit(false);
    }
  };

  const handleAcceptSuggestion = async (finding: Finding) => {
    try {
      setApplyingFindingId(finding.id);
      if (token) {
        const res = await fetch(`/api/v1/submissions/${submissionId}/apply-suggestion`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ finding_id: finding.id }),
        });
        if (res.ok) {
          const data = await res.json();
          setAuditRun(data.audit_run);
          setFindings(data.findings);
          setToastMessage(data.message || "Suggestion accepted! Created incremental revision.");
          await loadData();
          return;
        }
      }
      // Demo fallback simulation
      setTimeout(() => {
        setFindings((prev) =>
          prev.map((f) => (f.id === finding.id ? { ...f, status: "RESOLVED" } : f))
        );
        setAuditRun((prev) => (prev ? { ...prev, readiness_score: Math.min(100, (prev.readiness_score || 70) + 15) } : null));
        setToastMessage(`Suggestion accepted: "${finding.suggestion?.replacement || 'Approved value'}" applied into revision v2.`);
        setToRev(2);
        fetchDiffData(1, 2);
      }, 600);
    } finally {
      setApplyingFindingId(null);
    }
  };

  const handleOpenExceptionModal = (finding: Finding) => {
    setExceptionModalFinding(finding);
    setExceptionReason("");
  };

  const handleSubmitException = async () => {
    if (!exceptionModalFinding || !exceptionReason.trim()) return;
    try {
      setIsSubmittingException(true);
      if (token) {
        const res = await fetch(`/api/v1/findings/${exceptionModalFinding.id}/exceptions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ reason: exceptionReason.trim() }),
        });
        if (res.ok) {
          setFindings((prev) =>
            prev.map((f) => (f.id === exceptionModalFinding.id ? { ...f, status: "EXCEPTION_REQUESTED" } : f))
          );
          setToastMessage("Exception request submitted with business justification.");
          setExceptionModalFinding(null);
          return;
        }
      }
      // Demo simulation
      setFindings((prev) =>
        prev.map((f) => (f.id === exceptionModalFinding.id ? { ...f, status: "EXCEPTION_REQUESTED" } : f))
      );
      setToastMessage("Exception request submitted for human reviewer approval.");
      setExceptionModalFinding(null);
    } finally {
      setIsSubmittingException(false);
    }
  };

  const handleSaveManualEdit = async () => {
    if (!manualEditText.trim()) return;
    try {
      setIsSavingManual(true);
      if (token) {
        const res = await fetch(`/api/v1/submissions/${submissionId}/revisions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ raw_content: manualEditText }),
        });
        if (res.ok) {
          setToastMessage("Manual edit saved as new revision. Running audit...");
          setIsManualEditMode(false);
          await loadData();
          await handleRunAudit();
          return;
        }
      }
      // Demo simulation
      setIsManualEditMode(false);
      setToastMessage("Manual edit saved as Revision v3. Re-auditing content...");
      setAuditRun((prev) => (prev ? { ...prev, readiness_score: 95 } : null));
    } finally {
      setIsSavingManual(false);
    }
  };

  const handleFocusFinding = (findingId: string) => {
    setSelectedFindingId(findingId);
    const element = findingRefs.current[findingId];
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
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
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white text-xs font-medium px-4 py-3 rounded-xl shadow-xl flex items-center space-x-3 border border-slate-700 animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
          <button onClick={() => setToastMessage(null)} className="ml-2 hover:opacity-75">
            <X className="w-3.5 h-3.5 text-slate-400" />
          </button>
        </div>
      )}

      {/* Breadcrumb */}
      <div className="flex items-center space-x-2 text-xs font-medium text-slate-500">
        <Link href="/audits" className="hover:text-slate-800 transition">
          Submissions
        </Link>
        <span>/</span>
        <span className="text-slate-900 font-semibold">{submissionTitle}</span>
        <span>/</span>
        <span className="text-teal-700 font-mono">Explainable Diff Workspace</span>
      </div>

      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded border border-teal-200">
              Human-in-the-Loop Governance Diff
            </span>
            <span className="text-xs text-slate-500">Workspace: {activeWorkspace?.workspace_name || "Acme Global"}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-2">{submissionTitle}</h1>
          <p className="text-xs text-slate-600 mt-1">
            Deterministic Engine • Grounded Gemini 2.5 Flash • SequenceMatcher Diff • Revision Lineage
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsManualEditMode(!isManualEditMode)}
            className="inline-flex items-center space-x-2 px-3.5 py-2 bg-white text-slate-800 border border-slate-300 rounded-lg text-xs font-semibold hover:bg-slate-50 transition shadow-sm"
          >
            <Edit3 className="w-3.5 h-3.5 text-slate-600" />
            <span>{isManualEditMode ? "Close Editor" : "Manual Edit Mode"}</span>
          </button>
          <button
            onClick={handleRunAudit}
            disabled={isRunningAudit}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition shadow-sm disabled:opacity-50"
          >
            {isRunningAudit ? <RotateCcw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isRunningAudit ? "Analyzing Content..." : "Re-Run Complete Audit"}</span>
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
            <span>Core Philosophy: <strong>Suggest, Never Override.</strong> Human approval required.</span>
            <span className="font-mono text-[11px]">AI Engine: {auditRun?.ai_status || "READY"}</span>
          </div>
        </div>
      </div>

      {/* Manual Edit Mode Drawer */}
      {isManualEditMode && (
        <div className="bg-white p-6 rounded-2xl border-2 border-slate-900 shadow-md space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Edit3 className="w-4 h-4 text-slate-900" />
              <h3 className="text-sm font-bold text-slate-900">Manual Copy Editor (Creator Mode)</h3>
            </div>
            <span className="text-xs text-slate-500">Saving creates an immutable incremental revision</span>
          </div>
          <textarea
            value={manualEditText}
            onChange={(e) => setManualEditText(e.target.value)}
            rows={6}
            className="w-full text-xs font-mono p-4 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-900 leading-relaxed text-slate-800"
            placeholder="Edit submission text directly..."
          />
          <div className="flex items-center justify-end space-x-3">
            <button
              onClick={() => setIsManualEditMode(false)}
              className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveManualEdit}
              disabled={isSavingManual}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 disabled:opacity-50"
            >
              {isSavingManual ? <RotateCcw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              <span>{isSavingManual ? "Saving Revision..." : "Save as New Revision"}</span>
            </button>
          </div>
        </div>
      )}

      {/* Workspace Tabs Navigation */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 text-sm font-medium">
          <button
            onClick={() => setActiveTab("DIFF_WORKSPACE")}
            className={`pb-3 transition flex items-center space-x-2 border-b-2 ${
              activeTab === "DIFF_WORKSPACE"
                ? "border-slate-900 text-slate-900 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Split className="w-4 h-4" />
            <span>Explainable Diff Workspace</span>
          </button>
          <button
            onClick={() => setActiveTab("FINDINGS")}
            className={`pb-3 transition flex items-center space-x-2 border-b-2 ${
              activeTab === "FINDINGS"
                ? "border-slate-900 text-slate-900 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Traceable Violation Cards ({findings.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("CONTENT")}
            className={`pb-3 transition flex items-center space-x-2 border-b-2 ${
              activeTab === "CONTENT"
                ? "border-slate-900 text-slate-900 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Privacy Gate Stream</span>
          </button>
        </nav>
      </div>

      {/* --- TAB 1: EXPLAINABLE DIFF WORKSPACE --- */}
      {activeTab === "DIFF_WORKSPACE" && (
        <div className="space-y-6">
          {/* Diff Controls Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200">
            <div className="flex items-center space-x-3 text-xs">
              <span className="font-semibold text-slate-700">Revision Comparison:</span>
              <div className="flex items-center space-x-2">
                <select
                  value={fromRev}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setFromRev(val);
                    fetchDiffData(val, toRev);
                  }}
                  className="border border-slate-300 rounded px-2 py-1 bg-white font-mono text-xs"
                >
                  {revisions.map((r) => (
                    <option key={r.id} value={r.revision_number}>
                      v{r.revision_number} (Original)
                    </option>
                  ))}
                  {revisions.length === 0 && <option value={1}>v1 (Original)</option>}
                </select>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                <select
                  value={toRev}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setToRev(val);
                    fetchDiffData(fromRev, val);
                  }}
                  className="border border-slate-300 rounded px-2 py-1 bg-white font-mono text-xs"
                >
                  {revisions.map((r) => (
                    <option key={r.id} value={r.revision_number}>
                      v{r.revision_number} {r.revision_number === revisions.length ? "(Latest)" : ""}
                    </option>
                  ))}
                  {revisions.length === 0 && <option value={2}>v2 (Proposed)</option>}
                </select>
              </div>
            </div>

            {/* Diff Statistics */}
            {diffData && (
              <div className="flex items-center space-x-4 text-xs font-mono">
                <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-semibold">
                  +{diffData.stats.additions} insertions
                </span>
                <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 font-semibold">
                  -{diffData.stats.deletions} removals
                </span>
                <span className="text-slate-500 font-sans">
                  {diffData.stats.unchanged} lines unchanged
                </span>
              </div>
            )}
          </div>

          {/* Granular Inline Highlight Diff Strip */}
          {diffData && diffData.chunks && (
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                  <span>Interactive Token-Level Diff Highlights</span>
                </span>
                <span className="text-[11px] text-slate-500 font-mono">Click any flagged word to focus violation card</span>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl text-sm leading-relaxed font-mono border border-slate-200 text-slate-800 overflow-x-auto">
                {diffData.chunks.map((chunk, idx) => {
                  if (chunk.type === "delete") {
                    return (
                      <span
                        key={idx}
                        onClick={() => {
                          const match = findings.find((f) =>
                            f.location?.matched_text?.includes(chunk.text) ||
                            f.title.includes(chunk.text) ||
                            f.description.includes(chunk.text)
                          );
                          if (match) handleFocusFinding(match.id);
                        }}
                        className="bg-rose-100 text-rose-900 line-through decoration-rose-500 px-1 py-0.5 rounded cursor-pointer hover:bg-rose-200 transition mx-0.5 font-bold"
                        title="Click to view violation card and citation"
                      >
                        {chunk.text}
                      </span>
                    );
                  }
                  if (chunk.type === "insert") {
                    return (
                      <span
                        key={idx}
                        className="bg-emerald-100 text-emerald-950 px-1 py-0.5 rounded font-semibold border-b-2 border-emerald-500 mx-0.5"
                        title="Proposed intent-preserving correction"
                      >
                        {chunk.text}
                      </span>
                    );
                  }
                  return <span key={idx}>{chunk.text}</span>;
                })}
              </div>
            </div>
          )}

          {/* Side-by-Side Synchronized Line Diff Comparison */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column: Original Content */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase text-slate-900">Original Submission (v{fromRev})</span>
                  <span className="text-[10px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">Immutable</span>
                </div>
                <span className="text-xs text-rose-600 font-medium font-mono">Flagged Non-Compliant</span>
              </div>
              <div className="font-mono text-xs divide-y divide-slate-100 max-h-[500px] overflow-y-auto pr-2">
                {diffData?.lines.map((line, idx) => (
                  <div
                    key={`orig-${idx}`}
                    className={`py-2 px-2 flex items-start space-x-3 rounded ${
                      line.type === "delete" || line.type === "modified"
                        ? "bg-rose-50/70 text-rose-950 font-medium"
                        : "text-slate-700"
                    }`}
                  >
                    <span className="text-[10px] text-slate-400 select-none w-6 text-right shrink-0">
                      {line.line_number_orig || "-"}
                    </span>
                    <span className="leading-relaxed break-words flex-1">
                      {line.original_text || <span className="text-slate-300 italic">—</span>}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Right Column: Proposed / Revised Content */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase text-slate-900">Proposed Changes (v{toRev})</span>
                  <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded font-semibold">
                    Compliant Preview
                  </span>
                </div>
                <span className="text-xs text-emerald-700 font-medium font-mono">Intent Preserved</span>
              </div>
              <div className="font-mono text-xs divide-y divide-slate-100 max-h-[500px] overflow-y-auto pr-2">
                {diffData?.lines.map((line, idx) => (
                  <div
                    key={`rev-${idx}`}
                    className={`py-2 px-2 flex items-start space-x-3 rounded ${
                      line.type === "insert" || line.type === "modified"
                        ? "bg-emerald-50/80 text-emerald-950 font-semibold"
                        : "text-slate-700"
                    }`}
                  >
                    <span className="text-[10px] text-slate-400 select-none w-6 text-right shrink-0">
                      {line.line_number_rev || "-"}
                    </span>
                    <span className="leading-relaxed break-words flex-1">
                      {line.revised_text || <span className="text-slate-300 italic">—</span>}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- TAB 2: TRACEABLE VIOLATION CARDS --- */}
      {activeTab === "FINDINGS" && (
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
                  ref={(el) => {
                    findingRefs.current[finding.id] = el;
                  }}
                  className={`bg-white rounded-2xl border p-6 space-y-4 transition ${
                    selectedFindingId === finding.id
                      ? "border-teal-600 ring-2 ring-teal-200 shadow-md"
                      : "border-slate-200 shadow-sm hover:border-slate-300"
                  }`}
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
                        {finding.status === "RESOLVED" && (
                          <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                            RESOLVED
                          </span>
                        )}
                        {finding.status === "EXCEPTION_REQUESTED" && (
                          <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                            EXCEPTION PENDING
                          </span>
                        )}
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
                    <div className="bg-teal-50/60 p-4 rounded-xl border border-teal-200 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
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

                      <div className="flex items-center space-x-2 shrink-0">
                        {/* Copy button */}
                        <button
                          onClick={() => handleCopySuggestion(
                            finding.suggestion?.replacement || finding.suggestion?.approved_value || finding.suggestion?.approved_hex || "",
                            finding.id
                          )}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 bg-white border border-teal-300 rounded-lg text-xs font-medium text-teal-900 hover:bg-teal-50 transition"
                        >
                          {copiedId === finding.id ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-teal-700" />}
                          <span>{copiedId === finding.id ? "Copied" : "Copy"}</span>
                        </button>

                        {/* Request Exception button */}
                        <button
                          onClick={() => handleOpenExceptionModal(finding)}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 bg-white border border-amber-300 rounded-lg text-xs font-medium text-amber-900 hover:bg-amber-50 transition"
                        >
                          <HelpCircle className="w-3.5 h-3.5 text-amber-700" />
                          <span>Request Exception</span>
                        </button>

                        {/* Accept Suggestion (Creates Incremental Revision) */}
                        <button
                          onClick={() => handleAcceptSuggestion(finding)}
                          disabled={applyingFindingId === finding.id || finding.status === "RESOLVED"}
                          className="inline-flex items-center space-x-1 px-3.5 py-1.5 bg-teal-800 text-white rounded-lg text-xs font-semibold hover:bg-teal-900 transition disabled:opacity-50"
                        >
                          {applyingFindingId === finding.id ? (
                            <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <CheckSquare className="w-3.5 h-3.5" />
                          )}
                          <span>
                            {finding.status === "RESOLVED"
                              ? "Applied in v2"
                              : applyingFindingId === finding.id
                              ? "Applying..."
                              : "Accept Suggestion"}
                          </span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* --- TAB 3: CONTENT & PRIVACY GATE STREAM --- */}
      {activeTab === "CONTENT" && (
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

      {/* --- EXCEPTION REQUEST MODAL --- */}
      {exceptionModalFinding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl border border-slate-200 animate-in zoom-in-95">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  Human Exception Request
                </span>
                <h3 className="text-base font-bold text-slate-900 mt-1">
                  {exceptionModalFinding.title}
                </h3>
              </div>
              <button onClick={() => setExceptionModalFinding(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Exceptions are recorded in the immutable audit log and require formal sign-off from an authorized human reviewer.
            </p>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-800">
                Business Justification & Rationale <span className="text-red-500">*</span>
              </label>
              <textarea
                value={exceptionReason}
                onChange={(e) => setExceptionReason(e.target.value)}
                rows={4}
                placeholder="Explain why this phrasing or asset cannot adhere to brand standards (e.g. client legal requirement, grandfathered legacy contract)..."
                className="w-full text-xs p-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500 text-slate-800"
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setExceptionModalFinding(null)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitException}
                disabled={!exceptionReason.trim() || isSubmittingException}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-amber-600 text-white rounded-lg text-xs font-semibold hover:bg-amber-700 disabled:opacity-50"
              >
                {isSubmittingException ? <RotateCcw className="w-3.5 h-3.5 animate-spin" /> : <ShieldAlert className="w-3.5 h-3.5" />}
                <span>{isSubmittingException ? "Submitting..." : "Submit for Reviewer Approval"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
