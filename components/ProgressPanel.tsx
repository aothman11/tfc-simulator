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

  if (events.length === 0 && !sending) return null

  return (
    <div className="card animate-fade-in">
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className={`dot ${sending ? 'dot-sending' : done ? 'dot-done' : 'dot-idle'}`} />
          <span className="section-title-text">
            {sending ? 'Sending…' : done ? 'Complete' : 'Progress'}
          </span>
        </div>
        {total > 0 && (
          <span style={{ fontSize: 13, color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>
            {processed} / {total}
          </span>
        )}
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div style={{ marginBottom: 10 }}>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
            <div style={{ display: 'flex', gap: 14 }}>
              <span style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 500 }}>
                {sentCount} sent
              </span>
              {failedCount > 0 && (
                <span style={{ fontSize: 12, color: 'var(--red)', fontWeight: 500 }}>
                  {failedCount} failed
                </span>
              )}
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums' }}>
              {progress}%
            </span>
          </div>
        </div>
      )}

      {/* Event log */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, maxHeight: 200, overflowY: 'auto', marginTop: 8 }}>
        {events.map((ev, i) => <LogRow key={i} event={ev} />)}
      </div>

      {/* Done summary */}
      {done && (
        <div className={done.failedCount === 0 ? 'summary-ok animate-fade-in' : 'summary-warn animate-fade-in'}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>
            {done.failedCount === 0
              ? `All ${done.sentCount} emails delivered`
              : `${done.sentCount} sent · ${done.failedCount} failed`}
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 4 }}>
            {done.failedCount === 0
              ? 'Your batch completed successfully.'
              : 'Check the log above for details on failed sends.'}
          </div>
        </div>
      )}
    </div>
  )
}

function LogRow({ event }: { event: ProgressEvent }) {
  const base: React.CSSProperties = {
    display: 'flex', alignItems: 'flex-start', gap: 9,
    padding: '5px 8px', borderRadius: 6, fontSize: 12.5,
  }

  switch (event.type) {
    case 'sent':
      return (
        <div style={base} className="animate-fade-in">
          <span style={{ color: 'var(--primary)', fontSize: 11, fontWeight: 700, marginTop: 1, flexShrink: 0 }}>✓</span>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text)' }}>
            {event.email}
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-dim)', flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>
            #{event.index}
          </span>
        </div>
      )
    case 'failed':
      return (
        <div style={{ ...base, flexDirection: 'column' }} className="animate-fade-in">
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, width: '100%' }}>
            <span style={{ color: 'var(--red)', fontSize: 11, fontWeight: 700, flexShrink: 0 }}>✗</span>
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text)' }}>
              {event.email}
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-dim)', flexShrink: 0 }}>#{event.index}</span>
          </div>
          <p style={{ margin: 0, fontSize: 11.5, color: 'var(--red)', paddingLeft: 20, opacity: 0.8 }}>
            {event.reason}
          </p>
        </div>
      )
    case 'waiting':
      return (
        <div style={base}>
          <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>—</span>
          <span style={{ color: 'var(--text-muted)' }}>Waiting {event.seconds}s…</span>
        </div>
      )
    case 'countdown':
      return (
        <div style={base}>
          <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>◷</span>
          <span style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>
            {event.remaining}s until start…
          </span>
        </div>
      )
    case 'scheduled':
      return (
        <div style={base} className="animate-fade-in">
          <span style={{ color: 'var(--amber)', flexShrink: 0 }}>◷</span>
          <span style={{ color: 'var(--text-muted)' }}>
            Scheduled for {new Date(event.scheduledAt).toLocaleString()} — waiting {event.waitSeconds}s
          </span>
        </div>
      )
    case 'error':
      return (
        <div style={{ ...base, background: 'var(--red-bg)', borderRadius: 7 }} className="animate-fade-in">
          <span style={{ color: 'var(--red)', flexShrink: 0 }}>!</span>
          <span style={{ color: 'var(--red)' }}>{event.message}</span>
        </div>
      )
    case 'start':
      return (
        <div style={base} className="animate-fade-in">
          <span style={{ color: 'var(--primary)', flexShrink: 0 }}>→</span>
          <span style={{ color: 'var(--text-muted)' }}>
            Sending to {event.total} recipient{event.total !== 1 ? 's' : ''}…
          </span>
        </div>
      )
    case 'done':
      return (
        <div style={base}>
          <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>■</span>
          <span style={{ color: 'var(--text-muted)' }}>Finished.</span>
        </div>
      )
    default:
      return null
  }
}
