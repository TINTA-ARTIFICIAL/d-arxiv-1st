---
id: {ID}
title: {título}
type: feature | research | chore
subsystem: LIB | CLI | SKILL | PLUGIN | SETUP
sprint: backlog
status: TODO | IN_PROGRESS | IN_REVIEW | DONE | BLOCKED
priority: P1 | P2 | P3
depends_on: []
blocks: []
assignee: null
started: null
completed: null
branch: null
---

# {ID} — {título}

## Contexto

Por qué existe este ticket, qué problema resuelve.

## Interfaces

```python
def nombre_funcion(param: Tipo) -> ReturnType:
    """Una línea.

    Args:
        param: descripción

    Returns:
        descripción

    Raises:
        ValueError: cuándo
    """
```

## Estructuras de datos

Schemas YAML/JSON completos, con tipo y opcionalidad en cada campo.

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| ... | ... | ... |

## Fuera de scope

- ...

## Casos de test obligatorios

- `funcion()` con X → Y
- `funcion()` con Z inválido → lanza ValueError

## Estado de revisión

- Propuesto: {fecha}
- Aprobado: PENDIENTE
