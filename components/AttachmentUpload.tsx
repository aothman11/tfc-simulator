'use client'

import { useRef } from 'react'

interface AttachmentUploadProps {
  file: File | null
  setFile: (f: File | null) => void
}

export default function AttachmentUpload({ file, setFile }: AttachmentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (f.type !== 'application/pdf') { alert('Only PDF files are allowed.'); return }
    if (f.size > 10 * 1024 * 1024) { alert('File size must be under 10 MB.'); return }
    setFile(f)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (!f) return
    if (f.type !== 'application/pdf') { alert('Only PDF files are allowed.'); return }
    if (f.size > 10 * 1024 * 1024) { alert('File size must be under 10 MB.'); return }
    setFile(f)
  }

  const fmt = (b: number) =>
    b < 1024 ? `${b} B` : b < 1024 * 1024 ? `${(b / 1024).toFixed(1)} KB` : `${(b / (1024 * 1024)).toFixed(1)} MB`

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
        <span className="section-title-text">Attachment</span>
        <span style={{ fontSize: 11, color: 'var(--text-dim)', fontWeight: 400 }}>
          Optional · PDF · max 10 MB
        </span>
      </div>

      {file ? (
        <div
          className="animate-fade-in"
          style={{
            display: 'flex', alignItems: 'center', gap: 12,
            background: 'var(--surface2)', borderRadius: 10,
            border: '1px solid var(--border)', padding: '12px 14px',
          }}
        >
          {/* PDF icon */}
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: 'var(--red-bg)',
            border: '1px solid var(--red-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="#ef4444">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z" />
            </svg>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {file.name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{fmt(file.size)}</div>
          </div>
          <button
            onClick={() => { setFile(null); if (inputRef.current) inputRef.current.value = '' }}
            style={{
              background: 'none', border: 'none', color: 'var(--text-dim)',
              fontSize: 18, cursor: 'pointer', padding: '2px 4px',
              lineHeight: 1, transition: 'color 0.12s', fontFamily: 'inherit',
              borderRadius: 4,
            }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--red)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-dim)')}
            title="Remove attachment"
          >
            ×
          </button>
        </div>
      ) : (
        <div
          className="drop-zone"
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          onClick={() => inputRef.current?.click()}
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="1.5" strokeLinecap="round"
            style={{ margin: '0 auto 10px', display: 'block' }}>
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Drop a PDF here, or <span style={{ color: 'var(--primary)', fontWeight: 500 }}>browse</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 5 }}>
            Attached to every email in this batch
          </div>
        </div>
      )}

      <input ref={inputRef} type="file" accept=".pdf,application/pdf" onChange={handleChange} style={{ display: 'none' }} />
    </div>
  )
}
