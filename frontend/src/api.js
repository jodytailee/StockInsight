const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_URL = API_URL.replace(/^http/, 'ws') + '/ws'

export async function fetchSymbols() {
  const res = await fetch(`${API_URL}/symbols`)
  if (!res.ok) throw new Error('No se pudieron cargar los símbolos')
  return res.json()
}

export async function addSymbol(ticker, quantity, avgCost) {
  const res = await fetch(`${API_URL}/symbols`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker, quantity, avg_cost: avgCost }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || 'No se pudo agregar el símbolo')
  }
  return res.json()
}

export async function updatePosition(ticker, quantity, avgCost) {
  const res = await fetch(`${API_URL}/symbols/${ticker}/position`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity, avg_cost: avgCost }),
  })
  if (!res.ok) throw new Error('No se pudo actualizar la posición')
  return res.json()
}

export async function fetchPrice(ticker) {
  const res = await fetch(`${API_URL}/symbols/${ticker}/price`)
  if (!res.ok) throw new Error('No se pudo obtener el precio')
  return res.json()
}

export async function removeSymbol(ticker) {
  const res = await fetch(`${API_URL}/symbols/${ticker}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('No se pudo quitar el símbolo')
}

export async function fetchInsights(ticker) {
  const res = await fetch(`${API_URL}/symbols/${ticker}/insights`)
  if (!res.ok) throw new Error('No se pudo obtener el análisis')
  return res.json()
}

export async function fetchNews(ticker) {
  const res = await fetch(`${API_URL}/symbols/${ticker}/news`)
  if (!res.ok) throw new Error('No se pudo obtener las noticias')
  return res.json()
}

export function connectPriceSocket(onMessage) {
  const socket = new WebSocket(WS_URL)
  socket.onmessage = (event) => {
    onMessage(JSON.parse(event.data))
  }
  return socket
}
