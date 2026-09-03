import { useEffect, useState } from 'react'
import {
  addLot,
  addSymbol,
  fetchAiAnalysis,
  fetchInsights,
  fetchLots,
  fetchMarketNews,
  fetchNews,
  fetchPrice,
  fetchSymbols,
  removeLot,
  removeSymbol,
  updateLot,
} from './api'
import './App.css'

const TOPIC_LABELS = {
  earnings: 'Earnings',
  macro_rates: 'Tasas/macro',
  geopolitics: 'Geopolítica',
  regulation: 'Regulación',
  supply_chain: 'Cadena de suministro',
  product: 'Producto',
  m_and_a: 'Fusión/Adquisición',
  leadership: 'Liderazgo',
  market_sentiment: 'Sentimiento de mercado',
  other: 'Otro',
}

function topicLabel(topic) {
  return TOPIC_LABELS[topic] || topic
}

function impactLabel(direction) {
  if (direction === 'up') return 'Alcista'
  if (direction === 'down') return 'Bajista'
  return 'Neutral'
}

function impactClassName(direction) {
  if (direction === 'up') return 'sentiment-positive'
  if (direction === 'down') return 'sentiment-negative'
  return 'sentiment-neutral'
}

function Logo() {
  return (
    <svg width="36" height="36" viewBox="0 0 64 64" className="logo-icon">
      <defs>
        <linearGradient id="chartGrad" x1="0" y1="64" x2="64" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#1e3a8a" />
          <stop offset="1" stopColor="#67e8f9" />
        </linearGradient>
      </defs>
      <path
        d="M4 46 L16 34 L24 42 L34 20 L42 28 L58 8"
        fill="none"
        stroke="url(#chartGrad)"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M48 8 L58 8 L58 18"
        fill="none"
        stroke="url(#chartGrad)"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <ellipse cx="24" cy="46" rx="18" ry="10" fill="none" stroke="url(#chartGrad)" strokeWidth="4" />
      <circle cx="24" cy="46" r="5" fill="url(#chartGrad)" />
    </svg>
  )
}

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

function toDateInputValue(isoString) {
  return new Date(isoString).toISOString().slice(0, 10)
}

function LotRow({ ticker, lot, onChanged, onError }) {
  const [editing, setEditing] = useState(false)
  const [quantity, setQuantity] = useState(lot.quantity)
  const [price, setPrice] = useState(lot.price)
  const [purchasedAt, setPurchasedAt] = useState(toDateInputValue(lot.purchased_at))

  async function save(e) {
    e.preventDefault()
    try {
      await updateLot(ticker, lot.id, Number(quantity), Number(price), purchasedAt || null)
      setEditing(false)
      onChanged()
    } catch (err) {
      onError(err.message)
    }
  }

  async function handleRemove() {
    try {
      await removeLot(ticker, lot.id)
      onChanged()
    } catch (err) {
      onError(err.message)
    }
  }

  if (editing) {
    return (
      <li>
        <form onSubmit={save} className="lot-edit-form">
          <input type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          <input type="number" step="any" value={price} onChange={(e) => setPrice(e.target.value)} />
          <input type="date" value={purchasedAt} onChange={(e) => setPurchasedAt(e.target.value)} />
          <button type="submit">Guardar</button>
          <button type="button" onClick={() => setEditing(false)}>Cancelar</button>
        </form>
      </li>
    )
  }

  return (
    <li>
      <span>
        {lot.quantity} @ ${lot.price.toFixed(2)} — {new Date(lot.purchased_at).toLocaleDateString()}
      </span>
      <span className="lot-actions">
        <button type="button" className="remove-btn small" onClick={() => setEditing(true)}>
          Editar
        </button>
        <button type="button" className="remove-btn small" onClick={handleRemove}>
          Quitar
        </button>
      </span>
    </li>
  )
}

function fmt(value, suffix = '') {
  return value == null ? '—' : `${value}${suffix}`
}

