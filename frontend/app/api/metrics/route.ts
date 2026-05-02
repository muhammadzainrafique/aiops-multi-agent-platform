import { NextResponse } from 'next/server'
const SUP = process.env.SUPERVISOR_URL || 'http://localhost:5001'
export const dynamic = 'force-dynamic'
export async function GET() {
  try {
    const r = await fetch(`${SUP}/metrics`, { cache: 'no-store' })
    const text = await r.text()
    return NextResponse.json({ raw: text })
  } catch {
    return NextResponse.json({ raw: '' }, { status: 503 })
  }
}
