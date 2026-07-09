import { getStored } from './storage.js'

export function getBaseUrl() {
  return getStored('baseUrl', 'http://localhost:8000/api/v1').replace(/\/$/, '')
}

function buildUrl(path, params) {
  const url = new URL(`${getBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
    })
  }
  return url.toString()
}

async function request(path, options = {}) {
  const token = getStored('access_token', '')
  const response = await fetch(buildUrl(path, options.params), {
    method: options.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: options.body ? JSON.stringify(options.body) : undefined
  })
  const text = await response.text()
  const data = text ? JSON.parse(text) : {}
  if (!response.ok) {
    throw new Error(data.detail || data.msg || '请求失败')
  }
  return data
}

export const api = {
  get: (path, params) => request(path, { params }),
  post: (path, body) => request(path, { method: 'POST', body }),
  del: (path) => request(path, { method: 'DELETE' }),
  async streamPost(path, body, onData) {
    const token = getStored('access_token', '')
    const response = await fetch(buildUrl(path), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify(body)
    })
    if (!response.ok || !response.body) throw new Error('AI 服务暂时不可用')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''
      events.forEach((raw) => {
        const data = raw
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.replace(/^data:\s?/, ''))
          .join('\n')
          .trim()
        if (!data) return
        try {
          onData(JSON.parse(data))
        } catch {
          // Ignore malformed stream chunks.
        }
      })
    }
  }
}
