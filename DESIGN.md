# StockInsight — Documento de Diseño

> Estado: Borrador inicial. Este documento define el propósito, alcance y requisitos
> antes de tomar decisiones de código o arquitectura. Las secciones marcadas como
> **[ABIERTO]** son preguntas pendientes de decidir con el usuario.

## 1. Visión

StockInsight es un sistema de análisis y seguimiento de acciones en tiempo real que:

1. Sigue el precio de una acción (dado su símbolo/ticker) en tiempo real.
2. Recopila en tiempo real información sobre la empresa desde los principales
   sitios de noticias.
3. Genera una **proyección** de si el precio va a subir o bajar en distintos
   horizontes: próximos minutos, día y semana.
4. Envía **notificaciones en tiempo real** al usuario.
5. Genera **recomendaciones de compra o venta**.

## 2. Problema a resolver

Un inversor que sigue una o varias acciones necesita combinar múltiples fuentes
(precio de mercado + noticias) para tomar decisiones rápidas, y hoy tiene que
revisar eso manualmente en distintas pestañas/apps. StockInsight centraliza esa
información y añade una capa de proyección y recomendación automática.

## 3. Usuarios objetivo

- **[ABIERTO]** ¿Es una herramienta solo para uso personal del usuario, o se
  pretende que la usen otras personas (multiusuario, posible producto)?

## 4. Alcance funcional (v1)

### 4.1 Tracking de precio
- El usuario ingresa uno o más símbolos de acciones a seguir.
- El sistema obtiene el precio en tiempo real (o cuasi tiempo real, según
  restricciones de las fuentes de datos).
- Histórico de precios almacenado para poder calcular tendencias.

### 4.2 Agregación de noticias
- Recolección en tiempo real de noticias relacionadas con la empresa desde
  los principales sitios de noticias financieras.
- **[ABIERTO]** ¿Qué fuentes de noticias son prioritarias? (ej. Reuters,
  Bloomberg, Yahoo Finance, Google News, redes sociales/X, etc.) — esto
  determina qué APIs/proveedores de datos se necesitan y su costo.

### 4.3 Motor de proyección
- Genera una proyección de dirección del precio (sube/baja) para 3 horizontes:
  próximos minutos, próximo día, próxima semana.
- **[ABIERTO]** ¿La proyección debe ser un modelo propio (ML entrenado con
  histórico + sentimiento de noticias), o basta con integrar señales/indicadores
  técnicos estándar (medias móviles, RSI, MACD, etc.) sin ML en v1?
- **[ABIERTO]** Nivel de precisión esperado / cómo se va a medir el éxito de
  la proyección (esto es difícil de garantizar — hay que dejar expectativas
  claras desde el diseño).

### 4.4 Notificaciones en tiempo real
- El sistema notifica al usuario ante eventos relevantes (cambio brusco de
  precio, noticia importante, cambio en la recomendación).
- **[ABIERTO]** ¿Canal de notificación? (push en app web, email, SMS,
  Telegram/WhatsApp, notificación de escritorio, etc.)

### 4.5 Recomendaciones de compra/venta
- El sistema genera una recomendación (comprar / vender / mantener) basada en
  el motor de proyección y las noticias recientes.
- **Nota de responsabilidad**: esto se acerca a asesoría financiera. Hay que
  decidir cómo se comunica (ej. "señal informativa, no es asesoría financiera")
  y si hay implicaciones legales que considerar según la jurisdicción de uso.

## 5. Fuera de alcance (v1)

- **[ABIERTO]** ¿Ejecución automática de órdenes de compra/venta (trading
  automatizado)? Se asume que v1 es solo informativo/de recomendación, sin
  ejecutar operaciones reales, salvo que se indique lo contrario.

## 6. Requisitos no funcionales

- **Tiempo real**: los datos de precio y noticias deben reflejarse con la menor
  latencia posible.
- **Disponibilidad**: el sistema de notificaciones debe ser confiable — una
  notificación perdida tiene costo para el usuario.
- **[ABIERTO]** Volumen esperado: ¿cuántos símbolos se van a trackear en
  paralelo? Esto define si se necesita una arquitecture de streaming robusta
  o si alcanza con polling simple en v1.

## 7. Preguntas abiertas — resumen

| # | Pregunta | Impacto |
|---|----------|---------|
| 1 | Uso personal vs. multiusuario | Arquitectura de auth y aislamiento de datos |
| 2 | Fuentes de noticias prioritarias | Elección de proveedores/APIs y costo |
| 3 | Modelo ML propio vs. indicadores técnicos en v1 | Complejidad y tiempo de desarrollo |
| 4 | Canal de notificaciones | Infraestructura de entrega |
| 5 | Alcance legal de las recomendaciones | Disclaimers, posibles restricciones |
| 6 | Trading automatizado sí/no | Riesgo, alcance de v1 |
| 7 | Volumen de símbolos en paralelo | Arquitectura de datos en tiempo real |

## 8. Próximos pasos

1. Resolver las preguntas abiertas de la sección 7 con el usuario.
2. Con las respuestas, definir el alcance formal de v1 (MVP).
3. Recién entonces pasar a decisiones de arquitectura y stack tecnológico.
