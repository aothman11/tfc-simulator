'use client'

import { useState } from 'react'

interface ConfigPanelProps {
  sender: string
  setSender: (v: string) => void
  password: string
  setPassword: (v: string) => void
}

export default function ConfigPanel({
  sender, setSender,
  password, setPassword,
}: ConfigPanelProps) {
  const [showPass, setShowPass] = useState(false)

  return (
    <div className="card">
      <div className="section-header">
        <span className="section-num">01</span>
        <span className="section-title-text">Sender</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Sender email */}
        <div>
          <label className="field-label">Gmail address</label>
          <input
            type="email"
            value={sender}
            onChange={e => setSender(e.target.value)}
            placeholder="you@gmail.com"
            style={{ padding: '9px 13px' }}
          />
          <p className="field-hint">Must be a Gmail account with SMTP access enabled</p>
        </div>

        {/* App password */}
        <div>
          <label className="field-label" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>App password</span>
            <a
              href="https://myaccount.google.com/apppasswords"
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 11, color: 'var(--blue)', fontWeight: 500, letterSpacing: 0, textTransform: 'none' }}
            >
              Generate ↗
            </a>
          </label>
          <div style={{ position: 'relative' }}>
            <input
              type={showPass ? 'text' : 'password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="xxxx xxxx xxxx xxxx"
              style={{
                padding: '9px 50px 9px 13px',
                fontFamily: "'SF Mono', Consolas, monospace",
                letterSpacing: '0.04em',
              }}
            />
            <button
              type="button"
              onClick={() => setShowPass(p => !p)}
              style={{
                position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', color: 'var(--text-dim)',
                fontSize: 10, fontWeight: 700, cursor: 'pointer', padding: '4px 6px',
                borderRadius: 4, fontFamily: 'inherit', letterSpacing: '0.06em',
                transition: 'color 0.12s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-muted)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-dim)')}
            >
              {showPass ? 'HIDE' : 'SHOW'}
            </button>
          </div>
          <p className="field-hint">16-character Google app password — never your main password</p>
        </div>
      </div>
    </div>
  )
}
