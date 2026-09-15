import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Email Sender',
  description: 'Gmail SMTP bulk email sender',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen" style={{ background: '#0f1117' }}>{children}</body>
    </html>
  )
}
