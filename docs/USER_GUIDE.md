# Guía de usuario — wizard de instalación

Para quien va a *usar* `d-arxiv-1st` (no para quien desarrolla el repo — ver `README.md`/`ARCHITECTURE.md` §03b para esa distinción).

## ¿Se puede lanzar desde un chat de Claude?

Sí, de dos formas:

### A. Vía el comando del plugin — `/d-arxiv-1st:setup`

Es la forma pensada para un usuario final. Requiere que el plugin `d-arxiv-1st` esté dado de alta en Claude Code (añadir su ruta/repo como plugin — mecanismo propio de Claude Code, no verificado paso a paso en esta guía porque no lo hemos ejecutado nosotros mismos; consulta la documentación de plugins de Claude Code para el paso exacto de "añadir plugin local"). Una vez dado de alta, el comando `/d-arxiv-1st:setup` ejecuta `scripts/bootstrap.py` por ti y te va preguntando en el propio chat.

### B. Directamente, pidiéndole a Claude que ejecute el script

Funciona ahora mismo, sin dar de alta ningún plugin — verificado en esta misma sesión. En cualquier chat de Claude Code con acceso a una terminal (tool Bash), estando en el repo:

```bash
python3 scripts/bootstrap.py
```

Esto hace exactamente lo mismo que el comando del plugin: instala el motor y lanza el wizard interactivo en el terminal.

**Aviso sobre el origen del motor:** `bootstrap.py` intenta instalar desde la última release publicada en GitHub. Como todavía no se ha publicado ninguna (`SETUP-02` implementa cómo hacerlo, pero nadie ha ejecutado `publish_release` aún), si lo lanzas desde dentro de un checkout de este repo caerá automáticamente al modo de arranque para desarrollo (instalación editable desde ese checkout). El wizard funciona igual en ambos casos — la diferencia solo importa para alguien sin ningún checkout en su máquina, que hoy no podría instalar hasta que exista una release real.

## Qué preguntas hace el wizard, en orden

**Revisión 2026-09-03: el wizard se redujo a 2 preguntas.** Instalar la herramienta y decidir qué publicación vas a indexar son dos momentos distintos — la versión original pedía también la publicación inicial y la política de descarga, lo que ataba la instalación a una tarea concreta. Ahora eso se pregunta conversacionalmente, la primera vez que hace falta de verdad (ver más abajo).

| # | Pregunta | Valor por defecto si pulsas Enter |
|---|---|---|
| 1 | Ruta del workspace | `~/D-ARXIV-1ST-workspace` |
| 2 | Ámbito de instalación del skill (`user`/`project`) | `user` |

La política de descarga (`always_pdf: false`, `image_default_size: w500`) se escribe directamente en `config.yaml` con esos valores, sin preguntar — si quieres otros, edita el YAML a mano.

## Qué queda configurado al terminar

- `~/.d-arxiv-1st/venv/` — el motor instalado, autocontenido
- `~/.d-arxiv-1st/config.yaml` — workspace y política de descarga (con sus defaults)
- `~/.d-arxiv-1st/install.yaml` — dónde se instaló el skill y desde qué origen se instaló el motor
- El skill `archive-ingest` copiado en `~/.claude/skills/` (si elegiste `user`) o `./.claude/skills/` (si elegiste `project`)

**El wizard no toca `publications.yaml`.** No hay ninguna publicación registrada todavía al terminar — eso pasa la primera vez que le pides al skill que traiga o indexe algo (ver abajo).

## Después de instalar

Con el skill `archive-ingest` instalado, en cualquier chat de Claude Code puedes pedir cosas como "trae el número Summer 1978 de CoEvolution Quarterly" (identifier de archive.org: `coevolutionquart00unse_15`). La primera vez que le pidas indexar una publicación que no conoce todavía, el skill te pregunta un `key` (slug corto) y un `label` (nombre) y la registra en `publications.yaml` sobre la marcha — no hace falta que lo hayas decidido de antemano en el wizard. Las siguientes veces que trabajes con esa misma publicación, ya no vuelve a preguntar. Ver `skills/archive-ingest/SKILL.md` para el detalle completo del flujo.

## Relanzar el wizard

`d-arxiv wizard` (una vez el motor ya está instalado, invocando directamente `~/.d-arxiv-1st/venv/bin/d-arxiv wizard`) vuelve a correr el mismo flujo de instalación — útil si quieres reconfigurar el workspace o el ámbito del skill. No hace falta relanzarlo para añadir publicaciones nuevas; eso lo gestiona el skill.
