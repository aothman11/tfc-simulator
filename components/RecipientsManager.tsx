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
      <div className="section-title" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="dot dot-green" />
          Recipients
          {recipients.length > 0 && (
            <span style={{
              background: 'rgba(76,175,80,0.12)', color: '#4CAF50',
              fontSize: 11, fontWeight: 700, padding: '2px 9px', borderRadius: 100,
            }}>
              {recipients.length}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={() => setBulkMode(b => !b)}
            style={{
              background: bulkMode ? 'rgba(76,175,80,0.12)' : 'none',
              border: `1px solid ${bulkMode ? '#4CAF50' : '#2e3348'}`,
              color: bulkMode ? '#4CAF50' : '#6b7fa3',
              fontSize: 11, fontWeight: 600, cursor: 'pointer',
              padding: '4px 10px', borderRadius: 7, fontFamily: 'inherit',
              transition: 'all 0.12s',
            }}
          >
            Bulk Paste
          </button>
          {recipients.length > 0 && (
            <button
              onClick={clearAll}
              style={{
                background: 'none', border: 'none', color: '#4a5568',
                fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
                padding: '4px 8px', borderRadius: 7, transition: 'color 0.12s',
              }}
            >
              Clear all
            </button>
          )}
        </div>
      </div>

      {/* Single input */}
      {!bulkMode && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
          <input
            type="email"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addEmail()}
            placeholder="recipient@example.com"
            style={{ padding: '10px 14px' }}
          />
          <button
            onClick={addEmail}
            style={{
              background: '#4CAF50', color: 'white', border: 'none',
              borderRadius: 10, padding: '0 18px', height: 41, flexShrink: 0,
              fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = '#43A047')}
            onMouseLeave={e => (e.currentTarget.style.background = '#4CAF50')}
          >
            Add
          </button>
        </div>
      )}

      {/* Bulk mode */}
      {bulkMode && (
        <div style={{ marginBottom: 14 }}>
          <textarea
            value={bulkText}
            onChange={e => setBulkText(e.target.value)}
            placeholder={'alice@example.com\nbob@example.com, carol@example.com'}
            rows={4}
            style={{ padding: '12px 14px', resize: 'none', marginBottom: 8, fontSize: 13 }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={addBulk}
              style={{
                background: '#4CAF50', color: 'white', border: 'none',
                borderRadius: 9, padding: '8px 18px', fontSize: 13,
                fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
              }}
            >
              Add All
            </button>
            <button
              onClick={() => { setBulkMode(false); setBulkText('') }}
              style={{
                background: 'none', border: '1px solid #2e3348', color: '#6b7fa3',
                borderRadius: 9, padding: '8px 14px', fontSize: 13,
                cursor: 'pointer', fontFamily: 'inherit',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Chips */}
      {recipients.length > 0 ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, maxHeight: 148, overflowY: 'auto', paddingBottom: 2 }}>
          {recipients.map(email => (
            <div key={email} className="chip">
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 200 }}>
                {email}
              </span>
              <button className="chip-x" onClick={() => remove(email)}>×</button>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '28px 0', color: '#3d4460', fontSize: 13 }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
            style={{ margin: '0 auto 10px', display: 'block', opacity: 0.4 }}>
            <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
          </svg>
          No recipients yet — add emails above
        </div>
      )}
    </div>
  )
}
