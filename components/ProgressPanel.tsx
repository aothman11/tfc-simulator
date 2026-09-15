'use client'

export type ProgressEvent =
  | { type: 'start'; total: number }
  | { type: 'sent'; email: string; index: number; total: number; sentCount: number; failedCount: number }
  | { type: 'failed'; email: string; reason: string; index: number; total: number; sentCount: number; failedCount: number }
  | { type: 'waiting'; seconds: number }
  | { type: 'countdown'; remaining: number }
  | { type: 'scheduled'; waitSeconds: number; scheduledAt: string }
  | { type: 'error'; message: string }
  | { type: 'done'; total: number; sentCount: number; failedCount: number }

interface ProgressPanelProps {
  events: ProgressEvent[]
  total: number
  sentCount: number
  failedCount: number
  sending: boolean
  recipients: string[]
  emailResults: Record<string, { status: 'sent' | 'failed'; time: string; reason?: string }>
  processed: number
  progress: number
  elapsed: number
  remainingText: string | null
  formatElapsed: (ms: number) => string
}

function StatusCell({ email, idx, processed, sending, emailResults }: {
  email: string; idx: number; processed: number; sending: boolean;
  emailResults: Record<string, { status: 'sent' | 'failed'; time: string; reason?: string }>
}) {
  const result = emailResults[email]
  if (result) {
    if (result.status === 'sent') {
      return (
        <span className="status-sent">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          Sent
        </span>
      )
    }
    return (
      <span className="status-failed" title={result.reason}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
        Failed
      </span>
    )
  }
  if (sending && idx === processed) {
    return (
      <span className="status-sending">
        <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0" strokeOpacity="0.3"/>
          <path d="M21 12a9 9 0 00-9-9"/>
        </svg>
        Sending…
      </span>
    )
  }
  return (
    <span className="status-waiting">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>
      </svg>
      Waiting
    </span>
  )
}

export default function ProgressPanel({
  events, total, sentCount, failedCount, sending,
  recipients, emailResults, processed, progress,
  elapsed, remainingText, formatElapsed,
}: ProgressPanelProps) {
  const done = events.find(e => e.type === 'done') as Extract<ProgressEvent, { type: 'done' }> | undefined
  const errorEvent = events.find(e => e.type === 'error') as Extract<ProgressEvent, { type: 'error' }> | undefined
  const scheduledEvent = events.find(e => e.type === 'scheduled') as Extract<ProgressEvent, { type: 'scheduled' }> | undefined

  return (
    <div>
      {/* Scheduled notice */}
      {scheduledEvent && !done && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--amber-bg)', border: '1px solid var(--amber-border)', borderRadius: 8, padding: '10px 14px', marginBottom: 14 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          <span style={{ fontSize: 13, color: 'var(--amber)' }}>
            Scheduled for {new Date(scheduledEvent.scheduledAt).toLocaleString()} — waiting {scheduledEvent.waitSeconds}s
          </span>
        </div>
      )}

      {/* Error notice */}
      {errorEvent && (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, background: 'var(--red-bg)', border: '1px solid var(--red-border)', borderRadius: 8, padding: '10px 14px', marginBottom: 14 }}>
          <span style={{ color: 'var(--red)', flexShrink: 0, fontWeight: 700 }}>!</span>
          <span style={{ fontSize: 13, color: 'var(--red)' }}>{errorEvent.message}</span>
        </div>
      )}

      {/* Progress bar */}
      {(sending || total > 0) && (
        <div style={{ marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>
              {processed}<span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: 15 }}> / {total || recipients.length}</span>
              <span style={{ marginLeft: 10, fontSize: 13, fontWeight: 400, color: done ? 'var(--primary)' : 'var(--text-muted)' }}>
                {done ? (failedCount === 0 ? ' ✓ All delivered' : ` · ${failedCount} failed`) : ' emails sent'}
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 8, fontVariantNumeric: 'tabular-nums' }}>
              {elapsed > 0 && (
                <span>
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ verticalAlign: '-1px', marginRight: 3 }}><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                  {formatElapsed(elapsed)}
                </span>
              )}
              {remainingText && sending && (
                <span style={{ color: 'var(--text-dim)' }}>{remainingText}</span>
              )}
            </div>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5 }}>
            <div style={{ display: 'flex', gap: 12 }}>
              {sentCount > 0 && <span style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 500 }}>{sentCount} sent</span>}
              {failedCount > 0 && <span style={{ fontSize: 12, color: 'var(--red)', fontWeight: 500 }}>{failedCount} failed</span>}
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums' }}>{progress}%</span>
          </div>
        </div>
      )}

      {/* Per-email status table */}
      {recipients.length > 0 && (
        <div style={{ overflow: 'hidden', borderRadius: 8, border: '1px solid var(--border)' }}>
          <table className="progress-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Email</th>
                <th>Status</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {recipients.map((email, idx) => {
                const result = emailResults[email]
                return (
                  <tr key={email}>
                    <td style={{ color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums', width: 32 }}>{idx + 1}</td>
                    <td style={{ color: 'var(--text)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {email}
                      {result?.status === 'failed' && result.reason && (
                        <div style={{ fontSize: 11, color: 'var(--red)', marginTop: 2, opacity: 0.8, whiteSpace: 'normal' }}>
                          {result.reason}
                        </div>
                      )}
                    </td>
                    <td>
                      <StatusCell email={email} idx={idx} processed={processed} sending={sending} emailResults={emailResults} />
                    </td>
                    <td style={{ color: 'var(--text-dim)', fontSize: 12, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                      {result?.time ?? '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Done summary */}
      {done && (
        <div className={done.failedCount === 0 ? 'summary-ok animate-fade-in' : 'summary-warn animate-fade-in'} style={{ marginTop: 14 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>
            {done.failedCount === 0
              ? `✓ All ${done.sentCount} emails delivered`
              : `${done.sentCount} sent · ${done.failedCount} failed`}
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 4 }}>
            {done.failedCount === 0
              ? 'Your batch completed successfully.'
              : 'Check the table above for details on failed sends.'}
          </div>
        </div>
      )}
    </div>
  )
}
