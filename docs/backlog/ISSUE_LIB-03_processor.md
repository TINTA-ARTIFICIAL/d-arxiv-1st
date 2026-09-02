---
id: LIB-03
title: Persistir estructura indexada como Markdown procesado
type: feature
subsystem: LIB
sprint: backlog
status: TODO
priority: P1
depends_on: [LIB-02]
blocks: [SETUP-02, SKILL-01]
assignee: null
started: null
completed: null
branch: null
---

# LIB-03 — Persistir estructura indexada como Markdown procesado

## Contexto

`djvu.txt` trae el texto OCR de **todo el número** desde el primer `fetch_essentials` (LIB-02) — no hay coste adicional en extraer el cuerpo de un artículo concreto, es cortar una cadena que ya está en disco. Este módulo **no interpreta** `djvu.txt` ni `toc.xml`: eso lo hace Claude desde el skill, leyendo el texto crudo de `sources/{identifier}/` y decidiendo la estructura (artículos, autores, rangos) — el TOC de archive.org es OCR crudo sin estructura fiable (verificado en LIB-01). `processor.py` solo persiste esa estructura ya decidida como Markdown con front-matter en `processed/{identifier}/`, y mantiene `catalog_index.yaml`.

**Una sola función de escritura, no dos.** Una primera versión de este ticket separaba `write_index` (metadatos del número) de `write_article` (cuerpo de cada pieza), pensando en poder escribir cuerpos incrementalmente. Se descarta: como Claude ya ha leído el `djvu.txt` completo para proponer la lista de artículos, cuando propone la estructura ya tiene los cuerpos disponibles — no hay una razón real para forzar dos llamadas y arrastrar el riesgo de que `index.md` quede desincronizado de qué artículos tienen cuerpo escrito. `write_processed` hace ambas cosas en una operación atómica.

## Interfaces

```python
def write_processed(identifier: str, workspace: Path, data: dict) -> dict:
    """Escribe o amplía processed/{identifier}/: index.md + articles/{id}.md.

    Cada llamada es autocontenida: cada entrada en data['articulos'] debe
    incluir su body_text y se escribe de inmediato como fichero completo —
    no existe un estado "declarado pero pendiente de cuerpo" en lo
    persistido. Llamadas sucesivas para el mismo identifier hacen upsert
    por article_id sobre la lista de articulos ya existente en index.md:
    para añadir artículos a un número ya procesado basta con volver a
    llamar solo con los nuevos, sin repetir los anteriores.

    Args:
        identifier: identificador del item en archive.org.
        workspace: ruta raíz del workspace local.
        data: dict con las keys:
            titulo (str) — requerido si es la primera llamada para este
                identifier; en llamadas posteriores, si se omite, se
                conserva el valor ya guardado en index.md.
            fecha (str) — mismas reglas que titulo.
            publicacion_key (str) — mismas reglas que titulo.
            volumen (str, opcional)
            numero (str, opcional)
            articulos (list[dict], requerido, puede ser vacía) — cada uno con:
                article_id (str, requerido) — patrón {identifier}-{NN},
                    NN de dos dígitos con cero a la izquierda, posición
                    en el número.
                titulo (str, requerido)
                body_text (str, requerido) — cuerpo ya recortado de djvu.txt
                autores (list[str], opcional)
                paginas (dict, opcional) — {inicio: str, fin: str},
                    numeración impresa

    Returns:
        dict {"index_path": Path, "article_paths": list[Path]} — solo los
        artículos escritos o actualizados en ESTA llamada, no todos los
        que tenga el número acumulados de llamadas anteriores.

    Raises:
        ValueError: si es la primera llamada para este identifier y falta
            'titulo', 'fecha' o 'publicacion_key'; o si algún artículo de
            'articulos' no tiene 'article_id', 'titulo' o 'body_text', o su
            'article_id' no cumple el patrón {identifier}-{NN}.
    """

def read_index(identifier: str, workspace: Path) -> dict | None:
    """Lee y parsea el front-matter de processed/{identifier}/index.md.

    Args:
        identifier: identificador del item.
        workspace: ruta raíz del workspace local.

    Returns:
        dict con el front-matter YAML, o None si el fichero no existe.
    """

def read_article(identifier: str, article_id: str, workspace: Path) -> dict | None:
    """Lee un artículo procesado: front-matter + cuerpo.

    Args:
        identifier: identificador del item padre.
        article_id: identificador del artículo.
        workspace: ruta raíz del workspace local.

    Returns:
        dict con las keys del front-matter más 'body_text' (el cuerpo del
        Markdown, sin el front-matter), o None si el fichero no existe.
    """
```

