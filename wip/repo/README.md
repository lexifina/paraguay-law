# Paraguay: law history in git

The law of Paraguay as a git history: one file per provision, one commit per law on the day it took effect, and the law that made each change as the commit's author. `git blame` names the law behind every paragraph; `git log` lists every change to an article; checking out a date gives the text in force that day.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `py/`.

**What is in it now**

| Folder | Act | Versions | History |
| --- | --- | ---: | --- |
| `constitucion/` | Constitución de la República del Paraguay (1992) | 2 | As enacted (20 June 1992), then Enmienda Constitucional N° 1 (art. 120, in force 17 October 2011) |

The Constitution is complete: 291 articles, the preamble, the 20 final and transitional provisions, the closing formula, and an index of its parts, titles, chapters and sections (`constitucion/indice.md`). It has been amended once since 1992. More acts follow as their history can be shown from official text; see "What it does not show".

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What did art. 120 say on 1 January 2010? | `python tools/en_vigor_el.py 2010-01-01 constitucion 120` |
| The same, with raw git (bash) | `git show $(git rev-list -1 --before="2010-01-01T23:59:59Z" main -- constitucion/art-120.md):constitucion/art-120.md` |
| The same, in PowerShell | `$r = git rev-list -1 --before="2010-01-01T23:59:59Z" main -- constitucion/art-120.md; git show "$($r):constitucion/art-120.md"` |
| Which law wrote each paragraph of art. 120? | `git blame constitucion/art-120.md` |
| Every change to art. 120, word by word | `git log -p --word-diff constitucion/art-120.md` |
| Every law in the record, in order | `git log --reverse --format="%ad %an" --date=short main` |
| Everything one law changed | `git show law/enmienda-2011-1` (tags `law/<key>` mark each law's commit) |
| The whole act on a date | `python tools/en_vigor_el.py 2000-01-01 constitucion` |
| Laws passed but not yet in force | `git log main..futuro` (the branch exists only when there are any) |

After a rebuild, refresh tags with `git fetch --force --tags`: a plain fetch keeps stale tags.

## Dates

- Each commit is dated at **noon, America/Asuncion, on the day the change took effect** (the in-force date). Enactment and publication dates are trailers (`Enacted:`, `Published:`), and the in-force day is in `In-force:`, which the tools read.
- **Default rule.** Código Civil (Ley 1183/1985), Título preliminar, art. 1: "Las leyes son obligatorias en todo el territorio de la República desde el día siguiente al de su publicación, o desde el día que ellas determinen" (from the day after publication, unless the law sets its own day). Constitución Nacional art. 213: a law binds only once promulgated and published. A law's own vigencia clause overrides the default.
- **The Constitution** took effect on 20 June 1992 (its final provision art. 1: "entra en vigencia desde la fecha").
- **Constitutional amendments** (art. 290) are sanctioned and promulgated by an affirmative referendum and incorporated into the text. Enmienda N° 1 was approved by the Chamber of Deputies on 28 October 2010 and the Senate on 14 April 2011, approved in the referendum, and declared "sancionada y promulgada" on 17 October 2011 (Acuerdo y Sentencia N° 23 of the Tribunal Superior de Justicia Electoral). That date is on the signed original and in BACN's annotation, and it is the date used.
- `--before="YYYY-MM-DD"` alone uses your clock's time of day, so a law that took effect that day may be missed before noon. Use `T23:59:59Z` as above, or the tool.

## How it is checked

- Every version of every act is read back from git on the day it took effect and on the day before (`tools/check_repo.py`); both must match `corpus.json`. Results are in `REPRODUCE.md`.
- Health checks: no merge commits on `main`, commit dates never go backwards, nothing dated in the future, and every commit's trailers parse with `git interpret-trailers --parse`.
- Against the official text today: the repository's current text equals BACN's Constitution page in every provision except art. 120, where BACN still prints the 1992 wording under a "(Modificado por ENMIENDA CONSTITUCIONAL N° 1)" note. The repository follows the Enmienda itself. Every such difference is listed in `REPRODUCE.md` under the decisions.
- The amended art. 120 is read from the text layer of the signed original of the Enmienda (a BACN scan) and compared with BACN's HTML transcription. They differ in two small points ("Ley"/"ley", and a final full stop), and the signed original is used.

## What "author" means

The author of a commit is the law that made the change, with an e-mail address that cannot exist (`enmienda-2011-1@bacn.invalid`), so `git blame` and `git log --author` name laws. The committer is always `Lexifina <paraguay-law@lexifina.com>`. A change that no amendment note explains would be committed by the publisher, BACN, and labelled "unexplained"; there are none so far.

Blame credits whole lines (one paragraph per line). Use `git log -p --word-diff` to see exactly which words a law changed.

## What it does not show

- **No dated consolidations exist.** BACN publishes one current text per law, partly consolidated with "(Modificado por …)" notes; it keeps no earlier versions, and its text under a note is not always updated (art. 120). Every earlier version here is rebuilt from the amending act's own text. Where the history cannot be shown from official text, the act is left out rather than guessed.
- **The Gaceta Oficial** (gacetaoficial.gov.py) did not answer from the build machine (connection timeout), so publication dates in the Gaceta are not recorded.
- **SILpy**, the Congress bill tracker, is not read: its robots.txt disallows every agent except Googlebot.
- Court rulings of unconstitutionality in Paraguay apply to the case, not to the text, so none appears as a commit.
- Text in Guaraní (the Constitution is official in both languages) is not included.

## How it is built

`tools/fetch.py` downloads every source page once through curl (one request per second, cached by the sha256 of the URL), `tools/parse.py` turns the cache into `corpus.json`, and the shared builder `tools/build.py` writes the history with `git fast-import`. The same corpus always gives the same hashes. `REPRODUCE.md` records every command, tool version, data hash and decision, and the result of a hash-for-hash rebuild.

No AI model wrote or changed legal text. Claude Opus 5.5 wrote the scripts and chose the sources; see `REPRODUCE.md`.

## Sources

| Source | Kind | Past versions | Names the amending act | Bulk | Notes |
| --- | --- | --- | --- | --- | --- |
| [BACN, Biblioteca y Archivo Central del Congreso Nacional](https://www.bacn.gov.py/leyes-paraguayas) | Official legislation | no | partly ("Modificado por …") | sitemap.xml lists all 7,126 law pages | Used. Signed originals as PDF scans |
| [Gaceta Oficial](https://www.gacetaoficial.gov.py) | Official gazette | n/a | n/a | no | Not reachable from the build machine |
| [SILpy](https://silpy.congreso.gov.py) | Bill tracker | n/a | n/a | no | robots.txt disallows crawling |
| [ypsoftware/leyes-paraguayas](https://github.com/ypsoftware/leyes-paraguayas) | Volunteer git repo | yes | partly | n/a | Prior art, used only for reconciliation; no text copied |

Research guides that cover every country: [GlobaLex](https://www.nyulawglobal.org/globalex/) and the [Law Library of Congress Guide to Law Online](https://www.loc.gov/research-centers/law-library-of-congress/researcher-resources/guide-to-law-online/).

## Licence

The legal texts are official texts of the Republic of Paraguay, as published by the Biblioteca y Archivo Central del Congreso Nacional (www.bacn.gov.py). BACN states no licence for its pages; official legal texts are public. The scripts, tables and documentation are by Lexifina, under the terms in `LICENSE`.

This repository is not legal advice and not an official publication.

## En español

Historia del derecho paraguayo en git: un archivo por disposición y un commit por ley, fechado el día de su entrada en vigencia y firmado por la ley que hizo el cambio (`git blame` nombra la ley de cada párrafo). Contiene la Constitución Nacional de 1992 tal como fue sancionada y su Enmienda N° 1 (artículo 120, voto de los paraguayos en el exterior), sancionada y promulgada el 17 de octubre de 2011 tras el referéndum (Acuerdo y Sentencia N° 23 del TSJE).

- Texto vigente en una fecha: `python tools/en_vigor_el.py 2010-01-01 constitucion 120`
- Regla supletoria de vigencia: art. 1 del Código Civil (desde el día siguiente al de su publicación, o desde el día que la ley determine) y art. 213 de la Constitución.
- Fuente: Biblioteca y Archivo Central del Congreso Nacional (BACN). La BACN no publica versiones anteriores; cada versión anterior se reconstruye a partir del texto de la ley modificatoria. Ningún modelo de IA escribió texto legal.
