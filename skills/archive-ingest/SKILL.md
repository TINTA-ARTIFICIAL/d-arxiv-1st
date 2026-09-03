---
name: archive-ingest
description: Descarga, indexa y sirve material de publicaciones de Internet Archive (archive.org) para el workspace local de d-arxiv-1st. Úsalo cuando el usuario pida traer/descargar un número o identifier de archive.org (o pegue una URL archive.org/details/...), pida indexar o estructurar en artículos un número ya descargado, pida la imagen de una página impresa concreta de un número, o pida traer/descubrir una colección completa de una publicación.
---

# archive-ingest

Este skill enseña a Claude a operar conversacionalmente el motor de `d-arxiv-1st`
(`lib/archive_client.py`, `lib/downloader.py`, `lib/processor.py`, `lib/config.py`).
El motor solo mueve datos — descarga ficheros y los persiste en el workspace. La
lectura crítica (dónde empieza y termina cada artículo dentro de `djvu.txt`, qué
título y fecha corresponden al número) la hace Claude, en conversación con el
usuario, porque el TOC que ofrece archive.org es OCR crudo y no es fiable.

## Cómo invocar el motor

El motor es una librería Python pura (`lib/`), sin CLI todavía disponible. Se
invoca ejecutando Python con `lib/` importable, vía el tool Bash, con snippets
cortos y autocontenidos. Usa el intérprete del motor instalado:

```bash
~/.d-arxiv-1st/venv/bin/python3 -c "..."
```

Si esa ruta no existe (por ejemplo, trabajando sobre un checkout de desarrollo
del propio repo con `pip install -e .[dev]` en su propio entorno), usa el
`python3` de ese entorno en su lugar. No inventes un CLI (`d-arxiv ...`) que
todavía no existe — invoca siempre las funciones de `lib/` directamente.

Antes de cualquier operación, resuelve el workspace con
`lib.config.load_config()`:

```python
from lib import config
cfg = config.load_config()
workspace = cfg["workspace"]["root"]
```

Si `workspace` es `None`, el workspace no está configurado todavía — dilo al
usuario y pídele que ejecute primero el wizard de instalación
(`/d-arxiv-1st:setup` o `d-arxiv wizard`). No configures el workspace tú mismo
desde este skill: eso es responsabilidad de `SETUP-01`, fuera de este ticket.

## Reglas que no se rompen nunca

1. **Nunca escribas en `processed/` sin confirmación explícita del usuario.**
   `write_processed` persiste; antes de llamarlo, presenta la propuesta
   (título, fecha, lista de artículos con su recorte de texto) y espera un
   "sí"/confirmación equivalente. El TOC de archive.org es OCR crudo poco
   fiable — la propuesta de Claude necesita revisión humana antes de
   persistirse.
2. **Nunca descargues una imagen de página como efecto secundario de indexar.**
   `fetch_page_image` solo se llama si el usuario la pide explícitamente
   (una página impresa concreta, una portada). Indexar un número nunca
   dispara descargas de imagen por su cuenta — mantiene la huella del
   workspace ligera por defecto (metadata + djvu.txt + toc.xml +
   page_numbers.json, por debajo de 1 MB por número).

## Flujo 1 — Traer un número

Disparadores: un identifier de archive.org (ej. `coevolutionquart00unse_15`),
o una URL `archive.org/details/{identifier}`.

1. Si el usuario da una URL, extrae el `identifier` del segmento tras
   `/details/`.
2. Llama:

   ```python
   from pathlib import Path
   from lib import downloader
   result = downloader.fetch_essentials(identifier, Path(workspace))
   ```

3. `fetch_essentials` es idempotente por fichero — si ya se había descargado
   antes, no vuelve a pegar a archive.org, y el resultado es indistinguible
   para el caller. No hace falta preguntar "¿ya lo tienes?"; simplemente
   llama y reporta el resultado.
4. Confirma al usuario qué se descargó: lista `result["files"]` (las keys
   presentes; recuerda que `page_numbers` puede faltar si el item no lo
   ofrece) y la ruta `result["dir"]`.
5. Si `fetch_essentials` lanza `LookupError`, el identifier no existe en
   archive.org — dilo al usuario tal cual, no reintentes con variaciones
   inventadas del identifier.

Este flujo no propone estructura ni escribe nada en `processed/` — solo puebla
`sources/{identifier}/`. Indexar es el Flujo 2, un paso aparte.

## Flujo 2 — Indexar un número

Disparadores: "indexa el número...", "estructura este número en artículos",
o continuación natural del Flujo 1 cuando el usuario pide seguir.

Requiere que `sources/{identifier}/` ya exista (ejecuta primero el Flujo 1 si
no).

1. Lee `sources/{identifier}/{identifier}_djvu.txt` (texto OCR, fuente
   primaria) y, si existe, `sources/{identifier}/{identifier}_toc.xml` (pista
   de estructura, no confiable por sí sola) con el tool Read.
2. A partir de esa lectura, propón — sin escribir nada todavía:
   - `titulo` del número, `fecha`, y si aplica `volumen`/`numero`.
   - `publicacion_key`: resuélvela mirando `publications.yaml` del workspace
     con `lib.config.load_publications(Path(workspace))` — busca la
     publicación cuyo `archive_identifiers` incluya este `identifier`. Si no
     la encuentras, pregunta al usuario qué `publicacion_key` usar; no la
     inventes.
   - Una lista de artículos candidatos, cada uno con un título propuesto y su
     `body_text` ya recortado (el fragmento correspondiente de `djvu.txt`,
     no todo el texto del número). Numéralos en el orden en que aparecen:
     `article_id = f"{identifier}-{NN}"`, `NN` de dos dígitos con cero a la
     izquierda (`01`, `02`, ...) — es el patrón exacto que exige
     `write_processed`.
   - Puedes proponer solo un subconjunto de artículos si el usuario pidió
     "indexa el primer artículo" o similar; no hace falta cubrir el número
     entero en una sola pasada.
