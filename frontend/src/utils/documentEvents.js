const listeners = new Set()

let controller = null
let reconnectTimer = null
let started = false

function notify(payload) {
  listeners.forEach(listener => listener(payload))
}

function scheduleReconnect() {
  if (!started || reconnectTimer) return
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null
    connect()
  }, 3000)
}

async function connect() {
  if (controller) return

  const token = localStorage.getItem('token')
  if (!token) {
    scheduleReconnect()
    return
  }

  controller = new AbortController()

  try {
    const response = await fetch('/api/documents/events', {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'text/event-stream',
      },
      signal: controller.signal,
    })

    if (!response.ok || !response.body) {
      controller = null
      scheduleReconnect()
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (started) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''

      for (const chunk of chunks) {
        const eventLine = chunk.split('\n').find(line => line.startsWith('event: '))
        const dataLine = chunk.split('\n').find(line => line.startsWith('data: '))
        if (!dataLine) continue

        try {
          notify({
            event: eventLine ? eventLine.slice(7) : 'message',
            data: JSON.parse(dataLine.slice(6)),
          })
        } catch {}
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.warn('[DocumentEvents] stream disconnected:', err.message)
    }
  } finally {
    controller = null
    if (started) scheduleReconnect()
  }
}

export function subscribeDocumentEvents(listener) {
  listeners.add(listener)
  started = true
  connect()

  return () => {
    listeners.delete(listener)
    if (listeners.size > 0) return

    started = false
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (controller) {
      controller.abort()
      controller = null
    }
  }
}
