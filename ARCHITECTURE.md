---
version: v0.1
status: DISEÑO
updated: 2026-09-02
---

# Arquitectura de d-arxiv-1st

## 01 Visión general

`d-arxiv-1st` descarga, procesa e indexa localmente publicaciones alojadas en **Internet Archive** (archive.org), para que ese material sea explotable por IA: indexado, búsqueda, y como fuente para los flujos de activación de Tinta Artificial.

Es una herramienta **independiente** de `ta-ops` — repo propio, arquitectura propia. Puede evolucionar a compartir workspace con `ta-ops` en el futuro, pero no depende de él ni asume sus convenciones.

Se entrega como **Plugin de Claude Code** que empaqueta un **Skill** conversacional. El motor (descarga, procesado) es una librería Python pura, sin dependencias de Claude — eso es lo que permitió añadir, ya en Fase 1, una tercera interfaz sobre el mismo motor: un **servidor MCP local** (`mcp_server/`, `MCP-01`) sin reescribir nada de `lib/`.

```
┌──────────────────────────────┐   ┌──────────────────────────────┐
│      Claude Code (chat)       │   │   Cowork / Claude Desktop     │
│ Plugin d-arxiv-1st → Skill    │   │  Extensión .mcpb → servidor   │
│ archive-ingest                │   │  MCP local (mcp_server/)      │
└───────────────┬────────────────┘   └───────────────┬────────────────┘
                │ invoca                             │ tools MCP (stdio)
                ▼                                     │
┌──────────────────────────────────────────────┐      │
│                  cli/ (d-arxiv)                │      │
│      wizard · fetch · process · discover       │      │
└───────────────────────┬────────────────────────┘      │
                        │                                │
                        ▼                                ▼
┌──────────────────────────────────────────────────────────┐
│                          lib/                              │
│      archive_client · downloader · processor · config      │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────┐
│         Workspace (local o carpeta sync)        │
│   sources/ · processed/ · publications.yaml     │
└──────────────────────────────────────────────┘
```

**Por qué existe la interfaz MCP (adelantado de Fase 3, no planeado originalmente en Fase 1):** verificado en pruebas reales de `SETUP-03` que una sesión de Cowork no tiene red real hacia archive.org (su VM de ejecución de código está sujeta a `allowManagedDomainsOnly`, que ignora cualquier allowlist de proyecto) — así que `skills/archive-ingest` no puede invocar el motor directamente ahí. Verificado también, en pruebas reales, que ni `.claude/settings.json` ni el registro de servidores MCP vía `claude mcp add`/`~/.claude.json` llegan a una sesión de Cowork. Lo que sí funciona, confirmado con una descarga real de archive.org de extremo a extremo: una extensión **`.mcpb`** (MCP Bundle, formato oficial de Anthropic) instalada una vez en la app — sus tools quedan disponibles en las sesiones de Cowork de esa cuenta. Ver `MCP-01` y §03b para el detalle.

---

## 02 Fases

**Fase 1 (en curso)** — un único item de archive.org: descargar lo esencial, procesar a Markdown indexado, servir de fuente para IA. Publicación piloto: *CoEvolution Quarterly*, número Summer 1978 (`coevolutionquart00unse_15`).

**Fase 2** — generalización: `publications.yaml` curado, `discover` de colecciones enteras vía `advancedsearch.php`, ingesta batch reutilizando el pipeline de Fase 1.

**Fase 3 (fuera de scope, salvo lo ya adelantado)** — entorno colaborativo: workspace compartido, múltiples usuarios. El diseño de Fase 1/2 debe dejar esto abierto (motor desacoplado de la interfaz) sin implementarlo. **Excepción ya implementada:** el servidor MCP local (`MCP-01`) se adelantó a Fase 1 porque, además de sentar la base del modo colaborativo, resuelve el bloqueo real de red de Cowork (ver §01) — pero sigue siendo un bridge local de un solo usuario, no el modo colaborativo (workspace compartido en red, multi-usuario) que sigue pendiente.

---

## 03 Empaquetado — Plugin + Skill

