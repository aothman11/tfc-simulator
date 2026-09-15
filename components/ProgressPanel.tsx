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
}

export default function ProgressPanel({ events, total, sentCount, failedCount, sending }: ProgressPanelProps) {
  const done = events.find(e => e.type === 'done') as Extract<ProgressEvent, { type: 'done' }> | undefined
  const processed = sentCount + failedCount
  const progress = total > 0 ? Math.round((processed / total) * 100) : 0

  const dotClass = sending ? 'dot dot-sending' : done ? 'dot dot-done' : 'dot dot-idle'

  return (
    <div className="card">
      {/* Header */}
      <div className="section-title" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className={dotClass} />
          Progress
        </div>
        {total > 0 && (
          <span style={{ fontSize: 13, color: '#6b7fa3', fontVariantNumeric: 'tabular-nums' }}>
            {processed} / {total}
          </span>
        )}
      </div>

      {/* Progress bar */}
      {(events.length > 0 || sending) && total > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 9 }}>
            <span style={{ fontSize: 12, color: '#4CAF50', fontWeight: 600 }}>✓ {sentCount} sent</span>
            {failedCount > 0 && (
              <span style={{ fontSize: 12, color: '#ef4444', fontWeight: 600 }}>✗ {failedCount} failed</span>
            )}
            <span style={{ fontSize: 12, color: '#6b7fa3', fontVariantNumeric: 'tabular-nums' }}>{progress}%</span>
          </div>
        </div>
      )}

      {/* Log */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, maxHeight: 180, overflowY: 'auto' }}>
        {events.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 0', color: '#3d4460', fontSize: 13 }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
              style={{ margin: '0 auto 10px', display: 'block', opacity: 0.4 }}>
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            Logs will appear here during sending
          </div>
        ) : (
          events.map((ev, i) => <LogRow key={i} event={ev} />)
        )}
      </div>

      {/* Done summary */}
      {done && (
        <>
          <div className={done.failedCount === 0 ? 'summary-ok animate-fade-in' : 'summary-warn animate-fade-in'}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#e2e8f0' }}>
              {done.failedCount === 0
                ? `✅  All ${done.sentCount} emails delivered!`
                : `⚠️  ${done.sentCount} sent, ${done.failedCount} failed`}
            </div>
            <div style={{ fontSize: 13, color: '#8892a4', marginTop: 5 }}>
              {done.failedCount === 0
                ? 'Your batch has been sent successfully.'
                : 'Check the log above for details on failed sends.'}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function LogRow({ event }: { event: ProgressEvent }) {
  const rowStyle: React.CSSProperties = {
    display: 'flex', alignItems: 'flex-start', gap: 8,
    padding: '6px 8px', borderRadius: 8, fontSize: 13,
    transition: 'background 0.12s',
  }

  switch (event.type) {
    case 'sent':
      return (
        <div style={rowStyle} className="animate-fade-in">
          <span style={{ flexShrink: 0 }}>✅</span>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#c8d3e8' }}>
            {event.email}
          </span>
          <span style={{ fontSize: 11, color: '#3d4460', flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>
            #{event.index}
          </span>
        </div>
      )
    case 'failed':
      return (
        <div style={{ ...rowStyle, flexDirection: 'column' }} className="animate-fade-in">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
            <span style={{ flexShrink: 0 }}>❌</span>
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#c8d3e8' }}>
              {event.email}
            </span>
            <span style={{ fontSize: 11, color: '#3d4460', flexShrink: 0 }}>#{event.index}</span>
          </div>
          <p style={{ margin: 0, fontSize: 12, color: '#ef4444', paddingLeft: 26, opacity: 0.8, lineClamp: 2 }}>
            {event.reason}
          </p>
        </div>
      )
    case 'waiting':
      return (
        <div style={rowStyle}>
          <span style={{ flexShrink: 0 }}>⏳</span>
          <span style={{ color: '#6b7fa3' }}>Waiting {event.seconds}s before next email…</span>
        </div>
      )
    case 'countdown':
      return (
        <div style={rowStyle}>
          <span style={{ flexShrink: 0 }}>🕐</span>
          <span style={{ color: '#6b7fa3', fontFamily: 'monospace', fontSize: 12 }}>
            {event.remaining}s until sending begins…
          </span>
        </div>
      )
    case 'scheduled':
      return (
        <div style={rowStyle} className="animate-fade-in">
          <span style={{ flexShrink: 0 }}>📅</span>
          <span style={{ color: '#6b7fa3' }}>
            Scheduled for {new Date(event.scheduledAt).toLocaleString()} — waiting {event.waitSeconds}s
          </span>
        </div>
      )
    case 'error':
      return (
        <div style={{ ...rowStyle, background: 'rgba(239,68,68,0.08)', borderRadius: 9 }} className="animate-fade-in">
          <span style={{ flexShrink: 0 }}>⚠️</span>
          <span style={{ color: '#ef4444' }}>{event.message}</span>
        </div>
      )
    case 'start':
      return (
        <div style={rowStyle} className="animate-fade-in">
          <span style={{ flexShrink: 0 }}>🚀</span>
          <span style={{ color: '#6b7fa3' }}>
            Starting — sending to {event.total} recipient{event.total !== 1 ? 's' : ''}…
          </span>
        </div>
      )
    case 'done':
      return (
        <div style={rowStyle}>
          <span style={{ flexShrink: 0 }}>🏁</span>
          <span style={{ color: '#6b7fa3' }}>Finished.</span>
        </div>
      )
    default:
      return null
  }
}
