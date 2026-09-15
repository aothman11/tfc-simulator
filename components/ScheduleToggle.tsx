'use client'

import { useEffect, useState } from 'react'

interface ScheduleToggleProps {
  scheduled: boolean
  setScheduled: (v: boolean) => void
  scheduledAt: string
  setScheduledAt: (v: string) => void
}

function toLocalInput(date: Date) {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}T${p(date.getHours())}:${p(date.getMinutes())}`
}

export default function ScheduleToggle({ scheduled, setScheduled, scheduledAt, setScheduledAt }: ScheduleToggleProps) {
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

  const btnBase: React.CSSProperties = {
    flex: 1, padding: '11px 8px', borderRadius: 12,
    fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
    transition: 'all 0.15s',
  }
  const btnActive: React.CSSProperties = {
    ...btnBase,
    background: 'linear-gradient(135deg,#4CAF50,#5EC461)',
    border: '1px solid transparent',
    color: 'white',
    boxShadow: '0 3px 10px rgba(76,175,80,0.25)',
  }
  const btnInactive: React.CSSProperties = {
    ...btnBase,
    background: '#22263a',
    border: '1px solid #2e3348',
    color: '#6b7fa3',
  }

  return (
    <div className="card">
      <div className="section-title">
        <span className="dot dot-green" />
        Send Timing
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button style={!scheduled ? btnActive : btnInactive} onClick={() => handleToggle(false)}>
          🚀 Send Now
        </button>
        <button style={scheduled ? btnActive : btnInactive} onClick={() => handleToggle(true)}>
          🕐 Schedule
        </button>
      </div>

      {scheduled && (
        <div style={{ marginTop: 14 }}>
          <label className="field-label">Schedule Date &amp; Time</label>
          <input
            type="datetime-local"
            value={scheduledAt ? toLocalInput(new Date(scheduledAt)) : ''}
            min={toLocalInput(new Date(Date.now() + 60_000))}
            onChange={e => e.target.value && setScheduledAt(new Date(e.target.value).toISOString())}
            style={{ padding: '10px 14px' }}
          />
          {countdown && (
            <div style={{
              marginTop: 10, display: 'flex', alignItems: 'center', gap: 7,
              background: 'rgba(76,175,80,0.08)', border: '1px solid rgba(76,175,80,0.2)',
              borderRadius: 10, padding: '9px 14px',
            }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4CAF50" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" />
              </svg>
              <span style={{ fontSize: 13, color: '#4CAF50', fontFamily: 'monospace' }}>Sends in {countdown}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
