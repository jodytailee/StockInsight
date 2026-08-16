# StockInsight — Documento de Diseño

> Estado: Alcance de v1 cerrado. Este documento define el propósito, alcance y
> requisitos antes de tomar decisiones de código o arquitectura. Listo para
> pasar a la fase de arquitectura.

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
- Fuentes para v1: **solo fuentes gratuitas** — Yahoo Finance y Google News.
  Bloomberg/Reuters y sentimiento de redes sociales (X/Reddit) quedan fuera de
  v1 por su costo/límites de acceso; se reevalúan para una fase futura si el
  proyecto lo justifica.

### 4.3 Motor de proyección
- Genera una proyección de dirección del precio (sube/baja) para 3 horizontes:
  próximos minutos, próximo día, próxima semana.
- Se construirán **3 modelos de Machine Learning independientes, uno por
  horizonte** (minutos / día / semana), cada uno optimizado para su propia
  ventana temporal, en lugar de un único modelo genérico.
- Datos de entrenamiento: histórico de precios desde una **API gratuita**
  (ej. Yahoo Finance / `yfinance`) combinado con sentimiento extraído de las
  noticias recolectadas (sección 4.2).
- **[ABIERTO]** Features exactas por modelo (precio, volumen, indicadores
  técnicos derivados, score de sentimiento, etc.) y estrategia de
  reentrenamiento/actualización — se definen en la fase de arquitectura, ya
  con el stack técnico elegido.
- **Métrica de éxito**: retorno simulado. Se hará un backtest que simula
  haber seguido cada recomendación histórica del modelo y mide el retorno
  acumulado hipotético resultante, comparado contra una estrategia base
  (ej. buy-and-hold) — es más representativo del valor real que solo medir
  si acertó la dirección.
- Se comunica siempre que es una señal probabilística, no una certeza.

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

> **Nota**: este análisis es orientativo, basado en conocimiento general de
> regulación financiera (perspectiva EE.UU., por ser la referencia más común
> en este tipo de herramientas). **No es asesoría legal.** Si en algún
> momento el proyecto deja de ser 100% personal, se recomienda consultar con
> un abogado especializado en regulación de valores/fintech antes de lanzar.

- Las recomendaciones de compra/venta son una señal informativa generada por
  un modelo de proyección, **no constituyen asesoría financiera profesional**.
  Esto debe quedar visible en la interfaz cada vez que se muestre una
  recomendación.

**¿Por qué uso estrictamente personal reduce el riesgo?**
En EE.UU., por ejemplo, la regulación de "investment adviser" (Investment
Advisers Act) aplica a quien da consejo financiero **a terceros**, típicamente
a cambio de compensación o como actividad comercial regular. Un sistema que
tú mismo construyes, corres localmente y usas solo para tus propias
decisiones no encaja en esa definición — no hay "cliente" ni "compensación"
de por medio. El riesgo legal real aparece cuando la herramienta se comparte
con otras personas, se cobra por su uso, o se promociona públicamente como
fuente de recomendaciones.

**Disparadores a vigilar** (si el proyecto evoluciona más allá de uso
personal):
1. **Compartir el acceso** con otras personas (aunque sea gratis) — puede
   acercarse a "dar consejo a terceros".
2. **Cobrar** por el acceso o las recomendaciones — activa con más fuerza la
   regulación de asesoría de inversión.
3. **Publicar las recomendaciones** abiertamente (ej. red social, sitio
   público) — distinto régimen (más parecido a "publicación financiera" tipo
   newsletter, con sus propias exenciones, pero igual amerita disclaimer
   fuerte y, idealmente, revisión legal).
4. **Conectar con un broker para ejecutar operaciones reales** (fuera de
   alcance en v1, sección 5) — esto sí añade obligaciones regulatorias
   adicionales serias y debe evaluarse con un abogado antes de construirse.

**Decisión para v1**: dado que el uso es estrictamente personal (sección 3) y
no hay intención de compartir, cobrar o publicar las recomendaciones, un
disclaimer visible en la interfaz es suficiente por ahora. Si en el futuro se
cruza cualquiera de los 4 disparadores anteriores, se debe revisar esta
sección con asesoría legal real antes de avanzar.

## 8. Preguntas abiertas — resumen

Todas las decisiones de alcance de v1 quedaron resueltas. Solo queda un
detalle técnico fino a definir ya en la fase de arquitectura:

| # | Pregunta | Impacto |
|---|----------|---------|
| 1 | Features exactas de cada uno de los 3 modelos y estrategia de reentrenamiento | Se define junto con el stack técnico (sección 4.3) |

## 9. Próximos pasos

Con el alcance de v1 definido, el siguiente paso es pasar a decisiones de
arquitectura y stack tecnológico (lenguaje/framework, fuente de datos de
precio en tiempo real, almacenamiento, cómo se sirve el modelo ML, diseño del
dashboard web y del sistema de notificaciones).
