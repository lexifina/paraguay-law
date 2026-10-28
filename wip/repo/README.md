# Paraguay: law history in git

The law of Paraguay as a git history: one file per provision, one commit per law on the day it took effect, and the law that made each change as the commit's author. `git blame` names the law behind every paragraph; `git log` lists every change to an article; checking out a date gives the text in force that day.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `py/`.

**What is in it now**

| Folder | Act | Versions | History |
| --- | --- | ---: | --- |
| `constitucion/` | Constitución de la República del Paraguay (1992) | 2 | As enacted (20 June 1992), then Enmienda Constitucional N° 1 (art. 120, in force 17 October 2011) |
| `codigo-civil/` | Código Civil (Ley N° 1183/1985) | 19 | As enacted (in force 1 January 1987), then 18 amending laws from Ley 45/1991 (divorce) to Ley 7371/2025 (persons with disabilities), each applied from its own text |
| `codigo-penal/` | Código Penal (Ley N° 1160/1997) | 20 | As enacted (in force 26 November 1998), then 18 amending laws from Ley 2212/2003 (kidnapping) to Ley 7300/2024 (theft of electricity), each applied from its own text; Ley 3440/2008 takes effect in two steps (21 August 2008 and 16 July 2009) |
| `codigo-procesal-penal/` | Código Procesal Penal (Ley N° 1286/1998) | 16 | Applied in part from 9 July 1999 and in full from 1 March 2000 (Ley 1444/1999), then 13 laws to 2019, including the suspended Ley 4669/2012 and two temporary 2019 laws |

The Constitution is complete: 291 articles, the preamble, the 20 final and transitional provisions, the closing formula, and an index of its parts, titles, chapters and sections (`constitucion/indice.md`). It has been amended once since 1992.