## Estructuras de datos

`processed/{identifier}/index.md`:

```markdown
---
identifier: coevolutionquart00unse_15    # str
publicacion_key: coevolution-quarterly   # str
titulo: "CoEvolution Quarterly Summer 1978"  # str
fecha: "1978"                            # str
volumen: "5"                             # str, opcional
numero: "18"                             # str, opcional
articulos:                               # list[dict] — todos los ya escritos, con cuerpo
  - article_id: coevolutionquart00unse_15-01
    titulo: "The Pattern Which Connects"
processed_at: 2026-09-02                 # date, fecha de la última llamada a write_processed
---

(cuerpo libre en Markdown — notas del Productor, no estructurado)
```

`processed/{identifier}/articles/{article_id}.md`:

```markdown
---
article_id: coevolutionquart00unse_15-01   # str
identifier: coevolutionquart00unse_15      # str, referencia al padre
titulo: "The Pattern Which Connects"       # str
autores: ["Gregory Bateson"]               # list[str], opcional
paginas: {inicio: "16", fin: "17"}         # dict, opcional, numeración impresa
processed_at: 2026-09-02                   # date, autogenerado
---

{body_text tal cual, sin transformar}
```

`catalog_index.yaml` (raíz del workspace):

```yaml
items:
  - identifier: coevolutionquart00unse_15   # str
    publicacion_key: coevolution-quarterly  # str
    titulo: "CoEvolution Quarterly Summer 1978"
    fecha: "1978"
    articulo_count: 1                        # int, len(articulos) en index.md
    processed_at: 2026-09-02
```

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| `processor.py` no interpreta texto, solo persiste estructura ya decidida | Que el módulo intente segmentar `djvu.txt` en artículos automáticamente (regex/heurística) | El TOC de archive.org es OCR crudo sin estructura fiable (verificado en LIB-01); segmentar bien requiere criterio editorial, es trabajo de Claude en el skill, no del motor |
| Una sola función `write_processed`, no `write_index`/`write_article` separadas | Dos funciones (versión anterior de este ticket) | Sin coste real que diferir (djvu.txt ya está completo en disco desde LIB-02) y sin equipo que se reparta el trabajo por artículo, dos funciones solo añadían el riesgo de que index.md quedara desincronizado de qué artículos tienen cuerpo — una operación atómica lo elimina por construcción |
| `write_processed` hace upsert por `article_id` entre llamadas sucesivas, en vez de exigir la lista completa cada vez | Exigir siempre el conjunto completo de artículos del número en cada llamada | Permite indexar un número en varias sesiones sin tener que repetir el cuerpo de artículos ya escritos |
| `article_id` = `{identifier}-{NN}` | Un esquema legible con código de publicación + fecha + posición | Sin ambigüedad ni colisión posible entre publicaciones distintas; no requiere que Claude derive un código de publicación — trade-off aceptado: menos legible a cambio de determinismo |

## Fuera de scope

- Segmentación automática de `djvu.txt` en artículos — decisión editorial de Claude, no de este módulo
- Búsqueda / indexado full-text sobre `processed/` — ticket aparte (posible LIB-05, backlog)
- Sincronización con sistemas externos — no aplica a esta herramienta

## Casos de test obligatorios

- `write_processed(...)` sin `titulo` en la primera llamada para un identifier → lanza `ValueError`
- `write_processed(...)` válido, primera llamada → crea `index.md` y un `.md` por artículo en `articles/`, actualiza `catalog_index.yaml`
- `write_processed(...)` con un artículo sin `body_text` → lanza `ValueError`
- `write_processed(...)` con `article_id` que no matchea `{identifier}-{NN}` → lanza `ValueError`
- `write_processed(...)` llamado dos veces con el mismo identifier y artículos distintos (sin repetir los primeros) → `index.md` acaba con la unión de ambas listas de artículos, ambos ficheros de artículo existen en disco
- `write_processed(...)` llamado una segunda vez sin `titulo` (ya guardado antes) → conserva el `titulo` de la primera llamada, no lo borra
- `write_processed(...)` llamado dos veces con el mismo `article_id` → upsert, no duplica la entrada en `articulos` ni crea un segundo fichero
- `read_index(...)` con identifier no procesado → devuelve `None`
- `read_article(...)` con article_id no procesado → devuelve `None`
- `read_article(...)` tras `write_processed(...)` → devuelve dict con `body_text` igual al que se pasó

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: 2026-09-02 — supervisor (chat): colapsado a una sola función; se descarta el split de ta-ops por no aportar valor real en esta herramienta
