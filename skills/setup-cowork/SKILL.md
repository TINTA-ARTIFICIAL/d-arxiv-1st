---
name: setup-cowork
description: Configura d-arxiv-1st para trabajar en una sesión de Cowork — verifica Python y dependencias, pregunta la ruta del workspace y escribe la config del motor. Úsalo cuando el usuario pida configurar/instalar/preparar d-arxiv-1st en Cowork, o diga algo como "configura esto", "prepara el workspace" o "quiero empezar a traer números de archive.org" al arrancar una sesión de Cowork con la carpeta de la release conectada.
---

# setup-cowork

Este skill prepara `d-arxiv-1st` para usarse dentro de una sesión de **Cowork**
(sin terminal, sin repo clonado como lo tendría un desarrollador — solo la
carpeta de una release descomprimida, conectada a la sesión). No sustituye al
wizard de terminal (`d-arxiv wizard` / `/d-arxiv-1st:setup`, ver `SETUP-01`) —
es un camino de instalación adicional, para este producto y este público.

Cowork ya aísla la sesión y ejecuta código nativamente dentro de las carpetas
conectadas: la carpeta conectada *es* el entorno de ejecución. Por eso este
skill no crea ningún entorno virtual (venv) — el motor corre con el Python de
la propia sesión — y no copia ni "instala" el skill en ningún otro sitio: si
la carpeta de la release ya trae `skills/archive-ingest/` y
`skills/setup-cowork/` en `.claude/skills/`, ya están donde tienen que estar.

## Cómo invocar el motor

El motor es una librería Python pura (`lib/`), sin CLI todavía disponible. Se
invoca ejecutando Python con `lib/` importable, vía el tool Bash de Cowork,
con snippets cortos y autocontenidos. A diferencia de `archive-ingest`, aquí
**no** hay `~/.d-arxiv-1st/venv/bin/python3` — usa siempre el `python3` de la
sesión, ejecutado desde la raíz de la carpeta de código conectada (donde vive
`lib/`), para que `from lib import config` resuelva sin necesidad de instalar
ningún paquete.

## Flujo — Configurar d-arxiv-1st en esta sesión

Disparadores: arrancar una sesión de Cowork con la carpeta de la release
conectada y pedir que se configure/prepare `d-arxiv-1st`, o cualquier pedido
equivalente antes de poder usar `archive-ingest` por primera vez en esta
sesión.

1. **Verificar prerrequisitos.** Comprueba la versión de Python de la sesión
   con el tool Bash:

   ```bash
   python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
   ```

   Si la versión es menor que `3.11`, dilo al usuario tal cual y **para
   aquí** — no intentes instalar Python, no continúes con el resto del
   flujo. Instalar Python queda fuera de este skill; se asume ya disponible
   en el entorno de Cowork.

2. **Verificar/instalar dependencias.** `requests` y `pyyaml` deben ser
   importables (el import de `pyyaml` es `yaml`):

   ```bash
   python3 -c "import requests, yaml" && echo OK || echo MISSING
   ```

   Si falta alguna, instálalas con el tool Bash de Cowork (que pedirá
   permiso al usuario antes de ejecutar, como cualquier comando):

   ```bash
   pip install --user requests pyyaml
   ```

   Nunca crees un entorno virtual para esto — el motor corre con el Python
   de la sesión, no en un venv aislado (a diferencia de `SETUP-01`, donde sí
   tiene sentido porque ahí no hay una sesión de Cowork aislando ya el
   entorno). Tras instalar, repite la verificación del import para
   confirmar que quedó resuelto antes de seguir.

3. **Preguntar la ruta del workspace.** Asume que el usuario ya conectó a
   esta sesión de Cowork una carpeta para el workspace — una carpeta
   *distinta* de la carpeta de código (el workspace es independiente de
   dónde vive el motor, ver `ARCHITECTURE.md` §04). Pregúntale cuál es esa
   ruta.

   Si el usuario todavía no ha conectado ninguna carpeta para esto,
   pídeselo explícitamente y **espera** a que la conecte desde la propia
   interfaz de Cowork antes de continuar — este skill no puede conectar
   carpetas por su cuenta, y no debe asumir ni inventar una ruta (por
   ejemplo, reutilizar la carpeta del código sería un error: mezclaría
   workspace y código).

4. **Escribir la config.** Con la ruta ya confirmada, llama
   `lib.config.save_config` (`LIB-04`, sin cambios) con esa ruta:

   ```python
   from lib import config
   config.save_config({"workspace": {"root": ruta}})
   ```

   No preguntes política de descarga (`always_pdf`, `image_default_size`) —
   mismo criterio que `SETUP-01`: se queda con el default de `LIB-04`
   (`False` / `"w500"`); quien quiera otra cosa edita `config.yaml` a mano.
   Este skill tampoco escribe `install.yaml` — ese fichero describe una
   instalación de skill en Claude Code (`scope`, `skill_path`) que no tiene
   sentido en Cowork, donde el skill ya vive en su sitio final sin haberse
   "instalado" en ningún otro lugar.

5. **Confirmar que está listo.** Resume al usuario, en un mensaje breve:
   - la ruta del workspace que quedó configurada;
   - que las dependencias (`requests`, `pyyaml`) están verificadas;
   - que ya puede pedir cosas al skill `archive-ingest` en el mismo chat
     (por ejemplo, "trae el número Summer 1978 de CoEvolution Quarterly").

## Fuera de alcance de este skill

- Cómo se empaqueta y publica la carpeta de la release para Cowork — eso es
  responsabilidad de quien distribuye la release, no de este skill.
- Conectar carpetas a la sesión de Cowork — es una acción del usuario en la
  propia interfaz de Cowork; este skill solo la pide y espera.
- Cualquier cosa relacionada con `SETUP-01`, `PLUGIN-01`, `PLUGIN-02` o
  `SETUP-02` (el camino de instalación para Claude Code CLI) — siguen
  intactos, este es un camino adicional, no un reemplazo.
- Instalar Python si no está presente — se asume ya disponible en el
  entorno de Cowork.
- Copiar o "instalar" este skill o `archive-ingest` en otro sitio — en
  Cowork ya viven donde tienen que estar dentro de la carpeta conectada.
