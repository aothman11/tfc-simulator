'use client'

import { useState, useRef, useEffect } from 'react'
import AttachmentUpload from '@/components/AttachmentUpload'
import ProgressPanel, { ProgressEvent } from '@/components/ProgressPanel'

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve((reader.result as string).split(',')[1])
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function isValidEmail(e: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e.trim())
}

function toLocalInput(date: Date) {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${p(date.getMonth()+1)}-${p(date.getDate())}T${p(date.getHours())}:${p(date.getMinutes())}`
}

const STEPS = ['Setup', 'Compose', 'Recipients', 'Preview', 'Send']

// ── Stepper ──────────────────────────────────────────────────────────────────
function Stepper({ current, isDone, sending }: { current: number; isDone: boolean; sending: boolean }) {
  return (
    <div className="stepper-wrap">
      <div className="stepper">
        {STEPS.map((label, i) => {
          const num = i + 1
          const done = (isDone || sending) ? true : num < current
          const active = !isDone && !sending && num === current
          const future = !done && !active
          return (
            <div key={label} className="step-item">
              <div className="step-circle-wrap">
                <div className={`step-circle ${done ? 'done' : active ? 'current' : 'future'}`}>
                  {done ? (
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : num}
                </div>
                <span className={`step-label ${done ? 'done' : active ? 'current' : 'future'}`}>{label}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`step-line ${done ? 'done' : 'future'}`} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Spinner icon ──────────────────────────────────────────────────────────────
function Spinner({ size = 14, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg className="animate-spin" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  )
}

// ── Main ─────────────────────────────────────────────────────────────────────
export default function Home() {
  // ── Form state (preserved) ──
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

  // ── Wizard state ──
  const [step, setStep] = useState(1)
  const [showPass, setShowPass] = useState(false)
  const [recipientInput, setRecipientInput] = useState('')
  const [bulkText, setBulkText] = useState('')
  const [previewTab, setPreviewTab] = useState<'edit' | 'preview'>('preview')
  const [composeTab, setComposeTab] = useState<'edit' | 'preview'>('edit')
  const [scheduleCountdown, setScheduleCountdown] = useState('')
  const csvInputRef = useRef<HTMLInputElement>(null)

  // ── Per-email result tracking ──
  const [emailResults, setEmailResults] = useState<Record<string, { status: 'sent' | 'failed'; time: string; reason?: string }>>({})
  const [startTime, setStartTime] = useState<number | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (sending && startTime) {
      elapsedRef.current = setInterval(() => setElapsed(Date.now() - startTime), 1000)
    } else {
      if (elapsedRef.current) clearInterval(elapsedRef.current)
    }
    return () => { if (elapsedRef.current) clearInterval(elapsedRef.current) }
  }, [sending, startTime])

  // Schedule countdown
  useEffect(() => {
    if (!scheduled || !scheduledAt) { setScheduleCountdown(''); return }
    const update = () => {
      const diff = new Date(scheduledAt).getTime() - Date.now()
      if (diff <= 0) { setScheduleCountdown('Sending now…'); return }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setScheduleCountdown(`${h > 0 ? `${h}h ` : ''}${m > 0 ? `${m}m ` : ''}${s}s`)
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [scheduled, scheduledAt])

  // ── Event handling ──
  const appendEvent = (evt: ProgressEvent) => {
    setEvents(prev => [...prev, evt])
    if (evt.type === 'sent') {
      setSentCount(evt.sentCount)
      setFailedCount(evt.failedCount)
      setEmailResults(prev => ({ ...prev, [evt.email]: { status: 'sent', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) } }))
    }
    if (evt.type === 'failed') {
      setSentCount(evt.sentCount)
      setFailedCount(evt.failedCount)
      setEmailResults(prev => ({ ...prev, [evt.email]: { status: 'failed', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), reason: evt.reason } }))
    }
    if (evt.type === 'start') {
      setTotal(evt.total)
      setStartTime(Date.now())
    }
  }

  const handleSend = async () => {
    if (!canSend) return
    setEvents([])
    setSentCount(0)
    setFailedCount(0)
    setTotal(0)
    setEmailResults({})
    setStartTime(null)
    setElapsed(0)
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
      appendEvent({ type: 'error', message: err instanceof Error && err.name === 'AbortError' ? 'Sending cancelled.' : String(err) })
    } finally {
      setSending(false)
      abortRef.current = null
    }
  }

  // ── Recipient helpers ──
  const addOneEmail = () => {
    const e = recipientInput.trim()
    if (!e || !isValidEmail(e) || recipients.includes(e)) return
    setRecipients(prev => [...prev, e])
    setRecipientInput('')
  }
  const addBulk = (text: string) => {
    const lines = text.split(/[\n,;]+/).map(e => e.trim()).filter(Boolean)
    const valid = lines.filter(isValidEmail)
    const newOnes = valid.filter(e => !recipients.includes(e))
    if (newOnes.length) setRecipients(prev => [...prev, ...newOnes])
  }
  const importCSV = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    const reader = new FileReader()
    reader.onload = ev => addBulk(ev.target?.result as string)
    reader.readAsText(f)
    e.target.value = ''
  }
  const removeRecipient = (email: string) => setRecipients(prev => prev.filter(r => r !== email))

  // ── Validation ──
  const canSend = !!(sender && password && subject && body && recipients.length > 0 && !sending)
  const isDone = events.some(e => e.type === 'done')
  const processed = sentCount + failedCount
  const progress = total > 0 ? Math.round((processed / total) * 100) : 0

  const formatElapsed = (ms: number) => {
    const s = Math.floor(ms / 1000)
    const m = Math.floor(s / 60)
    return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
  }
  const remainingText = (() => {
    if (!total || !delay) return null
    const rem = (total - processed) * delay
    const m = Math.floor(rem / 60)
    const s = rem % 60
    return m > 0 ? `~${m}m ${s}s remaining` : `~${s}s remaining`
  })()

  const canNext = [
    !!(sender && password),
    !!(subject && body),
    recipients.length > 0,
    true,
  ]

  const resetAll = () => {
    setStep(1); setSender(''); setPassword(''); setSubject(''); setDelay(5)
    setRecipients([]); setBody(''); setAttachmentFile(null)
    setScheduled(false); setScheduledAt('')
    setEvents([]); setSentCount(0); setFailedCount(0); setTotal(0)
    setEmailResults({}); setStartTime(null); setElapsed(0)
  }

  // ── Recipient status helper ──
  const getEmailStatus = (email: string, idx: number) => {
    if (emailResults[email]) return emailResults[email].status
    if (sending && idx === processed) return 'sending'
    return 'waiting'
  }

  // ══════════════════════════════════════════════════════════════════════════
  // RENDER STEPS
  // ══════════════════════════════════════════════════════════════════════════

  const renderStep1 = () => (
    <div>
      <div className="step-heading">
        <div className="step-title">Campaign Setup</div>
        <div className="step-subtitle">Configure your email settings and sender details.</div>
      </div>

      {/* 01 Gmail Sender */}
      <div className="section-block">
        <div className="section-block-header">
          <div className="section-num active">01</div>
          <span className="section-block-title">Gmail Sender</span>
          <div className="section-block-header-right">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <rect x="2" y="4" width="20" height="16" rx="2" fill="#EA4335" opacity="0.15"/>
              <path d="M2 6l10 7L22 6" stroke="#EA4335" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
        </div>
        <div className="sender-grid">
          <div>
            <label className="field-label">Gmail sender address</label>
            <input type="email" value={sender} onChange={e => setSender(e.target.value)}
              placeholder="you@gmail.com" style={{ padding: '9px 13px' }} />
            <p className="field-hint">Use a Gmail account with App Password enabled</p>
          </div>
          <div>
            <label className="field-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>App password</span>
              <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer"
                style={{ fontSize: 11, color: 'var(--blue)', fontWeight: 500 }}>Generate one ↗</a>
            </label>
            <div style={{ position: 'relative' }}>
              <input type={showPass ? 'text' : 'password'} value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="xxxx xxxx xxxx xxxx"
                style={{ padding: '9px 48px 9px 13px', fontFamily: 'monospace', letterSpacing: '0.04em' }} />
              <button type="button" onClick={() => setShowPass(p => !p)} style={{
                position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', color: 'var(--text-dim)',
                fontSize: 10, fontWeight: 700, cursor: 'pointer', padding: '4px 6px', letterSpacing: '0.06em', fontFamily: 'inherit',
              }}>{showPass ? 'HIDE' : 'SHOW'}</button>
            </div>
          </div>
        </div>
      </div>

      {/* 02 Recipients (quick view) */}
      <div className="section-block">
        <div className="section-block-header">
          <div className="section-num">02</div>
          <span className="section-block-title">Recipients</span>
          <div className="section-block-header-right">
            {recipients.length > 0 && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 100, padding: '2px 10px' }}>
                {recipients.length} recipient{recipients.length !== 1 ? 's' : ''}
              </span>
            )}
            <button className="btn-sm primary" onClick={() => setStep(3)}>+ Add</button>
            <button className="btn-sm" onClick={() => setStep(3)}>Bulk Paste</button>
          </div>
        </div>
        {recipients.length === 0 ? (
          <div className="recipients-empty">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
              style={{ margin: '0 auto 10px', display: 'block', opacity: 0.3 }}>
              <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/>
              <path d="M22 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
            </svg>
            <div>No recipients yet</div>
            <div style={{ fontSize: 11, marginTop: 3, color: 'var(--text-dim)' }}>Add email addresses above or use Bulk Paste</div>
          </div>
        ) : (
          <div className="recipient-list" style={{ maxHeight: 120 }}>
            {recipients.slice(0, 5).map(email => (
              <div key={email} className="recipient-row">
                <span className="recipient-check">✓</span>
                <span className="recipient-email">{email}</span>
              </div>
            ))}
            {recipients.length > 5 && (
              <div style={{ padding: '6px 10px', fontSize: 12, color: 'var(--text-dim)' }}>
                +{recipients.length - 5} more — <button onClick={() => setStep(3)} style={{ background: 'none', border: 'none', color: 'var(--blue)', cursor: 'pointer', fontSize: 12, fontFamily: 'inherit' }}>View all</button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 03 Sending Options */}
      <div className="section-block">
        <div className="section-block-header">
          <div className="section-num">03</div>
          <span className="section-block-title">Sending Options</span>
        </div>
        <label className="field-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Delay between emails</span>
          <span style={{ color: 'var(--text)', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{delay}s</span>
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <input type="range" min={0} max={60} value={delay} onChange={e => setDelay(Number(e.target.value))} style={{ flex: 1 }} />
          <input type="number" min={0} max={60} value={delay}
            onChange={e => setDelay(Math.min(60, Math.max(0, Number(e.target.value) || 0)))}
            style={{ width: 56, padding: '7px', textAlign: 'center', fontSize: 13, flexShrink: 0 }} />
        </div>
        <p className="field-hint">Pause between sends. 0 = no delay (may trigger spam filters)</p>
      </div>

      <div className="step-nav">
        <button className="btn-outline" onClick={resetAll} style={{ padding: '9px 18px', fontSize: 13 }}>← Cancel</button>
        <button className={`btn-primary${canNext[0] ? '' : ' disabled'}`}
          onClick={() => canNext[0] && setStep(2)}
          style={{ opacity: canNext[0] ? 1 : 0.4, cursor: canNext[0] ? 'pointer' : 'not-allowed' }}>
          Next →
        </button>
      </div>
    </div>
  )

  const renderStep2 = () => (
    <div>
      <div className="step-heading">
        <div className="step-title">Compose Your Email</div>
        <div className="step-subtitle">Write your message and add any attachments.</div>
      </div>

      {/* Email card */}
      <div className="section-block">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5">
              <rect x="2" y="4" width="20" height="16" rx="2"/><path d="M2 8l10 6 10-6"/>
            </svg>
            <span className="section-block-title">Email</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {body.length > 0 && (
              <span style={{ fontSize: 11, color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums' }}>
                {body.length.toLocaleString()} characters
              </span>
            )}
            <div className="tab-group">
              <button className={`tab-btn${composeTab === 'edit' ? ' active' : ''}`} onClick={() => setComposeTab('edit')}>Edit</button>
              <button className={`tab-btn${composeTab === 'preview' ? ' active' : ''}`} onClick={() => setComposeTab('preview')}>Preview</button>
            </div>
          </div>
        </div>

        {composeTab === 'edit' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label className="field-label">Subject</label>
              <input type="text" value={subject} onChange={e => setSubject(e.target.value)}
                placeholder="e.g. Application for Software Engineer" style={{ padding: '9px 13px' }} />
            </div>
            <div>
              <label className="field-label">Message body</label>
              <textarea value={body} onChange={e => setBody(e.target.value)}
                placeholder={'Dear Hiring Manager,\n\nI am writing to express my interest in the position…'}
                rows={9} style={{ padding: '13px 14px', resize: 'vertical', lineHeight: 1.7, fontSize: 14 }} />
            </div>
            <p className="field-hint" style={{ marginTop: 0 }}>Plain text · No formatting</p>
          </div>
        ) : (
          <div className="email-preview-card animate-fade-in">
            <div className="email-preview-meta">
              <div className="email-preview-field">
                <span className="email-preview-label">From</span>
                <span className="email-preview-value" style={{ color: sender ? 'var(--text)' : 'var(--text-dim)', fontStyle: sender ? 'normal' : 'italic' }}>
                  {sender || 'not set'}
                </span>
              </div>
              <div className="email-preview-field">
                <span className="email-preview-label">To</span>
                <span className="email-preview-value" style={{ color: recipients.length ? 'var(--text)' : 'var(--text-dim)', fontStyle: recipients.length ? 'normal' : 'italic' }}>
                  {recipients.length ? `${recipients[0]}${recipients.length > 1 ? ` (+${recipients.length - 1} more)` : ''}` : 'no recipients'}
                </span>
              </div>
              <div className="email-preview-field">
                <span className="email-preview-label">Subject</span>
                <span className="email-preview-value" style={{ fontWeight: subject ? 500 : 400, color: subject ? 'var(--text)' : 'var(--text-dim)', fontStyle: subject ? 'normal' : 'italic' }}>
                  {subject || 'no subject'}
                </span>
              </div>
            </div>
            {body ? (
              <div className="email-preview-body">{body}</div>
            ) : (
              <div style={{ padding: '30px 16px', textAlign: 'center', color: 'var(--text-dim)', fontStyle: 'italic', fontSize: 13 }}>No message yet</div>
            )}
          </div>
        )}
      </div>

      {/* Attachment */}
      <AttachmentUpload file={attachmentFile} setFile={setAttachmentFile} />

      <div className="step-nav">
        <button className="btn-outline" onClick={() => setStep(1)} style={{ padding: '9px 18px', fontSize: 13 }}>← Back</button>
        <button className={`btn-primary`}
          onClick={() => canNext[1] && setStep(3)}
          style={{ opacity: canNext[1] ? 1 : 0.4, cursor: canNext[1] ? 'pointer' : 'not-allowed' }}>
          Next →
        </button>
      </div>
    </div>
  )

  const renderStep3 = () => (
    <div>
      <div className="step-heading" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div className="step-title">Recipients</div>
          <div className="step-subtitle">Add your email recipients (one per line or separated by commas).</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
          {recipients.length > 0 && (
            <span style={{ fontSize: 13, color: 'var(--primary)', fontWeight: 600, background: 'var(--primary-bg)', border: '1px solid var(--primary-border)', borderRadius: 100, padding: '3px 12px' }}>
              {recipients.length} recipients
            </span>
          )}
          {recipients.length > 0 && (
            <button onClick={() => { if (confirm('Remove all recipients?')) setRecipients([]) }}
              style={{ background: 'none', border: 'none', color: 'var(--text-dim)', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', padding: '4px 6px', borderRadius: 6, transition: 'color 0.12s' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--red)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-dim)')}>
              Clear all
            </button>
          )}
        </div>
      </div>

      <div className="section-block">
        {/* Textarea input */}
        <textarea
          value={bulkText}
          onChange={e => setBulkText(e.target.value)}
          placeholder={'Add email addresses (one per line or separated by commas):\n\nexample@company.com\nhr@company.com\ninfo@company.com'}
          rows={5}
          style={{ padding: '12px 14px', resize: 'none', fontSize: 13, marginBottom: 10 }}
        />
        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn-sm primary" onClick={() => {
            if (bulkText.trim()) { addBulk(bulkText); setBulkText('') }
          }}>
            + Add
          </button>
          <button className="btn-sm" onClick={() => {
            navigator.clipboard.readText().then(text => { addBulk(text) }).catch(() => {})
          }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
            </svg>
            Bulk Paste
          </button>
          <button className="btn-sm" onClick={() => csvInputRef.current?.click()}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            Import CSV
          </button>
          <input ref={csvInputRef} type="file" accept=".csv,text/csv" onChange={importCSV} style={{ display: 'none' }} />
        </div>
      </div>

      {/* Added recipients list */}
      {recipients.length > 0 && (
        <div className="section-block">
          <div className="section-block-header" style={{ marginBottom: 12 }}>
            <span className="section-block-title">Added Recipients ({recipients.length})</span>
            <div className="section-block-header-right">
              <button onClick={() => {}} style={{ background: 'none', border: 'none', color: 'var(--blue)', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
                View all ({recipients.length})
              </button>
            </div>
          </div>
          <div className="recipient-list">
            {recipients.map((email, idx) => (
              <div key={email} className="recipient-row">
                <span className="recipient-check">✓</span>
                <span className="recipient-email">{email}</span>
                <button className="recipient-remove" onClick={() => removeRecipient(email)} title="Remove">×</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="step-nav">
        <button className="btn-outline" onClick={() => setStep(2)} style={{ padding: '9px 18px', fontSize: 13 }}>← Back</button>
        <button className="btn-primary"
          onClick={() => canNext[2] && setStep(4)}
          style={{ opacity: canNext[2] ? 1 : 0.4, cursor: canNext[2] ? 'pointer' : 'not-allowed' }}>
          Next →
        </button>
      </div>
    </div>
  )

  const renderStep4 = () => (
    <div>
      <div className="step-heading" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div className="step-title">Email Preview</div>
          <div className="step-subtitle">Review your email before sending.</div>
        </div>
        <div className="tab-group" style={{ marginTop: 4 }}>
          <button className={`tab-btn${previewTab === 'edit' ? ' active' : ''}`} onClick={() => { setPreviewTab('edit'); setStep(2) }}>Edit</button>
          <button className={`tab-btn${previewTab === 'preview' ? ' active' : ''}`} onClick={() => setPreviewTab('preview')}>Preview</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 14 }}>
        {/* Email preview */}
        <div className="section-block" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="email-preview-meta">
            <div className="email-preview-field">
              <span className="email-preview-label">From</span>
              <span className="email-preview-value">{sender || <em style={{ color: 'var(--text-dim)' }}>not set</em>}</span>
            </div>
            <div className="email-preview-field">
              <span className="email-preview-label">To</span>
              <span className="email-preview-value">
                {recipients.length > 0
                  ? `${recipients[0]}${recipients.length > 1 ? ` (+${recipients.length - 1} more)` : ''}`
                  : <em style={{ color: 'var(--text-dim)' }}>no recipients</em>}
              </span>
            </div>
            <div className="email-preview-field">
              <span className="email-preview-label">Subject</span>
              <span className="email-preview-value" style={{ fontWeight: 500 }}>{subject || <em style={{ color: 'var(--text-dim)' }}>no subject</em>}</span>
            </div>
          </div>
          <div className="email-preview-body">{body || <span style={{ color: 'var(--text-dim)', fontStyle: 'italic' }}>No message body</span>}</div>
        </div>

        {/* Details panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="section-block" style={{ padding: '16px 18px' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Email Details</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <DetailRow icon="👥" label="Recipients" value={`${recipients.length}`} />
              <DetailRow icon="📝" label="Subject" value={subject || '—'} />
              {attachmentFile && (
                <DetailRow icon="📎" label="Attachment" value={`${attachmentFile.name}`} sub={`${(attachmentFile.size / 1024 / 1024).toFixed(1)} MB`} />
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="step-nav">
        <button className="btn-outline" onClick={() => setStep(3)} style={{ padding: '9px 18px', fontSize: 13 }}>← Back</button>
        <button className="btn-primary" onClick={() => setStep(5)}>Next →</button>
      </div>
    </div>
  )

  const renderStep5 = () => {
    if (sending || isDone) {
      // ── Sending Progress ──
      return (
        <div className="animate-fade-in">
          <div className="step-heading">
            <div className="step-title">{isDone ? 'Campaign Complete' : 'Sending Progress'}</div>
            <div className="step-subtitle">
              {isDone ? 'Your email campaign has finished.' : "Please don't close this page. This may take a few minutes."}
            </div>
          </div>

          <div className="section-block">
            <ProgressPanel
              events={events} total={total}
              sentCount={sentCount} failedCount={failedCount}
              sending={sending}
              recipients={recipients}
              emailResults={emailResults}
              processed={processed}
              progress={progress}
              elapsed={elapsed}
              remainingText={remainingText}
              formatElapsed={formatElapsed}
            />
          </div>

          {isDone && (
            <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
              <button className="btn-primary" style={{ flex: 1 }} onClick={resetAll}>
                ← Start New Campaign
              </button>
              {sending && (
                <button className="btn-danger-ghost" onClick={() => abortRef.current?.abort()} style={{ width: 'auto', padding: '12px 20px' }}>
                  Cancel
                </button>
              )}
            </div>
          )}
          {sending && (
            <button className="btn-danger-ghost" style={{ marginTop: 12 }} onClick={() => abortRef.current?.abort()}>
              Cancel Sending
            </button>
          )}
        </div>
      )
    }

    // ── Send Review ──
    return (
      <div>
        <div className="step-heading">
          <div className="step-title">Send Email Campaign</div>
          <div className="step-subtitle">You're all set! Review the details and send your emails.</div>
        </div>

        {/* Stats */}
        <div className="step5-stats">
          <div className="step5-stat">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2">
              <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/>
              <path d="M22 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
            </svg>
            <span className="step5-stat-val">{recipients.length}</span> Recipients
          </div>
          <div className="step5-stat">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
            </svg>
            <span className="step5-stat-val">{delay}s</span> Delay
          </div>
          {attachmentFile && (
            <div className="step5-stat">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
              </svg>
              <span className="step5-stat-val">1</span> Attachment
            </div>
          )}
        </div>

        {/* Send Now button */}
        <button
          className="btn-primary"
          style={{ width: '100%', padding: '14px 20px', fontSize: 15, marginBottom: 10, borderRadius: 10 }}
          onClick={handleSend}
          disabled={!canSend}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
          Send {recipients.length} Email{recipients.length !== 1 ? 's' : ''}
        </button>

        {/* Schedule button */}
        <button
          className="btn-outline"
          style={{ width: '100%', marginBottom: 14 }}
          onClick={() => { setScheduled(!scheduled); if (!scheduled && !scheduledAt) setScheduledAt(new Date(Date.now() + 15 * 60 * 1000).toISOString()) }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
          </svg>
          {scheduled ? 'Cancel Schedule' : 'Schedule'}
        </button>

        {/* Schedule datetime picker */}
        {scheduled && (
          <div className="section-block animate-fade-in" style={{ marginBottom: 14 }}>
            <label className="field-label">Scheduled date &amp; time</label>
            <input type="datetime-local"
              value={scheduledAt ? toLocalInput(new Date(scheduledAt)) : ''}
              min={toLocalInput(new Date(Date.now() + 60_000))}
              onChange={e => e.target.value && setScheduledAt(new Date(e.target.value).toISOString())}
              style={{ padding: '9px 13px', marginBottom: 8 }} />
            {scheduleCountdown && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, background: 'var(--amber-bg)', border: '1px solid var(--amber-border)', borderRadius: 8, padding: '8px 12px' }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                <span style={{ fontSize: 12.5, color: 'var(--amber)' }}>Sends in {scheduleCountdown}</span>
              </div>
            )}
          </div>
        )}

        {/* Ready status */}
        <div className={`validation-panel ${canSend ? 'ready' : 'incomplete'}`}>
          {canSend ? (
            <div className="validation-ready-text">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              Ready to send — all required fields are completed.
            </div>
          ) : (
            <>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 5, fontWeight: 500 }}>Please complete:</div>
              {!sender && <div className="validation-item">Sender email is required</div>}
              {!password && <div className="validation-item">App password is required</div>}
              {!subject && <div className="validation-item">Subject line is required</div>}
              {!body && <div className="validation-item">Email body is required</div>}
              {recipients.length === 0 && <div className="validation-item">Add at least one recipient</div>}
            </>
          )}
        </div>

        <div className="step-nav">
          <button className="btn-outline" onClick={() => setStep(4)} style={{ padding: '9px 18px', fontSize: 13 }}>← Back</button>
        </div>
      </div>
    )
  }

  // ── Layout ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>

      {/* Header */}
      <header className="app-header">
        <div className="app-header-inner">
          <div className="header-logo">
            <div className="header-logo-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="white">
                <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
              </svg>
            </div>
            <div>
              <div className="header-logo-title">Email Sender</div>
              <div className="header-logo-sub">Bulk email, simplified.</div>
            </div>
          </div>
          <div className="header-stats">
            {sending ? (
              <div className="stat-pill sending">
                <span className="stat-dot pulse" />
                {processed}/{total || recipients.length} sending
              </div>
            ) : isDone ? (
              <div className="stat-pill active">
                <span className="stat-dot" />
                {sentCount} sent
              </div>
            ) : (
              <div className="stat-pill">
                <span className="stat-dot" />
                Ready
              </div>
            )}
            {recipients.length > 0 && !sending && !isDone && (
              <div className="stat-pill">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/>
                  <path d="M22 21v-2a4 4 0 00-3-3.87"/>
                </svg>
                {recipients.length} Recipient{recipients.length !== 1 ? 's' : ''}
              </div>
            )}
            {attachmentFile && (
              <div className="stat-pill">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
                </svg>
                1 Attachment
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Stepper */}
      <Stepper current={step} isDone={isDone} sending={sending} />

      {/* Step content */}
      <div className="step-page">
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
        {step === 4 && renderStep4()}
        {step === 5 && renderStep5()}
      </div>
    </div>
  )
}

// ── Detail row helper ─────────────────────────────────────────────────────────
function DetailRow({ icon, label, value, sub }: { icon: string; label: string; value: string; sub?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
      <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>{icon}</span>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 11, color: 'var(--text-dim)', fontWeight: 500, marginBottom: 2 }}>{label}</div>
        <div style={{ fontSize: 13, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</div>
        {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>{sub}</div>}
      </div>
    </div>
  )
}