```
d-arxiv-1st/
├── .claude-plugin/
│   └── plugin.json            ← manifiesto del plugin
├── skills/
│   └── archive-ingest/
│       └── SKILL.md           ← instrucciones para Claude: cómo usar el motor conversacionalmente
├── commands/
│   └── setup.md               ← slash command /d-arxiv-1st:setup → ejecuta scripts/bootstrap.py
├── scripts/
│   └── bootstrap.py            ← stdlib puro, sin imports de lib/ — crea el venv e instala el motor (PLUGIN-01)
├── lib/                        ← motor Python puro, sin imports de Claude
├── cli/                        ← CLI `d-arxiv` (dev, debugging, y backend del wizard)
├── tests/
├── docs/
│   └── backlog/                ← tickets de diseño, uno por pieza de funcionalidad
├── pyproject.toml
└── README.md
```

**Decisión:** `lib/` nunca importa nada de Claude Code ni del plugin. `cli/` y `skills/` son las dos interfaces sobre el mismo motor. **Justificación:** permite añadir una interfaz MCP en Fase 3 sin tocar el motor.

---

## 03b Distribución — repo de desarrollo vs. instalación de usuario final

**Este repositorio es para desarrollo, no para instalar.** El público del plugin no son solo desarrolladores — un Productor sin experiencia técnica tiene que poder instalarlo sin `git clone`, sin saber qué es un venv, sin tocar una terminal más allá de pegar un comando o responder al wizard.

Tres caminos, deliberadamente distintos, para tres públicos distintos:

- **Desarrollador (contribuye a `d-arxiv-1st`)**: clona el repo, `pip install -e .[dev]`, trabaja sobre los tickets de `docs/backlog/`. Flujo de siempre, documentado en `README.md`/`CONTRIBUTING.md`, sin wizard — quien contribuye código ya sabe manejarse con git y pip.
- **Usuario final de Claude Code CLI**: instala desde una **release publicada** (ver `SETUP-02`), nunca desde un clon de git. El wizard (`SETUP-01`) crea un entorno autocontenido en `~/.d-arxiv-1st/venv/` — una ruta fija, propiedad del usuario, que no depende de que ningún directorio de repo siga existiendo en ningún sitio. Instalar, mover el plugin de carpeta, o borrar un clon de desarrollo en otra parte de la máquina no rompe nada. Requiere `.claude-plugin/plugin.json` + `marketplace.json` (`PLUGIN-01`/`PLUGIN-02`) para poder instalarse vía `/plugin marketplace add` + `/plugin install`.
- **Usuario final de Cowork** (`SETUP-03` + `MCP-01`): un público adicional, sin repo, sin terminal, verificado que puede no tener el código como lo tiene un desarrollador. **Revisión tras prueba real (2026-09-04):** el diseño original de `SETUP-03` asumía que `skills/setup-cowork/` podía invocar el motor directamente con Bash+Python dentro de la propia sesión de Cowork, igual que un desarrollador. Verificado que es falso — la VM donde Cowork ejecuta código no tiene red real hacia archive.org (`allowManagedDomainsOnly`, ignora cualquier allowlist de proyecto). `skills/setup-cowork/` y `skills/archive-ingest/` siguen siendo correctos para todo lo que es I/O de ficheros puro (leer/escribir en la carpeta conectada, trabajar con contenido ya descargado), pero **no pueden traer contenido nuevo de archive.org por sí solos**. Eso requiere la extensión `.mcpb` del servidor MCP (`MCP-01`) instalada una vez en la app, fuera de la sesión de Cowork — confirmado con una descarga real de extremo a extremo. Es un paso de instalación que, por diseño, no puede completarse desde dentro de un chat de Cowork (el servidor tiene que registrarse contra la máquina real del usuario, no contra la VM efímera de la sesión).

**Decisión (Claude Code CLI):** el venv de instalación vive siempre en `~/.d-arxiv-1st/venv/`, nunca dentro de un checkout de git. **Alternativa descartada:** crear el venv dentro del propio directorio del repo clonado (`{repo}/.venv`), como hace `pip install -e .` en un flujo de desarrollador típico. **Justificación:** un editable install (`-e .`) enlaza el venv al código fuente en su ubicación original — si esa carpeta se mueve o se borra, el venv deja de funcionar en silencio. Para un usuario final eso es inaceptable; para un desarrollador es aceptable (sabe que no debe borrar su propio checkout).

