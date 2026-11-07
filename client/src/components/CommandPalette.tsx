"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  FileCheck,
  FileText,
  Layers,
  History,
  BarChart3,
  Lock,
  Boxes,
  Activity,
  User,
  ShieldCheck,
  ArrowRight,
  ExternalLink,
  Sparkles,
  X,
} from "lucide-react";
import { useAuth, RoleType } from "@/context/AuthContext";

interface CommandItem {
  id: string;
  category: "Navigation" | "Personas" | "Actions";
  title: string;
  description: string;
  icon: React.ReactNode;
  action: () => void;
  badge?: string;
}

export default function CommandPalette({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const { switchDemoRole, activeWorkspace } = useAuth();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
      setQuery("");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const commands: CommandItem[] = [
    // Navigation
    {
      id: "nav-overview",
      category: "Navigation",
      title: "Overview & Dashboard",
      description: "Return to the central command dashboard & live engine",
      icon: <Sparkles className="w-4 h-4 text-teal-400" />,
      action: () => {
        router.push("/");
        onClose();
      },
    },
    {
      id: "nav-new-audit",
      category: "Navigation",
      title: "New Content Audit",
      description: "Upload copy, docx, pdf or images for Privacy Gate & compliance check",
      icon: <FileCheck className="w-4 h-4 text-emerald-400" />,
      action: () => {
        router.push("/audits/new");
        onClose();
      },
      badge: "Quick Start",
    },
    {
      id: "nav-audits",
      category: "Navigation",
      title: "All Submissions & Audits",
      description: "Inspect submitted assets, revisions, and sanitization logs",
      icon: <FileText className="w-4 h-4 text-sky-400" />,
      action: () => {
        router.push("/audits");
        onClose();
      },
    },
    {
      id: "nav-review",
      category: "Navigation",
      title: "Review Queue",
      description: "Side-by-side human diffing, exception handling & sign-off",
      icon: <History className="w-4 h-4 text-amber-400" />,
      action: () => {
        router.push("/review");
        onClose();
      },
      badge: "Action Required",
    },
    {
      id: "nav-vault",
      category: "Navigation",
      title: "Brand Vault",
      description: "Brand guidelines, approved facts, banned terms, and visual rules",
      icon: <Layers className="w-4 h-4 text-purple-400" />,
      action: () => {
        router.push("/brand-vault");
        onClose();
      },
    },
    {
      id: "nav-batches",
      category: "Navigation",
      title: "Campaign Batches",
      description: "Multi-channel marketing concurrent batch compliance checks",
      icon: <Boxes className="w-4 h-4 text-cyan-400" />,
      action: () => {
        router.push("/batches");
        onClose();
      },
    },
    {
      id: "nav-governance",
      category: "Navigation",
      title: "Governance Intelligence",
      description: "Workspace analytics, rule drift diagnostics, readiness trends",
      icon: <BarChart3 className="w-4 h-4 text-rose-400" />,
      action: () => {
        router.push("/governance");
        onClose();
      },
    },
    {
      id: "nav-ledger",
      category: "Navigation",
      title: "Tamper-Evident Audit Ledger",
      description: "SHA-256 cryptographic immutable history of every brand decision",
      icon: <Lock className="w-4 h-4 text-teal-400" />,
      action: () => {
        router.push("/audit-trail");
        onClose();
      },
    },
    {
      id: "nav-ops",
      category: "Navigation",
      title: "System Operations",
      description: "Service health, pgvector index status & workspace backups",
      icon: <Activity className="w-4 h-4 text-emerald-400" />,
      action: () => {
        router.push("/operations");
        onClose();
      },
    },

    // Personas
    {
      id: "role-creator",
      category: "Personas",
      title: "Switch to Creator (Alice)",
      description: "Submit assets, test copy, request exceptions",
      icon: <User className="w-4 h-4 text-sky-400" />,
      action: () => {
        switchDemoRole("CREATOR");
        onClose();
      },
      badge: activeWorkspace?.role === "CREATOR" ? "Active" : undefined,
    },
    {
      id: "role-reviewer",
      category: "Personas",
      title: "Switch to Reviewer (Bob)",
      description: "Inspect diffs, grant exceptions, issue certificates",
      icon: <ShieldCheck className="w-4 h-4 text-amber-400" />,
      action: () => {
        switchDemoRole("REVIEWER");
        onClose();
      },
      badge: activeWorkspace?.role === "REVIEWER" ? "Active" : undefined,
    },
    {
      id: "role-admin",
      category: "Personas",
      title: "Switch to Governance Admin (Carol)",
      description: "Full Brand Vault editing, rule policy changes & audit export",
      icon: <Lock className="w-4 h-4 text-emerald-400" />,
      action: () => {
        switchDemoRole("GOVERNANCE_ADMIN");
        onClose();
      },
      badge: activeWorkspace?.role === "GOVERNANCE_ADMIN" ? "Active" : undefined,
    },
  ];

  const filteredCommands = commands.filter((cmd) => {
    if (!query.trim()) return true;
    const term = query.toLowerCase();
    return (
      cmd.title.toLowerCase().includes(term) ||
      cmd.description.toLowerCase().includes(term) ||
      cmd.category.toLowerCase().includes(term)
    );
  });

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filteredCommands.length || 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) =>
        prev === 0 ? filteredCommands.length - 1 : prev - 1
      );
    } else if (e.key === "Enter" && filteredCommands[selectedIndex]) {
      e.preventDefault();
      filteredCommands[selectedIndex].action();
    } else if (e.key === "Escape") {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl bg-[#0e1320] border border-slate-700/80 shadow-2xl overflow-hidden text-slate-100 animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-slate-800 bg-[#141b2d]/50">
          <Search className="w-5 h-5 text-teal-400 mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command, page name, or persona..."
            className="w-full bg-transparent text-sm text-white placeholder-slate-400 focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="p-1 text-slate-400 hover:text-white mr-2"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono font-semibold text-slate-400 bg-slate-800 rounded border border-slate-700">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          {filteredCommands.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-400">
              No matching commands found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            filteredCommands.map((cmd, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <button
                  key={cmd.id}
                  onClick={cmd.action}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full text-left px-3.5 py-2.5 rounded-xl flex items-center justify-between transition ${
                    isSelected
                      ? "bg-teal-500/15 border border-teal-500/30 text-white"
                      : "hover:bg-slate-800/50 text-slate-300 border border-transparent"
                  }`}
                >
                  <div className="flex items-center space-x-3 min-w-0">
                    <div
                      className={`p-2 rounded-lg ${
                        isSelected
                          ? "bg-teal-500/20 text-teal-300"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      {cmd.icon}
                    </div>
                    <div className="min-w-0 truncate">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium truncate">
                          {cmd.title}
                        </span>
                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                          {cmd.category}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 truncate mt-0.5">
                        {cmd.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 shrink-0 ml-3">
                    {cmd.badge && (
                      <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-teal-500/10 text-teal-400 border border-teal-500/30">
                        {cmd.badge}
                      </span>
                    )}
                    <ArrowRight
                      className={`w-3.5 h-3.5 transition ${
                        isSelected
                          ? "text-teal-400 translate-x-0.5"
                          : "text-slate-600"
                      }`}
                    />
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Footer shortcuts helper */}
        <div className="px-4 py-2.5 border-t border-slate-800/80 bg-[#080c14] flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <div className="flex items-center space-x-3">
            <span>
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700 text-slate-300">
                ↑
              </kbd>{" "}
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700 text-slate-300">
                ↓
              </kbd>{" "}
              Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700 text-slate-300">
                ↵
              </kbd>{" "}
              Select
            </span>
          </div>
          <span className="text-teal-400">VeriBrand Trace Sovereign Engine</span>
        </div>
      </div>
    </div>
  );
}
