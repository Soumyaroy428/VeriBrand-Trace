"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  History,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Filter,
  ArrowRight,
  ShieldAlert,
  FileText,
  MessageSquare,
  Sparkles,
  RefreshCw,
  Search,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

interface ReviewQueueItem {
  submission_id: string;
  title: string;
  creator_id: string;
  creator_email?: string;
  format: string;
  current_status: string;
  revision_count: number;
  latest_revision_id: string;
  readiness_score?: number | null;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  pending_exceptions: number;
  comments_count: number;
  updated_at: string;
}

export default function ReviewQueuePage() {
  const { activeWorkspace, token, user } = useAuth();
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    setError(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";

    try {
      const res = await fetch(
        `${apiUrl}/workspaces/${activeWorkspace.workspace_id}/reviews/queue?status_filter=${filterStatus}`,
        {
          headers: {
            Authorization: `Bearer ${token || ""}`,
          },
        }
      );

      if (!res.ok) {
        throw new Error(`Failed to load queue (HTTP ${res.status})`);
      }

      const data = await res.json();
      setItems(data.items || []);
    } catch (err: any) {
      console.warn("Falling back to demo review queue items:", err);
      // Demo fallback so reviewers can interact even offline
      setItems([
        {
          submission_id: "demo-sub-1",
          title: "Q4 Enterprise Security Launch Press Release",
          creator_id: "usr-creator-1",
          creator_email: "creator@acme.com",
          format: "TEXT",
          current_status: "PENDING_REVIEW",
          revision_count: 2,
          latest_revision_id: "rev-2",
          readiness_score: 88,
          critical_findings: 0,
          high_findings: 1,
          medium_findings: 1,
          low_findings: 2,
          pending_exceptions: 1,
          comments_count: 2,
          updated_at: new Date(Date.now() - 3600000 * 2).toISOString(),
        },
        {
          submission_id: "demo-sub-2",
          title: "APAC Product Brochure & Spec Sheet",
          creator_id: "usr-creator-2",
          creator_email: "marketing.lead@acme.com",
          format: "PDF",
          current_status: "NEEDS_CHANGES",
          revision_count: 1,
          latest_revision_id: "rev-1",
          readiness_score: 65,
          critical_findings: 1,
          high_findings: 2,
          medium_findings: 3,
          low_findings: 1,
          pending_exceptions: 0,
          comments_count: 4,
          updated_at: new Date(Date.now() - 3600000 * 8).toISOString(),
        },
        {
          submission_id: "demo-sub-3",
          title: "Customer Case Study: Global FinTech Migration",
          creator_id: "usr-creator-1",
          creator_email: "creator@acme.com",
          format: "DOCX",
          current_status: "PENDING_REVIEW",
          revision_count: 1,
          latest_revision_id: "rev-1",
          readiness_score: 94,
          critical_findings: 0,
          high_findings: 0,
          medium_findings: 1,
          low_findings: 1,
          pending_exceptions: 0,
          comments_count: 1,
          updated_at: new Date(Date.now() - 3600000 * 24).toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [activeWorkspace, filterStatus, token]);

  const filteredItems = items.filter((item) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      (item.creator_email && item.creator_email.toLowerCase().includes(q))
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Approved
          </span>
        );
      case "NEEDS_CHANGES":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Needs Changes
          </span>
        );
      case "PENDING_REVIEW":
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-100 text-sky-800 border border-sky-300">
            <Clock className="w-3.5 h-3.5 mr-1" /> Pending Review
          </span>
        );
    }
  };

  const getScoreBadge = (score?: number | null) => {
    if (score === undefined || score === null) {
      return <span className="text-xs text-slate-400 font-mono">Unrated</span>;
    }
    let color = "text-emerald-700 bg-emerald-50 border-emerald-200";
    if (score < 70) color = "text-rose-700 bg-rose-50 border-rose-200";
    else if (score < 85) color = "text-amber-700 bg-amber-50 border-amber-200";

    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-md font-mono text-xs font-bold border ${color}`}>
        {score}%
      </span>
    );
  };

  return (
    <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-sm text-slate-400 font-medium">
              <Link href="/" className="hover:text-slate-200">Home</Link>
              <span>/</span>
              <span className="text-white font-semibold">Reviewer Queue</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
              Reviewer Governance Queue
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Inspect pending brand submissions, review explainable diffs, decide on creator exception requests, and execute official sign-off with cryptographic compliance certificates.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={fetchQueue}
              className="inline-flex items-center px-3.5 py-2 border border-slate-700 shadow-sm text-sm font-medium rounded-lg text-slate-300 bg-white hover:bg-[#080c14] transition"
            >
              <RefreshCw className={`w-4 h-4 mr-2 text-slate-400 ${loading ? "animate-spin" : ""}`} />
              Refresh Queue
            </button>
            <Link
              href="/audits/new"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-semibold rounded-lg shadow-sm text-white bg-slate-900 hover:bg-slate-800 transition"
            >
              <Sparkles className="w-4 h-4 mr-1.5 text-teal-400" />
              New Audit
            </Link>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="bg-[#0e1320] rounded-2xl border border-slate-800 p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider flex items-center mr-1">
              <Filter className="w-3.5 h-3.5 mr-1" /> Filter:
            </span>
            <button
              onClick={() => setFilterStatus("ALL")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                filterStatus === "ALL"
                  ? "bg-teal-500 text-slate-950 font-bold shadow-sm"
                  : "bg-slate-100 text-slate-400 hover:bg-slate-700"
              }`}
            >
              All Items
            </button>
            <button
              onClick={() => setFilterStatus("PENDING_REVIEW")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                filterStatus === "PENDING_REVIEW"
                  ? "bg-sky-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-400 hover:bg-slate-700"
              }`}
            >
              Pending Review
            </button>
            <button
              onClick={() => setFilterStatus("NEEDS_CHANGES")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                filterStatus === "NEEDS_CHANGES"
                  ? "bg-amber-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-400 hover:bg-slate-700"
              }`}
            >
              Needs Changes
            </button>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search submissions or creators..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-[#080c14] border border-slate-800 rounded-lg text-xs text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white"
            />
          </div>
        </div>

        {/* Queue Table */}
        <div className="bg-[#0e1320] rounded-2xl border border-slate-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-800">
              <thead className="bg-[#080c14]">
                <tr>
                  <th scope="col" className="px-6 py-3.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Submission
                  </th>
                  <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Readiness Score
                  </th>
                  <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Traceable Violations
                  </th>
                  <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Exceptions & Comments
                  </th>
                  <th scope="col" className="px-6 py-3.5 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-white">
                {loading && items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400 text-sm">
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <RefreshCw className="w-6 h-6 animate-spin text-slate-400" />
                        <span>Loading reviewer queue...</span>
                      </div>
                    </td>
                  </tr>
                ) : filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400 text-sm">
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                        <span className="font-semibold text-slate-200">Queue is Clear</span>
                        <span className="text-xs text-slate-400">No submissions currently match the active filter.</span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item) => (
                    <tr key={item.submission_id} className="hover:bg-[#080c14]/80 transition group">
                      <td className="px-6 py-4">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-semibold text-sm text-white group-hover:text-teal-400 transition">
                              {item.title}
                            </span>
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-400 border border-slate-800">
                              v{item.revision_count}
                            </span>
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-300">
                              {item.format}
                            </span>
                          </div>
                          <div className="text-xs text-slate-400">
                            Submitted by <span className="font-medium text-slate-300">{item.creator_email || item.creator_id}</span>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-4 whitespace-nowrap">
                        {getStatusBadge(item.current_status)}
                      </td>

                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {getScoreBadge(item.readiness_score)}
                          {item.readiness_score !== undefined && item.readiness_score !== null && (
                            <span className="text-[11px] text-slate-400 font-medium">
                              {item.readiness_score >= 85 ? "Passing" : "Needs Review"}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-1.5 text-xs font-mono">
                          {item.critical_findings > 0 && (
                            <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-bold border border-rose-200" title="Critical Findings">
                              {item.critical_findings} crit
                            </span>
                          )}
                          {item.high_findings > 0 && (
                            <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold border border-amber-200" title="High Findings">
                              {item.high_findings} high
                            </span>
                          )}
                          {item.medium_findings > 0 && (
                            <span className="px-2 py-0.5 rounded bg-yellow-100 text-yellow-800 font-medium" title="Medium Findings">
                              {item.medium_findings} med
                            </span>
                          )}
                          {item.critical_findings === 0 && item.high_findings === 0 && item.medium_findings === 0 && (
                            <span className="text-emerald-600 font-sans font-medium text-xs flex items-center">
                              <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Clean
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {item.pending_exceptions > 0 ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                              <ShieldAlert className="w-3.5 h-3.5 mr-1" /> {item.pending_exceptions} Exception{item.pending_exceptions > 1 ? "s" : ""}
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}

                          {item.comments_count > 0 && (
                            <span className="inline-flex items-center text-xs text-slate-400">
                              <MessageSquare className="w-3.5 h-3.5 mr-1 text-slate-400" />
                              {item.comments_count}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <Link
                          href={`/audits/${item.submission_id}`}
                          className="inline-flex items-center px-3 py-1.5 border border-slate-800 text-xs font-semibold rounded-lg text-slate-200 bg-white hover:bg-slate-100 hover:border-slate-700 shadow-sm transition"
                        >
                          Review & Decide
                          <ArrowRight className="w-3.5 h-3.5 ml-1 text-slate-400" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Governance Guidelines Box */}
        <div className="rounded-xl border border-slate-800 bg-[#0e1320] p-5 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-white flex items-center">
              <ShieldAlert className="w-4 h-4 mr-1.5 text-teal-400" />
              VeriBrand Trace Governance Sign-off Rules
            </h4>
            <p className="text-xs text-slate-400 max-w-3xl">
              Formal approval requires a minimum Brand Readiness Score of <strong>85%</strong> or approved exceptions for all open critical/high findings. Creators cannot approve their own submissions. All approvals issue a mathematically verifiable compliance certificate with tamper-evident SHA-256 hash chaining.
            </p>
          </div>
          <Link
            href="/governance"
            className="text-xs font-semibold text-teal-400 hover:text-teal-800 whitespace-nowrap flex items-center"
          >
            View Governance Analytics &rarr;
          </Link>
        </div>
    </div>
  );
}
