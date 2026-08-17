import { useEffect, useState } from 'react'
import {
  addSymbol,
  connectPriceSocket,
  fetchInsights,
  fetchNews,
  fetchPrice,
  fetchSymbols,
  removeSymbol,
} from './api'
import './App.css'

function sentimentLabel(score) {
  if (score == null) return { text: '—', className: 'sentiment-neutral' }
  if (score > 0.2) return { text: 'Positiva', className: 'sentiment-positive' }
  if (score < -0.2) return { text: 'Negativa', className: 'sentiment-negative' }
  return { text: 'Neutral', className: 'sentiment-neutral' }
}

function ratingClassName(rating) {
  if (rating === 'Strong Buy' || rating === 'Buy') return 'rating-buy'
  if (rating === 'Strong Sell' || rating === 'Sell') return 'rating-sell'
  return 'rating-neutral'
}

function App() {
  const [symbols, setSymbols] = useState([])
  const [prices, setPrices] = useState({})
  const [news, setNews] = useState({})
  const [insights, setInsights] = useState({})
  const [tickerInput, setTickerInput] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function loadInsights(ticker) {
    fetchInsights(ticker)
      .then((data) => setInsights((prev) => ({ ...prev, [ticker]: data })))
      .catch(() => {})
  }

  useEffect(() => {
    fetchSymbols()
      .then((data) => {
        setSymbols(data)
        data.forEach((s) => {
          fetchPrice(s.ticker)
            .then((p) => setPrices((prev) => ({ ...prev, [s.ticker]: p })))
            .catch(() => {})
          fetchNews(s.ticker)
            .then((items) => setNews((prev) => ({ ...prev, [s.ticker]: items })))
            .catch(() => {})
          loadInsights(s.ticker)
        })
      })
      .catch((e) => setError(e.message))

    const socket = connectPriceSocket((msg) => {
      if (msg.type === 'news') {
        setNews((prev) => {
          const existing = prev[msg.ticker] || []
          if (existing.some((n) => n.url === msg.url)) return prev
          return { ...prev, [msg.ticker]: [msg, ...existing].slice(0, 20) }
        })
        loadInsights(msg.ticker)
      } else {
        setPrices((prev) => ({
          ...prev,
          [msg.ticker]: { price: msg.price, fetched_at: msg.fetched_at },
        }))
        loadInsights(msg.ticker)
      }
    })
    return () => socket.close()
  }, [])

  async function handleRemoveSymbol(ticker) {
    try {
      await removeSymbol(ticker)
      setSymbols((prev) => prev.filter((s) => s.ticker !== ticker))
      setPrices((prev) => {
        const { [ticker]: _removed, ...rest } = prev
        return rest
      })
      setNews((prev) => {
        const { [ticker]: _removed, ...rest } = prev
        return rest
      })
      setInsights((prev) => {
        const { [ticker]: _removed, ...rest } = prev
        return rest
      })
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleAddSymbol(e) {
    e.preventDefault()
    const ticker = tickerInput.trim().toUpperCase()
    if (!ticker) return

    setLoading(true)
    setError('')
    try {
      const symbol = await addSymbol(ticker)
      setSymbols((prev) =>
        prev.some((s) => s.ticker === symbol.ticker) ? prev : [...prev, symbol]
      )
      const price = await fetchPrice(symbol.ticker)
      setPrices((prev) => ({ ...prev, [symbol.ticker]: price }))
      const items = await fetchNews(symbol.ticker)
      setNews((prev) => ({ ...prev, [symbol.ticker]: items }))
      loadInsights(symbol.ticker)
      setTickerInput('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="dashboard">
      <h1>StockInsight</h1>

      <form onSubmit={handleAddSymbol} className="add-symbol-form">
        <input
          type="text"
          placeholder="Ej. AAPL"
          value={tickerInput}
          onChange={(e) => setTickerInput(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Agregando...' : 'Agregar símbolo'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      <p className="muted preliminary-note">
        Los precios objetivo (1sem/1mes/1año) son una <strong>estimación preliminar</strong>{' '}
        basada en tendencia reciente + sentimiento de noticias — todavía no es el modelo de
        Machine Learning planeado, que requiere más histórico propio para entrenarse.
      </p>

      <div className="table-scroll">
        <table className="symbol-table">
          <thead>
            <tr>
              <th>Símbolo</th>
              <th>Precio</th>
              <th>Actualizado</th>
              <th>Sentimiento corto</th>
              <th>Sentimiento medio</th>
              <th>Sentimiento largo</th>
              <th>Analistas</th>
              <th>Target 1sem</th>
              <th>Target 1mes</th>
              <th>Target 1año</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {symbols.map((s) => {
              const insight = insights[s.ticker]
              const shortS = sentimentLabel(insight?.sentiment_short_term)
              const medS = sentimentLabel(insight?.sentiment_medium_term)
              const longS = sentimentLabel(insight?.sentiment_long_term)
              return (
                <tr key={s.ticker}>
                  <td>{s.ticker}</td>
                  <td>{prices[s.ticker] ? `$${prices[s.ticker].price.toFixed(2)}` : '—'}</td>
                  <td>
                    {prices[s.ticker]
                      ? new Date(prices[s.ticker].fetched_at).toLocaleTimeString()
                      : '—'}
                  </td>
                  <td className={shortS.className}>{shortS.text}</td>
                  <td className={medS.className}>{medS.text}</td>
                  <td className={longS.className}>{longS.text}</td>
                  <td className={insight ? ratingClassName(insight.analyst_rating) : ''}>
                    {insight?.analyst_rating ?? '—'}
                  </td>
                  <td>{insight ? `$${insight.target_price_1w.toFixed(2)}` : '—'}</td>
                  <td>{insight ? `$${insight.target_price_1m.toFixed(2)}` : '—'}</td>
                  <td>{insight ? `$${insight.target_price_1y.toFixed(2)}` : '—'}</td>
                  <td>
                    <button type="button" className="remove-btn" onClick={() => handleRemoveSymbol(s.ticker)}>
                      Quitar
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {symbols.map((s) => (
        <section key={s.ticker} className="news-section">
          <h2>Noticias — {s.ticker}</h2>
          {(news[s.ticker] || []).length === 0 && <p className="muted">Sin noticias todavía.</p>}
          <ul className="news-list">
            {(news[s.ticker] || []).map((item) => {
              const sentiment = sentimentLabel(item.sentiment_score)
              return (
                <li key={item.url} className="news-item">
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.headline}
                  </a>
                  <div className="news-meta">
                    <span>{item.source}</span>
                    <span>{new Date(item.published_at).toLocaleString()}</span>
                    <span className={sentiment.className}>{sentiment.text}</span>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </div>
  )
}

export default App
