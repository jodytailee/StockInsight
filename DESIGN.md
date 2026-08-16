# StockInsight — Documento de Diseño

> Estado: Alcance de v1 definido. Este documento define el propósito, alcance y
> requisitos antes de tomar decisiones de código o arquitectura.

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

Uso personal. Un único usuario (el dueño del proyecto). No se requiere sistema
de cuentas/login ni aislamiento de datos multiusuario en v1.

## 4. Alcance funcional (v1)

### 4.1 Tracking de precio
- El usuario ingresa uno o más símbolos de acciones a seguir.
- El sistema obtiene el precio en tiempo real (o cuasi tiempo real, según
  restricciones de las fuentes de datos).
- Histórico de precios almacenado para poder calcular tendencias.

### 4.2 Agregación de noticias
- Recolección en tiempo real de noticias relacionadas con la empresa desde
  los principales sitios de noticias financieras.
- Fuentes priorizadas para v1: Yahoo Finance, Google News, Bloomberg/Reuters,
  y sentimiento de redes sociales (X/Twitter, Reddit).
- **[ABIERTO]** Bloomberg/Reuters y las APIs de redes sociales suelen requerir
  suscripción de pago o tener límites estrictos de acceso — hay que evaluar
  costo y disponibilidad real de cada API antes de comprometerse a integrarla
  en v1 (puede que alguna quede para una fase posterior).

### 4.3 Motor de proyección
- Genera una proyección de dirección del precio (sube/baja) para 3 horizontes:
  próximos minutos, próximo día, próxima semana.
- Se construirá un **modelo de Machine Learning propio**, entrenado con
  histórico de precios y sentimiento de noticias, en lugar de limitarse a
  indicadores técnicos estándar.
- **[ABIERTO]** Enfoque del modelo: ¿un solo modelo para los 3 horizontes o
  un modelo distinto por horizonte? ¿Qué features de entrada (precio,
  volumen, sentimiento de noticias, indicadores técnicos como insumo del
  modelo, etc.)?
- **[ABIERTO]** Fuente y volumen de datos históricos para entrenamiento, y
  estrategia de reentrenamiento/actualización del modelo con datos nuevos.
- **[ABIERTO]** Nivel de precisión esperado / cómo se va a medir el éxito de
  la proyección (esto es difícil de garantizar — hay que dejar expectativas
  claras desde el diseño, y comunicar que es una señal probabilística, no
  una certeza).

### 4.4 Notificaciones en tiempo real
- El sistema notifica al usuario ante eventos relevantes (cambio brusco de
  precio, noticia importante, cambio en la recomendación).
- Canales para v1: app web (push/dashboard en vivo), email, y notificación
  de escritorio de Windows.

### 4.5 Recomendaciones de compra/venta
- El sistema genera una recomendación (comprar / vender / mantener) basada en
  el motor de proyección y las noticias recientes.
- **Nota de responsabilidad**: esto se acerca a asesoría financiera. Hay que
  decidir cómo se comunica (ej. "señal informativa, no es asesoría financiera")
  y si hay implicaciones legales que considerar según la jurisdicción de uso.

## 5. Fuera de alcance (v1)

- **Ejecución automática de órdenes de compra/venta.** v1 es estrictamente
  informativo: el sistema recomienda, el usuario decide y ejecuta manualmente
  en su propio broker. Integración con brokers (ej. Alpaca, Interactive
  Brokers) para trading automatizado queda para una fase futura, fuera de v1.

## 6. Requisitos no funcionales

- **Tiempo real**: los datos de precio y noticias deben reflejarse con la menor
  latencia posible.
- **Disponibilidad**: el sistema de notificaciones debe ser confiable — una
  notificación perdida tiene costo para el usuario.
- **Volumen**: v1 está dimensionado para trackear un número reducido de
  símbolos en paralelo (1-10). No se requiere arquitectura de streaming a gran
  escala en esta fase; alcanza con polling/streaming ligero por símbolo.

## 7. Responsabilidad y disclaimers

- Las recomendaciones de compra/venta son una señal informativa generada por
  un modelo de proyección, **no constituyen asesoría financiera profesional**.
  Esto debe quedar visible en la interfaz cada vez que se muestre una
  recomendación.
- **[ABIERTO]** Evaluar si, al ser de uso estrictamente personal (sección 3),
  hay implicaciones legales reales a considerar, o si con el disclaimer basta
  para v1.

## 8. Preguntas abiertas — resumen

| # | Pregunta | Impacto |
|---|----------|---------|
| 1 | Costo/disponibilidad real de APIs de Bloomberg/Reuters y redes sociales | Puede reducir el set de fuentes de noticias de v1 |
| 2 | Diseño del modelo ML (features, un modelo por horizonte o uno solo) | Complejidad y tiempo de desarrollo del motor de proyección |
| 3 | Fuente y estrategia de datos históricos para entrenar/reentrenar el modelo | Viabilidad y calidad del motor de proyección |
| 4 | Cómo medir el éxito/precisión de las proyecciones | Define métricas de evaluación del modelo |
| 5 | Implicaciones legales de las recomendaciones en uso personal | Alcance del disclaimer necesario |

## 9. Próximos pasos

1. Resolver las preguntas abiertas de la sección 8 con el usuario (mayormente
   relacionadas al diseño del modelo ML y las fuentes de datos).
2. Recién entonces pasar a decisiones de arquitectura y stack tecnológico.
