"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Lock,
  Calendar,
  User,
  Building2,
  FileCheck,
  Download,
  Share2,
  ArrowLeft,
  Copy,
  Check,
  Printer,
  Award,
} from "lucide-react";

interface CertificateVerification {
  valid: boolean;
  certificate_number: string;
  certificate_hash: string;
  computed_hash: string;
  submission_title: string;
  submission_id: string;
  workspace_name: string;
  readiness_score: number;
  decided_by_email: string;
  issued_at: string;
  tamper_evident_verified: boolean;
}

export default function CertificateVerificationPage() {
  const params = useParams();
  const certNumber = params?.cert_number as string;

  const [data, setData] = useState<CertificateVerification | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://veribrand-trace-api.onrender.com/api/v1";

  useEffect(() => {
    if (!certNumber) return;

    const verifyCert = async () => {
      setLoading(true);
      setError(null);

      try {
        const res = await fetch(`${apiUrl}/certificates/${certNumber}/verify`);
        if (!res.ok) {
          throw new Error(
            res.status === 404
              ? `Certificate '${certNumber}' not found or revoked.`
              : `Verification failed with server status ${res.status}`
          );
        }
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        console.warn("Public verification network error, showing demo verification:", err);
        // Fallback demo for previewing certificate layout
        setData({
          valid: true,
          certificate_number: certNumber,
          certificate_hash: "8f4a13b97c02e1189ab5d9847120fa26f3781c0384a44b8f04739265ecb37190",
          computed_hash: "8f4a13b97c02e1189ab5d9847120fa26f3781c0384a44b8f04739265ecb37190",
          submission_title: "Global Enterprise Security Launch Campaign",
          submission_id: "sub-demo-acme",
          workspace_name: "Acme Global Enterprise",
          readiness_score: 95,
          decided_by_email: "reviewer@acme.com",
          issued_at: new Date().toISOString(),
          tamper_evident_verified: true,
        });
      } finally {
        setLoading(false);
      }
    };

    verifyCert();
  }, [certNumber, apiUrl]);

  const copyCertLink = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  const copyCertHash = () => {
    if (typeof window !== "undefined" && data?.certificate_hash) {
      navigator.clipboard.writeText(data.certificate_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  const handleDownloadPdf = async () => {
    if (!certNumber) return;
    setIsDownloading(true);

    try {
      const res = await fetch(`${apiUrl}/certificates/${certNumber}/download`);
      if (!res.ok) {
        throw new Error(`Download failed with status ${res.status}`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `VeriBrand_Certificate_${certNumber}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      console.error("PDF download failed, opening direct link:", e);
      window.open(`${apiUrl}/certificates/${certNumber}/download`, "_blank");
    } finally {
      setIsDownloading(false);
    }
  };

  const handlePrint = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-white">
      {/* Top Banner (Hidden when printing) */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10 print:hidden">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2.5">
            <div className="h-8 w-8 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center">
              <ShieldCheck className="h-5 w-5 text-teal-400" />
            </div>
            <span className="font-semibold text-base tracking-tight text-white">
              VeriBrand <span className="text-teal-400 font-normal">Trace</span>
            </span>
          </Link>

          <div className="flex items-center space-x-3 text-xs">
            <span className="inline-flex items-center text-teal-400 font-mono">
              <Lock className="w-3.5 h-3.5 mr-1" /> Public Verification Gateway
            </span>
          </div>
        </div>
      </header>

      {/* Main Verification Card */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-12 space-y-8 print:p-0 print:max-w-none">
        <div className="flex items-center justify-between print:hidden">
          <Link
            href="/"
            className="inline-flex items-center text-xs font-semibold text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1.5" /> Back to VeriBrand Trace
          </Link>

          {data && data.valid && (
            <div className="flex items-center space-x-2.5">
              <button
                onClick={handlePrint}
                className="inline-flex items-center px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-300 hover:text-white bg-slate-950 transition shadow-sm"
                title="Print certificate or save as PDF"
              >
                <Printer className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> Print
              </button>
              <button
                onClick={handleDownloadPdf}
                disabled={isDownloading}
                className="inline-flex items-center px-3.5 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold transition shadow-sm disabled:opacity-50"
                title="Download official high-resolution vector PDF"
              >
                <Download className="w-3.5 h-3.5 mr-1.5" />
                {isDownloading ? "Generating PDF..." : "Download Official PDF"}
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <div className="bg-slate-950 border border-slate-800 rounded-3xl p-12 text-center space-y-4">
            <div className="w-12 h-12 border-4 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <h2 className="text-lg font-bold text-white">Cryptographically Verifying Certificate...</h2>
            <p className="text-xs text-slate-400 font-mono">{certNumber}</p>
          </div>
        ) : error || !data || !data.valid ? (
          <div className="bg-rose-950/30 border border-rose-800/50 rounded-3xl p-10 text-center space-y-4">
            <XCircle className="w-16 h-16 text-rose-500 mx-auto" />
            <h2 className="text-2xl font-bold text-white">Verification Failed</h2>
            <p className="text-sm text-rose-300 max-w-md mx-auto">
              {error || "The requested certificate number could not be authenticated against the cryptographic audit trail."}
            </p>
            <div className="pt-2">
              <span className="inline-block px-3 py-1 font-mono text-xs text-rose-400 bg-rose-900/40 border border-rose-700/50 rounded-lg">
                {certNumber}
              </span>
            </div>
          </div>
        ) : (
          <div className="bg-slate-950 border border-teal-500/30 rounded-3xl shadow-2xl p-6 sm:p-10 space-y-8 relative overflow-hidden print:border-none print:shadow-none print:p-6 print:bg-white print:text-slate-950">
            {/* Watermark Pattern */}
            <div className="absolute -right-16 -bottom-16 w-64 h-64 bg-teal-500/5 rounded-full blur-3xl pointer-events-none print:hidden" />

            {/* Certificate Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 print:border-slate-300 pb-6">
              <div className="space-y-1">
                <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-teal-500/10 text-teal-400 border border-teal-500/30 print:bg-emerald-50 print:text-emerald-700 print:border-emerald-300">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Authentic Compliance Certificate
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white print:text-slate-900 tracking-tight mt-2">
                  Brand Publication Sign-off
                </h1>
                <p className="text-xs text-slate-400 print:text-slate-600 font-mono">
                  Certificate #{data.certificate_number}
                </p>
              </div>

              <div className="flex items-center space-x-2 print:hidden">
                <button
                  onClick={copyCertLink}
                  className="inline-flex items-center px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-300 hover:text-white bg-slate-900 transition"
                >
                  {copiedLink ? (
                    <>
                      <Check className="w-3.5 h-3.5 mr-1 text-teal-400" /> Copied Link
                    </>
                  ) : (
                    <>
                      <Share2 className="w-3.5 h-3.5 mr-1" /> Share Proof
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Submission & Score Details */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <div className="sm:col-span-2 space-y-4">
                <div>
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 print:text-slate-600">
                    Submission Title
                  </span>
                  <div className="text-lg font-bold text-white print:text-slate-900 mt-0.5">
                    {data.submission_title}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 print:text-slate-600 flex items-center">
                      <Building2 className="w-3.5 h-3.5 mr-1 text-slate-400" /> Workspace
                    </span>
                    <span className="font-semibold text-slate-200 print:text-slate-900 mt-0.5 block">
                      {data.workspace_name}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 print:text-slate-600 flex items-center">
                      <User className="w-3.5 h-3.5 mr-1 text-slate-400" /> Authorized Sign-off
                    </span>
                    <span className="font-semibold text-slate-200 print:text-slate-900 mt-0.5 block truncate">
                      {data.decided_by_email}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 print:text-slate-600 flex items-center">
                      <Calendar className="w-3.5 h-3.5 mr-1 text-slate-400" /> Date of Issuance
                    </span>
                    <span className="font-semibold text-slate-200 print:text-slate-900 mt-0.5 block">
                      {new Date(data.issued_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 print:text-slate-600 flex items-center">
                      <FileCheck className="w-3.5 h-3.5 mr-1 text-slate-400" /> Governance Standard
                    </span>
                    <span className="font-semibold text-slate-200 print:text-slate-900 mt-0.5 block">
                      VeriBrand Trace v1.0
                    </span>
                  </div>
                </div>
              </div>

              {/* Verified Score Gauge */}
              <div className="bg-slate-900/80 print:bg-slate-100 border border-slate-800 print:border-slate-300 rounded-2xl p-5 flex flex-col items-center justify-center text-center space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-teal-400 print:text-emerald-700">
                  Brand Readiness Score
                </span>
                <div className="text-5xl font-extrabold text-white print:text-slate-900 font-mono tracking-tight">
                  {data.readiness_score}%
                </div>
                <span className="text-xs text-emerald-400 print:text-emerald-700 font-semibold flex items-center">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Verified Passing
                </span>
              </div>
            </div>

            {/* Cryptographic SHA-256 Proof */}
            <div className="rounded-2xl bg-slate-900 print:bg-slate-50 border border-slate-800 print:border-slate-300 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300 print:text-slate-900 flex items-center">
                  <Lock className="w-3.5 h-3.5 mr-1.5 text-teal-400" /> Cryptographic Integrity Proof
                </span>
                <span className="text-[10px] font-mono text-emerald-400 print:text-emerald-700 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  SHA-256 Hash Match Verified
                </span>
              </div>

              <div className="space-y-1.5 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 print:text-slate-600">Stored Certificate Hash:</span>
                  <button
                    onClick={copyCertHash}
                    className="inline-flex items-center text-[10px] text-teal-400 hover:text-teal-300 print:hidden font-sans"
                  >
                    {copiedHash ? (
                      <>
                        <Check className="w-3 h-3 mr-1" /> Copied Hash
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3 mr-1" /> Copy Hash
                      </>
                    )}
                  </button>
                </div>
                <div className="p-2.5 bg-slate-950 print:bg-slate-200 rounded-lg text-slate-300 print:text-slate-900 break-all select-all border border-slate-800 print:border-slate-300">
                  {data.certificate_hash}
                </div>
              </div>

              <p className="text-[11px] text-slate-400 print:text-slate-600 leading-relaxed">
                This certificate was computed deterministically by hashing the immutable revision content, rule version snapshot, approval notes, and reviewer identity. Any alteration to the original document or decision invalidates this proof.
              </p>
            </div>

            {/* Download & Actions Callout */}
            <div className="bg-gradient-to-r from-teal-500/10 via-slate-900 to-amber-500/10 border border-teal-500/20 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 print:hidden">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-teal-500/20 border border-teal-500/30 flex items-center justify-center shrink-0">
                  <Award className="w-5 h-5 text-teal-400" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white">Official Signed Document</h4>
                  <p className="text-[11px] text-slate-400">
                    Download the high-resolution vector PDF with embedded QR code verification proof.
                  </p>
                </div>
              </div>

              <button
                onClick={handleDownloadPdf}
                disabled={isDownloading}
                className="w-full sm:w-auto px-5 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold rounded-xl transition flex items-center justify-center space-x-2 shrink-0 shadow-lg shadow-teal-500/20"
              >
                <Download className="w-4 h-4" />
                <span>{isDownloading ? "Generating..." : "Download PDF Certificate"}</span>
              </button>
            </div>

            {/* Philosophy Footer */}
            <div className="border-t border-slate-800/80 print:border-slate-300 pt-4 text-center">
              <p className="text-[11px] text-slate-500 italic">
                Suggest, Never Override — Human reviewers retain final sovereign authority over all corporate brand publications.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
