---
id: LIB-02
title: Descarga de material esencial y bajo demanda al workspace
type: feature
subsystem: LIB
sprint: backlog
status: DONE
priority: P1
depends_on: [LIB-01, LIB-04]
blocks: [LIB-03, SETUP-01, SETUP-02, SKILL-01]
assignee: D-developer
started: 2026-09-03
completed: 2026-09-03
branch: feat/LIB-02-downloader
---

# LIB-02 — Descarga de material esencial y bajo demanda al workspace

## Contexto

Orquesta LIB-01 para poblar `{workspace}/sources/{identifier}/` según la política de §04-05 de `ARCHITECTURE.md`: lo esencial siempre (metadata, djvu.txt, toc.xml, page_numbers.json — <1MB combinado), todo lo demás (PDF, imágenes de página) bajo demanda explícita.

## Interfaces

```python
def fetch_essentials(identifier: str, workspace: Path, force: bool = False) -> dict:
    """Descarga el material esencial de un item a sources/{identifier}/.

    Descarga siempre: metadata.json (serializado desde get_metadata),
    {identifier}_djvu.txt, {identifier}_toc.xml, {identifier}_page_numbers.json.
    Si algún fichero no existe para este item (p.ej. no todos los items
    tienen page_numbers.json), se omite sin error — ver 'Decisiones'.

    Idempotente por fichero: si un fichero ya existe en disco y force=False,
    no se vuelve a pegar a archive.org para él — se devuelve su ruta tal
    cual. La decisión es por fichero, no por identifier completo: si
    djvu.txt ya existe pero toc.xml no, solo se descarga toc.xml.

    Args:
        identifier: identificador del item en archive.org.
        workspace: ruta raíz del workspace local.
        force: si True, re-descarga y sobreescribe aunque el fichero ya exista.

    Returns:
        dict {"identifier": str, "dir": str, "files": {nombre_lógico: ruta_absoluta}}
        — nombre_lógico ∈ {"metadata", "djvu_text", "toc", "page_numbers"};
        una key está ausente si el fichero correspondiente no existía en el item.
        No distingue en el resultado si un fichero se descargó ahora o ya
        existía — a efectos del caller, el resultado es el mismo.

    Raises:
        LookupError: si 'identifier' no existe en archive.org.
        OSError: si no se puede escribir en el workspace.
    """

def fetch_pdf(identifier: str, workspace: Path, force: bool = False) -> Path:
    """Descarga el PDF completo del item — llamada explícita, no automática.

    Idempotente: si sources/{identifier}/{identifier}.pdf ya existe y
    force=False, devuelve su ruta sin volver a descargar.

    Args:
        identifier: identificador del item.
        workspace: ruta raíz del workspace local.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Returns:
        Path absoluto de sources/{identifier}/{identifier}.pdf.

    Raises:
        LookupError: si el item no tiene un fichero de formato 'Text PDF' o 'PDF'.
    """

def fetch_page_image(
    identifier: str,
    workspace: Path,
    printed_page: str | None = None,
    leaf: int | None = None,
    size: str = "w500",
    force: bool = False,
) -> Path:
    """Descarga la imagen de una página suelta, bajo demanda.

    Exactamente uno de 'printed_page' o 'leaf' debe pasarse. Si se pasa
    'printed_page', se resuelve a 'leaf' usando page_numbers.json (debe
    haberse descargado antes con fetch_essentials).

    Idempotente: si sources/{identifier}/images/leaf-{leaf}_{size}.jpg ya
    existe y force=False, devuelve su ruta sin volver a descargar. El
    tamaño forma parte del nombre de fichero precisamente para que la
    idempotencia sea correcta — dos tamaños de la misma página son
    ficheros distintos, no una sobreescritura silenciosa (ver 'Decisiones').

    Args:
        identifier: identificador del item.
        workspace: ruta raíz del workspace local.
        printed_page: número de página impresa tal y como aparece en la
            revista (ej: "22"). Mutuamente excluyente con 'leaf'.
        leaf: índice interno de página de archive.org. Mutuamente excluyente
            con 'printed_page'.
        size: 'medium' | 'w500' | 'w1000' — resolución de la imagen.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Returns:
        Path absoluto de sources/{identifier}/images/leaf-{leaf}_{size}.jpg.

    Raises:
        ValueError: si no se pasa ni 'printed_page' ni 'leaf', o se pasan ambos,
            o 'size' no es uno de los valores válidos.
        FileNotFoundError: si 'printed_page' se pasa pero page_numbers.json no
            se ha descargado todavía para este identifier.
        LookupError: si 'printed_page' no se encuentra en page_numbers.json.
    """

def resolve_leaf(page_numbers: list[dict], printed_page: str) -> int:
    """Resuelve un número de página impreso al leaf interno de archive.org.

    Args:
        page_numbers: contenido de page_numbers.json, campo 'pages' — lista de
            dicts con keys 'leafNum' (int) y 'pageNumber' (str, puede ser "").
        printed_page: número de página impreso a buscar (ej: "22").

    Returns:
        El leafNum correspondiente.

    Raises:
        LookupError: si ningún entry tiene pageNumber == printed_page.
    """
```

