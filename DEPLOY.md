# StockInsight — Guía de Deploy (gratis)

Stack de hosting: **Vercel** (frontend) + **Render free** (backend, con keep-alive
ping) + **Neon** (Postgres gratis). Costo total: **$0/mes**.

Los pasos de creación de cuenta y conexión de repos requieren login por
navegador en cada plataforma — eso lo tienes que hacer tú. El resto
(archivos de configuración) ya está en el repo.

## 1. Base de datos — Neon

1. Entra a https://neon.tech y crea una cuenta (puedes usar tu cuenta de GitHub).
2. Crea un nuevo proyecto, ej. `stockinsight`.
3. Copia el **connection string** que te da Neon (empieza con `postgresql://...`).
   Guárdalo, lo necesitas en el paso 2.

## 2. Backend — Render

1. Entra a https://render.com y crea una cuenta con GitHub.
2. Click en **New > Blueprint**, selecciona el repo `StockInsight`. Render va
   a detectar automáticamente el archivo [render.yaml](./render.yaml) en la
   raíz del repo y configurar el servicio `stockinsight-backend`.
3. Cuando te pida las variables de entorno:
   - `DATABASE_URL` → pega el connection string de Neon del paso 1.
   - `FRONTEND_URL` → lo vas a completar en el paso 3, después de crear el
     proyecto en Vercel (por ahora puedes dejarlo vacío o poner un valor
     temporal y editarlo después).
4. Deploy. Cuando termine, copia la URL pública que te da Render
   (algo como `https://stockinsight-backend.onrender.com`).
5. Verifica que funciona entrando a `https://<tu-url>.onrender.com/health` —
   debería responder `{"status":"ok"}`.

## 3. Frontend — Vercel

1. Entra a https://vercel.com y crea una cuenta con GitHub.
2. Click en **Add New > Project**, selecciona el repo `StockInsight`.
3. En **Root Directory**, selecciona `frontend`.
4. En **Environment Variables**, agrega:
   - `VITE_API_URL` → la URL de Render del paso 2
     (ej. `https://stockinsight-backend.onrender.com`).
5. Deploy. Cuando termine, copia la URL pública de Vercel
   (algo como `https://stockinsight.vercel.app`).

## 4. Conectar el CORS del backend con la URL final del frontend

1. Vuelve a Render, entra a tu servicio → **Environment**.
2. Edita `FRONTEND_URL` con la URL real de Vercel del paso 3.
3. Guarda — Render va a redeployar automáticamente con el valor correcto.

## 5. Keep-alive ping (para que Render no se duerma)

1. En GitHub, entra al repo → **Settings > Secrets and variables > Actions**.
2. Agrega un secret nuevo:
   - Nombre: `BACKEND_HEALTH_URL`
   - Valor: `https://<tu-url-de-render>.onrender.com/health`
3. El workflow [.github/workflows/keepalive.yml](./.github/workflows/keepalive.yml)
   ya está en el repo y va a correr automáticamente cada ~10 minutos,
   manteniendo el backend despierto. No necesitas hacer nada más — puedes
   verificar que corre en la pestaña **Actions** del repo.

## Resultado final

- Frontend en vivo: la URL de Vercel.
- Backend en vivo: la URL de Render (despierto 24/7 gracias al ping).
- Datos persistidos en Neon (no se pierden en cada redeploy).
