import { NextResponse } from "next/server";

const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://backend:8000";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  try {
    const response = await fetch(
      `${INTERNAL_API_URL}/api/v1/investigations/${encodeURIComponent(id)}/agent-findings?limit=500`,
      { cache: "no-store" },
    );
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown backend error";
    return NextResponse.json(
      { detail: `Could not load investigation findings. ${message}` },
      { status: 502 },
    );
  }
}
