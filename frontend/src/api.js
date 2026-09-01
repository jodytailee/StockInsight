const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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

export async function fetchLots(ticker) {
  const res = await fetch(`${API_URL}/symbols/${ticker}/lots`)
  if (!res.ok) throw new Error('No se pudieron cargar los lotes')
  return res.json()
}

export async function addLot(ticker, quantity, price, purchasedAt) {
  const res = await fetch(`${API_URL}/symbols/${ticker}/lots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity, price, purchased_at: purchasedAt || null }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || 'No se pudo agregar el lote')
  }
  return res.json()
}

export async function updateLot(ticker, lotId, quantity, price, purchasedAt) {
  const res = await fetch(`${API_URL}/symbols/${ticker}/lots/${lotId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity, price, purchased_at: purchasedAt || null }),
  })
  if (!res.ok) throw new Error('No se pudo editar el lote')
  return res.json()
}

export async function removeLot(ticker, lotId) {
  const res = await fetch(`${API_URL}/symbols/${ticker}/lots/${lotId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('No se pudo quitar el lote')
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

export async function fetchAiAnalysis(ticker, refresh = false) {
  const url = `${API_URL}/symbols/${ticker}/analysis${refresh ? '?refresh=true' : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('No se pudo generar el análisis de IA')
  return res.json()
}

export async function fetchNews(ticker) {
  const res = await fetch(`${API_URL}/symbols/${ticker}/news`)
  if (!res.ok) throw new Error('No se pudo obtener las noticias')
  return res.json()
}

