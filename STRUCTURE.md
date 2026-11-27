# Estructura / Structure

Consolidated laws keep their own folders at the root (`codigo-civil/`, `ley-*/`, ...): one file per article, one commit per version.

Every other Ley, as enacted, is in `leyes/<año>/<número>-<objeto>/texto.md` (year of promulgation, four-digit number, short title; at most 1,000 folders per year). `texto.md` is the text exactly as the Biblioteca y Archivo Central del Congreso Nacional (BACN) publishes it. One commit per law, dated 12:00 America/Asuncion on the day it came into force; the commit trailers give `In-force`, `In-force-basis`, `Promulgated`, `Published` and `Source`.

Laws with no readable in-force day are not committed (see the held list kept with the build scripts).
