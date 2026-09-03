---
id: MCP-01
title: Servidor MCP local — bridge de red para Cowork/Claude Desktop sobre el motor existente
type: feature
subsystem: MCP
sprint: backlog
status: IN_PROGRESS
priority: P1
depends_on: [LIB-01, LIB-02, LIB-03, LIB-04]
blocks: []
assignee: D-developer
started: 2026-09-03
completed: null
branch: feat/MCP-01-local-bridge-server
---

# MCP-01 — Servidor MCP local (bridge de red)

## Contexto

`ARCHITECTURE.md` §01/§03 ya diseñó el motor (`lib/`) desacoplado de Claude
Code precisamente para poder "envolver un servidor MCP más adelante (modo
colaborativo) sin reescribir el motor" — pero lo marcaba como **Fase 3**, sin
fecha. Este ticket adelanta esa pieza, no por el modo colaborativo original,
sino porque resuelve un bloqueo real y ya verificado en Fase 1: en una sesión
de Cowork no existe ninguna superficie de ejecución con red real *y* escritura
local simultáneas (ver discusión y pruebas reales con `SETUP-03`) —
`WebFetch` tiene red pero resume vía modelo (no bytes exactos), la VM de
ejecución de código tiene red real pero sujeta a `allowManagedDomainsOnly`
(que ignora `.claude/settings.json`), y no hay combinación que sirva para
`fetch_essentials`/`fetch_pdf`/`fetch_page_image` tal y como están escritos.

Verificado antes de diseñar esto (no una suposición): un servidor MCP local
registrado vía `claude_desktop_config.json` corre como proceso normal en la
máquina del usuario — fuera de cualquier sandbox de Cowork — y Cowork lo
puentea automáticamente a su VM de sesión. Es el mismo patrón que ya usa
`ta-ops` en producción (servidor MCP propio, mismo mecanismo de registro).

Este ticket construye **solo el servidor y sus tools**, envolviendo el motor
tal cual existe hoy — no toca `lib/`, no reescribe `skills/archive-ingest`.
La reescritura de los skills para llamar a estas tools en vez de invocar
Bash+Python directamente es un ticket aparte (ver Fuera de scope).

## Interfaces

Nuevo paquete `mcp_server/`, hermano de `lib/`, `cli/`, `skills/`:

```python
# mcp_server/tools.py

def search_collection(
    collection: str, query: str | None = None, max_pages: int | None = None
) -> list[dict]:
    """Tool MCP. Delega en lib.archive_client.search_collection sin lógica propia.

    Args:
        collection: nombre de la colección de archive.org.
        query: filtro de texto adicional, igual que archive_client.search_collection.
        max_pages: tope de páginas del cursor, igual que archive_client.search_collection.

    Returns:
        Lista de dicts (metadata resumida por item), tal cual la devuelve
        lib.archive_client.search_collection.
    """


def get_metadata(identifier: str) -> dict:
    """Tool MCP. Delega en lib.archive_client.get_metadata."""


def fetch_essentials(identifier: str, publicacion_key: str, force: bool = False) -> dict:
    """Tool MCP. Delega en lib.downloader.fetch_essentials.

    El workspace NO es un parámetro de la tool (ver Decisiones de diseño) —
    se resuelve server-side desde lib.config.load_config() en cada llamada.

    Returns:
        Igual que lib.downloader.fetch_essentials, con todo Path serializado
        a str (ver Decisiones de diseño — JSON no tiene tipo Path).

    Raises:
        RuntimeError: si config.yaml no tiene workspace.root configurado —
            mensaje debe decir explícitamente "corre el setup primero".
    """


def fetch_pdf(identifier: str, publicacion_key: str, force: bool = False) -> dict:
    """Tool MCP. Delega en lib.downloader.fetch_pdf. Returns: {"path": str}."""


def fetch_page_image(
    identifier: str,
    publicacion_key: str,
    printed_page: str | None = None,
    leaf: int | None = None,
    size: str = "w500",
    force: bool = False,
) -> dict:
    """Tool MCP. Delega en lib.downloader.fetch_page_image. Returns: {"path": str}."""


def write_processed(identifier: str, publicacion_key: str, articulos: list[dict]) -> dict:
    """Tool MCP. Delega en lib.processor.write_processed, Paths serializados a str."""


def read_index(identifier: str, publicacion_key: str) -> dict | None:
    """Tool MCP. Delega en lib.processor.read_index."""


def read_article(identifier: str, article_id: str, publicacion_key: str) -> dict | None:
    """Tool MCP. Delega en lib.processor.read_article."""


def list_publications() -> list[dict]:
    """Tool MCP. Delega en lib.config.load_publications con el workspace resuelto server-side."""


def add_publication(publication: dict) -> list[dict]:
    """Tool MCP. Delega en lib.config.add_publication con el workspace resuelto server-side."""
```

```python
# mcp_server/server.py

def main() -> None:
    """Entry point del script `d-arxiv-mcp`. Levanta el servidor MCP sobre
    stdio (mcp.server.stdio, SDK oficial `mcp`), registra las tools de
    mcp_server.tools, y sirve hasta que el proceso padre (Claude
    Desktop/Code) cierre el stdio.
    """
```

