'use client'

interface EmailEditorProps {
  body: string
  setBody: (v: string) => void
}

export default function EmailEditor({ body, setBody }: EmailEditorProps) {
  return (
    <div className="card">
      <div className="section-title" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="dot dot-green" />
          Email Body
        </div>
        <span style={{ fontSize: 12, color: '#3d4460', fontWeight: 400 }}>
          {body.length.toLocaleString()} chars
        </span>
      </div>
      <textarea
        value={body}
        onChange={e => setBody(e.target.value)}
        placeholder={'Dear Hiring Manager,\n\nI am writing to express my interest in the position…'}
        rows={10}
        style={{
          padding: '13px 15px',
          resize: 'vertical',
          lineHeight: 1.65,
          fontFamily: "'SF Mono', 'Cascadia Code', Consolas, monospace",
          fontSize: 13,
        }}
      />
      <div style={{ marginTop: 8, fontSize: 11, color: '#3d4460' }}>
        Plain text · formatting not supported
      </div>
    </div>
  )
}
