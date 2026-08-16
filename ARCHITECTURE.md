# StockInsight — Arquitectura (v1)

> Basado en las decisiones de [DESIGN.md](./DESIGN.md). Define el stack técnico
> y la estructura del proyecto antes de escribir código.

## 1. Stack

| Capa | Elección | Motivo |
|------|----------|--------|
| Backend | Python + FastAPI | Mejor ecosistema para ML, datos financieros (`yfinance`, `pandas`) y NLP de sentimiento. FastAPI da API REST + WebSockets nativos |
| Frontend | React (Vite) | Dashboard en tiempo real vía WebSockets, accesible desde cualquier dispositivo |
| Base de datos | PostgreSQL | Precio histórico, noticias, y resultados de proyección — relacional, con buen soporte en cualquier hosting hobby |
| Precio de mercado | `yfinance` | Gratis, consistente con la fuente de datos históricos ya decidida en el design doc. ~15 min de delay (aceptable para v1, no day-trading de alta frecuencia) |
| Noticias | Yahoo Finance + Google News (scraping/RSS) | Fuentes gratuitas decididas en el design doc |
| Sentimiento de noticias | Modelo NLP pre-entrenado (ej. FinBERT vía `transformers`) | Evita entrenar un modelo de sentimiento desde cero; FinBERT está afinado para texto financiero |
| Motor de proyección | 3 modelos ML independientes (scikit-learn / LightGBM), uno por horizonte | Según decisión del design doc §4.3 |
| Tareas en segundo plano | APScheduler embebido en el proceso de FastAPI (v1) | Recolecta precios/noticias y corre los modelos en intervalos, dentro del mismo proceso que sirve el WebSocket — así puede empujar actualizaciones en vivo directamente sin infraestructura extra (Redis/Celery) |
| Notificaciones | WebSocket (dashboard) + SMTP (email) + Web Push (escritorio Windows vía navegador) | Según canales decididos en el design doc §4.4 |
| Hosting frontend | Vercel (plan gratis) | Deploy directo desde GitHub, gratis para un proyecto personal |
| Hosting backend | Render (plan free) + keep-alive ping cada ~10 min (GitHub Actions) | Gratis. El free tier de Render duerme tras ~15 min sin tráfico; un ping periódico externo lo mantiene despierto de forma efectiva, sin costo |
| Base de datos | Neon (Postgres serverless, plan free) | Render free no ofrece disco persistente ni Postgres gratis permanente — Neon da Postgres gratis "para siempre" con límite generoso, ideal para el volumen de v1 |

## 2. Componentes

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│  Scheduler   │────▶ │   PostgreSQL      │◀────│   FastAPI    │
│ (APScheduler)│      │ (precios, noticias,│      │  (REST + WS) │
│              │      │  proyecciones)     │      │              │
└──────┬───────┘      └──────────────────┘      └──────┬───────┘
       │                                                 │
       ▼                                                 ▼
┌─────────────┐                                  ┌─────────────┐
│ yfinance +   │                                  │  React (Vite)│
│ Yahoo/Google │                                  │  Dashboard   │
│ News + FinBERT│                                 └─────────────┘
└─────────────┘
```

- **Scheduler**: cada N minutos, por símbolo trackeado: (1) trae precio con
  `yfinance`, (2) trae noticias nuevas, (3) calcula sentimiento con FinBERT,
  (4) corre los 3 modelos de proyección, (5) guarda resultados, (6) si hay
  cambio relevante, dispara notificación.
- **FastAPI**: expone REST para consultar históricos/config, y WebSocket para
  push en vivo al dashboard.
- **React**: dashboard con precio en vivo, noticias recientes, proyecciones
  por horizonte y recomendación, más historial.

## 3. Estructura del repositorio

```
StockInsight/
├── DESIGN.md
├── ARCHITECTURE.md
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, rutas REST + WebSocket
│   │   ├── models/            # modelos ORM (SQLAlchemy)
│   │   ├── schemas/           # esquemas Pydantic
│   │   ├── services/          # ingestión de precios, noticias, sentimiento
│   │   ├── ml/                # entrenamiento e inferencia de los 3 modelos
│   │   └── notifications/     # email, websocket, push
│   ├── scheduler.py           # jobs de APScheduler
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   └── package.json
└── .gitignore
```

## 4. Próximos pasos

1. Scaffold del backend (FastAPI + estructura de carpetas + conexión a
   Postgres).
2. Scaffold del frontend (Vite + React).
3. Implementar tracking de precio con `yfinance` end-to-end (el flujo más
   simple) antes de sumar noticias/ML, para validar la arquitectura con algo
   funcionando.
