"use client";

import Link from "next/link";
import { ShieldCheck, Layers, FileCheck, History, BarChart3, Settings } from "lucide-react";

export default function Navbar() {
  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <Link href="/" className="flex items-center space-x-2.5 group">
            <div className="h-9 w-9 rounded-lg bg-slate-900 flex items-center justify-center text-white font-bold group-hover:bg-slate-800 transition">
              <ShieldCheck className="h-5 w-5 text-blue-400" />
            </div>
            <span className="font-semibold text-lg tracking-tight text-slate-900">
              VeriBrand <span className="text-blue-600 font-normal">Trace</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center space-x-1 text-sm font-medium text-slate-600">
            <Link
              href="/"
              className="px-3 py-2 rounded-md hover:text-slate-900 hover:bg-slate-50 transition"
            >
              Overview
            </Link>
            <Link
              href="/audits/new"
              className="px-3 py-2 rounded-md hover:text-slate-900 hover:bg-slate-50 transition flex items-center space-x-1.5"
            >
              <FileCheck className="h-4 w-4 text-slate-400" />
              <span>New Audit</span>
            </Link>
            <Link
              href="/brand-vault"
              className="px-3 py-2 rounded-md hover:text-slate-900 hover:bg-slate-50 transition flex items-center space-x-1.5"
            >
              <Layers className="h-4 w-4 text-slate-400" />
              <span>Brand Vault</span>
            </Link>
            <Link
              href="/review-queue"
              className="px-3 py-2 rounded-md hover:text-slate-900 hover:bg-slate-50 transition flex items-center space-x-1.5"
            >
              <History className="h-4 w-4 text-slate-400" />
              <span>Review Queue</span>
            </Link>
            <Link
              href="/analytics"
              className="px-3 py-2 rounded-md hover:text-slate-900 hover:bg-slate-50 transition flex items-center space-x-1.5"
            >
              <BarChart3 className="h-4 w-4 text-slate-400" />
              <span>Analytics</span>
            </Link>
          </nav>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          {/* Workspace Pill */}
          <div className="hidden sm:flex items-center px-2.5 py-1 rounded-md border border-slate-200 bg-slate-50 text-slate-700">
            <span className="text-slate-400 mr-1.5 font-mono">Workspace:</span>
            <span className="font-medium text-slate-800">Acme Global</span>
          </div>

          {/* Role Badge */}
          <div className="flex items-center px-2.5 py-1 rounded-md bg-blue-50 border border-blue-200 text-blue-700 font-semibold tracking-wide uppercase text-[11px]">
            Reviewer
          </div>
        </div>
      </div>
    </header>
  );
}
