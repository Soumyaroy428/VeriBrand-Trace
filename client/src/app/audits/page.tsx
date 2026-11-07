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
      extracted_text: "Our enterprise platform reduces carbon emissions by 40%. Reach press@acme.com or call +1 555-019-2834.",
      sanitized_text: "Our enterprise platform reduces carbon emissions by 40%. Reach [REDACTED_EMAIL] or call [REDACTED_PHONE].",
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
      revision_number: 1,
      content_hash: "b77e203c9f2110ea4b8c91d84f0012bc",
      extracted_text: "[PNG Image: 1920x1080 pixels, Mode RGB]",
      sanitized_text: "[PNG Image: 1920x1080 pixels, Mode RGB]",
      privacy_gate_metadata: {
        status: "PASSED",
        pii_detected: [],
        confidential_terms_masked: [],
        original_char_count: 40,
        sanitized_char_count: 40,
      },
      created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    },
  },
  {
    id: "sub-103",
    workspace_id: "demo-ws",
    title: "Project Titan Confidential Strategy Deck",
    input_type: "PDF",
    status: "APPROVED",
    created_at: new Date(Date.now() - 3600000 * 48).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 4).toISOString(),
    latest_revision: {
      id: "rev-103-1",
      submission_id: "sub-103",
      revision_number: 1,
      content_hash: "c411a76ef81b37996a1a1205e4dfa781",
      extracted_text: "Project Titan confidential briefing for Q4 roadmap.",
      sanitized_text: "[CONFIDENTIAL_PROJECT_1] confidential briefing for Q4 roadmap.",
      privacy_gate_metadata: {
        status: "SANITIZED",
        pii_detected: [],
        confidential_terms_masked: [
          { term: "Project Titan", token: "[CONFIDENTIAL_PROJECT_1]", occurrences: 1 },
        ],
        original_char_count: 51,
        sanitized_char_count: 62,
      },
      created_at: new Date(Date.now() - 3600000 * 48).toISOString(),
    },
  },
];