**Decisión (Cowork):** `skills/setup-cowork/` sigue sin venv ni plugin/marketplace — ver `SETUP-03` para la justificación completa de esa parte. Pero para poder traer contenido nuevo de archive.org (no solo trabajar con lo ya descargado), Cowork depende además de la extensión `.mcpb` del servidor MCP (`MCP-01`), instalada una vez fuera de la sesión — ver §01 y la revisión de `SETUP-03` arriba. No es un reemplazo del camino de Claude Code CLI, es un camino adicional para un producto distinto, con esta pieza extra de instalación que le es propia.

---

## 04 Workspace — estructura de ficheros local

El workspace es una carpeta local o sincronizada (Drive, iCloud, lo que sea — el motor es agnóstico al proveedor de sync, solo necesita una ruta de filesystem). Su ruta vive en la config de máquina (`~/.d-arxiv-1st/config.yaml`), no en el repo.

```
{workspace}/
├── publications.yaml           ← catálogo curado de qué seguimos (colecciones / items sueltos)
├── catalog_index.yaml          ← índice global de items descubiertos + ingeridos
├── sources/
│   └── {identifier}/           ← material crudo de archive.org, siempre ligero
│       ├── metadata.json       ← respuesta de archive.org/metadata/{identifier}
│       ├── djvu.txt            ← texto OCR limpio (fuente primaria de texto)
│       ├── toc.xml             ← tabla de contenidos cruda (pista, no estructurada)
│       ├── page_numbers.json   ← mapa leaf → página impresa
│       ├── {identifier}.pdf    ← opcional, bajo demanda (download.always_pdf)
│       └── images/
│           └── leaf-{n}_{size}.jpg  ← bajo demanda, página a página
└── processed/
    └── {identifier}/
        ├── index.md            ← Markdown + front-matter YAML: metadatos + estructura del número
        └── articles/
            └── {article_id}.md ← Markdown + front-matter por artículo
```

**Huella por defecto:** `metadata.json` + `djvu.txt` + `toc.xml` + `page_numbers.json` — combinado, por debajo de 1 MB por número. Todo lo demás (PDF, imágenes de página, OCR posicional, EPUB, JP2) es opt-in explícito.

---

## 05 Estrategia de formatos

Evaluación de los formatos que ofrece archive.org para un item de tipo `texts` (ver anexo con datos reales de `coevolutionquart00unse_15` en `docs/backlog/ISSUE_LIB-01_archive_client.md`):

| Formato | Uso | Por defecto |
|---|---|---|
| `_djvu.txt` | Texto OCR limpio — fuente primaria para indexar/buscar/dar contexto a LLM | Sí |
| metadata API / `_meta.xml` | Bibliográfico: título, fecha, vol/issue, colección, editor | Sí |
| `_toc.xml` | Pista de estructura (OCR crudo, necesita interpretación por LLM) | Sí (ligero, 60KB) |
| `_page_numbers.json` | Mapa página impresa ↔ leaf interno — habilita citar "página 22" y pedir esa imagen concreta | Sí (ligero, 25KB) |
| `.pdf` (Text PDF) | Referencia visual humana | No — bajo demanda |
| `/page/{leaf}_{size}.jpg` | Imagen de una página suelta (30–600KB según tamaño) | No — bajo demanda, página a página |
| `_djvu.xml` / `_hocr.html` / `_chocr.html.gz` | OCR posicional (coordenadas por palabra) | No — solo si se necesita alineación texto↔imagen exacta |
| `.epub` | Libro reflowable | No — redundante con djvu.txt |
| `_jp2.zip` / `_orig_jp2.tar` | Todas las páginas en imagen (240–320MB) | No, nunca por defecto — usar `/page/` individual en su lugar |

**Markdown es formato de salida, no de origen.** No existe `.md` nativo en archive.org — el motor lo genera a partir de `djvu.txt` + `toc.xml`, con front-matter YAML, como formato estándar para todo lo que consumen después indexado/búsqueda/activación.

