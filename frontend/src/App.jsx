import { useEffect, useState } from 'react'
import {
  addSymbol,
  connectPriceSocket,
  fetchInsights,
  fetchNews,
  fetchPrice,
  fetchSymbols,
  removeSymbol,
  updatePosition,
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

function recommendationClassName(action) {
  if (action === 'Comprar' || action === 'Comprar más') return 'rating-buy'
  if (action === 'Vender' || action === 'Evitar') return 'rating-sell'
  return 'rating-neutral'
}

function MlCell({ ml }) {
  if (!ml) return <td className="muted">Sin modelo</td>
  const pct = Math.round(ml.probability_up * 100)
  const className = pct >= 55 ? 'sentiment-positive' : pct <= 45 ? 'sentiment-negative' : 'sentiment-neutral'
  const accuracyPct = ml.test_accuracy != null ? Math.round(ml.test_accuracy * 100) : null
  return (
    <td className={className}>
      {pct}% sube
      {accuracyPct != null && <div className="ml-accuracy">acc. hist. {accuracyPct}%</div>}
    </td>
  )
}

function RecommendationCard({ label, rec }) {
  if (!rec) return null
  return (
    <div className={`rec-card ${recommendationClassName(rec.action)}`}>
      <div className="rec-label">{label}</div>
      <div className="rec-action">{rec.action}</div>
      <div className="rec-return">{rec.expected_return_pct >= 0 ? '+' : ''}{rec.expected_return_pct}%</div>
    </div>
  )
}

function PositionSection({ ticker, insight, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [quantity, setQuantity] = useState('')
  const [avgCost, setAvgCost] = useState('')

  function startEdit() {
    setQuantity(insight?.quantity ?? '')
    setAvgCost(insight?.avg_cost ?? '')
    setEditing(true)
  }

  async function save(e) {
    e.preventDefault()
    await onUpdate(ticker, quantity === '' ? null : Number(quantity), avgCost === '' ? null : Number(avgCost))
    setEditing(false)
  }

  const hasPosition = insight?.quantity != null && insight?.avg_cost != null

  return (
    <div className="position-box">
      {editing ? (
        <form onSubmit={save} className="position-form">
          <label>
            Cantidad
            <input type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </label>
          <label>
            Precio promedio
            <input type="number" step="any" value={avgCost} onChange={(e) => setAvgCost(e.target.value)} />
          </label>
          <button type="submit">Guardar</button>
          <button type="button" onClick={() => setEditing(false)}>Cancelar</button>
        </form>
      ) : (
        <div className="position-summary">
          {hasPosition ? (
            <>
              <span>
                {insight.quantity} acciones @ ${insight.avg_cost.toFixed(2)}
              </span>
              {insight.unrealized_pnl_pct != null && (
                <span className={insight.unrealized_pnl_pct >= 0 ? 'sentiment-positive' : 'sentiment-negative'}>
                  {insight.unrealized_pnl_pct >= 0 ? '+' : ''}{insight.unrealized_pnl_pct}% no realizado
                </span>
              )}
            </>
          ) : (
            <span className="muted">Sin posición registrada</span>
          )}
          <button type="button" onClick={startEdit}>Editar posición</button>
        </div>
      )}

      {insight && (
        <div className="rec-cards">
          <RecommendationCard label="1 semana" rec={insight.recommendation_1w} />
          <RecommendationCard label="1 mes" rec={insight.recommendation_1m} />
          <RecommendationCard label="1 año" rec={insight.recommendation_1y} />
        </div>
      )}
    </div>
  )
}

function App() {
  const [symbols, setSymbols] = useState([])
  const [prices, setPrices] = useState({})
  const [news, setNews] = useState({})
  const [insights, setInsights] = useState({})
  const [tickerInput, setTickerInput] = useState('')
  const [quantityInput, setQuantityInput] = useState('')
  const [avgCostInput, setAvgCostInput] = useState('')
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

  async function handleUpdatePosition(ticker, quantity, avgCost) {
    try {
      await updatePosition(ticker, quantity, avgCost)
      loadInsights(ticker)
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
      const quantity = quantityInput === '' ? null : Number(quantityInput)
      const avgCost = avgCostInput === '' ? null : Number(avgCostInput)
      const symbol = await addSymbol(ticker, quantity, avgCost)
      setSymbols((prev) =>
        prev.some((s) => s.ticker === symbol.ticker) ? prev : [...prev, symbol]
      )
      const price = await fetchPrice(symbol.ticker)
      setPrices((prev) => ({ ...prev, [symbol.ticker]: price }))
      const items = await fetchNews(symbol.ticker)
      setNews((prev) => ({ ...prev, [symbol.ticker]: items }))
      loadInsights(symbol.ticker)
      setTickerInput('')
      setQuantityInput('')
      setAvgCostInput('')
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
        <input
          type="number"
          step="any"
          placeholder="Cantidad (opcional)"
          value={quantityInput}
          onChange={(e) => setQuantityInput(e.target.value)}
        />
        <input
          type="number"
          step="any"
          placeholder="Precio promedio (opcional)"
          value={avgCostInput}
          onChange={(e) => setAvgCostInput(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Agregando...' : 'Agregar símbolo'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      <p className="muted preliminary-note">
        Los precios objetivo y las recomendaciones (1sem/1mes/1año) son una{' '}
        <strong>estimación preliminar</strong> basada en tendencia reciente + sentimiento de
        noticias, no el modelo ML. Las columnas "ML" sí son un modelo entrenado (Random Forest
        sobre indicadores técnicos), pero con pocos datos todavía — el accuracy histórico
        mostrado es bajo, tómalo como experimental.
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
              <th>ML 1 día</th>
              <th>ML 1 sem</th>
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
                  <MlCell ml={insight?.ml_direction_1d} />
                  <MlCell ml={insight?.ml_direction_1w} />
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
        <section key={s.ticker} className="symbol-detail">
          <h2>{s.ticker}</h2>
          <PositionSection ticker={s.ticker} insight={insights[s.ticker]} onUpdate={handleUpdatePosition} />

          <h3>Noticias</h3>
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
