---
description: Instala d-arxiv-1st (motor + skill) y ejecuta el wizard de configuración inicial
---

# /d-arxiv-1st:setup

Instala el motor de `d-arxiv-1st` y el skill `archive-ingest`, y guía al
usuario a través del wizard de configuración inicial (workspace,
publicación inicial, política de descarga).

## Qué hacer

1. Ejecuta con el tool Bash, en primer plano y sin capturar/filtrar su
   salida:

   ```
   python3 scripts/bootstrap.py
   ```

   No invoques `d-arxiv wizard` directamente — la primera vez que se
   ejecuta este comando, el motor todavía no está instalado en ningún
   Python accesible. `bootstrap.py` resuelve ese problema: crea el venv en
   `~/.d-arxiv-1st/venv/`, instala el motor desde la última release
   publicada de `TINTA-ARTIFICIAL/d-arxiv-1st` (o, si aún no existe
   ninguna release, desde el propio checkout de desarrollo si lo hay), y
   solo entonces invoca `d-arxiv wizard` internamente.

2. El wizard es interactivo: hace preguntas (ruta del workspace,
   publicación inicial, política de descarga de PDF, resolución de
   imágenes, ámbito de instalación del skill) directamente en el terminal
   expuesto al chat. Deja que el usuario responda cada pregunta él mismo —
   no rellenes las respuestas por él ni reimplementes el flujo del wizard
   en este comando.

3. Si el script termina con código de salida distinto de cero, muestra al
   usuario el mensaje de error tal cual lo imprimió `bootstrap.py` (sin
   inventar una causa) y ofrece los pasos obvios según el mensaje (por
   ejemplo, comprobar conectividad, o confirmar que hay una release
   publicada).

4. Si el script termina con éxito, resume al usuario el resultado a partir
   de lo que se imprimió en el terminal:
   - `workspace_root` — dónde quedó configurado el workspace.
   - La publicación inicial creada (nombre/identificador).
   - Dónde quedó instalado el skill (`skill_path`, ámbito `user`/`project`).

No reimplementes el wizard en este documento ni asumas sus preguntas o
valores por defecto — la única fuente de verdad del flujo interactivo es
`lib.setup.run_wizard` (SETUP-01), invocada indirectamente vía
`d-arxiv wizard` dentro de `bootstrap.py`.
