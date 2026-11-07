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
  Award,
  MessageSquare,
  Send,
  Lock,
  ThumbsUp,
  ThumbsDown,
  Building2,
  Calendar,
  User,
  Share2,
  Download,
  Printer,
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

interface ReviewCommentItem {
  id: string;
  submission_id: string;
  revision_id: string;
  user_id: string;
  user_name?: string;
  user_email?: string;
  comment_text: string;
  anchor_location?: Record<string, any>;
  created_at: string;
}

interface ComplianceCertificateData {
  id: string;
  certificate_number: string;
  submission_id: string;
  approval_id: string;
  workspace_id: string;
  certificate_hash: string;
  issued_at: string;
  metadata_json?: Record<string, any>;
}

export default function SubmissionAuditView() {
  const params = useParams();
  const submissionId = params.id as string;
  const router = useRouter();
  const { token, activeWorkspace, user } = useAuth();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";

  const [auditRun, setAuditRun] = useState<AuditRun | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [submissionTitle, setSubmissionTitle] = useState("Marketing Release");
  const [submissionStatus, setSubmissionStatus] = useState<string>("PENDING_REVIEW");
  const [submissionCreatorId, setSubmissionCreatorId] = useState<string>("");
  const [revisions, setRevisions] = useState<RevisionItem[]>([]);
  const [rawText, setRawText] = useState("");
  const [sanitizedText, setSanitizedText] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isRunningAudit, setIsRunningAudit] = useState(false);
  const [activeTab, setActiveTab] = useState<"DIFF_WORKSPACE" | "FINDINGS" | "CONTENT" | "COMMENTS">("DIFF_WORKSPACE");

  // Certificate State
  const [certificate, setCertificate] = useState<ComplianceCertificateData | null>(null);
  const [isCertModalOpen, setIsCertModalOpen] = useState(false);

  // Review Comments State
  const [comments, setComments] = useState<ReviewCommentItem[]>([]);
  const [newCommentText, setNewCommentText] = useState("");
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);

  // Review Approval & Rejection Modals
  const [isApproveModalOpen, setIsApproveModalOpen] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState("");
  const [isApproving, setIsApproving] = useState(false);

  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [rejectionNotes, setRejectionNotes] = useState("");
  const [isRejecting, setIsRejecting] = useState(false);
  const [decidingExceptionId, setDecidingExceptionId] = useState<string | null>(null);

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
      title: "Prohibited Claim: unbreakable security",
      description: "Rule: Banned claim regarding absolute infallible security protection.",
      status: "OPEN",
      location: { line: 1, column: 29 },
      suggestion: {
        action: "REPLACE_TERM",
        replacement: "highly resilient security",
      },
      evidence_list: [
        {
          id: "ev-1",
          source_type: "RULE",
          source_version: 1,
          quote: "Never state systems are 100% unbreakable or impenetrable. Use measured descriptions like 'highly resilient'.",
        },
      ],
    },
    {
      id: "f-2",
      category: "FACT_CHECK",
      severity: "HIGH",
      source_engine: "DETERMINISTIC",
      title: "Numeric Discrepancy: 99.99% uptime",
      description: "Fact sheet specifies 99.9% uptime SLA commitment.",
      status: "OPEN",
      location: { line: 1, column: 63 },
      suggestion: {
        action: "ALIGN_WITH_APPROVED_FACT",
        approved_value: "99.9% uptime SLA",
      },
      evidence_list: [
        {
          id: "ev-2",
          source_type: "APPROVED_FACT",
          source_version: 2,
          quote: "Core standard cloud availability commitment is 99.9% monthly uptime.",
        },
      ],
    },
  ];

  const fetchDiffData = async (fRev: number, tRev: number) => {
    setIsLoadingDiff(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";
    try {
      if (token) {
        const res = await fetch(`${apiUrl}/submissions/${submissionId}/diff?from_rev=${fRev}&to_rev=${tRev}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setDiffData(data);
          return;
        }
      }
      // Demo fallback
      setDiffData({
        submission_id: submissionId,
        from_revision_number: fRev,
        to_revision_number: tRev,
        original_text: demoOriginalText,
        revised_text: demoRevisedText,
        chunks: [
          { type: "equal", text: "Our cloud platform delivers " },
          { type: "delete", text: "unbreakable security" },
          { type: "insert", text: "highly resilient security" },
          { type: "equal", text: " and guaranteed " },
          { type: "delete", text: "99.99% uptime" },
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
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";

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
      const subRes = await fetch(`${apiUrl}/submissions/${submissionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (subRes.ok) {
        const subData = await subRes.json();
        setSubmissionTitle(subData.submission.title);
        setSubmissionStatus(subData.submission.status);
        setSubmissionCreatorId(subData.submission.created_by);
        const revList = subData.revisions || [];
        setRevisions(revList);

        if (subData.submission.status === "APPROVED") {
          try {
            const certRes = await fetch(`${apiUrl}/submissions/${submissionId}/certificate`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (certRes.ok) {
              const certData = await certRes.json();
              setCertificate(certData);
            }
          } catch (e) {
            console.warn("Could not load certificate:", e);
          }
        }

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

      // Fetch comments
      try {
        const commRes = await fetch(`${apiUrl}/submissions/${submissionId}/comments`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (commRes.ok) {
          const commData = await commRes.json();
          setComments(commData);
        }
      } catch (e) {
        console.warn("Could not load comments:", e);
      }

      const auditRes = await fetch(`${apiUrl}/submissions/${submissionId}/latest-audit`, {
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
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";
    try {
      setIsRunningAudit(true);
      if (token) {
        const res = await fetch(`${apiUrl}/submissions/${submissionId}/audits`, {
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
          setAuditRun((prev) => (prev ? { ...prev, readiness_score: 95 } : null));
          setToastMessage("Demo re-audit completed. Score updated.");
        }, 800);
      }
    } finally {
      setIsRunningAudit(false);
    }
  };

  const handleAcceptSuggestion = async (finding: Finding) => {
    if (!finding.suggestion) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";

    try {
      setApplyingFindingId(finding.id);
      if (token) {
        const res = await fetch(`${apiUrl}/submissions/${submissionId}/apply-suggestion`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ finding_id: finding.id }),
        });

        if (res.ok) {
          const data = await res.json();
          setToastMessage(data.message);
          await loadData();
          setToRev(data.revision.revision_number);
          await fetchDiffData(fromRev, data.revision.revision_number);
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
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";

    try {
      setIsSubmittingException(true);
      if (token) {
        const res = await fetch(`${apiUrl}/findings/${exceptionModalFinding.id}/exceptions`, {
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
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";

    try {
      setIsSavingManual(true);
      if (token) {
        const res = await fetch(`${apiUrl}/submissions/${submissionId}/revisions`, {
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

  const handleApproveSubmission = async () => {
    setIsApproving(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";
    try {
      if (token) {
        const res = await fetch(`${apiUrl}/submissions/${submissionId}/approve`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ decision_notes: approvalNotes }),
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Approval failed with HTTP ${res.status}`);
        }
        const data = await res.json();
        setSubmissionStatus("APPROVED");
        if (data.certificate) {
          setCertificate(data.certificate);
        }
      } else {
        // Demo simulation
        setSubmissionStatus("APPROVED");
        setCertificate({
          id: "cert-demo-id",
          certificate_number: "VBT-CERT-ACME-DEMO999",
          submission_id: submissionId,
          approval_id: "appr-demo",
          workspace_id: activeWorkspace?.workspace_id || "ws-acme",
          certificate_hash: "8f4a13b97c02e1189ab5d9847120fa26f3781c0384a44b8f04739265ecb37190",
          issued_at: new Date().toISOString(),
          metadata_json: {
            submission_title: submissionTitle,
            workspace_name: activeWorkspace?.workspace_name || "Acme Global",
            readiness_score: auditRun?.readiness_score || 95,
            approver_email: user?.email || "reviewer@acme.com",
          },
        });
      }
      setIsApproveModalOpen(false);
      setIsCertModalOpen(true);
      setToastMessage("Submission approved! Compliance certificate generated with tamper-evident proof.");
    } catch (err: any) {
      alert(err.message || "Approval failed");
    } finally {
      setIsApproving(false);
    }
  };

  const handleRejectSubmission = async () => {
    if (!rejectionNotes.trim()) {
      alert("Please provide decision notes explaining what changes are needed.");
      return;
    }
    setIsRejecting(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";
    try {
      if (token) {
        const res = await fetch(`${apiUrl}/submissions/${submissionId}/reject`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ decision_notes: rejectionNotes }),
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Rejection failed with HTTP ${res.status}`);
        }
      }
      setSubmissionStatus("NEEDS_CHANGES");
      setIsRejectModalOpen(false);
      setToastMessage("Changes requested. Status updated to Needs Changes.");
    } catch (err: any) {
      alert(err.message || "Failed to request changes");
    } finally {
      setIsRejecting(false);
    }
  };

  const handleDecideException = async (findingId: string, decision: "APPROVED" | "REJECTED") => {
    const note = prompt(
      decision === "APPROVED"
        ? "Enter justification note for approving this exception:"
        : "Enter reason for rejecting this exception:"
    );
    if (note === null) return;

    setDecidingExceptionId(findingId);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";
    try {
      if (token) {
        const excRes = await fetch(`${apiUrl}/submissions/${submissionId}/exceptions`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        let excId = "";
        if (excRes.ok) {
          const excList = await excRes.json();
          const match = excList.find((e: any) => e.finding_id === findingId && e.status === "PENDING");
          if (match) excId = match.id;
        }

        if (excId) {
          const decideRes = await fetch(`${apiUrl}/exceptions/${excId}/decide`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ decision, decision_note: note }),
          });
          if (!decideRes.ok) {
            const err = await decideRes.json().catch(() => ({}));
            throw new Error(err.detail || "Exception decision failed");
          }
        }
      }

      setFindings((prev) =>
        prev.map((f) =>
          f.id === findingId
            ? { ...f, status: decision === "APPROVED" ? "EXCEPTION_APPROVED" : "EXCEPTION_REJECTED" }
            : f
        )
      );
      if (decision === "APPROVED") {
        setAuditRun((prev) => (prev ? { ...prev, readiness_score: Math.min(100, (prev.readiness_score || 70) + 20) } : null));
      }
      setToastMessage(`Exception ${decision.toLowerCase()} successfully.`);
    } catch (err: any) {
      alert(err.message || "Failed to decide exception");
    } finally {
      setDecidingExceptionId(null);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCommentText.trim()) return;

    setIsSubmittingComment(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";
    try {
      if (token) {
        const res = await fetch(`${apiUrl}/submissions/${submissionId}/comments`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ comment_text: newCommentText }),
        });
        if (res.ok) {
          const newComm = await res.json();
          setComments((prev) => [...prev, newComm]);
          setNewCommentText("");
          setToastMessage("Comment posted.");
          return;
        }
      }
      // Demo fallback
      setComments((prev) => [
        ...prev,
        {
          id: `comm-${Date.now()}`,
          submission_id: submissionId,
          revision_id: "rev-1",
          user_id: user?.id || "usr-me",
          user_name: user?.full_name || "Current User",
          user_email: user?.email || "reviewer@acme.com",
          comment_text: newCommentText,
          created_at: new Date().toISOString(),
        },
      ]);
      setNewCommentText("");
      setToastMessage("Comment posted.");
    } finally {
      setIsSubmittingComment(false);
    }
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
    <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
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

        {/* 1. If Submission is APPROVED: Golden / Teal Compliance Certificate Banner */}
        {submissionStatus === "APPROVED" && (
          <div className="bg-gradient-to-r from-teal-900 to-slate-900 text-white rounded-2xl p-6 shadow-lg border border-teal-500/40 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-start space-x-3.5">
              <div className="p-3 bg-teal-500/20 rounded-xl border border-teal-500/30 shrink-0">
                <Award className="w-6 h-6 text-teal-400" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-teal-400">
                    Publication Approved
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    <CheckCircle2 className="w-3 h-3 mr-1" /> Ready to Publish
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white">
                  Cryptographic Compliance Certificate Issued
                </h3>
                <p className="text-xs text-slate-300 font-mono">
                  Certificate {certificate?.certificate_number ? `#${certificate.certificate_number}` : "#VBT-CERT-VERIFIED"} • Verified Tamper-Evident SHA-256 Chained
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={() => setIsCertModalOpen(true)}
                className="inline-flex items-center px-4 py-2 bg-teal-500 text-slate-950 font-bold rounded-lg text-xs hover:bg-teal-400 transition shadow"
              >
                <Award className="w-3.5 h-3.5 mr-1.5" />
                View Certificate
              </button>
              {certificate?.certificate_number && (
                <>
                  <a
                    href={`${apiUrl}/certificates/${certificate.certificate_number}/download`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-3.5 py-2 bg-slate-800 text-slate-200 border border-slate-700 font-semibold rounded-lg text-xs hover:bg-slate-700 transition"
                  >
                    <Download className="w-3.5 h-3.5 mr-1.5 text-teal-400" />
                    Download PDF
                  </a>
                  <Link
                    href={`/verify/${certificate.certificate_number}`}
                    target="_blank"
                    className="inline-flex items-center px-3.5 py-2 bg-slate-800 text-slate-200 border border-slate-700 font-semibold rounded-lg text-xs hover:bg-slate-700 transition"
                  >
                    <ExternalLink className="w-3.5 h-3.5 mr-1.5 text-teal-400" />
                    Public Proof
                  </Link>
                </>
              )}
            </div>
          </div>
        )}

        {/* 2. If Submission is PENDING_REVIEW or NEEDS_CHANGES: Reviewer Action Panel */}
        {submissionStatus !== "APPROVED" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-amber-50 rounded-lg border border-amber-200">
                  <ShieldAlert className="w-4 h-4 text-amber-700" />
                </div>
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-800">
                    Reviewer Governance Sign-Off Panel
                  </span>
                  <p className="text-xs text-slate-500">
                    Status: <strong className="font-semibold text-slate-800">{submissionStatus.replace("_", " ")}</strong> • Passing Score Required: &ge; 85%
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                {/* Request Changes button */}
                <button
                  onClick={() => setIsRejectModalOpen(true)}
                  className="inline-flex items-center px-3.5 py-2 bg-white text-amber-800 border border-amber-300 font-semibold rounded-lg text-xs hover:bg-amber-50 transition shadow-sm"
                >
                  <ThumbsDown className="w-3.5 h-3.5 mr-1.5 text-amber-700" />
                  Request Changes
                </button>

                {/* Approve Submission button */}
                <button
                  onClick={() => setIsApproveModalOpen(true)}
                  disabled={Boolean(user?.id && submissionCreatorId && user.id === submissionCreatorId)}
                  className="inline-flex items-center px-4 py-2 bg-emerald-700 text-white font-bold rounded-lg text-xs hover:bg-emerald-800 transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  title={user?.id && submissionCreatorId && user.id === submissionCreatorId ? "Creators cannot approve their own submission" : "Approve and issue certificate"}
                >
                  <ThumbsUp className="w-3.5 h-3.5 mr-1.5 text-emerald-200" />
                  Approve & Issue Certificate
                </button>
              </div>
            </div>

            {/* Self-approval Warning if user is creator */}
            {user?.id && submissionCreatorId && user.id === submissionCreatorId && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-center space-x-2">
                <Info className="w-4 h-4 text-amber-600 shrink-0" />
                <span>
                  <strong>Creator Sign-off Restricted:</strong> Per VeriBrand Trace governance rules, creators cannot approve their own submissions. Please switch to a Reviewer or Governance Admin account to sign off.
                </span>
              </div>
            )}
          </div>
        )}

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
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Audit Finding Distribution</h3>
                <span className="text-xs font-mono text-slate-500">Total Findings: {findings.length}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
                <div className="p-3 bg-red-50 rounded-xl border border-red-100">
                  <span className="text-[11px] font-semibold text-red-800 uppercase">Critical</span>
                  <p className="text-2xl font-bold text-red-900 mt-1">
                    {findings.filter((f) => f.severity === "CRITICAL" && f.status !== "RESOLVED" && f.status !== "EXCEPTION_APPROVED").length}
                  </p>
                  <span className="text-[10px] text-red-700">-25 pts each</span>
                </div>
                <div className="p-3 bg-orange-50 rounded-xl border border-orange-100">
                  <span className="text-[11px] font-semibold text-orange-800 uppercase">High</span>
                  <p className="text-2xl font-bold text-orange-900 mt-1">
                    {findings.filter((f) => f.severity === "HIGH" && f.status !== "RESOLVED" && f.status !== "EXCEPTION_APPROVED").length}
                  </p>
                  <span className="text-[10px] text-orange-700">-10 pts each</span>
                </div>
                <div className="p-3 bg-amber-50 rounded-xl border border-amber-100">
                  <span className="text-[11px] font-semibold text-amber-800 uppercase">Medium</span>
                  <p className="text-2xl font-bold text-amber-900 mt-1">
                    {findings.filter((f) => f.severity === "MEDIUM" && f.status !== "RESOLVED" && f.status !== "EXCEPTION_APPROVED").length}
                  </p>
                  <span className="text-[10px] text-amber-700">-5 pts each</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[11px] font-semibold text-slate-700 uppercase">Low</span>
                  <p className="text-2xl font-bold text-slate-900 mt-1">
                    {findings.filter((f) => f.severity === "LOW" && f.status !== "RESOLVED" && f.status !== "EXCEPTION_APPROVED").length}
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
            <button
              onClick={() => setActiveTab("COMMENTS")}
              className={`pb-3 transition flex items-center space-x-2 border-b-2 ${
                activeTab === "COMMENTS"
                  ? "border-slate-900 text-slate-900 font-semibold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              <span>Review Discussion ({comments.length})</span>
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
                    className="border border-slate-300 rounded px-2 py-1 bg-white font-mono text-xs text-slate-900"
                  >
                    {revisions.map((r) => (
                      <option key={r.id} value={r.revision_number}>
                        v{r.revision_number} ({r.content_hash.slice(0, 8)})
                      </option>
                    ))}
                  </select>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                  <select
                    value={toRev}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      setToRev(val);
                      fetchDiffData(fromRev, val);
                    }}
                    className="border border-slate-300 rounded px-2 py-1 bg-white font-mono text-xs text-slate-900"
                  >
                    {revisions.map((r) => (
                      <option key={r.id} value={r.revision_number}>
                        v{r.revision_number} ({r.content_hash.slice(0, 8)})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {diffData && (
                <div className="flex items-center space-x-3 text-xs font-mono">
                  <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    +{diffData.stats.additions} additions
                  </span>
                  <span className="text-red-700 bg-red-50 px-2 py-0.5 rounded border border-red-200">
                    -{diffData.stats.deletions} deletions
                  </span>
                  <span className="text-slate-500">
                    {diffData.stats.unchanged} unchanged
                  </span>
                </div>
              )}
            </div>

            {/* Word-level Granular Diff Strip */}
            {diffData && diffData.chunks && (
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-500 border-b border-slate-100 pb-2">
                  <span className="font-semibold text-slate-700 uppercase tracking-wider text-[11px]">
                    Granular Word-Level Diff Strip
                  </span>
                  <span className="font-mono text-[10px]">Inline additions (green) & deletions (red)</span>
                </div>
                <div className="text-xs font-mono leading-relaxed p-3 bg-slate-50 rounded-xl border border-slate-200">
                  {diffData.chunks.map((chunk, idx) => {
                    if (chunk.type === "delete") {
                      return (
                        <span key={idx} className="bg-red-100 text-red-900 line-through px-1 py-0.5 rounded mx-0.5 border border-red-200">
                          {chunk.text}
                        </span>
                      );
                    }
                    if (chunk.type === "insert") {
                      return (
                        <span key={idx} className="bg-emerald-100 text-emerald-900 font-semibold px-1 py-0.5 rounded mx-0.5 border border-emerald-200">
                          {chunk.text}
                        </span>
                      );
                    }
                    return <span key={idx} className="text-slate-700">{chunk.text}</span>;
                  })}
                </div>
              </div>
            )}

            {/* Synchronized Side-by-Side Dual-Pane Line Diff */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="grid grid-cols-2 bg-slate-100 border-b border-slate-200 text-xs font-bold text-slate-700 uppercase tracking-wider">
                <div className="p-3 border-r border-slate-200 flex items-center justify-between">
                  <span>Original Copy (v{fromRev})</span>
                  <span className="text-[10px] font-mono font-normal text-slate-500">Line Numbers</span>
                </div>
                <div className="p-3 flex items-center justify-between">
                  <span>Suggested Revision (v{toRev})</span>
                  <span className="text-[10px] font-mono font-normal text-slate-500">Corrected Copy</span>
                </div>
              </div>

              <div className="divide-y divide-slate-100 font-mono text-xs max-h-[500px] overflow-y-auto">
                {isLoadingDiff ? (
                  <div className="p-12 text-center text-slate-400">Loading synchronized line comparison...</div>
                ) : diffData && diffData.lines ? (
                  diffData.lines.map((line, idx) => (
                    <div
                      key={idx}
                      className={`grid grid-cols-2 hover:bg-slate-50/80 transition ${
                        line.type === "modified"
                          ? "bg-amber-50/40"
                          : line.type === "delete"
                          ? "bg-red-50/40"
                          : line.type === "insert"
                          ? "bg-emerald-50/40"
                          : ""
                      }`}
                    >
                      {/* Left: Original Line */}
                      <div className="p-3 border-r border-slate-200 flex items-start space-x-3">
                        <span className="text-slate-400 select-none w-6 text-right shrink-0">
                          {line.line_number_orig ?? "—"}
                        </span>
                        <span className={`break-words ${line.type === "modified" || line.type === "delete" ? "text-red-800 line-through bg-red-50/60 px-1 rounded" : "text-slate-800"}`}>
                          {line.original_text || <span className="text-slate-300 italic">Empty</span>}
                        </span>
                      </div>

                      {/* Right: Revised Line */}
                      <div className="p-3 flex items-start space-x-3">
                        <span className="text-slate-400 select-none w-6 text-right shrink-0">
                          {line.line_number_rev ?? "—"}
                        </span>
                        <span className={`break-words ${line.type === "modified" || line.type === "insert" ? "text-emerald-800 font-medium bg-emerald-50 px-1 rounded" : "text-slate-800"}`}>
                          {line.revised_text || <span className="text-slate-300 italic">Empty</span>}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-12 text-center text-slate-400">Select revisions to inspect explainable diff.</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* --- TAB 2: TRACEABLE VIOLATION CARDS --- */}
        {activeTab === "FINDINGS" && (
          <div className="space-y-6">
            {/* Filter Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200">
              <div className="flex items-center space-x-3">
                <Sliders className="w-4 h-4 text-slate-400" />
                <span className="text-xs font-semibold text-slate-700">Filter Category:</span>
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 font-medium"
                >
                  <option value="ALL">All Categories</option>
                  <option value="TERMINOLOGY">Terminology</option>
                  <option value="FACT_CHECK">Fact Check</option>
                  <option value="COLOR_COMPLIANCE">Color Compliance</option>
                  <option value="CONTRAST">Contrast</option>
                  <option value="CLAIM_ACCURACY">Claim Accuracy</option>
                </select>
              </div>

              <div className="flex items-center space-x-3">
                <span className="text-xs font-semibold text-slate-700">Severity:</span>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 font-medium"
                >
                  <option value="ALL">All Severities</option>
                  <option value="CRITICAL">Critical (-25)</option>
                  <option value="HIGH">High (-10)</option>
                  <option value="MEDIUM">Medium (-5)</option>
                  <option value="LOW">Low (-1)</option>
                </select>
              </div>
            </div>

            {/* Findings List */}
            {filteredFindings.length === 0 ? (
              <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 shadow-sm space-y-3">
                <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
                <h3 className="text-lg font-bold text-slate-900">Zero Violations Found</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  All examined copy conforms to active Brand Vault guidelines and approved fact sheets.
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
                          {finding.status === "EXCEPTION_APPROVED" && (
                            <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                              EXCEPTION APPROVED
                            </span>
                          )}
                          {finding.status === "EXCEPTION_REJECTED" && (
                            <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-rose-100 text-rose-800">
                              EXCEPTION REJECTED
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

                          {/* Request Exception button (for Creators) */}
                          {finding.status === "OPEN" && (
                            <button
                              onClick={() => handleOpenExceptionModal(finding)}
                              className="inline-flex items-center space-x-1 px-3 py-1.5 bg-white border border-amber-300 rounded-lg text-xs font-medium text-amber-900 hover:bg-amber-50 transition"
                            >
                              <HelpCircle className="w-3.5 h-3.5 text-amber-700" />
                              <span>Request Exception</span>
                            </button>
                          )}

                          {/* Reviewer Exception Controls */}
                          {finding.status === "EXCEPTION_REQUESTED" && (
                            <div className="flex items-center space-x-1.5">
                              <button
                                onClick={() => handleDecideException(finding.id, "APPROVED")}
                                disabled={decidingExceptionId === finding.id}
                                className="inline-flex items-center space-x-1 px-3 py-1.5 bg-emerald-700 text-white rounded-lg text-xs font-semibold hover:bg-emerald-800 transition shadow-sm"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                <span>Approve</span>
                              </button>
                              <button
                                onClick={() => handleDecideException(finding.id, "REJECTED")}
                                disabled={decidingExceptionId === finding.id}
                                className="inline-flex items-center space-x-1 px-3 py-1.5 bg-rose-700 text-white rounded-lg text-xs font-semibold hover:bg-rose-800 transition shadow-sm"
                              >
                                <X className="w-3.5 h-3.5" />
                                <span>Reject</span>
                              </button>
                            </div>
                          )}

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
                                ? "Resolved"
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

        {/* --- TAB 4: REVIEW COMMENTS & DISCUSSION --- */}
        {activeTab === "COMMENTS" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
            <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900">Reviewer Discussion Thread</h3>
                <p className="text-xs text-slate-500">Collaborative feedback, revision notes, and approval rationale.</p>
              </div>
              <span className="text-xs font-mono font-medium text-slate-400">{comments.length} comment{comments.length !== 1 ? "s" : ""}</span>
            </div>

            {/* Comment list */}
            <div className="space-y-4">
              {comments.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-xs">
                  No comments posted yet. Reviewers and creators can discuss revisions here.
                </div>
              ) : (
                comments.map((comm) => (
                  <div key={comm.id} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-slate-900">{comm.user_name || comm.user_email || "Reviewer"}</span>
                        <span className="text-slate-400">•</span>
                        <span className="text-slate-500">{new Date(comm.created_at).toLocaleString()}</span>
                      </div>
                      {comm.anchor_location && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                          Line {comm.anchor_location.line || "Anchor"}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-800 leading-relaxed">{comm.comment_text}</p>
                  </div>
                ))
              )}
            </div>

            {/* Comment form */}
            <form onSubmit={handleAddComment} className="pt-4 border-t border-slate-100 space-y-3">
              <textarea
                value={newCommentText}
                onChange={(e) => setNewCommentText(e.target.value)}
                rows={3}
                placeholder="Add an inline review comment or guidance..."
                className="w-full text-xs p-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-900 text-slate-900"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={!newCommentText.trim() || isSubmittingComment}
                  className="inline-flex items-center px-4 py-2 bg-slate-900 text-white font-semibold rounded-lg text-xs hover:bg-slate-800 transition disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5 mr-1.5" />
                  <span>{isSubmittingComment ? "Posting..." : "Post Comment"}</span>
                </button>
              </div>
            </form>
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

        {/* --- APPROVE SUBMISSION MODAL --- */}
        {isApproveModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl border border-slate-200 animate-in zoom-in-95">
              <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2">
                  <div className="p-2 bg-emerald-50 rounded-lg border border-emerald-200">
                    <Award className="w-5 h-5 text-emerald-700" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Approve Publication Sign-Off</h3>
                    <p className="text-xs text-slate-500">Brand Readiness Score: <strong>{readinessScore}%</strong></p>
                  </div>
                </div>
                <button onClick={() => setIsApproveModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 space-y-1">
                <p className="font-semibold flex items-center">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Ready for Cryptographic Issuance
                </p>
                <p className="text-[11px] text-emerald-700 leading-relaxed">
                  Approving will generate a mathematically verifiable Compliance Certificate with SHA-256 hash chaining.
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-800">
                  Reviewer Sign-off Notes (Optional)
                </label>
                <textarea
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  rows={3}
                  placeholder="e.g. All copy approved for Q4 marketing rollout. Verified against brand vault v1.2."
                  className="w-full text-xs p-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  onClick={() => setIsApproveModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleApproveSubmission}
                  disabled={isApproving}
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-emerald-700 text-white rounded-lg text-xs font-bold hover:bg-emerald-800 disabled:opacity-50"
                >
                  {isApproving ? <RotateCcw className="w-3.5 h-3.5 animate-spin" /> : <ThumbsUp className="w-3.5 h-3.5" />}
                  <span>{isApproving ? "Issuing Certificate..." : "Confirm Approval"}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* --- REJECT / REQUEST CHANGES MODAL --- */}
        {isRejectModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl border border-slate-200 animate-in zoom-in-95">
              <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2">
                  <div className="p-2 bg-amber-50 rounded-lg border border-amber-200">
                    <ThumbsDown className="w-5 h-5 text-amber-700" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Request Changes / Reject</h3>
                    <p className="text-xs text-slate-500">Provide required feedback to the creator</p>
                  </div>
                </div>
                <button onClick={() => setIsRejectModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-800">
                  Change Request Justification <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={rejectionNotes}
                  onChange={(e) => setRejectionNotes(e.target.value)}
                  rows={4}
                  placeholder="Explain exactly what needs to be changed (e.g. adjust contrast ratio, rephrase superlative claim, fix SLA number)..."
                  className="w-full text-xs p-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500 text-slate-800"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  onClick={() => setIsRejectModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRejectSubmission}
                  disabled={!rejectionNotes.trim() || isRejecting}
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-amber-600 text-white rounded-lg text-xs font-bold hover:bg-amber-700 disabled:opacity-50"
                >
                  {isRejecting ? <RotateCcw className="w-3.5 h-3.5 animate-spin" /> : <ThumbsDown className="w-3.5 h-3.5" />}
                  <span>{isRejecting ? "Requesting Changes..." : "Confirm Request Changes"}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* --- COMPLIANCE CERTIFICATE MODAL --- */}
        {isCertModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
            <div className="bg-slate-900 border border-teal-500/40 rounded-3xl max-w-xl w-full p-6 sm:p-8 space-y-6 shadow-2xl text-white relative animate-in zoom-in-95">
              <button
                onClick={() => setIsCertModalOpen(false)}
                className="absolute top-6 right-6 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-center space-x-3">
                <div className="p-3 bg-teal-500/10 rounded-2xl border border-teal-500/30">
                  <Award className="w-8 h-8 text-teal-400" />
                </div>
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-teal-400">
                    Official VeriBrand Trace Seal
                  </span>
                  <h3 className="text-xl font-extrabold text-white">Compliance Certificate</h3>
                  <p className="text-xs text-slate-400 font-mono">
                    {certificate?.certificate_number || "VBT-CERT-ACME-VERIFIED"}
                  </p>
                </div>
              </div>

              <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-3 text-xs">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Submission</span>
                  <span className="font-semibold text-white">{submissionTitle}</span>
                </div>
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Brand Readiness Score</span>
                  <span className="font-mono font-bold text-teal-400 text-sm">{readinessScore}%</span>
                </div>
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Date Issued</span>
                  <span className="text-slate-300 font-medium">
                    {certificate?.issued_at ? new Date(certificate.issued_at).toLocaleDateString() : new Date().toLocaleDateString()}
                  </span>
                </div>
                <div className="space-y-1 pt-1">
                  <span className="text-slate-400 block">SHA-256 Tamper-Evident Hash</span>
                  <p className="font-mono text-[10px] text-teal-300 break-all select-all bg-slate-900 p-2 rounded border border-slate-800">
                    {certificate?.certificate_hash || "8f4a13b97c02e1189ab5d9847120fa26f3781c0384a44b8f04739265ecb37190"}
                  </p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                <div className="flex items-center space-x-2">
                  {certificate?.certificate_number && (
                    <>
                      <a
                        href={`${apiUrl}/certificates/${certificate.certificate_number}/download`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-3 py-1.5 bg-slate-900 text-teal-400 border border-slate-700 hover:border-teal-500/50 rounded-lg text-xs font-semibold transition"
                      >
                        <Download className="w-3.5 h-3.5 mr-1.5" />
                        Download PDF
                      </a>
                      <Link
                        href={`/verify/${certificate.certificate_number}`}
                        target="_blank"
                        className="inline-flex items-center text-xs font-semibold text-slate-400 hover:text-white px-2 py-1.5"
                      >
                        <ExternalLink className="w-3.5 h-3.5 mr-1" />
                        Public Proof
                      </Link>
                    </>
                  )}
                </div>
                <button
                  onClick={() => setIsCertModalOpen(false)}
                  className="w-full sm:w-auto px-5 py-2 bg-teal-500 text-slate-950 rounded-xl text-xs font-bold hover:bg-teal-400 transition"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}
    </div>
  );
}
