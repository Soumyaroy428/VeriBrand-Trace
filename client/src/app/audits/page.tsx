"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  FileCheck,
  Plus,
  Shield,
  Eye,
  Download,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Search,
  Filter,
  FileText,
  Image as ImageIcon,
  ChevronRight,
  RefreshCw,
  Lock,
  ArrowRight,
  X,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

interface SubmissionRevision {
  id: string;
  submission_id: string;
  revision_number: number;
  storage_key?: string;
  content_hash: string;
  extracted_text?: string;
  sanitized_text?: string;
  privacy_gate_metadata?: {
    status: string;
    pii_detected?: Array<{
      type: string;
      snippet_masked: string;
      mask_applied: string;
    }>;
    confidential_terms_masked?: Array<{
      term: string;
      token: string;
      occurrences: number;
    }>;
    original_char_count?: number;
    sanitized_char_count?: number;
  };
  created_at: string;
}

interface Submission {
  id: string;
  workspace_id: string;
  title: string;
  input_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  latest_revision?: SubmissionRevision;
}

// Initial demo submissions when backend is in offline demo mode
const DEMO_SUBMISSIONS: Submission[] = [
  {
    id: "sub-101",
    workspace_id: "demo-ws",
    title: "Q3 Sustainability Launch Press Release",
    input_type: "DOCX",
    status: "DRAFT",
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    latest_revision: {
      id: "rev-101-1",
      submission_id: "sub-101",
      revision_number: 1,
      content_hash: "a89fb314c40e53a2f8c6722bc13d5b78",
      extracted_text:
        "Our enterprise platform reduces carbon emissions by 40%. Reach press@acme.com or call +1 555-019-2834.",
      sanitized_text:
        "Our enterprise platform reduces carbon emissions by 40%. Reach [REDACTED_EMAIL] or call [REDACTED_PHONE].",
      privacy_gate_metadata: {
        status: "SANITIZED",
        pii_detected: [
          { type: "EMAIL", snippet_masked: "pr***om", mask_applied: "[REDACTED_EMAIL]" },
          { type: "PHONE", snippet_masked: "+1***34", mask_applied: "[REDACTED_PHONE]" },
        ],
        confidential_terms_masked: [],
        original_char_count: 104,
        sanitized_char_count: 106,
      },
      created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    },
  },
  {
    id: "sub-102",
    workspace_id: "demo-ws",
    title: "Product Hero Banner & Spec Sheet",
    input_type: "IMAGE_PNG",
    status: "NEEDS_CHANGES",
    created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 12).toISOString(),
    latest_revision: {
      id: "rev-102-1",
      submission_id: "sub-102",
      revision_number: 2,
      content_hash: "f420e98112bc71aa43094857bdf88102",
      extracted_text: "FalconCore processing chip gives 100% infallible uptime.",
      sanitized_text: "[CONFIDENTIAL_PROJECT_1] processing chip gives 100% infallible uptime.",
      privacy_gate_metadata: {
        status: "SANITIZED",
        pii_detected: [],
        confidential_terms_masked: [
          { term: "FalconCore", token: "[CONFIDENTIAL_PROJECT_1]", occurrences: 1 },
        ],
      },
      created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
    },
  },
  {
    id: "sub-103",
    workspace_id: "demo-ws",
    title: "Corporate ESG Transparency Report 2026",
    input_type: "PDF",
    status: "APPROVED",
    created_at: new Date(Date.now() - 3600000 * 72).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 36).toISOString(),
    latest_revision: {
      id: "rev-103-1",
      submission_id: "sub-103",
      revision_number: 1,
      content_hash: "7bc32f9104eacdbb821938501239ab77",
      extracted_text: "Audited report adhering to GRI Sustainability Standards 2026.",
      sanitized_text: "Audited report adhering to GRI Sustainability Standards 2026.",
      privacy_gate_metadata: {
        status: "CLEAN",
        pii_detected: [],
        confidential_terms_masked: [],
      },
      created_at: new Date(Date.now() - 3600000 * 72).toISOString(),
    },
  },
];

