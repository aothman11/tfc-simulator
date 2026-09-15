'use client'

import { useState } from 'react'

interface ConfigPanelProps {
  sender: string
  setSender: (v: string) => void
  password: string
  setPassword: (v: string) => void
  subject: string
  setSubject: (v: string) => void
  delay: number
  setDelay: (v: number) => void
}

export default function ConfigPanel({
  sender, setSender,
  password, setPassword,
  subject, setSubject,
  delay, setDelay,
}: ConfigPanelProps) {
  const [showPass, setShowPass] = useState(false)

  return (
    <div className="card">
      <div className="section-title">
        <span className="dot dot-green" />
        Configuration
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        {/* Sender */}
        <div>
          <label className="field-label">Gmail Sender Address</label>
          <input
            type="email"
            value={sender}
            onChange={e => setSender(e.target.value)}
            placeholder="you@gmail.com"
            style={{ padding: '10px 14px' }}
          />
        </div>

        {/* Password */}
        <div>
          <label className="field-label" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>App Password</span>
            <a
              href="https://myaccount.google.com/apppasswords"
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 11, textTransform: 'none', letterSpacing: 0, color: '#4CAF50', fontWeight: 500 }}
            >
              Generate one ↗
            </a>
          </label>
          <div style={{ position: 'relative' }}>
            <input
              type={showPass ? 'text' : 'password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="xxxx xxxx xxxx xxxx"
              style={{
                padding: '10px 54px 10px 14px',
                fontFamily: "'SF Mono', Consolas, monospace",
                letterSpacing: '0.05em',
              }}
            />
            <button
              type="button"
              onClick={() => setShowPass(p => !p)}
              style={{
                position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', color: '#6b7fa3',
                fontSize: 10, fontWeight: 700, cursor: 'pointer', padding: '4px 6px',
                borderRadius: 5, fontFamily: 'inherit', letterSpacing: '0.06em',
                transition: 'color 0.12s',
              }}
            >
              {showPass ? 'HIDE' : 'SHOW'}
            </button>
          </div>
        </div>

        {/* Subject */}
        <div>
          <label className="field-label">Email Subject</label>
          <input
            type="text"
            value={subject}
            onChange={e => setSubject(e.target.value)}
            placeholder="e.g. Application for Software Engineer"
            style={{ padding: '10px 14px' }}
          />
        </div>

        {/* Delay */}
        <div>
          <label className="field-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Delay Between Emails</span>
            <span style={{ color: '#c8d3e8', fontSize: 12, fontWeight: 600, textTransform: 'none', letterSpacing: 0 }}>
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
              style={{ width: 58, padding: '7px', textAlign: 'center', fontSize: 14, borderRadius: 9, flexShrink: 0 }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
