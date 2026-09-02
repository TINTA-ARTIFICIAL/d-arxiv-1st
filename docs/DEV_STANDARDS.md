# Estándares de desarrollo — d-arxiv-1st

Esta es la referencia de estilo que sigue cualquier implementación de un ticket de `docs/backlog/`, humana o de `D-developer`. Un ticket especifica *qué* interfaz y *qué* comportamiento; este documento especifica *cómo* se escribe.

## Código Python

- Python 3.11+, type hints en toda firma pública (parámetros y retorno) — sin excepciones, un ticket sin tipos completos no está bien especificado y tampoco debería implementarse sin tipos
- `from __future__ import annotations` al principio de cada módulo — permite anotaciones modernas (`list[dict]`, `str | None`) sin restricciones de compatibilidad
- Docstrings estilo Google: una línea de resumen, luego `Args`, `Returns`, `Raises` — exactamente el formato que ya usan los tickets en su sección "Interfaces". La implementación copia esa docstring casi literal; no hace falta redactarla de cero
- Módulo con docstring de cabecera: una línea describiendo el módulo + `Ticket: {ID}` — para poder rastrear cualquier función hasta el ticket que la especificó
- Excepciones semánticas, nunca `Exception` genérica: `ValueError` para entrada inválida, `LookupError` para "no encontrado por clave/id", `FileNotFoundError` para rutas de fichero, `RuntimeError` para fallos de entorno/red. El tipo exacto ya lo fija cada ticket en su `Raises` — no se cambia por preferencia personal
- Mensajes de error descriptivos, con el valor inválido incluido vía `!r}` (repr) para que se vea exactamente qué se recibió — ej. `f"identifier inválido: {identifier!r}"`, no `"identifier inválido"` a secas
- Funciones públicas primero en el fichero, helpers `_privados` después, separados por un comentario banner (`# --- helpers internos ---` o similar) si el fichero mezcla ambos
- Sin comentarios que expliquen QUÉ hace el código — los nombres y las docstrings ya lo dicen. Un comentario solo se justifica si documenta un motivo no obvio (una restricción de una API externa, un workaround concreto) — igual que en cualquier código de este proyecto, dentro o fuera de este flujo
- Una responsabilidad por función — si implementar un caso de test obligatorio exige una función que hace dos cosas distintas, es señal de que falta una función auxiliar, no de que el test esté mal

## Tests

- pytest. Un test por cada línea de "Casos de test obligatorios" del ticket — mapeo literal y nombrado: `test_{funcion}_{condición_del_caso}` (ej. `test_get_metadata_identifier_inexistente_lanza_lookuperror`)
- Casos de error: `pytest.raises(TipoExacto, match="fragmento del mensaje")` — no basta con comprobar que lanza *algo*
- Tests que hablan con archive.org de verdad se marcan `@pytest.mark.integration` (ya definido en `pyproject.toml`) — el resto usa mocks, nunca red real por defecto
- Fixtures con `tmp_path` para cualquier test que toque el filesystem — nunca escribir en una ruta fija del sistema durante un test

## Commits y ramas

- Rama por ticket: `feat/{ticket-id}-{slug}` (ej. `feat/LIB-01-archive-client`)
- Mensaje de commit: `tipo(scope): descripción en minúsculas`
  - `tipo` ∈ `feat | fix | test | refactor | docs | chore`
  - `scope` ∈ `lib | cli | skill | plugin | setup | docs`
  - Referencia al ticket en el cuerpo o en el título: `feat(lib): implement archive_client — closes LIB-01`
- Un commit por ticket completo (implementación + tests juntos), salvo que una ronda de corrección de `D-dispatcher` justifique un commit adicional sobre la misma rama

## Cuando el ticket y este documento no coinciden

El ticket manda en interfaz y comportamiento (eso lo aprobó alguien explícitamente). Este documento manda en todo lo demás — formato, nombres de test, estilo de mensajes. Si un ticket antiguo tiene una interfaz que no sigue algo de aquí (por ejemplo, un docstring no exactamente Google-style), se implementa tal cual está especificado en el ticket sin "corregirlo" de paso — un cambio de estilo en una interfaz ya aprobada es su propio ticket, no un efecto colateral de implementar otro.