function FundamentalsSection({ fundamentals }) {
  if (!fundamentals) return null
  const f = fundamentals

  return (
    <div className="fundamentals-box">
      <h3 style={{ marginTop: 0 }}>Fundamentales{f.industry ? ` — ${f.industry}` : ''}</h3>
      <div className="fundamentals-grid">
        <div><span className="muted">P/E (TTM)</span><div>{fmt(f.pe_ttm)}</div></div>
        <div><span className="muted">P/E forward</span><div>{fmt(f.forward_pe)}</div></div>
        <div><span className="muted">PEG</span><div>{fmt(f.peg_ttm)}</div></div>
        <div><span className="muted">EPS (TTM)</span><div>{fmt(f.eps_ttm)}</div></div>
        <div><span className="muted">Cash flow/acción</span><div>{fmt(f.cash_flow_per_share_ttm)}</div></div>
        <div><span className="muted">Margen bruto</span><div>{fmt(f.gross_margin_ttm, '%')}</div></div>
        <div><span className="muted">Margen neto</span><div>{fmt(f.net_profit_margin_ttm, '%')}</div></div>
        <div><span className="muted">ROE</span><div>{fmt(f.roe_ttm, '%')}</div></div>
        <div><span className="muted">ROA</span><div>{fmt(f.roa_ttm, '%')}</div></div>
        <div><span className="muted">Deuda/Equity</span><div>{fmt(f.debt_to_equity)}</div></div>
        <div><span className="muted">Dividend yield</span><div>{fmt(f.dividend_yield_ttm, '%')}</div></div>
        <div><span className="muted">Beta</span><div>{fmt(f.beta)}</div></div>
        <div><span className="muted">Market cap</span><div>{f.market_cap != null ? `$${(f.market_cap / 1000).toFixed(1)}B` : '—'}</div></div>
        <div><span className="muted">Rango 52 sem.</span><div>{fmt(f.week52_low)} - {fmt(f.week52_high)}</div></div>
      </div>
    </div>
  )
}

function epsLabelClass(label) {
  if (label === 'Bueno' || label === 'Muy alto') return 'sentiment-positive'
  if (label === 'Negativo') return 'sentiment-negative'
  return 'sentiment-neutral'
}

function EpsAnalysisSection({ epsAnalysis }) {
  if (!epsAnalysis) return null
  const e = epsAnalysis

  return (
    <div className="fundamentals-box">
      <h3 style={{ marginTop: 0 }}>
        Análisis de EPS — <span className={epsLabelClass(e.quality_label)}>{e.quality_label}</span>
      </h3>
      <p>{e.growth_explanation}</p>
      {e.pe_context && <p className="muted">{e.pe_context}</p>}
      <div className="fundamentals-grid">
        <div><span className="muted">Crecimiento 3Y</span><div>{fmt(e.eps_growth_3y, '%')}</div></div>
        <div><span className="muted">Crecimiento 5Y</span><div>{fmt(e.eps_growth_5y, '%')}</div></div>
        <div><span className="muted">TTM YoY</span><div>{fmt(e.eps_growth_ttm_yoy, '%')}</div></div>
        <div><span className="muted">Trimestral YoY</span><div>{fmt(e.eps_growth_quarterly_yoy, '%')}</div></div>
      </div>
      <p className="muted ai-analysis-meta">
        No es el "EPS Rating" oficial de IBD (dato propietario) — es una clasificación propia basada en el
        crecimiento interanual del EPS (10-25%/año = saludable), no una comparación contra todo el mercado.
      </p>
    </div>
  )
}

