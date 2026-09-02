---
version: v0.1
status: DISEÑO
updated: 2026-09-02
---

# Arquitectura de d-arxiv-1st

## 01 Visión general

`d-arxiv-1st` descarga, procesa e indexa localmente publicaciones alojadas en **Internet Archive** (archive.org), para que ese material sea explotable por IA: indexado, búsqueda, y como fuente para los flujos de activación de Tinta Artificial.

Es una herramienta **independiente** de `ta-ops` — repo propio, arquitectura propia. Puede evolucionar a compartir workspace con `ta-ops` en el futuro, pero no depende de él ni asume sus convenciones.

Se entrega como **Plugin de Claude Code** que empaqueta un **Skill** conversacional. El motor (descarga, procesado) es una librería Python pura, sin dependencias de Claude — así el plugin puede envolver un servidor MCP más adelante (modo colaborativo) sin reescribir el motor.

```
┌──────────────────────────────────────────────┐
│              Claude Code (chat)               │
│   Plugin d-arxiv-1st → Skill archive-ingest   │
└───────────────────────┬────────────────────────┘
                        │ invoca
                        ▼
┌──────────────────────────────────────────────┐
│                  cli/ (d-arxiv)                │
│      wizard · fetch · process · discover       │
└───────────────────────┬────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│                    lib/                         │
│  archive_client · downloader · processor        │
│  config · publications                          │
└───────────────────────┬────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│         Workspace (local o carpeta sync)        │
│   sources/ · processed/ · publications.yaml     │
└──────────────────────────────────────────────┘
```

---

## 02 Fases

**Fase 1 (en curso)** — un único item de archive.org: descargar lo esencial, procesar a Markdown indexado, servir de fuente para IA. Publicación piloto: *CoEvolution Quarterly*, número Summer 1978 (`coevolutionquart00unse_15`).

**Fase 2** — generalización: `publications.yaml` curado, `discover` de colecciones enteras vía `advancedsearch.php`, ingesta batch reutilizando el pipeline de Fase 1.

**Fase 3 (fuera de scope por ahora)** — entorno colaborativo: workspace compartido, servidor MCP, múltiples usuarios. El diseño de Fase 1/2 debe dejar esto abierto (motor desacoplado de la interfaz) sin implementarlo.

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
│   └── setup.md               ← slash command /d-arxiv-1st:setup → lanza el wizard
├── lib/                        ← motor Python puro, sin imports de Claude
├── cli/                        ← CLI `d-arxiv` (dev, debugging, y backend del wizard)
├── tests/
├── docs/
│   └── backlog/                ← tickets de diseño, uno por pieza de funcionalidad
├── pyproject.toml
└── README.md
```

**Decisión:** `lib/` nunca importa nada de Claude Code ni del plugin. `cli/` y `skills/` son las dos interfaces sobre el mismo motor. **Justificación:** permite añadir una interfaz MCP en Fase 3 sin tocar el motor — mismo patrón que le funcionó a `ta-ops` (lib/ vs ta_mcp/).

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
python:
  bin: /opt/homebrew/bin/python3.11
```

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

| Paso | Qué hace | Default |
|---|---|---|
| 0 | Verifica Python 3.11+ y conectividad a archive.org | — |
| 1 | Pregunta la ruta del workspace | `~/D-ARXIV-1ST-workspace` |
| 2 | Pregunta la publicación inicial (identifier suelto o colección) | — |
| 3 | Pregunta política de descarga de PDF | bajo demanda |
| 4 | Pregunta resolución por defecto de imágenes | `w500` |
| 5 | Pregunta alcance de ingesta inicial (un número vs descubrir colección) | un número |
| 6 | Instala dependencias (venv propio) + smoke test contra archive.org | venv propio |
| 7 | Pregunta ámbito de instalación del skill | usuario (`~/.claude/skills/`) |
| 8 | Resumen + cómo invocar el skill | — |

Ver `docs/backlog/ISSUE_SETUP-01_wizard.md` para la especificación completa (interfaces, casos de test).

---

## 09 Backlog

Ver `docs/backlog/`. Un ticket por pieza de funcionalidad, con interfaces exactas, decisiones de diseño y casos de test obligatorios antes de implementar — ningún código se escribe sin ticket aprobado.
