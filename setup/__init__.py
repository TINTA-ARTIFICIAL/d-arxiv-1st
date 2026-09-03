"""Herramientas de mantenedor — empaquetado y publicación de releases.

No forma parte del motor (`lib/`) ni de la CLI (`cli/`) que se distribuyen a
usuarios finales: este paquete solo lo usa quien mantiene el repo para
publicar una release (ver `SETUP-02`), nunca se instala en `~/.d-arxiv-1st/venv/`.
"""

from __future__ import annotations
