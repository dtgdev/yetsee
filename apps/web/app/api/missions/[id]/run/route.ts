import { NextResponse } from "next/server";
const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://backend:8000";
export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try { const r=await fetch(`${INTERNAL_API_URL}/api/v1/missions/${encodeURIComponent(id)}/run`,{method:"POST",cache:"no-store"}); return new NextResponse(await r.text(),{status:r.status,headers:{"content-type":r.headers.get("content-type")??"application/json","cache-control":"no-store"}}); }
  catch(error){return NextResponse.json({detail:error instanceof Error?error.message:"Mission service unavailable"},{status:502});}
}
