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

| # | Pregunta | Valor por defecto si pulsas Enter |
|---|---|---|
| 1 | Ruta del workspace | `~/D-ARXIV-1ST-workspace` |
| 2 | Identificador corto (key) de la publicación inicial | — (requerido, sin default) |
| 3 | Nombre de la publicación (label) | — (requerido, sin default) |
| 4 | Alcance de ingesta inicial: `1` = un número suelto, `2` = descubrir colección completa | `1` |
| 5a | *(si elegiste 1)* Identifier(s) de archive.org, separados por coma | — |
| 5b | *(si elegiste 2)* Nombre de la colección en archive.org | — |
| 6 | ¿Descargar siempre el PDF completo? (s/N) | `n` (bajo demanda) |
| 7 | Resolución de imagen por defecto (`medium`/`w500`/`w1000`) | `w500` |
| 8 | Ámbito de instalación del skill (`user`/`project`) | `user` |

Ejemplo de identifier para la publicación piloto (CoEvolution Quarterly, Summer 1978): `coevolutionquart00unse_15`.

## Qué queda configurado al terminar

- `~/.d-arxiv-1st/venv/` — el motor instalado, autocontenido
- `~/.d-arxiv-1st/config.yaml` — workspace y política de descarga
- `~/.d-arxiv-1st/install.yaml` — dónde se instaló el skill y desde qué origen se instaló el motor
- `{workspace}/publications.yaml` — tu publicación inicial ya registrada
- El skill `archive-ingest` copiado en `~/.claude/skills/` (si elegiste `user`) o `./.claude/skills/` (si elegiste `project`)

## Después de instalar

Con el skill `archive-ingest` instalado, en cualquier chat de Claude Code puedes pedir cosas como "trae el número Summer 1978 de CoEvolution Quarterly" o "indexa este número que acabas de traer" — el skill sabe qué funciones del motor invocar. Ver `skills/archive-ingest/SKILL.md` para el detalle del flujo que cubre.

## Relanzar el wizard

`d-arxiv wizard` (una vez el motor ya está instalado, invocando directamente `~/.d-arxiv-1st/venv/bin/d-arxiv wizard`) vuelve a correr el mismo flujo — útil para añadir una publicación nueva a `publications.yaml` sin tener que editarlo a mano.
