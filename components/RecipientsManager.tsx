'use client'

import { useState } from 'react'

interface RecipientsManagerProps {
  recipients: string[]
  setRecipients: (v: string[]) => void
}

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
}

export default function RecipientsManager({ recipients, setRecipients }: RecipientsManagerProps) {
  const [input, setInput] = useState('')
  const [bulkMode, setBulkMode] = useState(false)
  const [bulkText, setBulkText] = useState('')

  const addEmail = () => {
    const email = input.trim()
    if (!email || !isValidEmail(email)) return
    if (recipients.includes(email)) return
    setRecipients([...recipients, email])
    setInput('')
  }

  const addBulk = () => {
    const lines = bulkText.split(/[\n,]+/).map(e => e.trim()).filter(Boolean)
    const valid = lines.filter(isValidEmail)
    const newEmails = valid.filter(e => !recipients.includes(e))
    setRecipients([...recipients, ...newEmails])
    setBulkText('')
    setBulkMode(false)
  }

  const remove = (email: string) => setRecipients(recipients.filter(e => e !== email))
  const clearAll = () => { if (confirm('Remove all recipients?')) setRecipients([]) }

  return (
    <div className="card">
      {/* Header */}
      <div className="section-header-row">
        <div className="section-header-left">
          <div className="section-header" style={{ margin: 0 }}>
            <span className="section-num">02</span>
            <span className="section-title-text">Recipients</span>
          </div>
          {recipients.length > 0 && (
            <span style={{
              background: 'var(--surface3)',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
              fontSize: 11, fontWeight: 600,
              padding: '2px 9px', borderRadius: 100,
              fontVariantNumeric: 'tabular-nums',
            }}>
              {recipients.length}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <button
            onClick={() => setBulkMode(b => !b)}
            className="btn-ghost"
            style={{
              fontSize: 11, padding: '4px 10px',
              ...(bulkMode ? {
                background: 'var(--surface2)',
                borderColor: 'var(--border-focus)',
                color: 'var(--text)',
              } : {}),
            }}
          >
            Bulk paste
          </button>
          {recipients.length > 0 && (
            <button
              onClick={clearAll}
              style={{
                background: 'none', border: 'none',
                color: 'var(--text-dim)', fontSize: 12,
                cursor: 'pointer', fontFamily: 'inherit',
                padding: '4px 6px', borderRadius: 6,
                transition: 'color 0.12s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--red)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-dim)')}
            >
              Clear all
            </button>
          )}
        </div>
      </div>

      {/* Single input */}
      {!bulkMode && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <input
            type="email"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addEmail()}
            placeholder="recipient@example.com"
            style={{ padding: '9px 13px' }}
          />
          <button
            onClick={addEmail}
            style={{
              background: 'var(--surface3)',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
              borderRadius: 8, padding: '0 16px', height: 39, flexShrink: 0,
              fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
              transition: 'border-color 0.15s, color 0.15s, background 0.15s',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'var(--primary)'
              e.currentTarget.style.color = 'var(--primary)'
              e.currentTarget.style.background = 'var(--primary-bg)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'var(--border)'
              e.currentTarget.style.color = 'var(--text-muted)'
              e.currentTarget.style.background = 'var(--surface3)'
            }}
          >
            Add
          </button>
        </div>
      )}

      {/* Bulk mode */}
      {bulkMode && (
        <div style={{ marginBottom: 12 }}>
          <textarea
            value={bulkText}
            onChange={e => setBulkText(e.target.value)}
            placeholder={'alice@example.com\nbob@example.com, carol@example.com'}
            rows={4}
            style={{ padding: '11px 13px', resize: 'none', marginBottom: 8, fontSize: 13 }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={addBulk}
              style={{
                background: 'var(--primary)', color: 'white', border: 'none',
                borderRadius: 7, padding: '7px 16px', fontSize: 13,
                fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
              }}
            >
              Add all
            </button>
            <button
              onClick={() => { setBulkMode(false); setBulkText('') }}
              className="btn-ghost"
              style={{ fontSize: 13, padding: '7px 13px' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Recipient list */}
      {recipients.length > 0 ? (
        <div className="recipient-list">
          {recipients.map(email => (
            <div key={email} className="recipient-row">
              <span className="recipient-check">✓</span>
              <span className="recipient-email">{email}</span>
              <button className="recipient-remove" onClick={() => remove(email)} title="Remove">×</button>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '28px 0 20px', color: 'var(--text-dim)', fontSize: 13 }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
            style={{ margin: '0 auto 10px', display: 'block', opacity: 0.35 }}>
            <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
          </svg>
          Add recipients above to get started
        </div>
      )}
    </div>
  )
}
