"use client";

import React, { useState, useEffect } from "react";
import {
  Layers,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Palette,
  FolderOpen,
  Plus,
  Shield,
  Search,
  Hash,
  ExternalLink,
  Info,
  Clock,
  Sparkles,
  BookOpen,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

type TabType = "guidelines" | "facts" | "terminology" | "visual" | "assets";

// Fallback seed data matching server/app/core/seed.py for instant client preview
const SEED_GUIDELINES = [
  {
    id: "g-001",
    title: "Acme Global Master Brand Identity & Voice Guide 2026",
    file_name: "acme-brand-voice-2026.md",
    storage_key: "guidelines/acme-brand-voice-2026.md",
    content_hash: "a4f89d31e9c9b1392e927fa1103982df4b988f01",
    version: 1,
    status: "ACTIVE",
    chunk_count: 8,
    created_at: "2026-11-01T10:00:00Z",
  },
  {
    id: "g-002",
    title: "Q3 Sustainability & ESG Disclosure Directives",
    file_name: "esg-disclosure-q3.pdf",
    storage_key: "guidelines/esg-disclosure-q3.pdf",
    content_hash: "d9e18b827361ab8942cd894103197ecbb209829f",
    version: 2,
    status: "ACTIVE",
    chunk_count: 5,
    created_at: "2026-11-03T14:30:00Z",
  },
];

const SEED_FACTS = [
  {
    id: "f-001",
    fact_key: "revenue_q3_2026",
    statement: "Acme Global generated $122.5M in audited recurring revenue in Q3 2026.",
    version: 1,
    status: "ACTIVE",
    source_reference: "SEC 10-Q Quarterly Filing, pg 14",
    created_at: "2026-11-02T09:15:00Z",
  },
  {
    id: "f-002",
    fact_key: "carbon_neutral_goal",
    statement: "Acme operations achieve net-zero carbon neutrality by 2030 across Scope 1 and Scope 2 emissions.",
    version: 2,
    status: "ACTIVE",
    source_reference: "2026 Environmental Impact Report, Clause 3.2",
    created_at: "2026-11-02T09:20:00Z",
  },
  {
    id: "f-003",
    fact_key: "customer_count_2026",
    statement: "Acme serves over 15,000 enterprise customers across 42 countries worldwide.",
    version: 1,
    status: "ACTIVE",
    source_reference: "Q3 2026 Corporate Factsheet, pg 1",
    created_at: "2026-11-04T11:00:00Z",
  },
];

const SEED_TERMINOLOGY = [
  {
    id: "t-001",
    term: "unbreakable security",
    rule_type: "BANNED",
    replacement: "industry-leading defense-in-depth architecture",
    guideline_reference: "FTC Section 5 Deceptive Advertising Compliance",
    severity: "CRITICAL",
    case_sensitive: false,
    whole_word: true,
    active: true,
  },
  {
    id: "t-002",
    term: "guaranteed 100% uptime",
    rule_type: "BANNED",
    replacement: "99.99% contractual service availability",
    guideline_reference: "SLA Terms of Service Agreement §4",
    severity: "HIGH",
    case_sensitive: false,
    whole_word: true,
    active: true,
  },
  {
    id: "t-003",
    term: "AI replaces humans",
    rule_type: "REPLACEMENT",
    replacement: "AI augments and empowers human decision-making",
    guideline_reference: "Ethical AI Principles & Positioning Charter",
    severity: "MEDIUM",
    case_sensitive: false,
    whole_word: true,
    active: true,
  },
];

const SEED_VISUAL = [
  {
    id: "v-001",
    rule_type: "COLOR_PALETTE",
    rule_config: {
      name: "Acme Primary Teal",
      color_hex: "#0D9488",
      tolerance_delta_e: 2.0,
      min_contrast_ratio: 4.5,
    },
    severity: "HIGH",
    source_reference: "Design System Tokens v4.2",
    active: true,
  },
  {
    id: "v-002",
    rule_type: "COLOR_PALETTE",
    rule_config: {
      name: "Slate Foundation Dark",
      color_hex: "#0F172A",
      tolerance_delta_e: 2.5,
      min_contrast_ratio: 7.0,
    },
    severity: "HIGH",
    source_reference: "Design System Tokens v4.2",
    active: true,
  },
  {
    id: "v-003",
    rule_type: "CONTRAST_RATIO",
    rule_config: {
      name: "WCAG 2.1 AA Normal Text",
      min_contrast_ratio: 4.5,
    },
    severity: "CRITICAL",
    source_reference: "WCAG 2.1 Success Criterion 1.4.3",
    active: true,
  },
];

const SEED_ASSETS = [
  {
    id: "a-001",
    name: "Acme Master Brand Mark (SVG)",
    asset_type: "LOGO",
    storage_key: "assets/logos/acme-master-dark.svg",
    file_hash: "7e83921af78921b34cd89123fe41098273619284",
    active: true,
    created_at: "2026-11-01T12:00:00Z",
  },
  {
    id: "a-002",
    name: "Acme Monogram App Icon (PNG 512px)",
    asset_type: "ICON",
    storage_key: "assets/icons/acme-icon-512.png",
    file_hash: "298319fbc9219830219840192837190283719028",
    active: true,
    created_at: "2026-11-02T15:00:00Z",
  },
];

export default function BrandVaultPage() {
  const { activeWorkspace, token } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>("guidelines");
  const [searchQuery, setSearchQuery] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Live state with seed defaults
  const [guidelines, setGuidelines] = useState(SEED_GUIDELINES);
  const [facts, setFacts] = useState(SEED_FACTS);
  const [terminology, setTerminology] = useState(SEED_TERMINOLOGY);
  const [visualRules, setVisualRules] = useState(SEED_VISUAL);
  const [assets, setAssets] = useState(SEED_ASSETS);

  // New Fact Form state
  const [newFactKey, setNewFactKey] = useState("");
  const [newFactStatement, setNewFactStatement] = useState("");
  const [newFactSource, setNewFactSource] = useState("");

  const isAdmin = activeWorkspace?.role === "GOVERNANCE_ADMIN";
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

  // Attempt fetching live data from backend if workspace is available
  useEffect(() => {
    if (!activeWorkspace?.workspace_id || !token) return;

    const fetchVaultData = async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const wsId = activeWorkspace.workspace_id;

        const [gRes, fRes, tRes, vRes, aRes] = await Promise.all([
          fetch(`${API_BASE}/workspaces/${wsId}/guidelines`, { headers }).catch(() => null),
          fetch(`${API_BASE}/workspaces/${wsId}/facts`, { headers }).catch(() => null),
          fetch(`${API_BASE}/workspaces/${wsId}/terminology-rules`, { headers }).catch(() => null),
          fetch(`${API_BASE}/workspaces/${wsId}/visual-rules`, { headers }).catch(() => null),
          fetch(`${API_BASE}/workspaces/${wsId}/assets`, { headers }).catch(() => null),
        ]);

        if (gRes?.ok) {
          const data = await gRes.json();
          if (data && data.length > 0) setGuidelines(data);
        }
        if (fRes?.ok) {
          const data = await fRes.json();
          if (data && data.length > 0) setFacts(data);
        }
        if (tRes?.ok) {
          const data = await tRes.json();
          if (data && data.length > 0) setTerminology(data);
        }
        if (vRes?.ok) {
          const data = await vRes.json();
          if (data && data.length > 0) setVisualRules(data);
        }
        if (aRes?.ok) {
          const data = await aRes.json();
          if (data && data.length > 0) setAssets(data);
        }
      } catch {
        // Fallback gracefully to demo seed data
      }
    };

    fetchVaultData();
  }, [activeWorkspace?.workspace_id, token, API_BASE]);

  const handleCreateFact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFactKey || !newFactStatement) return;

    const newFact = {
      id: `f-${Date.now()}`,
      fact_key: newFactKey,
      statement: newFactStatement,
      source_reference: newFactSource || "Approved by Governance Admin",
      version: 1,
      status: "ACTIVE",
      created_at: new Date().toISOString(),
    };

    // Optimistic UI update
    setFacts([newFact, ...facts]);
    setIsModalOpen(false);
    setNewFactKey("");
    setNewFactStatement("");
    setNewFactSource("");

    // Send to backend if connected
    if (activeWorkspace?.workspace_id && token) {
      try {
        await fetch(`${API_BASE}/workspaces/${activeWorkspace.workspace_id}/facts`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            fact_key: newFactKey,
            statement: newFactStatement,
            source_reference: newFactSource,
          }),
        });
      } catch {
        // Optimistic state remains
      }
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-7 h-7 rounded-md bg-teal-600/10 border border-teal-600/20 flex items-center justify-center text-teal-700">
              <Layers className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Brand Vault</h1>
          </div>
          <p className="text-sm text-slate-500">
            Immutable guideline registry, approved facts, terminology boundaries, and visual standards for{" "}
            <strong className="text-slate-800">{activeWorkspace?.workspace_name || "Acme Global"}</strong>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isAdmin ? (
            <button
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              <span>Add Approved Fact</span>
            </button>
          ) : (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-600 text-xs font-medium">
              <Shield className="w-3.5 h-3.5 text-slate-400" />
              <span>Read-Only View ({activeWorkspace?.role || "CREATOR"})</span>
            </div>
          )}
        </div>
      </div>

      {/* Permissions Callout if not Admin */}
      {!isAdmin && (
        <div className="p-3.5 rounded-lg bg-amber-50/70 border border-amber-200/80 text-amber-900 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              You are currently signed in with <strong>{activeWorkspace?.role}</strong> permissions. Brand Vault modifications are restricted to <strong>Governance Admins</strong>. Switch persona in the navbar to test admin editing.
            </span>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6">
          <button
            onClick={() => setActiveTab("guidelines")}
            className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
              activeTab === "guidelines"
                ? "border-teal-600 text-teal-700 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Guidelines ({guidelines.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("facts")}
            className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
              activeTab === "facts"
                ? "border-teal-600 text-teal-700 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Approved Facts ({facts.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("terminology")}
            className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
              activeTab === "terminology"
                ? "border-teal-600 text-teal-700 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            <span>Terminology Rules ({terminology.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("visual")}
            className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
              activeTab === "visual"
                ? "border-teal-600 text-teal-700 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
            }`}
          >
            <Palette className="w-4 h-4" />
            <span>Visual Standards ({visualRules.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("assets")}
            className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
              activeTab === "assets"
                ? "border-teal-600 text-teal-700 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
            }`}
          >
            <FolderOpen className="w-4 h-4" />
            <span>Brand Assets ({assets.length})</span>
          </button>
        </nav>
      </div>

      {/* Tab 1: Guidelines Registry */}
      {activeTab === "guidelines" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span>Official brand documentation ingested and indexed for vector RAG retrieval.</span>
            <span>Total chunks: {guidelines.reduce((acc, g) => acc + (g.chunk_count || 0), 0)}</span>
          </div>

          <div className="grid gap-3">
            {guidelines.map((doc) => (
              <div
                key={doc.id}
                className="p-5 bg-white border border-slate-200 rounded-xl hover:border-slate-300 transition shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2.5">
                    <span className="font-semibold text-slate-900 text-sm">{doc.title}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-600 border border-slate-200">
                      v{doc.version}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {doc.status}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span className="flex items-center gap-1 font-mono text-[11px]">
                      <FileText className="w-3.5 h-3.5 text-slate-400" />
                      {doc.file_name}
                    </span>
                    <span className="flex items-center gap-1 font-mono text-[11px]">
                      <Hash className="w-3.5 h-3.5 text-slate-400" />
                      {doc.content_hash.slice(0, 16)}...
                    </span>
                    <span className="flex items-center gap-1 text-[11px]">
                      <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                      {doc.chunk_count} RAG chunks
                    </span>
                  </div>
                </div>

                <div className="shrink-0 flex items-center gap-2">
                  <button className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition flex items-center gap-1">
                    <span>Inspect Chunks</span>
                    <ExternalLink className="w-3 h-3 text-slate-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Approved Facts Registry */}
      {activeTab === "facts" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Audited corporate statements used to verify quantitative and historical marketing claims.
            </span>
            <div className="relative w-64">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search approved facts..."
                className="w-full pl-8 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
            </div>
          </div>

          <div className="grid gap-3">
            {facts
              .filter(
                (f) =>
                  !searchQuery ||
                  f.fact_key.toLowerCase().includes(searchQuery.toLowerCase()) ||
                  f.statement.toLowerCase().includes(searchQuery.toLowerCase())
              )
              .map((fact) => (
                <div
                  key={fact.id}
                  className="p-5 bg-white border border-slate-200 rounded-xl hover:border-slate-300 transition shadow-sm space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-teal-50 text-teal-800 border border-teal-200">
                        {fact.fact_key}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-slate-500 border border-slate-200">
                        v{fact.version}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {fact.status}
                      </span>
                    </div>

                    <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3" />
                      {new Date(fact.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <p className="text-sm font-medium text-slate-900 leading-relaxed">{fact.statement}</p>

                  {fact.source_reference && (
                    <div className="text-xs text-slate-500 flex items-center gap-1.5 pt-1 border-t border-slate-100">
                      <span className="font-semibold text-slate-700">Source Evidence:</span>
                      <span className="italic">{fact.source_reference}</span>
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Tab 3: Terminology Rules */}
      {activeTab === "terminology" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Deterministic dictionary enforcing banned claims, preferred jargon, and compliance replacements.</span>
          </div>

          <div className="grid gap-3">
            {terminology.map((rule) => (
              <div
                key={rule.id}
                className="p-5 bg-white border border-slate-200 rounded-xl hover:border-slate-300 transition shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase ${
                        rule.rule_type === "BANNED"
                          ? "bg-rose-50 text-rose-700 border border-rose-200"
                          : "bg-amber-50 text-amber-700 border border-amber-200"
                      }`}
                    >
                      {rule.rule_type}
                    </span>
                    <span className="font-semibold text-slate-900 text-sm font-mono">&ldquo;{rule.term}&rdquo;</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 uppercase">
                      {rule.severity}
                    </span>
                  </div>

                  {rule.replacement && (
                    <div className="text-xs text-slate-700 flex items-center gap-2">
                      <span className="text-slate-400 font-medium">Approved Replacement:</span>
                      <strong className="text-teal-700">&ldquo;{rule.replacement}&rdquo;</strong>
                    </div>
                  )}

                  {rule.guideline_reference && (
                    <div className="text-xs text-slate-500 italic">
                      Policy rationale: {rule.guideline_reference}
                    </div>
                  )}
                </div>

                <div className="shrink-0 flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                  <span>Match: {rule.whole_word ? "Whole word" : "Partial"}</span>
                  <span>&bull;</span>
                  <span>{rule.case_sensitive ? "Case-sensitive" : "Case-insensitive"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: Visual Standards */}
      {activeTab === "visual" && (
        <div className="space-y-4">
          <div className="text-xs text-slate-500">
            Approved color palettes, CIEDE2000 Delta-E tolerances, and WCAG contrast ratio requirements.
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {visualRules.map((rule) => {
              const cfg = rule.rule_config || {};
              return (
                <div
                  key={rule.id}
                  className="p-5 bg-white border border-slate-200 rounded-xl hover:border-slate-300 transition shadow-sm space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-800 uppercase tracking-wide">
                      {rule.rule_type.replace("_", " ")}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                      {rule.severity}
                    </span>
                  </div>

                  {cfg.color_hex && (
                    <div className="flex items-center gap-3">
                      <div
                        className="w-12 h-12 rounded-lg border border-slate-300 shadow-inner shrink-0"
                        style={{ backgroundColor: cfg.color_hex }}
                      />
                      <div>
                        <div className="font-semibold text-slate-900 text-sm">{cfg.name || "Brand Color"}</div>
                        <div className="font-mono text-xs text-slate-500">{cfg.color_hex}</div>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-100 font-mono">
                    {cfg.tolerance_delta_e !== undefined && (
                      <div className="p-2 bg-slate-50 rounded-lg">
                        <span className="text-[10px] text-slate-400 block uppercase">Max Delta-E</span>
                        <strong className="text-slate-800 text-xs">&le; {cfg.tolerance_delta_e}</strong>
                      </div>
                    )}
                    {cfg.min_contrast_ratio !== undefined && (
                      <div className="p-2 bg-slate-50 rounded-lg">
                        <span className="text-[10px] text-slate-400 block uppercase">Min Contrast</span>
                        <strong className="text-slate-800 text-xs">&ge; {cfg.min_contrast_ratio}:1</strong>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 5: Brand Assets */}
      {activeTab === "assets" && (
        <div className="space-y-4">
          <div className="text-xs text-slate-500">
            Registered digital brand assets, logos, and vector marks stored for reference validation.
          </div>

          <div className="grid sm:grid-cols-2 gap-3">
            {assets.map((asset) => (
              <div
                key={asset.id}
                className="p-5 bg-white border border-slate-200 rounded-xl hover:border-slate-300 transition shadow-sm space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-900 text-sm">{asset.name}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-600 border border-slate-200">
                    {asset.asset_type}
                  </span>
                </div>

                <div className="text-xs text-slate-500 font-mono truncate">{asset.storage_key}</div>

                <div className="text-[11px] text-slate-400 font-mono pt-2 border-t border-slate-100 flex items-center justify-between">
                  <span>SHA-256: {asset.file_hash.slice(0, 16)}...</span>
                  <span className="text-emerald-600 font-medium">Verified Active</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal: Add Approved Fact (Admin only) */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="font-bold text-slate-900 text-base">Add Approved Corporate Fact</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateFact} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Fact Key (Unique Identifier)
                </label>
                <input
                  type="text"
                  required
                  value={newFactKey}
                  onChange={(e) => setNewFactKey(e.target.value)}
                  placeholder="e.g. q4_net_retention"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Audited Fact Statement
                </label>
                <textarea
                  required
                  rows={3}
                  value={newFactStatement}
                  onChange={(e) => setNewFactStatement(e.target.value)}
                  placeholder="e.g. Acme achieved 118% Net Revenue Retention in FY2026."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Source Reference / Filing Citation
                </label>
                <input
                  type="text"
                  value={newFactSource}
                  onChange={(e) => setNewFactSource(e.target.value)}
                  placeholder="e.g. FY2026 Annual Shareholder Letter, Section 2"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div className="pt-4 flex items-center justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-200 text-slate-700 text-xs font-medium hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-medium shadow-sm transition"
                >
                  Save Fact to Registry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

