# Tools

The scripts behind this Paraguay-only run of global-law's vulnerability detectors. They run inside a copy of
[global-law/vulnerabilities/scripts](https://github.com/lexifina/global-law/tree/main/vulnerabilities/scripts) (Python 3.11+,
`pip install duckdb pyarrow`), with a bare clone of this repository at `sources/corpus/paraguay-law.git`, a blobless bare
clone of global-law at `sources/global-law.git`, and a `pins.json` that names only paraguay-law, its commit and its
language (`es`). `build_vulns.py`, `flags_chart.py`, `late_ext_select.py`, `late_ext_rebut.py` and `config.json` sit two
folders above the scripts.

| Script | What it does |
| --- | --- |
| `run.sh` | Indexes the history and texts, maps paths to the folders since a move (`map_moved.py`), adds this repository's history rows, and runs the detectors (`bash run.sh <shards>`) |
| `add_root.py` | Builds the history rows from this repository's own commits (global-law replays it only up to an earlier commit), so the history detectors read every change |
| `map_moved.py` | Rewrites the paths in the history table to each act's folder after a move of folders (`data/paths.json`); this repository has no such file, so here it changes nothing |
| `run_triage.sh` | The model review: the 40 strongest flags per category, the 40 strongest lapsed time limits in law texts, and the empty periods (here none) |
| `late_ext_select.py` | Chooses the empty periods for global-law's review of that category (here there were none) |
| `late_ext_rebut.py` | Adds the second, arguing-against pass to the empty-period review, as `triage.py` does for the other categories |
| `build_vulns.py` | Builds `data/flags.csv`, `data/reviewed.csv` and `data/by_category.csv` from the findings and the model review |
| `flags_chart.py` | Draws the chart at the top of the READMEs, in Spanish and English, light and dark |
| `config.json` | The repository, the Spanish category names, the folders and files that are not law, and the chart's labels |
| `patch_detectors.py` | Fixes blind spots found in runs on several country repositories in the copy of global-law's scripts (`python -X utf8 patch_detectors.py <scripts dir>`; a fix already in place is skipped) |
| `patch_detectors_vi.py`, `patch_es.py`, `patch_ca.py`, `patch_en.py`, `patch_de.py`, `patch_en_et.py`, `patch_co.py`, `patch_sv.py`, `patch_pt.py`, `patch_ru.py`, `patch_r18.py`, `patch_xk.py`, `patch_mo.py`, `patch_lu.py`, `patch_li.py`, `patch_mx.py`, `patch_mn.py`, `patch_mt.py`, `patch_np.py`, `patch_en_nr.py`, `patch_dv.py`, `patch_az.py`, `patch_ar.py`, `patch_en_nz.py`, `patch_nb.py`, `patch_mk.py`, `patch_pa.py` | The same for the Vietnamese, Spanish, Catalan, English, German, Colombian, Salvadoran, Brazilian, Russian, Kosovar, Macanese, Luxembourg, Liechtenstein, Mexican, Mongolian, Maltese, Nepalese, Nauruan, Maldivian, Azerbaijani, Omani, New Zealand, Norwegian, Macedonian and Panamanian blind spots and a round on currencies, found by other runs; this run's copy carries them all. Of them, the Spanish and Colombian date forms ("hasta el día 31 de diciembre de 2020", "1o. de enero", "a más tardar el ...") also serve Paraguayan Spanish |
| `patch_py.py` | The fixes below, made for this repository |
| `apply_patches.py` | Applies every patch above once, in order (`patch_py.py` last), recording each in `.kit_patches.json` beside the scripts so that none runs twice (`python -X utf8 apply_patches.py <scripts dir>`) |
| `redo.py` | Runs the patches, then again only the scans and detectors the fixes change, the model review of lapsed time limits, references to deleted provisions and empty periods, and the build (`python -X utf8 redo.py <run folder> [--keep-reviews] [--full]`; `--full` runs every step again through `run.sh`; `EMBED_FONTS` names the script that embeds the chart's fonts). It applies the patches through the `apply_patches.py` beside it, `patch_py.py` among them |

The model review needs `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` and `LLM_AUTH` set for an OpenAI-compatible Responses API.
There were only 14 flags, so the review read all of them; the one lapsed time limit is in a law text, so the two reviews of
that category drew the same flag, and `build_vulns.py` keeps the later review.

Changes made for this repository:

- `add_root.py`: this repository marks its laws `Kind: law`, the one change no law explains (Article 2 of the narcotics law,
  credited to BACN) `Kind: publisher`, and Constitutional Amendment No. 1 of 2011, approved by referendum,
  `Kind: referendum`. The last was not counted as law, so `referendum` was added to the list: 357 of the 370 commits now
  count (355 laws, the publisher change and the amendment); the other 13 are documentation and carry no `Kind:`.
- `patch_py.py`, dead currencies: in Spanish "marco" is a framework, not the Deutsche Mark ("8. marco penal:", the
  sentencing range, in Article 14 of the Criminal Code, was read as a mark). For Spanish texts the mark is now read only
  as "marcos" after an amount or as "marco(s) alemán/alemanes": 1 flag became 0.
- `patch_py.py`, publisher notes: "no pudo realizarse" is ordinary law text in Spanish ("Si ésta no pudo realizarse, se
  estará a su valor", Article 982 of the Civil Code), but the search read it as a note on an amendment that could not be
  made. Those words now need an amendment as their subject ("la modificación no pudo realizarse"); "no ha podido ser
  incorporada" is read as before: 1 flag became 0.
- `patch_py.py`, publisher notes (all languages): a comment that `patch_mx.py` added ran on into the Austrian pattern
  `\(Anm\.: richtig` that an earlier patch had put on the same line, so that pattern was commented out. It is put back on a
  line of its own; no effect on Paraguay. Every change in `patch_py.py` carries a marker, so it is recognised as in place
  even if a later patch edits the same text.
- `patch_pa.py` reached the kit after the run; `apply_patches.py` applied it, and the duplicate-numbering and currency
  searches it changes were run again: no count changed (both were already at 0).
- `flags_chart.py` takes a `tip1` from `config.json`, the tooltip for a category with one flag ("1 alerta", not
  "1 alertas"), and draws no "other texts" legend when every flag is in a law text.
- `config.json` counts as not law `data/`, `tools/` and the top-level files (`README`, `REPRODUCE.md`, `LICENSE`,
  `jurisdiction.json`), and each act's `README.md` (its list of provisions) and `indice.md` (its headings) wherever they
  are. The act folders (`constitucion/`, the `codigo-*` folders, `estatuto-agrario/` and the `ley-*` folders), with their
  enacting formulas (`sancion.md`), are law. It gives the chart shorter Spanish labels for the two reference categories, as
  Mexico's does.
- `pins.json` names the language (`es`); Spanish month names were already in the time-limit search.