The Civil Code has 2,810 of its 2,815 articles as enacted (BACN's transcription lacks arts. 733, 1170, 1571, 2414 and 2566), the closing formula, and an index of its books, titles, chapters, sections and paragraphs (`codigo-civil/indice.md`). BACN publishes the Code only as enacted, so every later version here is rebuilt by applying each amending law's own text in order of entry into force: rewritten articles (for example art. 36, majority at 18, by Ley 2169/2003 and again by Ley 7371/2025), repealed articles (40 by Ley 1/1992, arts. 867-879 by Ley 1328/1998), one transitional wording (art. 1725 under Ley 805/1996 until 1 January 1997) and two retitled chapters. The Penal Code has all 326 articles as enacted and the closing formula. Its later versions replay 18 amending laws the same way, including Ley 3440/2008 (about sixty articles), the computer-crime articles of Ley 4439/2011 (146b-146d, 174b, 175b, 248b) and the sicariato article 105b of Ley 7062/2023. Where a law replaces art. N by lettered articles (129 by 129a-129c, 184 by 184a-184c, 135, 191, 268, 105), art. N is removed and the lettered articles are added. Its book, title and chapter headings are not kept (see "What it does not show").

The Code of Criminal Procedure has 504 of its 506 articles as they first applied on 9 July 1999 (Ley 1444/1999 repealed art. 17 inc. 15 and art. 505 that day), the closing formula and an index of its parts, books, titles and chapters. Its history shows three kinds of change that leave a trace even without new words:
- Ley 4669/2012 rewrote arts. 136-137 from 24 July 2012; Ley 4734/2012 suspended it from 12 September 2012 (that commit restores the earlier wording, `Restores:` trailer); three laws extended the suspension and Ley 6146/2018 repealed Ley 4669. Each of those four is a commit with `Words-changed: no`.
- Leyes 6353/2019 and 6418/2019 changed arts. 129, 141, 251 and 253 until 31 January 2020 (`Temporary-until:`); on 1 February 2020 a "fin de vigencia" commit restores the original wording.
- Full application on 1 March 2000 is a commit by Ley 1444/1999 that changes no words.

More acts follow as their history can be shown from official text; see "What it does not show".

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What did art. 120 say on 1 January 2010? | `python tools/en_vigor_el.py 2010-01-01 constitucion 120` |
| Majority age in the Civil Code on 1 January 2003 | `python tools/en_vigor_el.py 2003-01-01 codigo-civil 36` |
| Maximum length of a criminal case (CPP art. 136) on 1 August 2012, during Ley 4669 | `python tools/en_vigor_el.py 2012-08-01 codigo-procesal-penal 136` |
| Family violence (Penal Code art. 229) on 1 January 2013, and who wrote it | `python tools/en_vigor_el.py --law 2013-01-01 codigo-penal 229` |
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
- **The Civil Code cannot be checked against an official consolidated text, because none is published.** Its history is a replay: the enacted text plus every amending law found with BACN's full-text search and sitemap (queries for "1183", "1.183", "1183/85", "1183/1985" and "código civil"), each read for the articles it rewrites or repeals. The replay stops with an error if a law rewrites or repeals an article that is not in force. An amending law that BACN's search does not find would be missing; laws that only say "the contrary provisions are repealed" (Ley 45/1991 art. 23, Ley 1/1992 art. 98 second paragraph) are not applied, because they name no article.

## What "author" means

The author of a commit is the law that made the change, with an e-mail address that cannot exist (`enmienda-2011-1@bacn.invalid`), so `git blame` and `git log --author` name laws. The committer is always `Lexifina <paraguay-law@lexifina.com>`. A change that no amendment note explains would be committed by the publisher, BACN, and labelled "unexplained"; there are none so far.

Blame credits whole lines (one paragraph per line). Use `git log -p --word-diff` to see exactly which words a law changed.

## What it does not show

- **Penal Code headings.** The book/title/chapter headings of the Penal Code are not in the repository: Ley 3440/2008 rearranged the chapters of Title II of Book Two and Ley 6452/2019 added one, and the laws print the new headings next to the first article they rewrite, so the structure cannot be rebuilt mechanically. Each article keeps its own epigraph.
- **The Code of Criminal Procedure's first day.** Ley 1444/1999 repealed art. 17 inc. 15 and art. 505 from the same day the Code first applied (9 July 1999), so the first version already lacks them and no separate commit records those two repeals.
- **The Penal Code and the Code of Criminal Procedure, like the Civil Code, have no official consolidated text** to check the current text against; the history is a replay of every amending law found with BACN's search ("1160", "1.160", "1160/97", "1160/1997", "código penal").
- **Five Civil Code articles are missing** (733, 1170, 1571, 2414, 2566): BACN's HTML skips them and the scan it links has no text layer. They are left out rather than typed in.
- **Publication dates.** Where BACN gives no usable publication date (Leyes 1/1992, 388/1994, 701/1995), a version is dated the day after promulgation; `REPRODUCE.md` lists each case. For Ley 1/1992, BACN's promulgation date (9 April 1992) is earlier than its sanción, so the date cited in Ley 985/1996 (15 July 1992) is used.
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

Historia del derecho paraguayo en git: un archivo por disposición y un commit por ley, fechado el día de su entrada en vigencia y firmado por la ley que hizo el cambio (`git blame` nombra la ley de cada párrafo). Contiene la Constitución Nacional de 1992 tal como fue sancionada y su Enmienda N° 1 (artículo 120, voto de los paraguayos en el exterior), sancionada y promulgada el 17 de octubre de 2011 tras el referéndum (Acuerdo y Sentencia N° 23 del TSJE). Contiene también el Código Civil (Ley N° 1183/1985) tal como fue sancionado, vigente desde el 1 de enero de 1987, y sus modificaciones por 18 leyes, desde la Ley 45/1991 hasta la Ley 7371/2025, aplicadas a partir del texto de cada ley modificatoria. La BACN no publica un texto consolidado del Código, por lo que el texto actual no puede cotejarse con uno oficial; faltan los artículos 733, 1170, 1571, 2414 y 2566, ausentes en la transcripción de la BACN. Contiene además el Código Penal (Ley N° 1160/1997), vigente desde el 26 de noviembre de 1998, y sus modificaciones por 18 leyes, desde la Ley 2212/2003 hasta la Ley 7300/2024, aplicadas del mismo modo. Y el Código Procesal Penal (Ley N° 1286/1998), aplicado parcialmente desde el 9 de julio de 1999 y plenamente desde el 1 de marzo de 2000 (Ley 1444/1999), con la Ley 4669/2012 (suspendida y luego derogada) y las modificaciones temporales de 2019 (Leyes 6353 y 6418).

- Texto vigente en una fecha: `python tools/en_vigor_el.py 2010-01-01 constitucion 120`
- Regla supletoria de vigencia: art. 1 del Código Civil (desde el día siguiente al de su publicación, o desde el día que la ley determine) y art. 213 de la Constitución.
- Fuente: Biblioteca y Archivo Central del Congreso Nacional (BACN). La BACN no publica versiones anteriores; cada versión anterior se reconstruye a partir del texto de la ley modificatoria. Ningún modelo de IA escribió texto legal.