## Estructuras de datos

Ninguna nueva — todas las tools son wrappers finos sobre estructuras que
`LIB-01`/`LIB-02`/`LIB-03`/`LIB-04` ya definen. El único cambio de forma es
serialización: cualquier `Path` que el motor devuelva se convierte a `str`
antes de devolverlo desde una tool (el protocolo MCP serializa resultados a
JSON, que no tiene tipo `Path`).

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| El servidor resuelve `workspace` server-side desde `~/.d-arxiv-1st/config.yaml` en cada llamada; ninguna tool recibe `workspace` como parámetro | Pasar `workspace` como argumento de cada tool, igual que hoy lo pasan `SKILL-01`/`SETUP-03` | El servidor corre en la máquina real del usuario, no en la carpeta conectada de Cowork — una ruta de workspace "sugerida" por el lado del chat no tiene por qué existir ni ser de fiar en ese proceso. `config.yaml` (`LIB-04`) ya es la fuente de verdad de esa ruta a nivel de máquina; reutilizarla evita una segunda forma de decir lo mismo y evita que un chat pueda apuntar el servidor a una ruta arbitraria |
| Tools = wrappers finos, cero lógica nueva; el motor (`lib/`) no se toca | Mover parte de la lógica de orquestación a `mcp_server/` | El motor ya está diseñado (`ARCHITECTURE.md` §01/§03) para no depender de Claude — repetir esa disciplina aquí es lo que permite que este mismo servidor sirva a la vez a Claude Code CLI, Claude Desktop y Cowork sin tres implementaciones |
| Transporte `stdio` (proceso local hijo), no HTTP/SSE | Servidor HTTP local con puerto propio | `stdio` es el patrón ya probado en producción por `ta-ops`, no necesita gestión de puertos ni auth (el proceso padre es quien lo lanza y quien le habla) — HTTP añadiría superficie sin necesidad real para un bridge de un solo usuario local |
| Un único paquete `mcp_server/` con tools para archive.org | Un servidor MCP genérico multi-fuente desde ya | El motor de hoy solo sabe hablar con archive.org (`LIB-01`) — diseñar ya un servidor "multi-fuente" sería construir para fuentes que no existen todavía; cuando llegue una fuente nueva, se añaden tools nuevas al mismo servidor, no se rediseña esto |
| Paths serializados a `str` en el borde de cada tool | Devolver objetos `Path` y confiar en que el SDK los serialice | El protocolo MCP transporta JSON; `Path` no es serializable ahí. Es más explícito convertir en el wrapper que descubrirlo como error en tiempo de ejecución |

## Fuera de scope

- Reescribir `skills/archive-ingest/SKILL.md` o `skills/setup-cowork/SKILL.md`
  para llamar a estas tools en vez de Bash+Python — ticket aparte una vez
  este servidor exista y esté probado de verdad (evita acoplar "¿funciona el
  servidor?" con "¿funciona el skill nuevo?" en la misma validación)
- Empaquetado de un instalador de un clic (`.mcpb`/Desktop Extension) para
  que un usuario no técnico registre el servidor sin terminal — ticket
  aparte; este ticket asume que el registro inicial en
  `claude_desktop_config.json` se hace a mano una vez, documentado
- Modo colaborativo real (multi-usuario, workspace compartido en red) — eso
  sigue siendo Fase 3 tal cual la describe `ARCHITECTURE.md` §02; este
  ticket es un bridge de red *local y de un solo usuario*, no un servidor
  compartido
- Transporte HTTP/SSE, auth, o exponer el servidor fuera de `localhost`
- Tools de escritura arbitraria (borrar, sobreescribir `publications.yaml`
  entero) — solo se exponen las operaciones que el motor ya expone hoy

## Casos de test obligatorios

- Cada tool de `mcp_server/tools.py`, llamada directamente (sin pasar por el
  transporte MCP), delega en la función de `lib/` correspondiente con los
  argumentos exactos y devuelve la misma forma con `Path` convertido a `str`
- `fetch_essentials`/`fetch_pdf`/`fetch_page_image`/`list_publications`/
  `add_publication` con `config.yaml` sin `workspace.root` configurado →
  `RuntimeError` con mensaje que menciona explícitamente correr el setup
- `search_collection`/`get_metadata` (no dependen de workspace) funcionan
  con `config.yaml` inexistente o vacío
- Verificación manual (no automatizable con pytest): registrar el servidor
  localmente (`claude mcp add --transport stdio d-arxiv -- <python> -m
  mcp_server.server` o entrada equivalente en `claude_desktop_config.json`),
  abrir una sesión de Claude Desktop, llamar `fetch_essentials` contra un
  identifier real de archive.org ya usado en pruebas anteriores, confirmar
  que el fichero aparece en el workspace configurado
- Verificación manual: la misma sesión, sin reiniciar el servidor, llama
  `fetch_essentials` con un `identifier`/`publicacion_key` distinto al
  anterior → funciona igual, sin ningún estado colgado del primer request
  (confirma que el servidor es stateless por request, no atado a una
  publicación)

## Estado de revisión

- Propuesto: 2026-09-03
- Aprobado: 2026-09-03 — supervisor (chat)
