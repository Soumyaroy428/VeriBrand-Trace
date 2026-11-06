import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json(
    {
      status: "healthy",
      service: "VeriBrand Trace Web Client",
      version: "1.0.0",
      timestamp: new Date().toISOString(),
      checks: {
        frontend: "operational",
        nextjs: "14.2.15",
      },
    },
    { status: 200 }
  );
}
