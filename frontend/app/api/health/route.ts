import { NextResponse } from 'next/server';
const SUP = process.env.SUPERVISOR_URL || 'http://localhost:5001';
export const dynamic = 'force-dynamic';
export async function GET() {
  try {
    const r = await fetch(`${SUP}/health`, { cache: 'no-store' });
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({ status: 'offline', redis: 'unreachable' }, { status: 503 });
  }
}
