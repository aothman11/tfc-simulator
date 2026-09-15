'use client'

import { useState } from 'react'

interface EmailEditorProps {
  body: string
  setBody: (v: string) => void
  subject: string
  setSubject: (v: string) => void
  sender: string
  recipientCount: number
}

export default function EmailEditor({ body, setBody, subject, setSubject, sender, recipientCount }: EmailEditorProps) {
  const [tab, setTab] = useState<'edit' | 'preview'>('edit')

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <span className="section-title-text">Email</span>
        <div className="tab-group">
          <button
            className={`tab-btn${tab === 'edit' ? ' active' : ''}`}
            onClick={() => setTab('edit')}
          >
            Edit
          </button>
          <button
            className={`tab-btn${tab === 'preview' ? ' active' : ''}`}
            onClick={() => setTab('preview')}
          >
            Preview
          </button>
        </div>
      </div>

      {tab === 'edit' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Subject */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <label className="field-label" style={{ margin: 0 }}>Subject</label>
              {subject.length > 0 && (
                <span style={{ fontSize: 11, color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums' }}>
                  {subject.length} chars
                </span>
              )}
            </div>
            <input
              type="text"
              value={subject}
              onChange={e => setSubject(e.target.value)}
              placeholder="e.g. Application for Software Engineer Role"
              style={{ padding: '10px 13px', fontSize: 14 }}
            />
          </div>

          {/* Body */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <label className="field-label" style={{ margin: 0 }}>Message body</label>
              {body.length > 0 && (
                <span style={{ fontSize: 11, color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums' }}>
                  {body.length.toLocaleString()} chars
                </span>
              )}
            </div>
            <textarea
              value={body}
              onChange={e => setBody(e.target.value)}
              placeholder={'Dear Hiring Manager,\n\nI am writing to express my interest in the position…'}
              rows={11}
              style={{
                padding: '13px 14px',
                resize: 'vertical',
                lineHeight: 1.7,
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                fontSize: 14,
                letterSpacing: '0.01em',
              }}
            />
            <p className="field-hint">Plain text · HTML tags are not rendered</p>
          </div>
        </div>
      ) : (
        <div className="email-preview animate-fade-in">
          <div className="preview-header">
            <div className="preview-field">
              <span className="preview-field-label">From</span>
              <span className="preview-field-value" style={{ color: sender ? 'var(--text)' : 'var(--text-dim)', fontStyle: sender ? 'normal' : 'italic' }}>
                {sender || 'not set'}
              </span>
            </div>
            <div className="preview-field">
              <span className="preview-field-label">To</span>
              <span className="preview-field-value" style={{ color: recipientCount > 0 ? 'var(--text)' : 'var(--text-dim)', fontStyle: recipientCount > 0 ? 'normal' : 'italic' }}>
                {recipientCount > 0 ? `${recipientCount} recipient${recipientCount !== 1 ? 's' : ''}` : 'no recipients added'}
              </span>
            </div>
            <div className="preview-field">
              <span className="preview-field-label">Subject</span>
              <span className="preview-field-value" style={{ color: subject ? 'var(--text)' : 'var(--text-dim)', fontStyle: subject ? 'normal' : 'italic', fontWeight: subject ? 500 : 400 }}>
                {subject || 'no subject'}
              </span>
            </div>
          </div>
          {body ? (
            <div className="preview-body">{body}</div>
          ) : (
            <div className="preview-empty">No message body yet</div>
          )}
        </div>
      )}
    </div>
  )
}
