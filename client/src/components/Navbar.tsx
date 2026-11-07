"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldCheck,
  Layers,
  FileCheck,
  History,
  BarChart3,
  LogOut,
  LogIn,
  ChevronDown,
  Building2,
  Lock,
  Boxes,
  Activity,
  Search,
  Menu,
  X,
  Sparkles,
  FileText,
} from "lucide-react";
import { useAuth, RoleType } from "@/context/AuthContext";
import CommandPalette from "./CommandPalette";

export default function Navbar() {
  const pathname = usePathname();
  const { user, activeWorkspace, workspaces, setActiveWorkspace, switchDemoRole, logout } = useAuth();
  const [wsMenuOpen, setWsMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Keyboard shortcut listener for Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Close menus on route change
  useEffect(() => {
    setMobileMenuOpen(false);
    setWsMenuOpen(false);
    setUserMenuOpen(false);
  }, [pathname]);

  const getRoleBadgeStyle = (role?: RoleType) => {
    switch (role) {
      case "GOVERNANCE_ADMIN":
        return "bg-emerald-500/15 border-emerald-500/30 text-emerald-300";
      case "REVIEWER":
        return "bg-amber-500/15 border-amber-500/30 text-amber-300";
      case "CREATOR":
      default:
        return "bg-sky-500/15 border-sky-500/30 text-sky-300";
    }
  };

  const navLinks = [
    { href: "/", label: "Overview", icon: <Sparkles className="h-4 w-4" /> },
    { href: "/audits/new", label: "New Audit", icon: <FileCheck className="h-4 w-4" /> },
    { href: "/audits", label: "Submissions", icon: <FileText className="h-4 w-4" /> },
    { href: "/review", label: "Review Queue", icon: <History className="h-4 w-4" /> },
    { href: "/brand-vault", label: "Brand Vault", icon: <Layers className="h-4 w-4" /> },
    { href: "/batches", label: "Batches", icon: <Boxes className="h-4 w-4" /> },
    { href: "/governance", label: "Governance", icon: <BarChart3 className="h-4 w-4" /> },
    { href: "/audit-trail", label: "Ledger", icon: <Lock className="h-4 w-4" /> },
    { href: "/operations", label: "Ops", icon: <Activity className="h-4 w-4" /> },
  ];

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-[#080c14]/90 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Status Beacon */}
          <div className="flex items-center space-x-4 lg:space-x-6">
            <Link href="/" className="flex items-center space-x-2.5 group">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-teal-400/20 via-slate-900 to-slate-950 border border-teal-500/30 flex items-center justify-center text-teal-400 shadow-[0_0_15px_rgba(20,184,166,0.2)] group-hover:border-teal-400 group-hover:scale-105 transition-all duration-200">
                <ShieldCheck className="h-5 w-5 text-teal-400 drop-shadow-[0_0_8px_rgba(20,184,166,0.6)]" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center space-x-1.5">
                  <span className="font-bold text-base tracking-tight text-white font-sans">
                    VeriBrand
                  </span>
                  <span className="text-teal-400 font-mono text-sm font-semibold tracking-wider">
                    TRACE
                  </span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                    Governance Active
                  </span>
                </div>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden xl:flex items-center space-x-0.5 text-xs font-medium text-slate-400">
              {navLinks.map((link) => {
                const isActive =
                  link.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`px-2.5 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 ${
                      isActive
                        ? "text-teal-300 bg-teal-500/10 border border-teal-500/25 font-semibold shadow-[0_0_10px_rgba(20,184,166,0.1)]"
                        : "hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
                    }`}
                  >
                    <span className={isActive ? "text-teal-400" : "text-slate-500"}>
                      {link.icon}
                    </span>
                    <span>{link.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Center/Right Toolbar */}
          <div className="flex items-center space-x-2 sm:space-x-3 text-xs">
            {/* Quick Command Palette Button */}
            <button
              onClick={() => setCommandPaletteOpen(true)}
              className="flex items-center space-x-2 px-2.5 py-1.5 rounded-lg border border-slate-800 bg-[#0e1320] hover:border-slate-700 text-slate-400 hover:text-slate-200 transition"
              title="Press ⌘K or Ctrl+K to search"
            >
              <Search className="w-3.5 h-3.5 text-teal-400" />
              <span className="hidden sm:inline text-xs text-slate-400">Search</span>
              <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-400 bg-slate-800/80 rounded border border-slate-700">
                ⌘K
              </kbd>
            </button>

            {/* Fast Persona Switcher (Alice, Bob, Carol) */}
            <div className="hidden lg:flex items-center bg-[#0e1320] p-0.5 rounded-lg border border-slate-800">
              <button
                onClick={() => switchDemoRole("CREATOR")}
                className={`px-2.5 py-1 rounded-md text-[11px] font-mono font-medium transition ${
                  activeWorkspace?.role === "CREATOR"
                    ? "bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Switch to Alice Creator (Drafting & Exception Requests)"
              >
                Creator
              </button>
              <button
                onClick={() => switchDemoRole("REVIEWER")}
                className={`px-2.5 py-1 rounded-md text-[11px] font-mono font-medium transition ${
                  activeWorkspace?.role === "REVIEWER"
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Switch to Bob Reviewer (Diff Review & Sign-Off)"
              >
                Reviewer
              </button>
              <button
                onClick={() => switchDemoRole("GOVERNANCE_ADMIN")}
                className={`px-2.5 py-1 rounded-md text-[11px] font-mono font-medium transition ${
                  activeWorkspace?.role === "GOVERNANCE_ADMIN"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Switch to Carol Admin (Brand Vault & System Config)"
              >
                Admin
              </button>
            </div>

            {/* Workspace Switcher */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setWsMenuOpen(!wsMenuOpen)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-800 bg-[#0e1320] hover:border-slate-700 text-slate-300 hover:text-white transition"
              >
                <Building2 className="w-3.5 h-3.5 text-teal-400" />
                <span className="font-medium truncate max-w-[100px] sm:max-w-[130px]">
                  {activeWorkspace ? activeWorkspace.workspace_name : "Workspace"}
                </span>
                <ChevronDown className="w-3 h-3 text-slate-500" />
              </button>

              {wsMenuOpen && (
                <div className="absolute right-0 mt-1.5 w-60 bg-[#0e1320] border border-slate-700 rounded-xl shadow-2xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100">
                  <div className="px-3 py-1.5 text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                    Switch Workspace
                  </div>
                  {workspaces.map((ws) => (
                    <button
                      key={ws.workspace_id}
                      onClick={() => {
                        setActiveWorkspace(ws.workspace_id);
                        setWsMenuOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-slate-800/60 transition ${
                        activeWorkspace?.workspace_id === ws.workspace_id
                          ? "bg-teal-500/10 font-semibold text-teal-300"
                          : "text-slate-300"
                      }`}
                    >
                      <span className="truncate">{ws.workspace_name}</span>
                      <span className="text-[10px] font-mono uppercase text-slate-400 ml-2">
                        {ws.role.replace("_", " ")}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Role Badge Indicator */}
            <div
              className={`hidden sm:flex items-center px-2 py-0.5 rounded-md border font-mono font-semibold tracking-wide uppercase text-[10px] ${getRoleBadgeStyle(
                activeWorkspace?.role
              )}`}
            >
              {activeWorkspace?.role ? activeWorkspace.role.replace("_", " ") : "Guest"}
            </div>

            {/* User Account / Sign In */}
            {user ? (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-1.5 p-1 rounded-lg hover:bg-slate-800 border border-slate-800 transition"
                >
                  <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-300 border border-teal-500/30 flex items-center justify-center font-bold text-xs">
                    {user.full_name ? user.full_name[0].toUpperCase() : "U"}
                  </div>
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 mt-1.5 w-52 bg-[#0e1320] border border-slate-700 rounded-xl shadow-2xl py-1 z-50">
                    <div className="px-3.5 py-2.5 border-b border-slate-800">
                      <p className="text-xs font-semibold text-white truncate">
                        {user.full_name}
                      </p>
                      <p className="text-[11px] text-slate-400 truncate font-mono">
                        {user.email}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        logout();
                        setUserMenuOpen(false);
                      }}
                      className="w-full text-left px-3.5 py-2 text-xs text-rose-400 hover:bg-rose-500/10 flex items-center gap-2 transition"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link
                href="/login"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold transition shadow-[0_0_15px_rgba(20,184,166,0.25)]"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </Link>
            )}

            {/* Mobile Menu Hamburger Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="xl:hidden p-2 rounded-lg border border-slate-800 bg-[#0e1320] text-slate-400 hover:text-white transition"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Mobile Slide-down Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="xl:hidden border-t border-slate-800 bg-[#080c14] px-4 py-4 space-y-4 animate-in slide-in-from-top-2 duration-150">
            {/* Mobile Persona Switcher */}
            <div className="p-2.5 rounded-xl bg-[#0e1320] border border-slate-800 space-y-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                Active Persona
              </span>
              <div className="grid grid-cols-3 gap-1.5">
                <button
                  onClick={() => switchDemoRole("CREATOR")}
                  className={`py-1.5 text-center text-xs font-mono font-medium rounded-lg border transition ${
                    activeWorkspace?.role === "CREATOR"
                      ? "bg-sky-500/20 text-sky-300 border-sky-500/40"
                      : "bg-slate-800/40 text-slate-400 border-slate-800"
                  }`}
                >
                  Creator
                </button>
                <button
                  onClick={() => switchDemoRole("REVIEWER")}
                  className={`py-1.5 text-center text-xs font-mono font-medium rounded-lg border transition ${
                    activeWorkspace?.role === "REVIEWER"
                      ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                      : "bg-slate-800/40 text-slate-400 border-slate-800"
                  }`}
                >
                  Reviewer
                </button>
                <button
                  onClick={() => switchDemoRole("GOVERNANCE_ADMIN")}
                  className={`py-1.5 text-center text-xs font-mono font-medium rounded-lg border transition ${
                    activeWorkspace?.role === "GOVERNANCE_ADMIN"
                      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                      : "bg-slate-800/40 text-slate-400 border-slate-800"
                  }`}
                >
                  Admin
                </button>
              </div>
            </div>

            {/* Mobile Links */}
            <div className="grid grid-cols-2 gap-1.5">
              {navLinks.map((link) => {
                const isActive =
                  link.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`px-3 py-2 rounded-lg text-xs font-medium flex items-center space-x-2 transition ${
                      isActive
                        ? "bg-teal-500/20 text-teal-300 border border-teal-500/30"
                        : "bg-slate-900/60 text-slate-300 hover:bg-slate-800/60 border border-slate-800"
                    }`}
                  >
                    <span className={isActive ? "text-teal-400" : "text-slate-400"}>
                      {link.icon}
                    </span>
                    <span>{link.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </header>

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />
    </>
  );
}