3. Presenta la propuesta al usuario y **pide confirmación explícita** antes
   de continuar (regla 1 de arriba). Si el usuario pide cambios, ajusta la
   propuesta y vuelve a confirmar — no escribas una propuesta a medio
   corregir.
4. Solo tras la confirmación, llama:

   ```python
   from pathlib import Path
   from lib import processor
   result = processor.write_processed(
       identifier,
       Path(workspace),
       {
           "titulo": titulo,
           "fecha": fecha,
           "publicacion_key": publicacion_key,
           "volumen": volumen,       # opcional, o no incluir la key
           "numero": numero,         # opcional, o no incluir la key
           "articulos": articulos,   # cada uno con article_id, titulo,
                                      # body_text, y opcionalmente autores/paginas
       },
   )
   ```

5. `write_processed` hace upsert por `article_id` sobre el número ya
   procesado: si el usuario ya confirmó algunos artículos en una llamada
   anterior y ahora quiere añadir más, basta con pasar los artículos nuevos
   en `articulos` — no repitas los ya escritos. `titulo`/`fecha`/
   `publicacion_key` solo son obligatorios en la primera llamada para un
   identifier; en llamadas posteriores puedes omitirlos si no cambian (se
   conserva lo ya guardado).
6. Si `write_processed` lanza `ValueError` (falta un campo requerido, o un
   `article_id` no cumple el patrón), corrige la propuesta y repite — no
   ocultes el error al usuario.
7. Confirma el resultado: `result["index_path"]` y `result["article_paths"]`
   son los ficheros escritos o actualizados en esta llamada.

## Flujo 3 — Pedir una imagen de página

Disparadores: el usuario pide explícitamente una página impresa concreta
("tráeme la portada", "la página 16 en imagen", "el facsímil del artículo de
Bateson"). **Nunca se dispara solo porque se está indexando un número** (regla
2 de arriba) — si el usuario no lo pide, no se descarga ninguna imagen.

1. Necesita `sources/{identifier}/{identifier}_page_numbers.json`, que ya
   debería existir si se corrió el Flujo 1 antes (es parte de
   `fetch_essentials`). Si no existe para este item, dilo al usuario: este
   número no tiene mapa de páginas impresas en archive.org.
2. Llama directamente con el número de página impreso tal y como lo dio el
   usuario (la resolución a `leaf` interno la hace `fetch_page_image`
   internamente, usando `resolve_leaf` sobre `page_numbers.json`):

   ```python
   from pathlib import Path
   from lib import downloader
   path = downloader.fetch_page_image(
       identifier, Path(workspace), printed_page="16"
   )
   ```

   Usa `size` explícito solo si el usuario pide una resolución concreta
   (`"medium" | "w500" | "w1000"`) — si no dice nada, deja el default
   (`w500`).
3. Si `fetch_page_image` lanza `LookupError`, ese número de página impresa no
   aparece en `page_numbers.json` — dilo al usuario; puedes ofrecer inspeccionar
   `page_numbers.json` a mano con `lib.downloader.resolve_leaf` sobre su
   contenido para ayudar a encontrar el `leaf` correcto si el usuario conoce
   el índice interno en vez del número impreso.
4. Confirma al usuario la ruta del fichero descargado. No descargues ninguna
   otra página ni el número completo en imagen — solo la pedida.

## Flujo 4 — Traer una colección completa (Fase 2)

Disparadores: "trae toda la colección de {publicación}", "descubre los
números que faltan de {publicación}" — publicaciones con
`mode: discover_collection` en `publications.yaml`.

1. Resuelve la publicación:

   ```python
   from lib import config
   publicaciones = config.load_publications(Path(workspace))
   ```

   Busca la entrada cuyo `key` coincida con lo que pidió el usuario y cuyo
   `mode` sea `discover_collection`; toma su `archive_collection`. Si no
   existe tal publicación en `publications.yaml`, dilo al usuario — este
   flujo no crea publicaciones nuevas (eso es `SETUP-01`/el wizard).
2. Llama:

   ```python
   from lib import archive_client
   candidatos = archive_client.search_collection(archive_collection)
   ```

3. **No descargues nada todavía.** Lista los candidatos al usuario (identifier,
   título, fecha, volumen/número — los campos que devuelva `search_collection`)
   y espera a que confirme explícitamente cuáles quiere ingerir.
4. Solo para los identifiers que el usuario confirme, ejecuta el Flujo 1
   (`fetch_essentials`) uno por uno, y opcionalmente encadena el Flujo 2 si
   también pide indexarlos.

## Fuera de alcance de este skill

- No genera contenido de activación (historias, prompts creativos) a partir
  de `processed/` — eso consume el material que este skill produce, pero es
  otra herramienta o un skill posterior.
- No traduce contenido multi-idioma. Trabaja en español con el usuario, pero
  no traduce el material fuente (que puede estar en inglés, como
  *CoEvolution Quarterly*) al proponer título/artículos.
