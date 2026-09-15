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

  const sendLabel = scheduled && scheduledAt
    ? `Schedule ${recipients.length} Email${recipients.length !== 1 ? 's' : ''}`
    : `Send ${recipients.length} Email${recipients.length !== 1 ? 's' : ''}`

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>

      {/* ── HEADER ── */}
      <header style={{
        background: 'rgba(13,15,24,0.92)',
        borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0, zIndex: 10,
        backdropFilter: 'blur(12px)',
      }}>
        <div className="header-inner" style={{
          maxWidth: 1300, margin: '0 auto', padding: '0 28px',
          height: 58, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'var(--primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
                <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z" />
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
                Email Sender
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 1 }}>
                Bulk email, simplified.
              </div>
            </div>
          </div>

          {/* Status indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {sending ? (
              <div className="animate-fade-in" style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'var(--amber-bg)', border: '1px solid var(--amber-border)',
                borderRadius: 100, padding: '4px 12px 4px 8px',
              }}>
                <span className="dot dot-sending" />
                <span style={{ fontSize: 12, color: 'var(--amber)', fontWeight: 500 }}>
                  {sentCount + failedCount}&thinsp;/&thinsp;{total || recipients.length} sending
                </span>
              </div>
            ) : isDone ? (
              <div className="animate-fade-in" style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'var(--primary-bg)', border: '1px solid var(--primary-border)',
                borderRadius: 100, padding: '4px 12px 4px 8px',
              }}>
                <span className="dot dot-done" />
                <span style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 500 }}>
                  {sentCount} sent
                </span>
              </div>
            ) : (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'var(--surface2)', border: '1px solid var(--border)',
                borderRadius: 100, padding: '4px 12px 4px 8px',
              }}>
                <span className="dot dot-ready" style={{ width: 5, height: 5 }} />
                <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 400 }}>
                  Ready
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── MAIN GRID ── */}
      <main className="main-content" style={{
        maxWidth: 1300, margin: '0 auto', padding: '28px 28px 60px',
        display: 'grid',
        gridTemplateColumns: 'minmax(0,420px) minmax(0,1fr)',
        gap: 22,
      }} data-grid="main-grid">

        {/* LEFT COLUMN — Campaign setup */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <ConfigPanel
            sender={sender} setSender={setSender}
            password={password} setPassword={setPassword}
          />
          <RecipientsManager recipients={recipients} setRecipients={setRecipients} />
          <ScheduleToggle
            scheduled={scheduled} setScheduled={setScheduled}
            scheduledAt={scheduledAt} setScheduledAt={setScheduledAt}
            delay={delay} setDelay={setDelay}
          />
        </div>

        {/* RIGHT COLUMN — Email composition */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <EmailEditor
            body={body} setBody={setBody}
            subject={subject} setSubject={setSubject}
            sender={sender}
            recipientCount={recipients.length}
          />
          <AttachmentUpload file={attachmentFile} setFile={setAttachmentFile} />

          {/* Send card */}
          <div className="card">
            {/* Validation panel */}
            {!sending && !isDone && (
              <div className={`validation-panel ${hints.length === 0 ? 'ready' : 'incomplete'}`}>
                {hints.length === 0 ? (
                  <div className="validation-ready-text">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    Ready to send
                  </div>
                ) : (
                  <>
                    <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 6, fontWeight: 500 }}>
                      Please complete:
                    </div>
                    {hints.map(h => (
                      <div key={h} className="validation-item">{h}</div>
                    ))}
                  </>
                )}
              </div>
            )}

            {/* Send button */}
            <button
              onClick={handleSend}
              disabled={!canSend}
              style={{
                border: 'none', borderRadius: 9, padding: '13px 20px',
                fontSize: 14, fontWeight: 600, cursor: canSend ? 'pointer' : 'not-allowed',
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                fontFamily: 'inherit', letterSpacing: '-0.01em',
                transition: 'background 0.15s, transform 0.1s, box-shadow 0.15s',
                ...(canSend
                  ? {
                    background: 'var(--primary)',
                    color: 'white',
                    boxShadow: '0 2px 10px rgba(61,158,66,0.3)',
                  }
                  : {
                    background: 'var(--surface2)',
                    color: 'var(--text-dim)',
                  }),
              }}
              onMouseEnter={e => { if (canSend) { e.currentTarget.style.background = 'var(--primary-light)'; e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 4px 16px rgba(61,158,66,0.38)' } }}
              onMouseLeave={e => { if (canSend) { e.currentTarget.style.background = 'var(--primary)'; e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = '0 2px 10px rgba(61,158,66,0.3)' } }}
            >
              {sending ? (
                <>
                  <svg className="animate-spin" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                  Sending…
                </>
              ) : (
                <>
                  {recipients.length > 0 && canSend && (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                    </svg>
                  )}
                  {recipients.length > 0 ? sendLabel : (scheduled && scheduledAt ? 'Schedule Emails' : 'Send Emails')}
                </>
              )}
            </button>

            {/* Cancel button */}
            {sending && (
              <button
                onClick={() => abortRef.current?.abort()}
                className="btn-danger-ghost"
                style={{ marginTop: 8 }}
              >
                Cancel
              </button>
            )}

            {/* Reset button */}
            {isDone && !sending && (
              <button
                onClick={() => { setEvents([]); setSentCount(0); setFailedCount(0); setTotal(0) }}
                className="btn-ghost"
                style={{ width: '100%', marginTop: 8, textAlign: 'center' }}
              >
                ← New batch
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

      <style>{`
        @media (max-width: 900px) {
          [data-grid="main-grid"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  )
}