export default function SubmissionsDashboard() {
  const { token, activeWorkspace } = useAuth();
  const [submissions, setSubmissions] = useState<Submission[]>(DEMO_SUBMISSIONS);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [selectedSub, setSelectedSub] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchSubmissions() {
      if (!token || !activeWorkspace) return;
      try {
        setLoading(true);
        const res = await fetch(`/api/v1/workspaces/${activeWorkspace.workspace_id}/submissions`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          if (data.submissions && data.submissions.length > 0) {
            setSubmissions(data.submissions);
          }
        }
      } catch {
        // Fall back gracefully to demo data
      } finally {
        setLoading(false);
      }
    }
    fetchSubmissions();
  }, [token, activeWorkspace]);

  const filtered = submissions.filter((sub) => {
    const matchesSearch = sub.title.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || sub.status === statusFilter;
    const matchesType = typeFilter === "ALL" || sub.input_type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200"><CheckCircle2 className="w-3 h-3 mr-1" /> Approved</span>;
      case "NEEDS_CHANGES":
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200"><AlertTriangle className="w-3 h-3 mr-1" /> Needs Changes</span>;
      case "PROCESSING":
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-50 text-sky-800 border border-sky-200"><RefreshCw className="w-3 h-3 mr-1 animate-spin" /> Auditing</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200"><Clock className="w-3 h-3 mr-1" /> Draft</span>;
    }
  };

  const getTypeIcon = (type: string) => {
    if (type.startsWith("IMAGE")) return <ImageIcon className="w-4 h-4 text-purple-600" />;
    return <FileText className="w-4 h-4 text-sky-600" />;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded border border-teal-200">
              Content Pipeline
            </span>
            <span className="text-xs text-slate-500">Workspace: {activeWorkspace?.workspace_name || "Global Brand"}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-2">
            Content Submissions & Privacy Gate
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Pre-publication governance archive. Every submission is immutably versioned with cryptographic SHA-256 hash chaining and PII sanitization.
          </p>
        </div>
        <Link
          href="/audits/new"
          className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition shadow-sm space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>New Submission</span>
        </Link>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-xs font-medium text-slate-500">Total Submissions</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{submissions.length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-xs font-medium text-slate-500">Active In Review</p>
          <p className="text-2xl font-bold text-amber-700 mt-1">
            {submissions.filter((s) => s.status === "NEEDS_CHANGES" || s.status === "PROCESSING").length}
          </p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-xs font-medium text-slate-500">Approved & Certified</p>
          <p className="text-2xl font-bold text-emerald-700 mt-1">
            {submissions.filter((s) => s.status === "APPROVED").length}
          </p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-xs font-medium text-slate-500">Privacy Gate Scrubbed</p>
          <p className="text-2xl font-bold text-teal-700 mt-1">
            {submissions.filter((s) => s.latest_revision?.privacy_gate_metadata?.status === "SANITIZED").length}
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
        </div>
        <div className="flex items-center space-x-3 w-full md:w-auto">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium text-slate-600">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-md py-1.5 px-2 bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
            >
              <option value="ALL">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="PROCESSING">Auditing</option>
              <option value="NEEDS_CHANGES">Needs Changes</option>
              <option value="APPROVED">Approved</option>
            </select>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-medium text-slate-600">Format:</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-md py-1.5 px-2 bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
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
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3.5 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Submission Title
              </th>
              <th className="px-6 py-3.5 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Format
              </th>
              <th className="px-6 py-3.5 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Revision
              </th>
              <th className="px-6 py-3.5 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Privacy Gate
              </th>
              <th className="px-6 py-3.5 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Governance Status
              </th>
              <th className="px-6 py-3.5 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3.5 text-right text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-sm text-slate-500">
                  No submissions found matching criteria. Click &quot;New Submission&quot; to upload your first document.
                </td>
              </tr>
            ) : (
              filtered.map((sub) => {
                const isSanitized = sub.latest_revision?.privacy_gate_metadata?.status === "SANITIZED";
                return (
                  <tr key={sub.id} className="hover:bg-slate-50 transition">
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-slate-100 rounded-lg">
                          {getTypeIcon(sub.input_type)}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-900">{sub.title}</p>
                          <p className="text-xs font-mono text-slate-400 mt-0.5">
                            Hash: {sub.latest_revision?.content_hash.slice(0, 12)}...
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs font-mono font-medium text-slate-600">
                      {sub.input_type}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-slate-100 text-slate-700 border border-slate-300">
                        v{sub.latest_revision?.revision_number || 1}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {isSanitized ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-50 text-teal-800 border border-teal-200">
                          <Shield className="w-3 h-3 mr-1" /> PII Redacted
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-50 text-slate-700 border border-slate-200">
                          <CheckCircle2 className="w-3 h-3 mr-1" /> Clean
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(sub.status)}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {new Date(sub.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <Link
                        href={`/audits/${sub.id}`}
                        className="inline-flex items-center text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 px-3 py-1.5 rounded-md transition shadow-sm"
                      >
                        <FileCheck className="w-3.5 h-3.5 mr-1" />
                        Audit Results
                      </Link>
                      <button
                        onClick={() => setSelectedSub(sub)}
                        className="inline-flex items-center text-xs font-medium text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-2.5 py-1.5 rounded-md transition"
                      >
                        <Eye className="w-3.5 h-3.5 mr-1" />
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

      {/* Privacy Gate Inspection Modal */}
      {selectedSub && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-6 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <span className="text-xs font-mono uppercase bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                  Revision {selectedSub.latest_revision?.revision_number || 1}
                </span>
                <h2 className="text-lg font-bold text-slate-900 mt-1">{selectedSub.title}</h2>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  Content SHA-256: {selectedSub.latest_revision?.content_hash}
                </p>
              </div>
              <button
                onClick={() => setSelectedSub(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg p-1"
              >
                ✕
              </button>
            </div>

            {/* Privacy Gate Summary Card */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-slate-700 flex items-center">
                  <Shield className="w-4 h-4 text-teal-600 mr-1.5" />
                  Privacy Gate Verification Status
                </span>
                <span className="text-xs font-medium px-2 py-0.5 rounded bg-teal-100 text-teal-800">
                  {selectedSub.latest_revision?.privacy_gate_metadata?.status || "PASSED"}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-slate-500">PII Entities Scrubbed:</span>
                  <p className="text-base font-bold text-slate-900 mt-0.5">
                    {selectedSub.latest_revision?.privacy_gate_metadata?.pii_detected?.length || 0}
                  </p>
                </div>
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-slate-500">Confidential Terms Masked:</span>
                  <p className="text-base font-bold text-slate-900 mt-0.5">
                    {selectedSub.latest_revision?.privacy_gate_metadata?.confidential_terms_masked?.length || 0}
                  </p>
                </div>
              </div>
            </div>

            {/* Scrubbed Items Breakdown */}
            {selectedSub.latest_revision?.privacy_gate_metadata?.pii_detected &&
              selectedSub.latest_revision.privacy_gate_metadata.pii_detected.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-slate-700 uppercase">Redacted PII Items</h3>
                  <div className="space-y-1.5">
                    {selectedSub.latest_revision.privacy_gate_metadata.pii_detected.map((pii, i) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-red-50 text-red-900 rounded-lg text-xs border border-red-200">
                        <span className="font-mono font-medium">{pii.type}</span>
                        <span className="font-mono text-slate-600">Mask: {pii.mask_applied}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Confidential Terms Breakdown */}
            {selectedSub.latest_revision?.privacy_gate_metadata?.confidential_terms_masked &&
              selectedSub.latest_revision.privacy_gate_metadata.confidential_terms_masked.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-slate-700 uppercase">Masked Confidential Terms</h3>
                  <div className="space-y-1.5">
                    {selectedSub.latest_revision.privacy_gate_metadata.confidential_terms_masked.map((term, i) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-amber-50 text-amber-900 rounded-lg text-xs border border-amber-200">
                        <span className="font-medium">{term.term}</span>
                        <span className="font-mono font-semibold text-amber-800">{term.token}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Sanitized Text vs Raw Text Comparison */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-slate-700 uppercase">
                Sanitized Content (Delivered to AI & Vector DB)
              </h3>
              <div className="p-3 bg-slate-900 text-slate-100 rounded-xl text-xs font-mono leading-relaxed max-h-48 overflow-y-auto">
                {selectedSub.latest_revision?.sanitized_text || selectedSub.latest_revision?.extracted_text}
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-200">
              <button
                onClick={() => setSelectedSub(null)}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-medium hover:bg-slate-800 transition"
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
