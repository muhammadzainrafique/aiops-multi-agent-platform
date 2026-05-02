import { NextRequest, NextResponse } from 'next/server'
import Groq from 'groq-sdk'
const groq = new Groq({ apiKey: process.env.GROQ_API_KEY })
export async function POST(req: NextRequest) {
  try {
    const { message, context, history } = await req.json()
    const completion = await groq.chat.completions.create({
      model: process.env.GROQ_MODEL || 'llama-3.3-70b-versatile',
      max_tokens: 500,
      temperature: 0.3,
      messages: [
        {
          role: 'system',
          content: `You are an expert AIOps Incident Analyst embedded in a Kubernetes operations dashboard.
You have full context about the current incident including logs, AI diagnosis, and automated actions taken.
Be concise, specific and actionable. Use **bold** for key terms and \`code\` for technical values.
Keep responses under 250 words unless detail is explicitly requested.
INCIDENT CONTEXT:\n${context || 'No incident selected.'}`,
        },
        ...(history || []).slice(-6).map((h: any) => ({
          role: h.role as 'user' | 'assistant',
          content: h.content,
        })),
        { role: 'user', content: message },
      ],
    })
    let reply = completion.choices[0]?.message?.content || 'No response.'
    reply = reply
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.*?)`/g, '<code class="bg-ink-3 px-1 py-0.5 rounded text-blue-mid text-xs">$1</code>')
      .replace(/\n\n/g, '<br/><br/>')
      .replace(/\n/g, '<br/>')
    return NextResponse.json({ reply })
  } catch (e: any) {
    return NextResponse.json({ reply: `⚠️ Chat error: ${e.message}` }, { status: 500 })
  }
}
