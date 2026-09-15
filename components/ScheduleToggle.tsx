'use client'

import { useEffect, useState } from 'react'

interface ScheduleToggleProps {
  scheduled: boolean
  setScheduled: (v: boolean) => void
  scheduledAt: string
  setScheduledAt: (v: string) => void
  delay: number
  setDelay: (v: number) => void
}

function toLocalInput(date: Date) {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}T${p(date.getHours())}:${p(date.getMinutes())}`
}

export default function ScheduleToggle({
  scheduled, setScheduled,
  scheduledAt, setScheduledAt,
  delay, setDelay,
}: ScheduleToggleProps) {
  const [countdown, setCountdown] = useState('')

  useEffect(() => {
    if (!scheduled || !scheduledAt) { setCountdown(''); return }
    const update = () => {
      const diff = new Date(scheduledAt).getTime() - Date.now()
      if (diff <= 0) { setCountdown('Sending now…'); return }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setCountdown(`${h > 0 ? `${h}h ` : ''}${m > 0 ? `${m}m ` : ''}${s}s`)
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [scheduled, scheduledAt])

  const handleToggle = (on: boolean) => {
    setScheduled(on)
    if (on && !scheduledAt) {
      setScheduledAt(new Date(Date.now() + 15 * 60 * 1000).toISOString())
    }
  }

  return (
    <div className="card">
      <div className="section-header">
        <span className="section-num">03</span>
        <span className="section-title-text">Sending options</span>
      </div>

      {/* Delay */}
      <div style={{ marginBottom: 20 }}>
        <label className="field-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Delay between emails</span>
          <span style={{ color: 'var(--text)', fontSize: 13, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
            {delay}s
          </span>
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <input
            type="range"
            min={0}
            max={60}
            value={delay}
            onChange={e => setDelay(Number(e.target.value))}
            style={{ flex: 1 }}
          />
          <input
            type="number"
            min={0}
            max={60}
            value={delay}
            onChange={e => setDelay(Math.min(60, Math.max(0, Number(e.target.value) || 0)))}
            style={{ width: 56, padding: '7px', textAlign: 'center', fontSize: 13, borderRadius: 8, flexShrink: 0 }}
          />
        </div>
        <p className="field-hint">Pause between each email send. 0 = no delay (may trigger spam filters)</p>
      </div>

      {/* Send timing */}
      <div>
        <label className="field-label">Send timing</label>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8,
        }}>
          <button
            style={{
              padding: '11px 8px',
              borderRadius: 8,
              fontSize: 13, fontWeight: 600,
              cursor: 'pointer', fontFamily: 'inherit',
              transition: 'all 0.15s',
              ...(!scheduled ? {
                background: 'var(--primary)',
                border: '1px solid transparent',
                color: 'white',
                boxShadow: '0 2px 8px rgba(61,158,66,0.25)',
              } : {
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                color: 'var(--text-muted)',
              }),
            }}
            onClick={() => handleToggle(false)}
          >
            Send now
          </button>
          <button
            style={{
              padding: '11px 8px',
              borderRadius: 8,
              fontSize: 13, fontWeight: 600,
              cursor: 'pointer', fontFamily: 'inherit',
              transition: 'all 0.15s',
              ...(scheduled ? {
                background: 'var(--surface3)',
                border: '1px solid var(--border-focus)',
                color: 'var(--text)',
              } : {
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                color: 'var(--text-muted)',
              }),
            }}
            onClick={() => handleToggle(true)}
          >
            Schedule
          </button>
        </div>

        {scheduled && (
          <div style={{ marginTop: 14 }}>
            <label className="field-label">Scheduled date &amp; time</label>
            <input
              type="datetime-local"
              value={scheduledAt ? toLocalInput(new Date(scheduledAt)) : ''}
              min={toLocalInput(new Date(Date.now() + 60_000))}
              onChange={e => e.target.value && setScheduledAt(new Date(e.target.value).toISOString())}
              style={{ padding: '9px 13px' }}
            />
            {countdown && (
              <div style={{
                marginTop: 10, display: 'flex', alignItems: 'center', gap: 7,
                background: 'var(--amber-bg)', border: '1px solid var(--amber-border)',
                borderRadius: 8, padding: '8px 12px',
              }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" strokeWidth="2" strokeLinecap="round">
                  <circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" />
                </svg>
                <span style={{ fontSize: 12.5, color: 'var(--amber)', fontVariantNumeric: 'tabular-nums' }}>
                  Sends in {countdown}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
