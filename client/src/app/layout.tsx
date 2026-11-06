import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import { AuthProvider } from "@/context/AuthContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "VeriBrand Trace | Pre-Publication Brand Governance",
  description: "Explainable Pre-Publication Brand Governance & Human-in-the-Loop Diff Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased selection:bg-teal-100 selection:text-teal-900">
        <AuthProvider>
          <Navbar />
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
          <footer className="border-t border-slate-200 bg-white py-6 mt-16 text-center text-xs text-slate-500">
            <p>
              VeriBrand Trace &copy; {new Date().getFullYear()} Team Last of Us. Suggest, Never Override.
            </p>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