## Estructuras de datos

```
{workspace}/sources/{identifier}/
├── metadata.json          # JSON, respuesta cruda de get_metadata()
├── {identifier}_djvu.txt   # texto plano, tal cual de archive.org
├── {identifier}_toc.xml    # XML, tal cual de archive.org
├── {identifier}_page_numbers.json  # JSON, tal cual de archive.org
├── {identifier}.pdf        # opcional — solo si se llamó fetch_pdf
└── images/
    └── leaf-{n}_{size}.jpg  # opcional — uno por cada (leaf, size) pedido
```

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| `fetch_essentials` omite silenciosamente ficheros ausentes en el item (no todos traen `_page_numbers.json` o `_toc.xml`) | Lanzar error si falta cualquiera de los cuatro | Confirmado con la API real: no todo item de la colección `texts` genera los cuatro ficheros (depende del pipeline de escaneo usado); el caller debe poder seguir con lo que haya |
| `fetch_page_image` exige `printed_page` XOR `leaf`, nunca ambos | Aceptar ambos y priorizar uno | Ambigüedad silenciosa (¿qué pasa si no coinciden?) es peor que forzar al caller a elegir |
| Nombres de fichero en `sources/` conservan el prefijo `{identifier}_` tal y como lo da archive.org (excepto `metadata.json`) | Renombrar a nombres genéricos (`djvu.txt` sin prefijo) | Facilita depurar comparando con la descarga manual desde archive.org; `metadata.json` es la excepción porque no es un fichero descargado sino la serialización de la respuesta de la API |
| Idempotencia simple por existencia de fichero (`force: bool`, default False), por fichero individual, no por identifier completo | (a) Sin idempotencia — siempre re-descargar; (b) caché con TTL/checksums | (a) desperdicia red en el uso repetido normal del skill (SKILL-01 puede invocar "traer el número" más de una vez); (b) es complejidad innecesaria — el contenido de un item publicado en archive.org no cambia, "¿existe ya?" es suficiente señal, no hace falta invalidación por tiempo |
| `fetch_page_image` incluye `size` en el nombre de fichero (`leaf-{n}_{size}.jpg`) | Un solo `leaf-{n}.jpg` y que `force` decida si se sobreescribe al pedir otro tamaño | Sin el tamaño en el nombre, pedir la misma página en `w1000` tras haberla pedido en `w500` devolvería silenciosamente el fichero equivocado bajo `force=False` — son ficheros distintos, deben tener rutas distintas |

## Fuera de scope

- Descarga de `jp2.zip` / `orig_jp2.tar` / `epub` / `hocr` / `chocr` — no forman parte de este ticket; si se necesitan en el futuro, es un ticket nuevo que reutiliza `LIB-01.download_file`
- Invalidación de caché (checksums, TTL, detectar que archive.org actualizó un fichero) — `force=True` manual cubre el caso de uso real esperado
- Descarga paralela / progreso — descarga secuencial simple en esta primera versión

## Casos de test obligatorios

- `fetch_essentials(...)` con item que tiene los 4 ficheros → devuelve dict con las 4 keys, ficheros escritos en disco
- `fetch_essentials(...)` con item mockeado sin `_page_numbers.json` → devuelve dict sin la key `page_numbers`, sin error
- `fetch_essentials(...)` con identifier inexistente → lanza `LookupError`
- `fetch_essentials(...)` llamado dos veces seguidas (mismo identifier, force=False) → la segunda llamada no hace ninguna petición HTTP de descarga (mock de `download_file` con `assert_not_called`), devuelve el mismo dict
- `fetch_essentials(...)` con un fichero ya en disco y otro no (djvu.txt existe, toc.xml no) → solo descarga toc.xml, deja djvu.txt intacto
- `fetch_essentials(..., force=True)` con ficheros ya en disco → re-descarga todos, sobreescribe
- `fetch_pdf(...)` con item sin formato PDF → lanza `LookupError`
- `fetch_pdf(...)` con el PDF ya en disco y force=False → no descarga, devuelve la ruta existente
- `fetch_page_image(..., printed_page="22", leaf=5)` (ambos) → lanza `ValueError`
- `fetch_page_image(...)` sin `page_numbers.json` descargado previamente → lanza `FileNotFoundError`
- `fetch_page_image(..., leaf=5, size="w500")` seguido de `fetch_page_image(..., leaf=5, size="w1000")` → dos ficheros distintos en disco (`leaf-5_w500.jpg` y `leaf-5_w1000.jpg`), ambas llamadas descargan (no hay falso-positivo de idempotencia entre tamaños distintos)
- `resolve_leaf([{"leafNum": 8, "pageNumber": "6"}], "6")` → `8`
- `resolve_leaf([...], "999")` con página inexistente → lanza `LookupError`

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: 2026-09-02 — supervisor (chat): idempotencia simple con force=True, tamaño incluido en el nombre de fichero de imágenes
