import { NextResponse } from 'next/server';
import { NextRequest } from 'next/server';
const SUP = process.env.SUPERVISOR_URL || 'http://localhost:5001';
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const r = await fetch(`${SUP}/test-alert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({ error: 'Supervisor offline' }, { status: 503 });
  }
}