**Imágenes:** nunca se descarga el archivo de imágenes completo. El endpoint `/download/{id}/page/{leaf}_{size}.jpg` sirve páginas sueltas bajo demanda; `page_numbers.json` resuelve qué `leaf` corresponde a una página impresa concreta.

---

## 06 Config de máquina — `config.yaml` + `install.yaml`

Dos ficheros en `~/.d-arxiv-1st/`, separados a propósito (LIB-04): ninguno vive en el workspace, ninguno se sincroniza, pero tienen dueños distintos y ciclos de vida distintos.

**`config.yaml`** — config del *motor*. La lee `lib/`/`cli/` y, en Fase 3, el servidor MCP colaborativo:

```yaml
workspace:
  root: /ruta/al/workspace        # str, requerido — carpeta local o sincronizada
download:
  always_pdf: false               # bool — si false, el PDF se pide bajo demanda
  image_default_size: w500        # medium | w500 | w1000
```

No incluye la ruta de Python: el motor se invoca siempre en `~/.d-arxiv-1st/venv/bin/d-arxiv` — una ruta fija (§03b), no hace falta registrarla.

**`install.yaml`** — estado de *esta instalación del skill/plugin en Claude Code*. Solo la tocan `SETUP-01` y `PLUGIN-01`; el motor nunca la lee. Se mantiene aparte porque un servidor MCP compartido (Fase 3) no tiene sentido acoplado a "dónde se copió un skill en la máquina de un usuario":

```yaml
scope: user                        # user | project — dónde se registró el skill
skill_path: /Users/.../.claude/skills/archive-ingest
installed_at: "2026-09-02"
```

## 07 Config de workspace — `publications.yaml`

Sí viaja con el workspace (compartible si el workspace está en Drive):

```yaml
publications:
  - key: coevolution-quarterly     # str, requerido — identificador corto y estable
    label: "CoEvolution Quarterly" # str, requerido
    mode: single_item              # single_item | discover_collection
    archive_identifiers:           # list[str] — usado si mode = single_item
      - coevolutionquart00unse_15
    archive_collection: coevolutionquarterly  # str — usado si mode = discover_collection
```

---

## 08 Wizard de instalación

Ejecutable como `d-arxiv wizard` (CLI) o `/d-arxiv-1st:setup` (slash command del plugin, invoca el mismo CLI).

**Revisión 2026-09-03 — el wizard solo pregunta lo que es genuinamente de instalación.** La versión original pedía también la publicación inicial y la política de descarga, acoplando "instalar la herramienta" a "qué voy a indexar hoy". Se simplifica a dos preguntas; el resto se mueve a `SKILL-01` (se pregunta la primera vez que hace falta de verdad, no por adelantado) o se fija con un default sensato sin preguntar.

| Paso | Qué hace | Default |
|---|---|---|
| 0 | Verifica Python 3.11+ disponible en el sistema y conectividad a archive.org | — |
| 1 | Pregunta la ruta del workspace | `~/D-ARXIV-1ST-workspace` |
| 2 | Escribe `config.yaml` con la política de descarga (`always_pdf`, `image_default_size`) — sin preguntar | bajo demanda / `w500` |
| 3 | Crea `~/.d-arxiv-1st/venv/` e instala el motor ahí desde una release publicada (§03b) + smoke test contra archive.org | última release de GitHub |
| 4 | Pregunta ámbito de instalación del skill | usuario (`~/.claude/skills/`) |
| 5 | Resumen + cómo invocar el skill | — |

El registro de la primera publicación (`key`, `label`, alcance, identifier(s)/colección) ya no es parte del wizard — lo hace `SKILL-01` conversacionalmente la primera vez que se indexa algo de una publicación no registrada todavía.

Ver `docs/backlog/ISSUE_SETUP-01_wizard.md` para la especificación completa (interfaces, casos de test) y `docs/backlog/ISSUE_SETUP-02_release_packaging.md` para cómo se publican las releases de las que instala el paso 3.

---

## 09 Backlog

Ver `docs/backlog/`. Un ticket por pieza de funcionalidad, con interfaces exactas, decisiones de diseño y casos de test obligatorios antes de implementar — ningún código se escribe sin ticket aprobado.
