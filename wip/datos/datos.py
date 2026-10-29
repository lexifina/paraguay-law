"""Data protection laws of Paraguay: writes corpus.d/60-datos-crediticios.json and
corpus.d/62-proteccion-datos-personales.json, one part per act (scripts/gitlaw_common/SCHEMA.md).

    python -X utf8 datos/datos.py --fetch     fetch (or reuse) every page in datos/sources.json
    python -X utf8 datos/datos.py             read the cache only, write both parts into ../corpus.d
    python -X utf8 datos/datos.py --out DIR   write the test parts into DIR

Two acts: Ley 6534/2020 de Protección de Datos Personales Crediticios (in force since 2020) and Ley 7593/2025 de
Protección de Datos Personales en la República del Paraguay (in force only from 2027, so it is on the future branch),
which repeals provisions of Ley 6534 from the day it takes effect. Reuses the BACN helpers and the Replay engine of
../parse.py (imported, not copied); datos/pages.py reads the nested HTML lists these two pages use. Deterministic:
the same cache gives the same bytes. No network unless --fetch.
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
sys.path.insert(0, str(HERE))

import parse  # noqa: E402
import pages  # noqa: E402
from parse import LAWS, MISMATCHES, Replay, enacted_code, law, page_meta, sha, split_upper, unit  # noqa: E402

URLS = json.loads((HERE / 'sources.json').read_text(encoding='utf-8'))['urls']
parse.AMEND_URLS.extend(u for u in URLS if u not in parse.AMEND_URLS)
parse.page_lines = pages.page_lines   # parse.enacted_code looks it up at call time; same lines on un-nested pages

URL_6534 = next(u for u in URLS if '/leyes-paraguayas/9417/' in u)
URL_7593 = next(u for u in URLS if '/leyes-paraguayas/12924/' in u)
SLUG_6534 = 'ley-datos-crediticios'
SLUG_7593 = 'ley-proteccion-datos-personales'
ART = re.compile(r'^Art[íi]culo\s+(\d+)\s*(?:\.\s*[°º]|[°º]\s*\.-|\.-|\.)\s*(.*)$')
CLOSING = 'Aprobado el Proyecto de Ley por la Honorable'


def unit_6534(n: int, rest: str, paras: list[str]) -> dict:
    """'Artículo 1°.- OBJETO. La presente Ley …': the capital-letter sentence(s) are the epigraph."""
    epi, first = split_upper(rest)
    return unit(f'Art. {n}', 'art', f'Artículo {n}.- {epi}' if epi else f'Artículo {n}',
                [p for p in [first, *paras] if p])


def unit_7593(n: int, rest: str, paras: list[str]) -> dict:
    """'Artículo 1.° Objeto de la ley.' on a line of its own, the text below it."""
    if not paras:
        return unit(f'Art. {n}', 'art', f'Artículo {n}', [rest])
    assert len(rest) < 160, (n, rest)
    return unit(f'Art. {n}', 'art', f'Artículo {n}. {rest.rstrip(".")}', paras)


def headings_7593() -> tuple[str, ...]:
    """Ley 7593 prints chapter headings in mixed case ('Capítulo I' / 'Del objeto y ámbito de aplicación.'):
    a 'Capítulo' line and the line after it are headings (title lines are in capitals and found by parse.py)."""
    L = pages.page_lines(URL_7593)
    out = []
    for i, ln in enumerate(L):
        if re.fullmatch(r'Cap[íi]tulo (?:[IVX]+|Único)', ln):
            assert not ART.match(L[i + 1]), L[i + 1]
            out += [ln, L[i + 1]]
    return tuple(out)


def in_force_7593(published: str) -> str:
    """Art. 57: in force 'luego de transcurridos veinticuatro meses de su publicación oficial'. Código Civil art.
    339: a period of months ends when the day with the same number as the day it began has passed."""
    p = dt.date.fromisoformat(published)
    end = p.replace(year=p.year + 2)
    return (end + dt.timedelta(days=1)).isoformat()


def drop_lines(starts: list[str], *, then_numbered: bool = False):
    """Remove the inciso lines that begin with each of `starts` (and, with then_numbered, the '1.', '2.', … items
    printed under it), checking that each is found once."""
    def fn(u: dict) -> dict:
        lines = u['text'].rstrip('\n').split('\n')
        out = []
        skipping = False
        hit = {s: 0 for s in starts}
        for ln in lines:
            s = next((s for s in starts if ln.startswith(s)), None)
            if s:
                hit[s] += 1
                skipping = then_numbered
                continue
            if skipping and re.match(r'^\d+\. ', ln):
                continue
            skipping = False
            out.append(ln)
        assert all(v == 1 for v in hit.values()), hit
        return dict(u, text='\n'.join(out) + '\n')
    return fn


def ley_6534() -> dict:
    m = page_meta(URL_6534)
    assert m == {'promulgated': '2020-10-27', 'published': '2020-10-27'}, m
    base = enacted_code(URL_6534, ART, ('Descripción', 'LEY N° 6534', 'DE PROTECCIÓN DE DATOS PERSONALES CREDITICIOS',
                                        'EL CONGRESO DE LA NACIÓN PARAGUAYA SANCIONA CON FUERZA DE', 'LEY:'),
                        CLOSING, 31, unit_6534, SLUG_6534)
    # no vigencia clause (art. 29 only gives existing entities 24 months from publication to adapt)
    assert not any(re.search(r'(?i)entrar[áa] en (vigencia|vigor)|regir[áa] (a partir|desde)', base[k]['text'])
                   for k in base if k != 'indice')
    law('ley-6534-2020', label='Ley N° 6534/2020', title='De Protección de Datos Personales Crediticios',
        kind='law', enacted=m['promulgated'], published=m['published'], url=URL_6534)
    first = {'from': parse.day_after(m['published']), 'source_url': URL_6534, 'sha256': sha(URL_6534), 'units': base,
             'credits': {},
             'note': 'The law as enacted, from its BACN page; it has no vigencia clause, so it is in force the day '
                     'after publication (Código Civil art. 1).'}
    rp = Replay(SLUG_6534, base, first)

    # Ley 7593/2025 art. 59, from the day Ley 7593 takes effect
    L = pages.page_lines(URL_7593)
    i = L.index('Artículo 59. Derogaciones.')
    assert L[i + 1] == ('Quedan derogados los incisos a) y b) del artículo 3º, el artículo 4º, el inciso b) del '
                        'artículo 20, el inciso x) del artículo 21 de la Ley Nº 6534/2020 "DE PROTECCIÓN DE DATOS '
                        'PERSONALES CREDITICIOS".'), L[i + 1]
    frm = in_force_7593(page_meta(URL_7593)['published'])
    k = 'ley-7593-2025'
    rp.op(frm, k, URL_7593, 'fn', 'art-003', drop_lines(['a. Datos Personales: ', 'b. Datos personales sensibles: ']),
          note='Ley 7593/2025 art. 59 repeals art. 3 incisos a) and b), art. 4, art. 20 inciso b) (with its numbered '
               'items 1-13) and art. 21 inciso x), from the day Ley 7593 takes effect; the remaining incisos keep '
               'their letters.')
    rp.op(frm, k, URL_7593, 'del', 'art-004')
    rp.op(frm, k, URL_7593, 'fn', 'art-020',
          drop_lines(['b. SECRETARÍA DE DEFENSA DEL CONSUMIDOR Y EL USUARIO. '], then_numbered=True))
    rp.op(frm, k, URL_7593, 'fn', 'art-021', drop_lines(['x. La transferencia internacional de datos personales ']))
    versions = rp.build()
    v = versions[-1]
    assert v['from'] == frm and sorted(v['credits']) == ['art-003', 'art-004', 'art-020', 'art-021'], v['credits']
    assert v['units']['art-020']['text'].count('\n') == base['art-020']['text'].count('\n') - 14
    return {'slug': SLUG_6534, 'short': 'LDPC', 'title': 'Ley N° 6534/2020 de Protección de Datos Personales Crediticios',
            'url': URL_6534, 'first_law': 'ley-6534-2020', 'earlier_laws': [], 'versions': versions}


def ley_7593() -> dict:
    m = page_meta(URL_7593)
    assert m == {'promulgated': '2025-11-27', 'published': '2025-11-27'}, m
    base = enacted_code(URL_7593, ART, ('Descripción', 'LEY Nº 7593',
                                        'DE PROTECCIÓN DE DATOS PERSONALES EN LA REPÚBLICA DEL PARAGUAY.',
                                        'EL CONGRESO DE LA NACIÓN PARAGUAYA SANCIONA CON FUERZA DE', 'L E Y:'),
                        CLOSING, 61, unit_7593, SLUG_7593, heading_lines=headings_7593())
    assert 'La presente ley entrará en vigor luego de transcurridos veinticuatro meses de su publicación oficial.' \
        in base['art-057']['text']
    law('ley-7593-2025', label='Ley N° 7593/2025',
        title='De Protección de Datos Personales en la República del Paraguay', kind='law',
        enacted=m['promulgated'], published=m['published'], url=URL_7593)
    frm = in_force_7593(m['published'])
    first = {'from': frm, 'source_url': URL_7593, 'sha256': sha(URL_7593), 'units': base, 'credits': {},
             'note': 'The law as enacted, from its BACN page; in force once twenty-four months from its publication '
                     '(27 November 2025) have passed (art. 57).'}
    return {'slug': SLUG_7593, 'short': 'LPDP',
            'title': 'Ley N° 7593/2025 de Protección de Datos Personales en la República del Paraguay',
            'url': URL_7593, 'first_law': 'ley-7593-2025', 'earlier_laws': [], 'versions': [first]}


def decisions(frm_7593: str) -> list[str]:
    return [
        'Datos personales: Ley 6534/2020 (Protección de Datos Personales Crediticios) and Ley 7593/2025 (Protección '
        'de Datos Personales en la República del Paraguay) are read from their BACN pages, as enacted. Amending laws '
        'were looked for with the BACN search (queries "datos personales", "crediticios", "6534", "6.534", "7593") '
        'and every hit from 2020 on was screened for a citation of either law: only Ley 7593/2025 changes Ley 6534; '
        'Ley 7636/2026 (del obstetra) only cites Ley 7593. Neither has an official consolidated text to compare with.',
        'Ley 6534/2020 has no vigencia clause: it is in force from 2020-10-28, the day after its publication on '
        '2020-10-27 (BACN metadata; Código Civil art. 1).',
        f'Ley 7593/2025 art. 57: in force "luego de transcurridos veinticuatro meses de su publicación oficial". BACN '
        f'gives publication on 2025-11-27; by Código Civil art. 339 a period of months ends when the day with the same '
        f'number as its first day has passed (2027-11-27), so the law is dated {frm_7593}. Counting from the day after '
        f'publication instead would give one day later. The whole act is on the future branch until then.',
        f'Ley 7593/2025 art. 59 repeals, in Ley 6534/2020, art. 3 incisos a) and b), art. 4, art. 20 inciso b) and '
        f'art. 21 inciso x); this is a future version of Ley 6534 dated {frm_7593}, credited to Ley 7593. Art. 20 '
        f'inciso b) ("SECRETARÍA DE DEFENSA DEL CONSUMIDOR Y EL USUARIO") is removed with the thirteen numbered '
        f'items printed under it; the closing paragraph of art. 20 ("En cuanto sea pertinente, ambas autoridades …") '
        f'belongs to the article, not to the inciso, and stays. The remaining incisos keep their printed letters.',
        'Ley 7593/2025 art. 58 makes every reference in Ley 6534 to the Secretaría de Defensa del Consumidor y el '
        'Usuario read as one to the new Agencia Nacional de Protección de Datos Personales, without changing its '
        'words; it is not entered as a change of text.',
        'Datos personales: BACN wraps many incisos of both laws in nested HTML lists whose outer items are styled '
        '"list-style-type:none"; datos/pages.py numbers the innermost lists first, with the marker rules of parse.py '
        '(start=, value=, list-style-type), so each item shows the marker a browser draws ("a.", "i.", "1."). On '
        'every page parse.py reads (none has nested lists) it gives the same lines as parse.py.',
        'Datos personales, units: art-NNN. Ley 6534 articles are headed "# Artículo N.- EPIGRAPH" (the capital-letter '
        'sentence that opens the article; art. 22 and art. 31 have none). Ley 7593 prints its epigraph on a line of '
        'its own, headed "# Artículo N. Epigraph" without the final full stop; art. 61 ("Comuníquese …") has none. '
        'Title and chapter headings are kept verbatim in indice.md, and the closing formula in sancion.md.',
    ]


def write_part(dest: Path, part: dict) -> None:
    for a in part['acts']:
        prev = a['versions'][0]['units']
        for v in a['versions'][1:]:
            cur = v.pop('units')
            ch = {k: u for k, u in cur.items() if prev.get(k) != u}
            ch.update({k: None for k in prev if k not in cur})
            v['changes'] = dict(sorted(ch.items()))
            prev = cur
    out = json.dumps(part, ensure_ascii=False, indent=1) + '\n'
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_name(dest.name + '.tmp')
    tmp.write_text(out, encoding='utf-8', newline='\n')
    tmp.replace(dest)
    print(*(f'{a["slug"]} {len(a["versions"])} versions' for a in part['acts']), f'{len(part["laws"])} laws ->', dest)


def main():
    """Two parts, one per act: 60-datos-crediticios.json (Ley 6534, with its future version credited to Ley 7593)
    and 62-proteccion-datos-personales.json (Ley 7593). --out DIR writes them to DIR instead of ../corpus.d."""
    if '--fetch' in sys.argv:
        from fetch import fetch
        for u in URLS:
            fetch(u)
        return
    a6534, a7593 = ley_6534(), ley_7593()
    frm = a7593['versions'][0]['from']
    mism = [m for m in MISMATCHES if m.split('/')[0] in (SLUG_6534, SLUG_7593)]
    joins = list(parse.JOINS)
    assert not mism and not joins, (mism, joins)
    d = decisions(frm)
    ai = ('Claude Opus 5.5 (claude-opus-5-5) in Claude Code wrote datos/datos.py and datos/pages.py, ran the BACN '
          'searches, screened the hits and read Ley 7593/2025 to write the repeal table (art. 59) and the notes. No '
          'model wrote or changed legal text: every provision is extracted by code from BACN pages.')
    outdir = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else ROOT / 'corpus.d'
    write_part(outdir / '60-datos-crediticios.json', {
        'laws': {k: LAWS[k] for k in ('ley-6534-2020', 'ley-7593-2025')},
        'acts': [a6534],
        'decisions': [d[0], d[1], d[3], d[4], d[5], d[6], 'Ley 6534/2020: no line joins were needed.'],
        'ai_use': ['Ley 6534/2020 part: ' + ai]})
    write_part(outdir / '62-proteccion-datos-personales.json', {
        'laws': {'ley-7593-2025': LAWS['ley-7593-2025']},
        'acts': [a7593],
        'decisions': [d[0], d[2], d[5], d[6], 'Ley 7593/2025: no line joins were needed.'],
        'ai_use': ['Ley 7593/2025 part: ' + ai]})


if __name__ == '__main__':
    main()