function MarketNewsSection() {
  const [items, setItems] = useState([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    fetchMarketNews()
      .then(setItems)
      .catch(() => {})
  }, [])

  if (items.length === 0) return null

  const avgImpact = items.filter((i) => i.impact_direction).length
    ? Math.round(
        (100 * items.filter((i) => i.impact_direction === 'up').length) /
          items.filter((i) => i.impact_direction).length
      )
    : null

  return (
    <div className="ai-analysis-box">
      <div className="ai-analysis-header">
        <h3 style={{ margin: 0 }}>
          Mercado general{avgImpact != null && <span className="muted"> — {avgImpact}% de señales alcistas</span>}
        </h3>
        <button type="button" onClick={() => setOpen((v) => !v)}>
          {open ? 'Ocultar' : `Ver (${items.length})`}
        </button>
      </div>
      {open && (
        <ul className="news-list">
          {items.map((item) => {
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
                  {item.topic && <span className="news-tag">{topicLabel(item.topic)}</span>}
                  {item.impact_direction && (
                    <span className={impactClassName(item.impact_direction)}>
                      Impacto: {impactLabel(item.impact_direction)}
                    </span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function AiAnalysisSection({ ticker }) {
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  function load(refresh = false) {
    setLoading(true)
    setError('')
    fetchAiAnalysis(ticker, refresh)
      .then(setAnalysis)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker])

  return (
    <div className="ai-analysis-box">
      <div className="ai-analysis-header">
        <h3 style={{ margin: 0 }}>Análisis IA</h3>
        <button type="button" onClick={() => load(true)} disabled={loading}>
          {loading ? 'Generando...' : 'Regenerar'}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {analysis && (
        <>
          <p className="ai-analysis-text">{analysis.text}</p>
          <p className="muted ai-analysis-meta">
            Generado: {new Date(analysis.generated_at).toLocaleString()}
          </p>
        </>
      )}
    </div>
  )
}

function PositionSection({ ticker, insight, onLotsChanged }) {
  const [lots, setLots] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [quantity, setQuantity] = useState('')
  const [price, setPrice] = useState('')
  const [purchasedAt, setPurchasedAt] = useState('')
  const [error, setError] = useState('')

  function loadLots() {
    fetchLots(ticker)
      .then(setLots)
      .catch(() => {})
  }

  useEffect(() => {
    loadLots()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker])

  async function handleAddLot(e) {
    e.preventDefault()
    setError('')
    try {
      await addLot(ticker, Number(quantity), Number(price), purchasedAt || null)
      setQuantity('')
      setPrice('')
      setPurchasedAt('')
      setShowForm(false)
      loadLots()
      onLotsChanged(ticker)
    } catch (err) {
      setError(err.message)
    }
  }

  function handleLotChanged() {
    loadLots()
    onLotsChanged(ticker)
  }

  const hasPosition = insight?.quantity != null && insight?.avg_cost != null

  return (
    <div className="position-box">
      <div className="position-summary">
        {hasPosition ? (
          <>
            <span>
              {insight.quantity} acciones @ ${insight.avg_cost.toFixed(2)} promedio
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
        <button type="button" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancelar' : 'Agregar lote de compra'}
        </button>
      </div>

      {lots.length > 0 && (
        <ul className="lots-list">
          {lots.map((lot) => (
            <LotRow key={lot.id} ticker={ticker} lot={lot} onChanged={handleLotChanged} onError={setError} />
          ))}
        </ul>
      )}

      {showForm && (
        <form onSubmit={handleAddLot} className="position-form">
          <label>
            Cantidad
            <input type="number" step="any" required value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </label>
          <label>
            Precio de compra
            <input type="number" step="any" required value={price} onChange={(e) => setPrice(e.target.value)} />
          </label>
          <label>
            Fecha (opcional)
            <input type="date" value={purchasedAt} onChange={(e) => setPurchasedAt(e.target.value)} />
          </label>
          <button type="submit">Guardar lote</button>
        </form>
      )}

      {error && <p className="error">{error}</p>}

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

  function refreshAll() {
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
  }

  useEffect(() => {
    refreshAll()
    // Sin WebSocket (el backend corre en funciones serverless de Vercel, sin
    // proceso persistente) — se refresca por polling en vez de push en vivo.
    const interval = setInterval(refreshAll, 60000)
    return () => clearInterval(interval)
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

  function handleLotsChanged(ticker) {
    loadInsights(ticker)
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
      <div className="brand">
        <Logo />
        <h1>StockInsight</h1>
      </div>

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

      <MarketNewsSection />

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
              <th>Precio promedio</th>
              <th>Actualizado</th>
              <th>Sentimiento corto</th>
              <th>Sentimiento medio</th>
              <th>Sentimiento largo</th>
              <th>Analistas</th>
              <th>Recomendación</th>
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
                  <td>{insight?.avg_cost != null ? `$${insight.avg_cost.toFixed(2)}` : '—'}</td>
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
                  <td className={insight ? recommendationClassName(insight.recommendation_1w.action) : ''}>
                    {insight?.recommendation_1w.action ?? '—'}
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
          <FundamentalsSection fundamentals={insights[s.ticker]?.fundamentals} />
          <EpsAnalysisSection epsAnalysis={insights[s.ticker]?.eps_analysis} />
          <AiAnalysisSection ticker={s.ticker} />
          <PositionSection ticker={s.ticker} insight={insights[s.ticker]} onLotsChanged={handleLotsChanged} />

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
                    {item.topic && <span className="news-tag">{topicLabel(item.topic)}</span>}
                    {item.scope && (
                      <span className="news-tag">
                        {item.scope === 'market_wide' ? 'Mercado general' : 'Específica'}
                      </span>
                    )}
                    {item.impact_direction && (
                      <span className={impactClassName(item.impact_direction)}>
                        Impacto: {impactLabel(item.impact_direction)}
                      </span>
                    )}
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
