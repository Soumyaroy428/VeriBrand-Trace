"use client";

import React, { useState } from "react";
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
  User,
} from "lucide-react";
import { useAuth, RoleType } from "@/context/AuthContext";

export default function Navbar() {
  const pathname = usePathname();
  const { user, activeWorkspace, workspaces, setActiveWorkspace, switchDemoRole, logout } = useAuth();
  const [wsMenuOpen, setWsMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const getRoleBadgeStyle = (role?: RoleType) => {
    switch (role) {
      case "GOVERNANCE_ADMIN":
        return "bg-emerald-50 border-emerald-200 text-emerald-800";
      case "REVIEWER":
        return "bg-amber-50 border-amber-200 text-amber-800";
      case "CREATOR":
      default:
        return "bg-sky-50 border-sky-200 text-sky-800";
    }
  };

  const roleLabel = activeWorkspace?.role ? activeWorkspace.role.replace("_", " ") : "Guest";

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6 lg:space-x-8">
          <Link href="/" className="flex items-center space-x-2.5 group">
            <div className="h-9 w-9 rounded-lg bg-slate-900 flex items-center justify-center text-white font-bold group-hover:bg-slate-800 transition">
              <ShieldCheck className="h-5 w-5 text-teal-400" />
            </div>
            <span className="font-semibold text-lg tracking-tight text-slate-900">
              VeriBrand <span className="text-teal-600 font-normal">Trace</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center space-x-1 text-sm font-medium text-slate-600">
            <Link
              href="/"
              className={`px-3 py-1.5 rounded-md transition ${
                pathname === "/" ? "text-slate-950 bg-slate-100 font-semibold" : "hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              Overview
            </Link>
            <Link
              href="/audits/new"
              className={`px-3 py-1.5 rounded-md transition flex items-center space-x-1.5 ${
                pathname.startsWith("/audits") ? "text-slate-950 bg-slate-100 font-semibold" : "hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <FileCheck className="h-4 w-4 text-slate-400" />
              <span>New Audit</span>
            </Link>
            <Link
              href="/brand-vault"
              className={`px-3 py-1.5 rounded-md transition flex items-center space-x-1.5 ${
                pathname.startsWith("/brand-vault") ? "text-slate-950 bg-slate-100 font-semibold" : "hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <Layers className="h-4 w-4 text-slate-400" />
              <span>Brand Vault</span>
            </Link>
            <Link
              href="/review-queue"
              className={`px-3 py-1.5 rounded-md transition flex items-center space-x-1.5 ${
                pathname.startsWith("/review-queue") ? "text-slate-950 bg-slate-100 font-semibold" : "hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <History className="h-4 w-4 text-slate-400" />
              <span>Review Queue</span>
            </Link>
            <Link
              href="/analytics"
              className={`px-3 py-1.5 rounded-md transition flex items-center space-x-1.5 ${
                pathname.startsWith("/analytics") ? "text-slate-950 bg-slate-100 font-semibold" : "hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <BarChart3 className="h-4 w-4 text-slate-400" />
              <span>Analytics</span>
            </Link>
          </nav>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          {/* Workspace Switcher */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setWsMenuOpen(!wsMenuOpen)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition"
            >
              <Building2 className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-medium text-slate-900 truncate max-w-[120px]">
                {activeWorkspace ? activeWorkspace.workspace_name : "No Workspace"}
              </span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {wsMenuOpen && (
              <div className="absolute right-0 mt-1 w-56 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-50">
                <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  Switch Workspace
                </div>
                {workspaces.map((ws) => (
                  <button
                    key={ws.workspace_id}
                    onClick={() => {
                      setActiveWorkspace(ws.workspace_id);
                      setWsMenuOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-slate-50 ${
                      activeWorkspace?.workspace_id === ws.workspace_id ? "bg-slate-50 font-semibold text-teal-700" : "text-slate-700"
                    }`}
                  >
                    <span className="truncate">{ws.workspace_name}</span>
                    <span className="text-[10px] uppercase text-slate-400 ml-2">{ws.role}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Role Badge */}
          <div
            className={`flex items-center px-2.5 py-1 rounded-md border font-semibold tracking-wide uppercase text-[11px] ${getRoleBadgeStyle(
              activeWorkspace?.role
            )}`}
          >
            {roleLabel}
          </div>

          {/* Fast Role Persona Switcher (For Pair-Programming & Evaluation) */}
          <div className="hidden lg:flex items-center gap-1 bg-slate-100 p-0.5 rounded-md border border-slate-200">
            <button
              onClick={() => switchDemoRole("CREATOR")}
              className={`px-2 py-0.5 rounded text-[10px] font-medium transition ${
                activeWorkspace?.role === "CREATOR" ? "bg-white text-sky-700 shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
              title="Switch to Alice Creator"
            >
              Creator
            </button>
            <button
              onClick={() => switchDemoRole("REVIEWER")}
              className={`px-2 py-0.5 rounded text-[10px] font-medium transition ${
                activeWorkspace?.role === "REVIEWER" ? "bg-white text-amber-700 shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
              title="Switch to Bob Reviewer"
            >
              Reviewer
            </button>
            <button
              onClick={() => switchDemoRole("GOVERNANCE_ADMIN")}
              className={`px-2 py-0.5 rounded text-[10px] font-medium transition ${
                activeWorkspace?.role === "GOVERNANCE_ADMIN" ? "bg-white text-emerald-700 shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
              title="Switch to Carol Governance Admin"
            >
              Admin
            </button>
          </div>

          {/* User Account / Sign In */}
          {user ? (
            <div className="relative">
              <button
                type="button"
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-1.5 p-1.5 rounded-md hover:bg-slate-100 transition"
              >
                <div className="w-7 h-7 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs">
                  {user.full_name ? user.full_name[0].toUpperCase() : "U"}
                </div>
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-50">
                  <div className="px-3 py-2 border-b border-slate-100">
                    <p className="text-xs font-semibold text-slate-900 truncate">{user.full_name}</p>
                    <p className="text-[11px] text-slate-500 truncate">{user.email}</p>
                  </div>
                  <button
                    onClick={() => {
                      logout();
                      setUserMenuOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 flex items-center gap-1.5 transition"
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
              className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-teal-600 hover:bg-teal-500 text-white font-medium transition"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
