---
id: LIB-03
title: Persistir estructura indexada como Markdown procesado
type: feature
subsystem: LIB
sprint: backlog
status: TODO
priority: P1
depends_on: [LIB-02]
blocks: []
---

# LIB-03 — Persistir estructura indexada como Markdown procesado

## Contexto

Igual que `ta-ops` (Variante B: Claude hace el análisis, las tools solo mueven datos), este módulo **no interpreta** `djvu.txt` ni `toc.xml` — eso lo hace Claude desde el skill, leyendo el texto crudo de `sources/{identifier}/` y decidiendo la estructura (artículos, autores, rangos). `processor.py` solo persiste esa estructura ya decidida como Markdown con front-matter en `processed/{identifier}/`, y mantiene `catalog_index.yaml`.

## Interfaces

```python
def write_index(identifier: str, workspace: Path, data: dict) -> Path:
    """Escribe processed/{identifier}/index.md — la ficha de nivel de número.

    Crea o sobreescribe el fichero. Actualiza catalog_index.yaml con la entrada
    de este identifier (upsert por identifier).

    Args:
        identifier: identificador del item en archive.org.
        workspace: ruta raíz del workspace local.
        data: dict con las keys:
            titulo (str, requerido)
            fecha (str, requerido)
            publicacion_key (str, requerido) — referencia a publications.yaml
            volumen (str, opcional)
            numero (str, opcional)
            articulos (list[dict], opcional) — cada uno con al menos 'titulo'
                y 'article_id'; ver write_article para el resto de campos.

    Returns:
        Path absoluto de processed/{identifier}/index.md.

    Raises:
        ValueError: si falta 'titulo', 'fecha' o 'publicacion_key' en data.
    """

def write_article(identifier: str, article_id: str, workspace: Path, data: dict) -> Path:
    """Escribe processed/{identifier}/articles/{article_id}.md.

    Además, marca la entrada correspondiente en articulos[] de
    processed/{identifier}/index.md con processed_at=hoy — así index.md
    siempre refleja qué artículos de la lista ya tienen cuerpo escrito y
    cuáles siguen pendientes (mismo patrón que _update_piece_indexed_at
    en ta-ops).

    Args:
        identifier: identificador del item padre en archive.org.
        article_id: identificador del artículo — patrón {identifier}-{NN}
            (NN, dos dígitos con cero a la izquierda, posición en el número).
        workspace: ruta raíz del workspace local.
        data: dict con las keys:
            titulo (str, requerido)
            body_text (str, requerido) — cuerpo ya recortado de djvu.txt
            autores (list[str], opcional)
            paginas (dict, opcional) — {inicio: str, fin: str} en numeración impresa

    Returns:
        Path absoluto del fichero .md escrito.

    Raises:
        ValueError: si falta 'titulo' o 'body_text', o si article_id no
            cumple el patrón {identifier}-{NN}.
        FileNotFoundError: si processed/{identifier}/index.md no existe
            (write_index debe ejecutarse antes que el primer write_article).
        LookupError: si article_id no aparece en articulos[] de index.md
            (el artículo no fue declarado al indexar el número).
    """

def read_index(identifier: str, workspace: Path) -> dict | None:
    """Lee y parsea el front-matter de processed/{identifier}/index.md.

    Args:
        identifier: identificador del item.
        workspace: ruta raíz del workspace local.

    Returns:
        dict con el front-matter YAML, o None si el fichero no existe.
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
articulos:                               # list[dict], puede estar vacía hasta indexar
  - article_id: coevolutionquart00unse_15-01
    titulo: "The Pattern Which Connects"
    processed_at: 2026-09-02               # date, null hasta que write_article lo procese
processed_at: 2026-09-02                 # date, autogenerado — de write_index, no confundir con el de cada artículo
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
    articulo_count: 1                        # int
    processed_at: 2026-09-02
```

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| `processor.py` no interpreta texto, solo persiste estructura ya decidida | Que el módulo intente segmentar `djvu.txt` en artículos automáticamente (regex/heurística) | El TOC de archive.org es OCR crudo sin estructura fiable (verificado en LIB-01); segmentar bien requiere criterio editorial — es trabajo de Claude en el skill, no del motor |
| `article_id` = `{identifier}-{NN}` | Un esquema legible tipo `{journal_code}-{fecha}-{NN}` (como ta-ops) | Sin ambigüedad ni colisión posible entre publicaciones distintas; no requiere que Claude derive un código de revista — trade-off aceptado: menos legible a cambio de determinismo |
| `write_article` exige que `write_index` se haya ejecutado antes | Permitir escribir artículos sueltos sin índice padre | Evita artículos huérfanos sin número asociado en `catalog_index.yaml` |
| `write_article` exige que `article_id` ya esté declarado en `articulos[]` de `index.md`, y marca esa entrada con `processed_at` | Permitir escribir cualquier `article_id` aunque no estuviera en la lista propuesta al indexar | Sin esto, `index.md` no puede responder "qué falta por procesar" — que es lo que necesita el paso 3 de SKILL-01; permitir artículos no declarados dejaría huecos en ese tracking |

## Fuera de scope

- Segmentación automática de `djvu.txt` en artículos — decisión editorial de Claude, no de este módulo
- Búsqueda / indexado full-text sobre `processed/` — ticket aparte (posible LIB-05, backlog)
- Sincronización con sistemas externos (Notion, etc.) — no aplica a esta herramienta en Fase 1/2

## Casos de test obligatorios

- `write_index(...)` sin `titulo` → lanza `ValueError`
- `write_index(...)` válido → crea `index.md` con front-matter correcto y actualiza `catalog_index.yaml` (crea la entrada si no existe)
- `write_index(...)` llamado dos veces con el mismo identifier → upsert, no duplica entrada en `catalog_index.yaml`
- `write_article(...)` con `article_id` que no matchea `{identifier}-{NN}` → lanza `ValueError`
- `write_article(...)` sin `index.md` previo → lanza `FileNotFoundError`
- `write_article(...)` con `article_id` no declarado en `articulos[]` de `index.md` → lanza `LookupError`
- `write_article(...)` con `article_id` sí declarado → tras la llamada, `read_index(...)['articulos']` tiene esa entrada con `processed_at` igual a hoy; las demás entradas no declaradas siguen con `processed_at: null`
- `read_index(...)` con identifier no procesado → devuelve `None`
- `read_index(...)` tras `write_index(...)` → devuelve el mismo dict (round-trip)

## Estado de revisión

- Propuesto: 2026-09-02
- Fix de sincronización processed_at: aprobado 2026-09-02
- Aprobación final: PENDIENTE — revisar primero el rol de write_article en el flujo (ver discusión en chat)