export default function SubmissionsDashboard() {
  const { token, activeWorkspace } = useAuth();
  const [submissions, setSubmissions] = useState<Submission[]>(DEMO_SUBMISSIONS);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [selectedSub, setSelectedSub] = useState<Submission | null>(null);

  const fetchSubmissions = async () => {
    try {
      setLoading(true);
      const wsId = activeWorkspace?.workspace_id || "demo-ws";
      const res = await fetch(`/api/v1/workspaces/${wsId}/submissions`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setSubmissions(data);
        }
      }
    } catch {
      // Retain demo submissions on fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmissions();
  }, [activeWorkspace, token]);

  const filtered = submissions.filter((sub) => {
    const matchesSearch = sub.title.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || sub.status === statusFilter;
    const matchesType = typeFilter === "ALL" || sub.input_type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-mono font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3 mr-1" /> Approved
          </span>
        );
      case "NEEDS_CHANGES":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-mono font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <AlertTriangle className="w-3 h-3 mr-1" /> Needs Changes
          </span>
        );
      case "PROCESSING":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-mono font-semibold bg-sky-500/15 text-sky-300 border border-sky-500/30">
            <Clock className="w-3 h-3 mr-1 animate-spin" /> Processing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-mono font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            Draft
          </span>
        );
    }
  };

  const getTypeIcon = (type: string) => {
    if (type.startsWith("IMAGE")) return <ImageIcon className="w-4 h-4 text-purple-400" />;
    return <FileText className="w-4 h-4 text-teal-400" />;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-teal-300 bg-teal-500/10 px-2.5 py-0.5 rounded border border-teal-500/30">
              Content Pipeline
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Workspace: {activeWorkspace?.workspace_name || "Global Brand Workspace"}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mt-2">
            Content Submissions & Privacy Gate
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Pre-publication governance archive. Every submission is immutably versioned with cryptographic SHA-256 hash chaining and PII sanitization.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={fetchSubmissions}
            className="p-2.5 rounded-xl border border-slate-800 bg-[#0e1320] hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <Link
            href="/audits/new"
            className="inline-flex items-center justify-center px-4 py-2.5 text-xs font-bold text-slate-950 bg-teal-500 hover:bg-teal-400 rounded-xl transition shadow-[0_0_15px_rgba(20,184,166,0.3)] space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>New Submission</span>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#0e1320] p-4 rounded-2xl border border-slate-800 shadow-lg">
          <p className="text-xs font-mono uppercase tracking-wider text-slate-400">Total Submissions</p>
          <p className="text-2xl font-extrabold text-white font-mono mt-1 font-tabular">
            {submissions.length}
          </p>
        </div>
        <div className="bg-[#0e1320] p-4 rounded-2xl border border-slate-800 shadow-lg">
          <p className="text-xs font-mono uppercase tracking-wider text-slate-400">Active In Review</p>
          <p className="text-2xl font-extrabold text-amber-400 font-mono mt-1 font-tabular">
            {submissions.filter((s) => s.status === "NEEDS_CHANGES" || s.status === "PROCESSING").length}
          </p>
        </div>
        <div className="bg-[#0e1320] p-4 rounded-2xl border border-slate-800 shadow-lg">
          <p className="text-xs font-mono uppercase tracking-wider text-slate-400">Approved & Certified</p>
          <p className="text-2xl font-extrabold text-emerald-400 font-mono mt-1 font-tabular">
            {submissions.filter((s) => s.status === "APPROVED").length}
          </p>
        </div>
        <div className="bg-[#0e1320] p-4 rounded-2xl border border-slate-800 shadow-lg">
          <p className="text-xs font-mono uppercase tracking-wider text-slate-400">Privacy Gate Scrubbed</p>
          <p className="text-2xl font-extrabold text-teal-400 font-mono mt-1 font-tabular">
            {submissions.filter((s) => s.latest_revision?.privacy_gate_metadata?.status === "SANITIZED").length}
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#0e1320] p-4 rounded-2xl border border-slate-800 shadow-lg flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs bg-[#080c14] text-white placeholder-slate-500 border border-slate-700 rounded-xl focus:outline-none focus:border-teal-500/60"
          />
        </div>
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-teal-400" />
            <span className="text-xs font-mono text-slate-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs bg-[#080c14] text-slate-200 border border-slate-700 rounded-lg py-1.5 px-2.5 focus:outline-none focus:border-teal-500/60"
            >
              <option value="ALL">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="PROCESSING">Auditing</option>
              <option value="NEEDS_CHANGES">Needs Changes</option>
              <option value="APPROVED">Approved</option>
            </select>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-slate-400">Format:</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="text-xs bg-[#080c14] text-slate-200 border border-slate-700 rounded-lg py-1.5 px-2.5 focus:outline-none focus:border-teal-500/60"
            >
              <option value="ALL">All Formats</option>
              <option value="TEXT">Text</option>
              <option value="DOCX">DOCX</option>
              <option value="PDF">PDF</option>
              <option value="IMAGE_PNG">PNG Image</option>
              <option value="IMAGE_JPG">JPG Image</option>
            </select>
          </div>
        </div>
      </div>

      {/* Submissions Table */}
      <div className="bg-[#0e1320] rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="bg-[#141b2d]/60">
              <tr>
                <th className="px-6 py-3.5 text-left text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                  Submission Title
                </th>
                <th className="px-6 py-3.5 text-left text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                  Format
                </th>
                <th className="px-6 py-3.5 text-left text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                  Revision
                </th>
                <th className="px-6 py-3.5 text-left text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                  Privacy Gate
                </th>
                <th className="px-6 py-3.5 text-left text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                  Governance Status
                </th>
                <th className="px-6 py-3.5 text-left text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3.5 text-right text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-sm text-slate-400">
                    No submissions found matching criteria. Click &quot;New Submission&quot; to upload your first document.
                  </td>
                </tr>
              ) : (
                filtered.map((sub) => {
                  const isSanitized =
                    sub.latest_revision?.privacy_gate_metadata?.status === "SANITIZED";
                  return (
                    <tr key={sub.id} className="hover:bg-slate-800/40 transition">
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-3">
                          <div className="p-2 bg-[#141b2d] rounded-xl border border-slate-800">
                            {getTypeIcon(sub.input_type)}
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-white">{sub.title}</p>
                            <p className="text-xs font-mono text-slate-500 mt-0.5">
                              Hash: {sub.latest_revision?.content_hash.slice(0, 12)}...
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-xs font-mono text-slate-300">
                        {sub.input_type}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700">
                          v{sub.latest_revision?.revision_number || 1}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {isSanitized ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-mono bg-teal-500/15 text-teal-300 border border-teal-500/30">
                            <Shield className="w-3 h-3 mr-1" /> PII Redacted
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-mono bg-slate-800 text-slate-400 border border-slate-700">
                            <CheckCircle2 className="w-3 h-3 mr-1" /> Clean
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">{getStatusBadge(sub.status)}</td>
                      <td className="px-6 py-4 text-xs font-mono text-slate-400">
                        {new Date(sub.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        <Link
                          href={`/audits/${sub.id}`}
                          className="inline-flex items-center text-xs font-semibold text-slate-950 bg-teal-500 hover:bg-teal-400 px-3 py-1.5 rounded-lg transition shadow-sm"
                        >
                          <FileCheck className="w-3.5 h-3.5 mr-1" />
                          Audit Results
                        </Link>
                        <button
                          onClick={() => setSelectedSub(sub)}
                          className="inline-flex items-center text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 rounded-lg border border-slate-700 transition"
                        >
                          <Eye className="w-3.5 h-3.5 mr-1 text-teal-400" />
                          Privacy Gate
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Privacy Gate Inspection Modal */}
      {selectedSub && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in"
          onClick={() => setSelectedSub(null)}
        >
          <div
            className="bg-[#0e1320] rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-6 shadow-2xl border border-slate-700 animate-in zoom-in-95"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <span className="text-[10px] font-mono uppercase bg-slate-800 px-2 py-0.5 rounded text-teal-300">
                  Revision {selectedSub.latest_revision?.revision_number || 1}
                </span>
                <h2 className="text-lg font-bold text-white mt-1">{selectedSub.title}</h2>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Content SHA-256: {selectedSub.latest_revision?.content_hash}
                </p>
              </div>
              <button
                onClick={() => setSelectedSub(null)}
                className="text-slate-400 hover:text-white font-bold p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Privacy Gate Summary Card */}
            <div className="bg-[#141b2d] p-4 rounded-xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-semibold uppercase text-slate-300 flex items-center">
                  <Shield className="w-4 h-4 text-teal-400 mr-1.5" />
                  Privacy Gate Verification Status
                </span>
                <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-teal-500/15 text-teal-300 border border-teal-500/30">
                  {selectedSub.latest_revision?.privacy_gate_metadata?.status || "PASSED"}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-[#080c14] p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400 font-mono text-[11px]">PII Entities Scrubbed:</span>
                  <p className="text-lg font-bold text-teal-300 font-mono mt-0.5">
                    {selectedSub.latest_revision?.privacy_gate_metadata?.pii_detected?.length || 0}
                  </p>
                </div>
                <div className="bg-[#080c14] p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400 font-mono text-[11px]">Confidential Terms Masked:</span>
                  <p className="text-lg font-bold text-amber-300 font-mono mt-0.5">
                    {selectedSub.latest_revision?.privacy_gate_metadata?.confidential_terms_masked?.length || 0}
                  </p>
                </div>
              </div>
            </div>

            {/* Scrubbed Items Breakdown */}
            {selectedSub.latest_revision?.privacy_gate_metadata?.pii_detected &&
              selectedSub.latest_revision.privacy_gate_metadata.pii_detected.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-mono font-semibold text-slate-300 uppercase">
                    Redacted PII Items
                  </h3>
                  <div className="space-y-1.5">
                    {selectedSub.latest_revision.privacy_gate_metadata.pii_detected.map((pii, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between p-2.5 bg-rose-500/10 text-rose-300 rounded-lg text-xs border border-rose-500/30 font-mono"
                      >
                        <span className="font-semibold">{pii.type}</span>
                        <span className="text-slate-400">Mask: {pii.mask_applied}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Sanitized Text vs Raw Text Comparison */}
            <div className="space-y-2">
              <h3 className="text-xs font-mono font-semibold text-slate-300 uppercase">
                Sanitized Content (Delivered to AI & Vector DB)
              </h3>
              <div className="p-3.5 bg-[#080c14] text-slate-300 rounded-xl text-xs font-mono leading-relaxed max-h-48 overflow-y-auto border border-slate-800 whitespace-pre-wrap">
                {selectedSub.latest_revision?.sanitized_text ||
                  selectedSub.latest_revision?.extracted_text}
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-800">
              <button
                onClick={() => setSelectedSub(null)}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold transition"
              >
                Close Gate Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
