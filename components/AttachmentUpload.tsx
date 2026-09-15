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
      <div className="section-title" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="dot dot-green" />
          CV / Attachment
        </div>
        <span style={{ fontSize: 11, color: '#3d4460', fontWeight: 400 }}>
          Optional · PDF · max 10 MB
        </span>
      </div>

      {file ? (
        <div
          className="animate-fade-in"
          style={{
            display: 'flex', alignItems: 'center', gap: 12,
            background: '#1e2235', borderRadius: 13,
            border: '1px solid rgba(76,175,80,0.2)', padding: '14px 16px',
          }}
        >
          {/* PDF icon */}
          <div style={{
            width: 38, height: 38, borderRadius: 9,
            background: 'rgba(239,68,68,0.12)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#f87171">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z" />
            </svg>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {file.name}
            </div>
            <div style={{ fontSize: 11, color: '#6b7fa3', marginTop: 2 }}>{fmt(file.size)}</div>
          </div>
          <button
            onClick={() => { setFile(null); if (inputRef.current) inputRef.current.value = '' }}
            style={{ background: 'none', border: 'none', color: '#4a5568', fontSize: 20, cursor: 'pointer', padding: '0 2px', lineHeight: 1, transition: 'color 0.12s' }}
            onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
            onMouseLeave={e => (e.currentTarget.style.color = '#4a5568')}
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
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#3d4460" strokeWidth="1.5" strokeLinecap="round"
            style={{ margin: '0 auto 12px', display: 'block' }}>
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <div style={{ fontSize: 14, color: '#6b7fa3' }}>
            Drop your PDF here, or <span style={{ color: '#4CAF50', fontWeight: 600 }}>browse</span>
          </div>
          <div style={{ fontSize: 12, color: '#3d4460', marginTop: 6 }}>Attached to every email in this batch</div>
        </div>
      )}

      <input ref={inputRef} type="file" accept=".pdf,application/pdf" onChange={handleChange} style={{ display: 'none' }} />
    </div>
  )
}
