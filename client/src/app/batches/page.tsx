"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Boxes,
  Plus,
  Trash2,
  FileText,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  Download,
  Play,
  RefreshCw,
  ArrowRight,
  Sparkles,
  Layers,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import { useAuth } from "@/context/AuthContext";

interface BatchItemSummary {
  submission_id: string;
  title: string;
  status: string;
  readiness_score: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  total_findings: number;
}

interface BatchAudit {
  id: string;
  workspace_id: string;
  title: string;
  campaign_tag?: string;
  created_by: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  total_items: number;
  completed_items: number;
  aggregate_score: number;
  critical_violations: number;
  warning_violations: number;
  info_violations: number;
  campaign_rating: "CAMPAIGN_READY" | "REQUIRES_REMEDIATION" | "CRITICAL_RISK" | "PENDING_AUDIT";
  created_at: string;
  updated_at: string;
  items: BatchItemSummary[];
}

export default function CampaignBatchesPage() {
  const { activeWorkspace, token } = useAuth();
  const [batches, setBatches] = useState<BatchAudit[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [runningBatchId, setRunningBatchId] = useState<string | null>(null);

  // Form State
  const [batchTitle, setBatchTitle] = useState("");
  const [campaignTag, setCampaignTag] = useState("");
  const [items, setItems] = useState<Array<{ title: string; content: string }>>([
    {
      title: "Omni-Channel Press Release",
      content: "Acme Global announces next-generation zero-latency cloud architecture. Certified 99.99% uptime for enterprise teams.",
    },
    {
      title: "Social Ad Campaign Copy",
      content: "Experience 100% guaranteed error-free deployment today. Guaranteed zero downtime on all cloud tiers.",
    },
  ]);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";

  const fetchBatches = async () => {
    if (!activeWorkspace) return;
    setLoading(true);

    try {
      const res = await fetch(`${apiUrl}/workspaces/${activeWorkspace.workspace_id}/batches`, {
        headers: {
          Authorization: `Bearer ${token || ""}`,
        },
      });

      if (!res.ok) {
        throw new Error(`Failed to load batches (HTTP ${res.status})`);
      }

      const data = await res.json();
      setBatches(data);
    } catch (err) {
      console.warn("Using demo batch data fallback:", err);
      setBatches([
        {
          id: "demo-batch-1",
          workspace_id: activeWorkspace.workspace_id,
          title: "Q3 Omni-Channel Product Launch",
          campaign_tag: "q3-omni-launch",
          created_by: "user-1",
          status: "COMPLETED",
          total_items: 3,
          completed_items: 3,
          aggregate_score: 84.5,
          critical_violations: 0,
          warning_violations: 4,
          info_violations: 2,
          campaign_rating: "REQUIRES_REMEDIATION",
          created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
          updated_at: new Date(Date.now() - 3600000 * 3).toISOString(),
          items: [
            {
              submission_id: "demo-sub-101",
              title: "Press Release Announcement",
              status: "AUDITED",
              readiness_score: 92.0,
              critical_findings: 0,
              high_findings: 0,
              medium_findings: 1,
              low_findings: 1,
              total_findings: 2,
            },
            {
              submission_id: "demo-sub-102",
              title: "Social Ad Promotional Copy",
              status: "AUDITED",
              readiness_score: 75.0,
              critical_findings: 0,
              high_findings: 2,
              medium_findings: 1,
              low_findings: 0,
              total_findings: 3,
            },
            {
              submission_id: "demo-sub-103",
              title: "Product Landing Page One-Pager",
              status: "AUDITED",
              readiness_score: 86.5,
              critical_findings: 0,
              high_findings: 0,
              medium_findings: 0,
              low_findings: 1,
              total_findings: 1,
            },
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, [activeWorkspace?.workspace_id]);

  const handleAddItem = () => {
    if (items.length >= 10) return;
    setItems([...items, { title: `Campaign Asset #${items.length + 1}`, content: "" }]);
  };

  const handleRemoveItem = (index: number) => {
    if (items.length <= 1) return;
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: "title" | "content", val: string) => {
    const updated = [...items];
    updated[index][field] = val;
    setItems(updated);
  };

  const handleCreateBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || submitting) return;

    setSubmitting(true);
    try {
      const res = await fetch(`${apiUrl}/workspaces/${activeWorkspace.workspace_id}/batches?auto_run=true`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token || ""}`,
        },
        body: JSON.stringify({
          title: batchTitle,
          campaign_tag: campaignTag || undefined,
          items: items.map((it) => ({
            title: it.title,
            content: it.content,
          })),
        }),
      });

      if (!res.ok) {
        throw new Error(`Failed to create batch (HTTP ${res.status})`);
      }

      const newBatch = await res.json();
      setBatches([newBatch, ...batches]);
      setShowCreateModal(false);
      setBatchTitle("");
      setCampaignTag("");
    } catch (err: any) {
      alert(`Error creating batch: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRunBatch = async (batchId: string) => {
    if (!activeWorkspace || runningBatchId) return;
    setRunningBatchId(batchId);

    try {
      const res = await fetch(`${apiUrl}/workspaces/${activeWorkspace.workspace_id}/batches/${batchId}/run`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token || ""}`,
        },
      });

      if (!res.ok) {
        throw new Error(`Audit run failed (HTTP ${res.status})`);
      }

      const updated = await res.json();
      setBatches(batches.map((b) => (b.id === batchId ? updated : b)));
    } catch (err: any) {
      alert(`Error running batch audit: ${err.message}`);
    } finally {
      setRunningBatchId(null);
    }
  };

  const handleExportReport = async (batchId: string, title: string) => {
    if (!activeWorkspace) return;

    try {
      const res = await fetch(`${apiUrl}/workspaces/${activeWorkspace.workspace_id}/batches/${batchId}/export`, {
        headers: {
          Authorization: `Bearer ${token || ""}`,
        },
      });

      if (!res.ok) throw new Error("Export failed");
      const data = await res.json();

      // Trigger download as formatted JSON
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `governance_report_${title.toLowerCase().replace(/[^a-z0-9]/g, "_")}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Could not export report: ${err.message}`);
    }
  };

  const getRatingBadge = (rating: BatchAudit["campaign_rating"]) => {
    switch (rating) {
      case "CAMPAIGN_READY":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Campaign Ready
          </span>
        );
      case "REQUIRES_REMEDIATION":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            Requires Remediation
          </span>
        );
      case "CRITICAL_RISK":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
            Critical Risk
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            Pending Audit
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200 uppercase tracking-wider">
                Phase 8 — High Volume
              </span>
              <span className="text-xs text-slate-500 font-mono">Multi-Asset Pipeline</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950 flex items-center gap-2">
              <Boxes className="w-6 h-6 text-teal-600" />
              Campaign Batch Auditing
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Audit multi-channel marketing campaigns concurrently with privacy scrubbing, deterministic rule matching, and executive readiness exports.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchBatches}
              disabled={loading}
              className="p-2 text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition"
              title="Refresh Batches"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 transition shadow-sm"
            >
              <Plus className="w-4 h-4 text-teal-400" />
              New Campaign Batch
            </button>
          </div>
        </div>

        {/* Batches List */}
        {loading && batches.length === 0 ? (
          <div className="text-center py-20 bg-white border border-slate-200 rounded-xl p-8">
            <RefreshCw className="w-8 h-8 text-teal-600 animate-spin mx-auto mb-3" />
            <p className="text-sm text-slate-600 font-medium">Loading campaign batches...</p>
          </div>
        ) : batches.length === 0 ? (
          <div className="text-center py-16 bg-white border border-slate-200 rounded-xl p-8 max-w-xl mx-auto space-y-4">
            <div className="w-12 h-12 bg-teal-50 text-teal-600 rounded-full flex items-center justify-center mx-auto border border-teal-100">
              <Boxes className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900">No Campaign Batches Created</h3>
              <p className="text-xs text-slate-500 mt-1">
                Queue multiple marketing assets, ads, press releases, and copy sheets together to evaluate overall campaign readiness.
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 transition"
            >
              <Plus className="w-4 h-4 text-teal-400" />
              Create First Campaign Batch
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {batches.map((batch) => (
              <div
                key={batch.id}
                className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:border-slate-300 transition"
              >
                {/* Batch Top Header */}
                <div className="p-6 border-b border-slate-100 flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-50/50">
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <h2 className="text-lg font-semibold text-slate-900">{batch.title}</h2>
                      {batch.campaign_tag && (
                        <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-slate-100 text-slate-600 border border-slate-200">
                          #{batch.campaign_tag}
                        </span>
                      )}
                      {getRatingBadge(batch.campaign_rating)}
                    </div>
                    <p className="text-xs text-slate-500">
                      Created on {new Date(batch.created_at).toLocaleDateString()} at {new Date(batch.created_at).toLocaleTimeString()} • {batch.total_items} Content Assets
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2.5">
                    {batch.status !== "COMPLETED" && (
                      <button
                        onClick={() => handleRunBatch(batch.id)}
                        disabled={runningBatchId === batch.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 text-white rounded-lg text-xs font-medium hover:bg-teal-700 transition"
                      >
                        <Play className="w-3.5 h-3.5" />
                        {runningBatchId === batch.id ? "Auditing..." : "Run Audit"}
                      </button>
                    )}
                    <button
                      onClick={() => handleExportReport(batch.id, batch.title)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50 transition"
                    >
                      <Download className="w-3.5 h-3.5 text-slate-400" />
                      Executive Report
                    </button>
                  </div>
                </div>

                {/* Score & Risk Summary Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-slate-100 border-b border-slate-100">
                  <div className="p-5 flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg border ${
                      batch.aggregate_score >= 85
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : batch.aggregate_score >= 70
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : "bg-rose-50 text-rose-700 border-rose-200"
                    }`}>
                      {batch.aggregate_score.toFixed(0)}%
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 font-medium">Readiness Index</div>
                      <div className="text-sm font-semibold text-slate-900">
                        {batch.aggregate_score >= 85 ? "Safe to Publish" : "Remediation Needed"}
                      </div>
                    </div>
                  </div>

                  <div className="p-5 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center font-semibold">
                      {batch.completed_items}/{batch.total_items}
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 font-medium">Processed Items</div>
                      <div className="text-sm font-semibold text-slate-900">
                        {batch.status === "COMPLETED" ? "100% Verified" : "Processing"}
                      </div>
                    </div>
                  </div>

                  <div className="p-5 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-rose-50 text-rose-700 border border-rose-100 flex items-center justify-center font-semibold">
                      {batch.critical_violations}
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 font-medium">Critical Violations</div>
                      <div className="text-sm font-semibold text-slate-900">
                        {batch.critical_violations === 0 ? "Zero Blocker" : "Must Resolve"}
                      </div>
                    </div>
                  </div>

                  <div className="p-5 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-700 border border-amber-100 flex items-center justify-center font-semibold">
                      {batch.warning_violations}
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 font-medium">Warnings & Drift</div>
                      <div className="text-sm font-semibold text-slate-900">
                        {batch.warning_violations} Advisory Items
                      </div>
                    </div>
                  </div>
                </div>

                {/* Submissions in this batch */}
                <div className="p-6">
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">
                    Audited Content Assets ({batch.items?.length || 0})
                  </h3>

                  <div className="space-y-3">
                    {batch.items && batch.items.length > 0 ? (
                      batch.items.map((item, idx) => (
                        <div
                          key={item.submission_id || idx}
                          className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-lg border border-slate-100 hover:border-slate-200 bg-slate-50/30 gap-3"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded bg-white border border-slate-200 flex items-center justify-center text-slate-400">
                              <FileText className="w-4 h-4" />
                            </div>
                            <div>
                              <div className="text-sm font-semibold text-slate-900">{item.title}</div>
                              <div className="text-xs text-slate-500 flex items-center gap-2">
                                <span>Status: {item.status}</span>
                                <span>•</span>
                                <span>{item.total_findings} total findings</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-4">
                            {/* Score pill */}
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-slate-500 font-medium">Score:</span>
                              <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                                item.readiness_score >= 85
                                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                                  : item.readiness_score >= 70
                                  ? "bg-amber-50 text-amber-800 border border-amber-200"
                                  : "bg-rose-50 text-rose-800 border border-rose-200"
                              }`}>
                                {item.readiness_score.toFixed(0)}%
                              </span>
                            </div>

                            {/* View Diff Link */}
                            <Link
                              href={`/audits/${item.submission_id}`}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 transition"
                            >
                              <span>Diff Workspace</span>
                              <ExternalLink className="w-3 h-3 text-slate-400" />
                            </Link>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-500 italic">No asset items found in this batch.</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modal: Create Campaign Batch */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 overflow-y-auto">
            <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 space-y-6 my-8">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-950 flex items-center gap-2">
                    <Boxes className="w-5 h-5 text-teal-600" />
                    New Campaign Batch
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Batch-upload marketing copy, social ads, and announcements for unified pre-publication audit.
                  </p>
                </div>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateBatch} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Campaign Title *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Q3 Omni-Channel Product Launch"
                      value={batchTitle}
                      onChange={(e) => setBatchTitle(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Campaign Tag (Optional)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. q3-launch-2026"
                      value={campaignTag}
                      onChange={(e) => setCampaignTag(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                    />
                  </div>
                </div>

                {/* Items */}
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Content Assets ({items.length})
                    </label>
                    <button
                      type="button"
                      onClick={handleAddItem}
                      disabled={items.length >= 10}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-teal-600 hover:text-teal-700"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add Asset
                    </button>
                  </div>

                  {items.map((it, idx) => (
                    <div key={idx} className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <input
                          type="text"
                          required
                          placeholder="Asset Title (e.g. Press Release, Social Ad)"
                          value={it.title}
                          onChange={(e) => handleItemChange(idx, "title", e.target.value)}
                          className="w-full px-2.5 py-1.5 text-xs font-semibold border border-slate-200 rounded bg-white focus:outline-none focus:ring-1 focus:ring-teal-500"
                        />
                        {items.length > 1 && (
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(idx)}
                            className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded"
                            title="Remove Asset"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                      <textarea
                        required
                        rows={3}
                        placeholder="Paste asset text or marketing copy here..."
                        value={it.content}
                        onChange={(e) => handleItemChange(idx, "content", e.target.value)}
                        className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded bg-white focus:outline-none focus:ring-1 focus:ring-teal-500"
                      />
                    </div>
                  ))}
                </div>

                {/* Submit Actions */}
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="inline-flex items-center gap-2 px-5 py-2 bg-slate-900 text-white rounded-lg text-sm font-semibold hover:bg-slate-800 transition disabled:opacity-50"
                  >
                    {submitting ? "Auditing Batch..." : "Queue & Audit Batch"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
