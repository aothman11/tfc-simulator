import { NextRequest } from 'next/server'
import nodemailer from 'nodemailer'

export const runtime = 'nodejs'
export const maxDuration = 300 // 5 minutes

interface SendEmailsPayload {
  sender: string
  password: string
  subject: string
  body: string
  recipients: string[]
  attachment?: { name: string; data: string } // base64
  delay: number
  scheduledAt?: string // ISO string, optional
}

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
}

function sseMessage(data: object): string {
  return `data: ${JSON.stringify(data)}\n\n`
}

export async function POST(req: NextRequest) {
  let payload: SendEmailsPayload

  try {
    payload = await req.json()
  } catch {
    return new Response('Invalid JSON body', { status: 400 })
  }

  const { sender, password, subject, body, recipients, attachment, delay, scheduledAt } = payload

  // Validate required fields
  if (!sender || !password || !subject || !body) {
    return new Response('Missing required fields: sender, password, subject, body', { status: 400 })
  }
  if (!validateEmail(sender)) {
    return new Response('Invalid sender email address', { status: 400 })
  }
  if (!Array.isArray(recipients) || recipients.length === 0) {
    return new Response('recipients must be a non-empty array', { status: 400 })
  }

  const validRecipients = recipients.filter(validateEmail)
  if (validRecipients.length === 0) {
    return new Response('No valid recipient email addresses', { status: 400 })
  }

  const delayMs = Math.max(0, Math.min(Number(delay) || 5, 60)) * 1000

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      const send = (data: object) => {
        controller.enqueue(encoder.encode(sseMessage(data)))
      }

      // If scheduled, wait until the scheduled time
      if (scheduledAt) {
        const scheduledTime = new Date(scheduledAt).getTime()
        const now = Date.now()
        if (scheduledTime > now) {
          const waitMs = scheduledTime - now
          const waitSecs = Math.ceil(waitMs / 1000)
          send({ type: 'scheduled', waitSeconds: waitSecs, scheduledAt })

          // Stream countdown every second (up to 3600s to avoid indefinite hold)
          const maxWait = Math.min(waitMs, 3600 * 1000)
          const start = Date.now()
          while (Date.now() - start < maxWait) {
            const remaining = Math.ceil((scheduledTime - Date.now()) / 1000)
            if (remaining <= 0) break
            send({ type: 'countdown', remaining })
            await new Promise((r) => setTimeout(r, 1000))
          }
        }
      }

      // Create transporter — credentials used only in-memory for this request
      let transporter: nodemailer.Transporter
      try {
        transporter = nodemailer.createTransport({
          host: 'smtp.gmail.com',
          port: 465,
          secure: true,
          auth: { user: sender, pass: password },
        })
        await transporter.verify()
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err)
        send({ type: 'error', message: `SMTP authentication failed: ${msg}` })
        controller.close()
        return
      }

      send({ type: 'start', total: validRecipients.length })

      let sentCount = 0
      let failedCount = 0

      for (let i = 0; i < validRecipients.length; i++) {
        const recipient = validRecipients[i].trim()

        try {
          const mailOptions: nodemailer.SendMailOptions = {
            from: sender,
            to: recipient,
            subject,
            text: body,
          }

          if (attachment?.data && attachment?.name) {
            mailOptions.attachments = [
              {
                filename: attachment.name,
                content: Buffer.from(attachment.data, 'base64'),
                contentType: 'application/pdf',
              },
            ]
          }

          await transporter.sendMail(mailOptions)
          sentCount++
          send({ type: 'sent', email: recipient, index: i + 1, total: validRecipients.length, sentCount, failedCount })
        } catch (err: unknown) {
          const reason = err instanceof Error ? err.message : String(err)
          failedCount++
          send({ type: 'failed', email: recipient, reason, index: i + 1, total: validRecipients.length, sentCount, failedCount })
        }

        // Delay between emails (skip after last one)
        if (i < validRecipients.length - 1 && delayMs > 0) {
          const delaySecs = delayMs / 1000
          send({ type: 'waiting', seconds: delaySecs })
          await new Promise((r) => setTimeout(r, delayMs))
        }
      }

      send({ type: 'done', total: validRecipients.length, sentCount, failedCount })
      controller.close()
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  })
}
