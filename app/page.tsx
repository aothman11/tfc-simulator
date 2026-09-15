'use client'

import { useState, useRef } from 'react'
import ConfigPanel from '@/components/ConfigPanel'
import RecipientsManager from '@/components/RecipientsManager'
import EmailEditor from '@/components/EmailEditor'
import AttachmentUpload from '@/components/AttachmentUpload'
import ProgressPanel, { ProgressEvent } from '@/components/ProgressPanel'
import ScheduleToggle from '@/components/ScheduleToggle'

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve((reader.result as string).split(',')[1])
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export default function Home() {
  const [sender, setSender] = useState('')
  const [password, setPassword] = useState('')
  const [subject, setSubject] = useState('')
  const [delay, setDelay] = useState(5)
  const [recipients, setRecipients] = useState<string[]>([])
  const [body, setBody] = useState('')
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null)
  const [scheduled, setScheduled] = useState(false)
  const [scheduledAt, setScheduledAt] = useState('')
  const [sending, setSending] = useState(false)
  const [events, setEvents] = useState<ProgressEvent[]>([])
  const [sentCount, setSentCount] = useState(0)
  const [failedCount, setFailedCount] = useState(0)
  const [total, setTotal] = useState(0)
  const abortRef = useRef<AbortController | null>(null)

  const appendEvent = (evt: ProgressEvent) => {
    setEvents(prev => [...prev, evt])
    if (evt.type === 'sent' || evt.type === 'failed') {
      setSentCount(evt.sentCount)
      setFailedCount(evt.failedCount)
    }
    if (evt.type === 'start') setTotal(evt.total)
  }

  const canSend = !!(sender && password && subject && body && recipients.length > 0 && !sending)

  const hints: string[] = []
  if (!sender) hints.push('Sender email is required')
  if (!password) hints.push('App password is required')
  if (!subject) hints.push('Subject line is required')
  if (!body) hints.push('Email body is required')
  if (recipients.length === 0) hints.push('Add at least one recipient')

  const handleSend = async () => {
    if (!canSend) return
    setEvents([])
    setSentCount(0)
    setFailedCount(0)
    setTotal(0)
    setSending(true)

    const abort = new AbortController()
    abortRef.current = abort

    try {
      let attachmentData: { name: string; data: string } | undefined
      if (attachmentFile) {
        attachmentData = { name: attachmentFile.name, data: await fileToBase64(attachmentFile) }
      }

      const res = await fetch('/api/send-emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender: sender.trim(), password, subject: subject.trim(),
          body, recipients, attachment: attachmentData, delay,
          scheduledAt: scheduled && scheduledAt ? scheduledAt : undefined,
        }),
        signal: abort.signal,
      })

      if (!res.ok) {
        appendEvent({ type: 'error', message: (await res.text()) || `HTTP ${res.status}` })
        return
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''
        for (const part of parts) {
          const line = part.trim()
          if (line.startsWith('data: ')) {
            try { appendEvent(JSON.parse(line.slice(6)) as ProgressEvent) } catch { /* skip */ }
          }
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      appendEvent({ type: 'error', message: err instanceof Error && err.name === 'AbortError' ? 'Sending cancelled.' : msg })
    } finally {
      setSending(false)
      abortRef.current = null
    }
  }

  const isDone = events.some(e => e.type === 'done')

  return (
    <div style={{ minHeight: '100vh', background: '#0f1117' }}>

      {/* ── HEADER ── */}
      <header style={{
        background: 'rgba(20,23,34,0.95)',
        borderBottom: '1px solid #1e2235',
        position: 'sticky', top: 0, zIndex: 10,
        backdropFilter: 'blur(16px)',
      }}>
        <div style={{
          maxWidth: 1360, margin: '0 auto', padding: '0 32px',
          height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 13 }}>
            <div style={{
              width: 38, height: 38, borderRadius: 11,
              background: 'linear-gradient(140deg,#4CAF50,#2E7D32)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 3px 12px rgba(76,175,80,0.4), inset 0 1px 0 rgba(255,255,255,0.15)',
            }}>
              <svg width="19" height="19" viewBox="0 0 24 24" fill="white">
                <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z" />
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#f0f4ff', letterSpacing: '-0.03em', lineHeight: 1 }}>
                Email Sender
              </div>
              <div style={{ fontSize: 11, color: '#4a5568', marginTop: 2 }}>Gmail SMTP bulk mailer</div>
            </div>
          </div>

          {/* Status pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {sending && (
              <div className="animate-fade-in" style={{
                display: 'flex', alignItems: 'center', gap: 7,
                background: 'rgba(250,204,21,0.08)', border: '1px solid rgba(250,204,21,0.25)',
                borderRadius: 100, padding: '5px 14px 5px 9px',
              }}>
                <span className="dot dot-sending" />
                <span style={{ fontSize: 12, color: '#FACC15', fontWeight: 600 }}>
                  Sending {sentCount + failedCount}&thinsp;/&thinsp;{total || recipients.length}
                </span>
              </div>
            )}
            {isDone && !sending && (
              <div className="animate-fade-in" style={{
                display: 'flex', alignItems: 'center', gap: 7,
                background: 'rgba(76,175,80,0.08)', border: '1px solid rgba(76,175,80,0.25)',
                borderRadius: 100, padding: '5px 14px 5px 9px',
              }}>
                <span style={{ fontSize: 13 }}>✓</span>
                <span style={{ fontSize: 12, color: '#4CAF50', fontWeight: 600 }}>Done — {sentCount} sent</span>
              </div>
            )}
            {!sending && !isDone && recipients.length > 0 && (
              <div style={{
                background: '#1e2235', border: '1px solid #2e3348', borderRadius: 100,
                padding: '5px 14px', fontSize: 12, color: '#6b7fa3', fontWeight: 500,
              }}>
                {recipients.length} recipient{recipients.length !== 1 ? 's' : ''}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── MAIN GRID ── */}
      <main style={{
        maxWidth: 1360, margin: '0 auto', padding: '32px 32px 56px',
        display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: 28,
      }}>

        {/* LEFT COLUMN */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
          <ConfigPanel
            sender={sender} setSender={setSender}
            password={password} setPassword={setPassword}
            subject={subject} setSubject={setSubject}
            delay={delay} setDelay={setDelay}
          />
          <RecipientsManager recipients={recipients} setRecipients={setRecipients} />
          <ScheduleToggle
            scheduled={scheduled} setScheduled={setScheduled}
            scheduledAt={scheduledAt} setScheduledAt={setScheduledAt}
          />
        </div>

        {/* RIGHT COLUMN */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
          <EmailEditor body={body} setBody={setBody} />
          <AttachmentUpload file={attachmentFile} setFile={setAttachmentFile} />

          {/* Send card */}
          <div className="card">
            {/* Validation hints */}
            {hints.length > 0 && !sending && !isDone && (
              <div style={{
                marginBottom: 16, padding: '13px 15px',
                background: 'rgba(255,255,255,0.02)',
                borderRadius: 11, border: '1px solid #1e2235',
              }}>
                {hints.map(h => (
                  <div key={h} style={{ fontSize: 12, color: '#6b7fa3', padding: '2px 0', display: 'flex', alignItems: 'center', gap: 7 }}>
                    <span style={{ color: '#3d4460' }}>•</span>{h}
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={handleSend}
              disabled={!canSend}
              style={{
                border: 'none', borderRadius: 13, padding: '15px 24px',
                fontSize: 15, fontWeight: 600, cursor: canSend ? 'pointer' : 'not-allowed',
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 9,
                fontFamily: 'inherit', letterSpacing: '-0.01em',
                ...(canSend
                  ? {
                    background: 'linear-gradient(135deg,#4CAF50 0%,#5EC461 50%,#4CAF50 100%)',
                    backgroundSize: '200%',
                    color: 'white',
                    boxShadow: '0 5px 20px rgba(76,175,80,0.35)',
                    transition: 'transform 0.1s, box-shadow 0.15s',
                  }
                  : {
                    background: '#1e2235',
                    color: '#3d4460',
                  }),
              }}
              onMouseEnter={e => { if (canSend) { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 8px 28px rgba(76,175,80,0.45)' } }}
              onMouseLeave={e => { if (canSend) { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = '0 5px 20px rgba(76,175,80,0.35)' } }}
            >
              {sending ? (
                <>
                  <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                  Sending…
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                  </svg>
                  {scheduled && scheduledAt ? '📅  Schedule Emails' : 'Send Emails'}
                </>
              )}
            </button>

            {sending && (
              <button
                onClick={() => abortRef.current?.abort()}
                style={{
                  width: '100%', marginTop: 9, background: 'none',
                  border: '1px solid rgba(239,68,68,0.25)', borderRadius: 11,
                  color: '#ef4444', padding: 10, cursor: 'pointer', fontSize: 14,
                  fontFamily: 'inherit', transition: 'background 0.15s, border-color 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.08)'; e.currentTarget.style.borderColor = 'rgba(239,68,68,0.4)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.borderColor = 'rgba(239,68,68,0.25)' }}
              >
                Cancel
              </button>
            )}

            {isDone && !sending && (
              <button
                onClick={() => { setEvents([]); setSentCount(0); setFailedCount(0); setTotal(0) }}
                style={{
                  width: '100%', marginTop: 10, background: 'none',
                  border: '1px solid #2e3348', borderRadius: 11,
                  color: '#8892a4', padding: 10, cursor: 'pointer', fontSize: 14,
                  fontFamily: 'inherit', transition: 'border-color 0.15s, color 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#4a5568'; e.currentTarget.style.color = '#c8d3e8' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#2e3348'; e.currentTarget.style.color = '#8892a4' }}
              >
                ← Send Another Batch
              </button>
            )}
          </div>

          <ProgressPanel
            events={events}
            total={total}
            sentCount={sentCount}
            failedCount={failedCount}
            sending={sending}
          />
        </div>
      </main>
    </div>
  )
}
