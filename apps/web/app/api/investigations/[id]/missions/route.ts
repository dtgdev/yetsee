import { NextResponse } from "next/server";

const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://backend:8000";

async function forward(response: Response) {
  const body = await response.text();
  return new NextResponse(body, { status: response.status, headers: { "content-type": response.headers.get("content-type") ?? "application/json", "cache-control": "no-store" } });
}

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try { return forward(await fetch(`${INTERNAL_API_URL}/api/v1/investigations/${encodeURIComponent(id)}/missions`, { cache: "no-store" })); }
  catch (error) { return NextResponse.json({ detail: error instanceof Error ? error.message : "Mission service unavailable" }, { status: 502 }); }
}

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const payload = await request.json();
    return forward(await fetch(`${INTERNAL_API_URL}/api/v1/investigations/${encodeURIComponent(id)}/missions`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload), cache: "no-store" }));
  } catch (error) { return NextResponse.json({ detail: error instanceof Error ? error.message : "Mission service unavailable" }, { status: 502 }); }
}
