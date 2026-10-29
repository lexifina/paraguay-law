"""Two administrative-law acts of Paraguay, one corpus.d part each (scripts/gitlaw_common/SCHEMA.md):

    corpus.d/63-procedimientos-administrativos.json   Ley 6715/2021 de Procedimientos Administrativos
    corpus.d/64-acceso-informacion-publica.json       Ley 5282/2014 de Libre Acceso Ciudadano a la Información
                                                      Pública y Transparencia Gubernamental

    python -X utf8 administrativo/administrativo.py --fetch     fetch (or reuse) every page in sources.json
    python -X utf8 administrativo/administrativo.py             read the cache only, write both parts
    python -X utf8 administrativo/administrativo.py --out DIR   write the test parts into DIR

Both laws are read as enacted from their BACN pages; the BACN search found no law that amends either. Reuses the BACN
helpers of ../parse.py and the list reader of ../datos/pages.py (imported, not copied). Deterministic: the same cache
gives the same bytes. No network unless --fetch.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'datos'))

import pages  # noqa: E402
import parse  # noqa: E402
from parse import LAWS, enacted_code, law, page_meta, sha, unit  # noqa: E402

URLS = json.loads((HERE / 'sources.json').read_text(encoding='utf-8'))['urls']
parse.AMEND_URLS.extend(u for u in URLS if u not in parse.AMEND_URLS)
parse.page_lines = pages.page_lines   # same lines as parse.py on pages without nested lists
URL_6715 = next(u for u in URLS if '/leyes-paraguayas/10974/' in u)
URL_5282 = next(u for u in URLS if '/leyes-paraguayas/3013/' in u)
ART = re.compile(r'^Art[íi]culo\s+(\d+)\s*(?:\.\s*[°º]|[°º]\s*\.-|\.-|\.)\s*(.*)$')
CLOSING = 'Aprobado el Proyecto de Ley por la Honorable'
NO_EPIGRAPH: dict[str, set[int]] = {'6715': set(), '5282': set()}


def unit_6715(n: int, rest: str, paras: list[str]) -> dict:
    """'Artículo 1°.- Objeto y Finalidad.' on a line of its own, the text below it; arts. 88, 90 and 91
    have no epigraph and print their text on the article line."""
    if not paras:
        NO_EPIGRAPH['6715'].add(n)
        return unit(f'Art. {n}', 'art', f'Artículo {n}', [rest])
    assert len(rest) < 160, (n, rest)
    return unit(f'Art. {n}', 'art', f'Artículo {n}. {rest.rstrip(".")}', paras)


def unit_5282(n: int, rest: str, paras: list[str]) -> dict:
    """'Artículo 1.° Objeto. La presente ley …': a first sentence of at most 60 characters followed by a capital is
    the epigraph; a short sentence alone on the line with text below it is one too (art. 26 'Cumplimiento.')."""
    m = re.match(r'^([^.]{1,60})\.\s+(?=[A-ZÁÉÍÓÚÑ"¿(])(.*)$', rest)
    if m:
        return unit(f'Art. {n}', 'art', f'Artículo {n}. {m.group(1)}', [m.group(2), *paras])
    if paras and re.fullmatch(r'[^.]{1,60}\.', rest):
        return unit(f'Art. {n}', 'art', f'Artículo {n}. {rest[:-1]}', paras)
    NO_EPIGRAPH['5282'].add(n)
    return unit(f'Art. {n}', 'art', f'Artículo {n}', [rest, *paras])


def anniversary(d: str) -> str:
    x = dt.date.fromisoformat(d)
    return x.replace(year=x.year + 1).isoformat()


def ley_6715() -> dict:
    m = page_meta(URL_6715)
    assert m == {'promulgated': '2021-09-29', 'published': '2021-09-29'}, m
    base = enacted_code(URL_6715, ART, ('Descripción', 'LEY N° 6715', 'DE PROCEDIMIENTOS ADMINISTRATIVOS',
                                        'EL CONGRESO DE LA NACIÓN PARAGUAYA SANCIONA CON FUERZA DE', 'LEY:'),
                        CLOSING, 91, unit_6715, 'ley-procedimientos-administrativos')
    assert NO_EPIGRAPH['6715'] == {88, 90, 91}, NO_EPIGRAPH
    assert base['art-090']['text'].startswith('# Artículo 90\nLa presente Ley entrará en vigencia un año después de '
                                              'su publicación en la Gaceta Oficial de la República.')
    law('ley-6715-2021', label='Ley N° 6715/2021', title='De Procedimientos Administrativos', kind='law',
        enacted=m['promulgated'], published=m['published'], url=URL_6715)
    first = {'from': anniversary(m['published']), 'source_url': URL_6715, 'sha256': sha(URL_6715), 'units': base,
             'credits': {},
             'note': 'The law as enacted, from its BACN page; in force one year after its publication on 29 September '
                     '2021 (art. 90).'}
    return {'slug': 'ley-procedimientos-administrativos', 'short': 'LPA',
            'title': 'Ley N° 6715/2021 de Procedimientos Administrativos', 'url': URL_6715,
            'first_law': 'ley-6715-2021', 'earlier_laws': [], 'versions': [first]}


def ley_5282() -> dict:
    m = page_meta(URL_5282)
    assert m == {'promulgated': '2014-09-18', 'published': '2014-09-19'}, m
    base = enacted_code(URL_5282, ART, ('Descripción', 'LEY N° 5.282',
                                        'DE LIBRE ACCESO CIUDADANO A LA INFORMACIÓN PÚBLICA Y TRANSPARENCIA '
                                        'GUBERNAMENTAL.', 'EL CONGRESO DE LA NACION PARAGUAYA SANCIONA CON FUERZA DE',
                                        'LEY'),
                        CLOSING, 33, unit_5282, 'ley-acceso-informacion-publica')
    assert NO_EPIGRAPH['5282'] == {27, 33}, NO_EPIGRAPH
    assert base['art-032']['text'] == ('# Artículo 32. Entrada en vigencia\nLa presente ley entrará a regir a partir '
                                       'del año siguiente de su promulgación.\n'), base['art-032']['text']
    law('ley-5282-2014', label='Ley N° 5282/2014',
        title='De Libre Acceso Ciudadano a la Información Pública y Transparencia Gubernamental', kind='law',
        enacted=m['promulgated'], published=m['published'], url=URL_5282)
    first = {'from': anniversary(m['promulgated']), 'source_url': URL_5282, 'sha256': sha(URL_5282), 'units': base,
             'credits': {},
             'note': 'The law as enacted, from its BACN page; in force one year after its promulgation on 18 '
                     'September 2014 (art. 32).'}
    return {'slug': 'ley-acceso-informacion-publica', 'short': 'LAIP',
            'title': 'Ley N° 5282/2014 de Libre Acceso Ciudadano a la Información Pública y Transparencia '
                     'Gubernamental', 'url': URL_5282, 'first_law': 'ley-5282-2014', 'earlier_laws': [],
            'versions': [first]}


SEARCH = ('Amending laws were looked for with the BACN search (queries "6715", "6715/2021", "procedimientos '
          'administrativos", "5282", "5282/2014", "5.282", "libre acceso ciudadano"); every hit was screened for a '
          'modifying, repealing or suspending formula that names the law, and none was found (Leyes 7411/2024, '
          '7547/2025 and 7593/2025 only refer to Ley 6715). The current text is therefore the enacted text; there is '
          'no official consolidated text to compare it with.')
LISTS = ('BACN HTML lists are read with datos/pages.py (nested lists numbered innermost first, markers as the page '
         'CSS shows them); unit headings and chapter headings as for the other acts (indice.md, sancion.md).')


def write_part(dest: Path, part: dict) -> None:
    out = json.dumps(part, ensure_ascii=False, indent=1) + '\n'
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_name(dest.name + '.tmp')
    tmp.write_text(out, encoding='utf-8', newline='\n')
    tmp.replace(dest)
    print(*(f'{a["slug"]} {len(a["versions"])} versions' for a in part['acts']), f'{len(part["laws"])} laws ->', dest)


def main():
    if '--fetch' in sys.argv:
        from fetch import fetch
        for u in URLS:
            fetch(u)
        return
    a6715, a5282 = ley_6715(), ley_5282()
    assert not parse.JOINS and not parse.MISMATCHES, (parse.JOINS, parse.MISMATCHES)
    ai = ('Claude Opus 5.5 (claude-opus-5-5) in Claude Code wrote administrativo/administrativo.py, ran the BACN '
          'searches and screened the hits. No model wrote or changed legal text: every provision is extracted by '
          'code from the BACN page.')
    outdir = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else ROOT / 'corpus.d'
    write_part(outdir / '63-procedimientos-administrativos.json', {
        'laws': {'ley-6715-2021': LAWS['ley-6715-2021']},
        'acts': [a6715],
        'decisions': [
            'Ley 6715/2021 de Procedimientos Administrativos: BACN publishes it as enacted (promulgated and, per BACN, '
            'published on 29 September 2021). Art. 90: in force "un año después de su publicación en la Gaceta '
            'Oficial", taken as the anniversary, 2022-09-29, as for the Código Penal ("un año después de su '
            'promulgación"). Art. 89 repeals arts. 11-17 of Ley 4679/2012 (not in this repository).',
            'Ley 6715/2021: ' + SEARCH,
            'Ley 6715/2021 units: art-NNN headed "# Artículo N. Epigraph" (BACN prints the epigraph on the article '
            'line and the text below it; arts. 88, 90 and 91 have none). ' + LISTS,
            'Ley 6715/2021: no line joins were needed.'],
        'ai_use': ['Ley 6715/2021 part: ' + ai]})
    write_part(outdir / '64-acceso-informacion-publica.json', {
        'laws': {'ley-5282-2014': LAWS['ley-5282-2014']},
        'acts': [a5282],
        'decisions': [
            'Ley 5282/2014 de Libre Acceso Ciudadano a la Información Pública y Transparencia Gubernamental: BACN '
            'publishes it as enacted (promulgated 18 September 2014). Art. 32: "entrará a regir a partir del año '
            'siguiente de su promulgación", taken as one year after promulgation, 2015-09-18.',
            'Ley 5282/2014: ' + SEARCH,
            'Ley 5282/2014 units: art-NNN headed "# Artículo N. Epigraph": the epigraph is the opening sentence when '
            'it has at most 60 characters and is followed by a capital (art. 26 prints "Cumplimiento." alone on its '
            'line); arts. 27 and 33 have none. ' + LISTS,
            'Ley 5282/2014: no line joins were needed.'],
        'ai_use': ['Ley 5282/2014 part: ' + ai]})


if __name__ == '__main__':
    main()
