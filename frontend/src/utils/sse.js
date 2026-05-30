export async function streamChat(params, callbacks) {
  const { onChunk, onSources, onDone, onError } = callbacks
  const token = localStorage.getItem('token')

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    })

    if (!response.ok) {
      onError?.(`HTTP ${response.status}`)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let doneReceived = false
    let errorReceived = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const payload = JSON.parse(line.slice(6))
          if (payload.event === 'answer') onChunk?.(payload.data)
          else if (payload.event === 'sources') onSources?.(JSON.parse(payload.data))
          else if (payload.event === 'done') {
            doneReceived = true
            onDone?.(JSON.parse(payload.data))
          } else if (payload.event === 'error') {
            errorReceived = true
            onError?.(payload.data)
          }
        } catch {}
      }
    }

    if (!doneReceived && !errorReceived) {
      onError?.('连接已中断，请稍后重试或检查模型配置。')
    }
  } catch (err) {
    onError?.(err.message || '网络连接失败，请检查服务状态。')
  }
}
