---
id: CLI-01
title: Entry point del CLI d-arxiv (cli/main.py)
type: feature
subsystem: CLI
sprint: backlog
status: IN_PROGRESS
priority: P1
depends_on: [SETUP-01]
blocks: []
assignee: D-developer
started: 2026-09-03
completed: null
branch: feat/CLI-01-entrypoint
---

# CLI-01 — Entry point del CLI d-arxiv

## Contexto

Hallazgo real detectado durante la validación de `PLUGIN-01`, no atribuible a ningún ticket existente: `pyproject.toml` declara `d-arxiv = "cli.main:main"` como entry point desde el diseño inicial del repo, pero ningún ticket del backlog original especificó implementar `cli/main.py` — `lib.setup.run_wizard` (SETUP-01) y el resto del motor están completos y probados, pero no hay nada que los exponga como el comando `d-arxiv` real. Consecuencia concreta: el flujo de instalación de usuario final (`bootstrap.py` → instala el wheel → ejecuta `{venv}/bin/d-arxiv wizard`) falla hoy con `ModuleNotFoundError` — cada pieza individual funciona, pero no están conectadas.

Alcance mínimo para cerrar el gap: solo el subcomando `wizard`, que es el único bloqueante real (lo invoca `bootstrap.py` de `PLUGIN-01`). `fetch`/`process`/`discover` (mencionados como aspiración en `ARCHITECTURE.md` §01) quedan fuera — son conveniencias de desarrollo, no bloquean nada.

## Interfaces

```python
def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del CLI d-arxiv. Registrado en pyproject.toml como
    project.scripts: d-arxiv = "cli.main:main".

    Args:
        argv: argumentos de línea de comandos, sin el nombre del programa.
            Si es None, usa sys.argv[1:].

    Returns:
        Código de salida del proceso: 0 en éxito, 1 si el subcomando lanza
        una excepción (el mensaje de la excepción se imprime a stderr, sin
        traceback crudo), 2 si argv no matchea ningún subcomando conocido
        (comportamiento estándar de argparse).
    """

def _cmd_wizard(args: argparse.Namespace) -> int:
    """Subcomando 'wizard' — invoca lib.setup.run_wizard() interactivo.

    Args:
        args: namespace de argparse (sin argumentos propios en esta versión;
            existe por consistencia con el resto de subcomandos futuros).

    Returns:
        0 si run_wizard() completa sin excepción, 1 si lanza RuntimeError
        o ValueError (mensaje impreso a stderr).
    """
```

## Estructuras de datos

N/A — este ticket no persiste nada propio, es la capa de invocación sobre `lib.setup.run_wizard` (ya especificado en `SETUP-01`).

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| Alcance mínimo: solo `wizard` | Implementar también `fetch`/`process`/`discover` en el mismo ticket, como sugiere el diagrama de `ARCHITECTURE.md` §01 | Son las únicas piezas que bloquean el flujo real de usuario final (`bootstrap.py` → `d-arxiv wizard`); añadir subcomandos sin ticket propio que los especifique con su propio contrato repite el problema que causó este gap |
| Excepciones capturadas en `main()`, nunca traceback crudo al usuario | Dejar que la excepción se propague tal cual | `bootstrap.py` y el usuario final ejecutan esto sin contexto de desarrollo — un traceback de Python no es una salida de error aceptable para ese público |
| `main(argv=None)` acepta argv inyectable | Leer `sys.argv` directamente dentro de la función | Testeable sin mockear `sys.argv` globalmente |
| `main()` captura el `SystemExit` que `argparse.parse_args()` lanza por defecto ante argv inválido, y devuelve su código como int en vez de dejar que mate el proceso | Dejar que `SystemExit` se propague sin capturar | El contrato dice que `main()` devuelve un int siempre — un test que llama `main(["no-existe"])` esperando `2` como valor de retorno fallaría (o mataría el proceso de test) si `SystemExit` no se captura explícitamente |
| `main()` captura `Exception` de forma específica alrededor de la llamada al subcomando, nunca `KeyboardInterrupt` ni el `SystemExit` ya mencionado de argparse | `except:` desnudo o `except BaseException` | Un `Ctrl+C` del usuario real durante el wizard debe interrumpir el proceso de verdad, no reportarse como "error del subcomando" con código 1 |

## Fuera de scope

- Subcomandos `fetch`, `process`, `discover` — issue nuevo si se necesitan, con su propio contrato de interfaz
- Autocompletado de shell, `--help` más allá de lo que argparse genera por defecto
- Empaquetado/instalación — eso ya lo cubren `SETUP-01`/`SETUP-02`, este ticket solo añade el punto de entrada que consumen

## Casos de test obligatorios

- `main(["wizard"])` con `lib.setup.run_wizard` mockeado devolviendo éxito → `0`
- `main(["wizard"])` con `run_wizard` mockeado lanzando `RuntimeError("x")` → devuelve `1`, imprime "x" a stderr, sin traceback
- `main(["no-existe"])` → devuelve `2`, no lanza `SystemExit` ni mata el proceso de test (comportamiento de argparse capturado, no propagado)
- `main([])` sin subcomando → devuelve `2` con mensaje de uso, no lanza excepción
- `main(["wizard"])` con `run_wizard` mockeado lanzando `KeyboardInterrupt` → la excepción se propaga (no se captura como error del subcomando, no devuelve `1`)
- Instalación real (smoke test manual, no pytest): tras `pip install .` en un venv limpio, `d-arxiv wizard` se ejecuta sin `ModuleNotFoundError`

## Estado de revisión

- Propuesto: 2026-09-03
- Aprobado: 2026-09-03 — supervisor (chat): precisado el manejo de SystemExit/KeyboardInterrupt en main()
