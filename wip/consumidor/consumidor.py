"""Ley 1334/1998 de Defensa del Consumidor y del Usuario: writes corpus.d/61-consumidor.json (gitlaw_common/SCHEMA.md).

    python -X utf8 consumidor/consumidor.py --fetch     fetch (or reuse) every page in consumidor/sources.json
    python -X utf8 consumidor/consumidor.py             read the cache only, write corpus.d/61-consumidor.json
    python -X utf8 consumidor/consumidor.py --out PATH  write a test part elsewhere

The law as enacted (BACN page), then its amending laws replayed in order of entry into force, each from its own BACN
page. Reuses the BACN helpers and the Replay engine of ../parse.py and the list reader of ../datos/pages.py (imported,
not copied). Deterministic: the same cache gives the same bytes. No network unless --fetch.
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
from parse import (GEN_ART, LAWS, MISMATCHES, Replay, bacn_law, enacted_code, join_broken, law, page_meta,  # noqa: E402
                   plain_unit, quoted, segment_lines, sha)

URLS = json.loads((HERE / 'sources.json').read_text(encoding='utf-8'))['urls']
parse.AMEND_URLS.extend(u for u in URLS if u not in parse.AMEND_URLS)
parse.page_lines = pages.page_lines   # same lines as parse.py on pages without nested lists
CODE_URL = next(u for u in URLS if '/leyes-paraguayas/897/' in u)
SLUG = 'ley-defensa-consumidor'
make = plain_unit('Artículo')


def enacted() -> dict:
    return enacted_code(CODE_URL, GEN_ART, ('Descripción', 'LEY N° 1.334', 'DE DEFENSA DEL CONSUMIDOR Y DEL USUARIO',
                                            'EL CONGRESO DE LA NACION PARAGUAYA SANCIONA CON FUERZA DE', 'LEY'),
                        'Aprobado el Proyecto de Ley por la Honorable', 54, make, SLUG)


def renumbered(u: dict, n: int) -> dict:
    """An article moved to number n (Ley 2340/2003 art. 3): same words, new heading."""
    head, _, rest = u['text'].partition('\n')
    assert re.fullmatch(r'# Artículo \d+', head), head
    return dict(u, label=f'Art. {n}', text=f'# Artículo {n}\n{rest}')


def ley_2340(rp: Replay):
    """New Capítulo XV (telecommunications, arts. 53-57); the old Capítulo XV (arts. 53-54) becomes XVI (58-59)."""
    key = 'ley-2340-2003'
    url, L, frm = bacn_law(key, '5040', 'Ley N° 2340/2003')
    seg = segment_lines(L, r'^Artículo 1º\.- Amplíase la Ley N° 1334')
    assert seg[0] == '"CAPITULO XV' and seg[1] == 'DE LOS SERVICIOS DE TELECOMUNICACIONES', seg[:2]
    body = list(seg[2:])
    assert body[-1].endswith('."'), body[-1][-20:]
    body[-1] = body[-1][:-1]           # the chapter's closing quotation mark (the opening one is on "CAPITULO XV")
    arts: list[tuple[int, list[str]]] = []
    for ln in body:
        m = re.match(r'^Art\. (\d+)\.-\s*(.*)$', ln)
        if m:
            arts.append((int(m.group(1)), [m.group(2)]))
        else:
            arts[-1][1].append(ln)
    assert [n for n, _ in arts] == [53, 54, 55, 56, 57], arts
    renum = {53: 58, 54: 59}
    for old, new in renum.items():
        rp.op(frm, key, url, 'add', f'art-{new:03d}', renumbered(rp.units[f'art-{old:03d}'], new))
    for n, paras in arts:
        rp.op(frm, key, url, 'set' if n in renum else 'add', f'art-{n:03d}',
              make(n, paras[0], join_broken(paras[1:], f'{key} art. {n}')))

    def index(u):
        t = u['text']
        old = 'art-053: CAPITULO XV - DISPOSICIONES FINALES\n'
        assert t.endswith(old), t[-120:]
        return dict(u, text=t[:-len(old)] + 'art-053: CAPITULO XV - DE LOS SERVICIOS DE TELECOMUNICACIONES\n'
                    'art-058: CAPITULO XVI - DISPOSICIONES FINALES\n')
    rp.op(frm, key, url, 'fn', 'indice', index,
          note='Ley 2340/2003 art. 1 inserts a new Capítulo XV (arts. 53-57, telecommunication services) and art. 3 '
               'renumbers the chapter and articles that follow: the former arts. 53 and 54 (Capítulo XV, '
               'Disposiciones finales) are arts. 58 and 59 of Capítulo XVI, with unchanged words.')
    i = L.index(next(x for x in L if x.startswith('Artículo 2°.-')))
    assert L[i] == ('Artículo 2°.- Los Artículos 54 "De la Facturación Transparente" y 55 "De la Identificación del '
                    'Comprador", referidos en el artículo precedente, serán aplicables a partir del sexto mes de la '
                    'entrada en vigencia de la presente Ley.'), L[i]


def ley_4974(rp: Replay):
    key = 'ley-4974-2013'
    url, L, frm = bacn_law(key, '4772', 'Ley N° 4974/2013')
    assert ('Artículo 22.- Derogaciones. Deróganse los Artículos N°s 40, 41 y 42 de la Ley N° 1334/98 "DE DEFENSA DEL '
            'CONSUMIDOR Y DEL USUARIO", en lo atinente al Ministerio de Industria y Comercio y toda norma contraria a '
            'esta Ley.') in L
    LAWS[key]['note'] = ('Ley 4974/2013 creates the Secretaría de Defensa del Consumidor y el Usuario (SEDECO) and, by '
                         'its art. 22, repeals arts. 40, 41 and 42 of Ley 1334/1998 only "en lo atinente al Ministerio '
                         'de Industria y Comercio"; the repeal names no words to strike, so the text is unchanged.')
    for n in (40, 41, 42):
        rp.op(frm, key, url, 'touch', f'art-{n:03d}')


def ley_5427(rp: Replay):
    key = 'ley-5427-2015'
    url, L, frm = bacn_law(key, '4415', 'Ley N° 5427/2015')
    b = quoted(L, r'^Artículo 1\.° Modifícase el artículo 28', make, key)
    assert [n for n, _ in b] == [28], b
    rp.op(frm, key, url, 'set', 'art-028', b[0][1])


def ley_6366(rp: Replay):
    key = 'ley-6366-2019'
    url, L, frm = bacn_law(key, '9529', 'Ley N° 6366/2019')
    b = quoted(L, r'^Artículo 1°\.- Modifícanse los Artículos 4o, 6o, 10, 15 y 29', make, key)
    assert [n for n, _ in b] == [4, 6, 10, 15, 29], [n for n, _ in b]
    for n, u in b:
        rp.op(frm, key, url, 'set', f'art-{n:03d}', u)


def ley_6624(rp: Replay):
    """Art. 30 rewritten; the new text opens 'Articulo 30.' without an opening quotation mark."""
    key = 'ley-6624-2020'
    url, L, frm = bacn_law(key, '9409', 'Ley N° 6624/2020')
    i = L.index(next(x for x in L if x.startswith('Artículo 1.° Modifícase el artículo 30 de la Ley N° 1334/1998')))
    j = L.index(next(x for x in L if x.startswith('Artículo 2.° ')))
    seg = L[i + 1:j]                   # parse.segments would take "Articulo 30." for an article of the amending law
    assert seg[0].startswith('Articulo 30. ') and seg[-1].endswith('."'), (seg[0][:40], seg[-1][-10:])
    paras = [seg[0][len('Articulo 30. '):], *seg[1:-1], seg[-1][:-2] + '.']
    assert ('Artículo 2.° La presente ley se aplicará desde el día siguiente de su publicación en los registros '
            'oficiales a todos los casos de obligaciones a plazo, sin exclusión alguna.') in L
    rp.op(frm, key, url, 'set', 'art-030', make(30, paras[0], join_broken(paras[1:], f'{key} art. 30')))


def ley_1334() -> dict:
    base = enacted()
    m = page_meta(CODE_URL)
    assert m == {'promulgated': '1998-10-27', 'published': '1998-10-30'}, m
    assert base['art-053']['text'].startswith('# Artículo 53\nLa presente ley entrará en vigencia a los ciento ochenta '
                                              'días de su promulgación.')
    frm = (dt.date.fromisoformat(m['promulgated']) + dt.timedelta(days=180)).isoformat()
    law('ley-1334-1998', label='Ley N° 1334/1998', title='De Defensa del Consumidor y del Usuario', kind='law',
        enacted=m['promulgated'], published=m['published'], url=CODE_URL)
    first = {'from': frm, 'source_url': CODE_URL, 'sha256': sha(CODE_URL), 'units': base, 'credits': {},
             'note': 'The law as enacted, from its BACN page; in force 180 days after its promulgation on 27 October '
                     '1998 (art. 53).'}
    rp = Replay(SLUG, base, first)
    for f in (ley_2340, ley_4974, ley_5427, ley_6366, ley_6624):
        f(rp)
    versions = rp.build()
    return {'slug': SLUG, 'short': 'LDC', 'title': 'Ley N° 1334/1998 de Defensa del Consumidor y del Usuario',
            'url': CODE_URL, 'first_law': 'ley-1334-1998', 'earlier_laws': [], 'versions': versions}


DECISIONS = [
    'Ley 1334/1998 de Defensa del Consumidor y del Usuario: BACN publishes it only as enacted (promulgated 27 October '
    '1998); it is in force from 1999-04-25, 180 days after promulgation (art. 53), counted as for the Código '
    'Aduanero. Later versions replay the amending laws, each from its own BACN page. They were found with the BACN '
    'search ("1334", "1334/98", "1334/1998", "1.334", "defensa del consumidor", "consumidor y del usuario"), every hit '
    'screened for a modifying formula that names the law: Leyes 2340/2003, 4974/2013, 5427/2015, 6366/2019 and '
    '6624/2020. There is no official consolidated text to check the current text against.',
    'Ley 1334/1998, Ley 2340/2003: art. 1 "amplía" the law "desde el Capítulo XV" with a new Capítulo XV (arts. 53-57, '
    'telecommunication services) and art. 3 renumbers "consecuentemente" the chapters and articles that follow. The '
    'former Capítulo XV (art. 53 vigencia, art. 54 comuníquese) therefore becomes Capítulo XVI, arts. 58 and 59, '
    'with the same words; indice.md is updated to match. Art. 2 makes arts. 54 and 55 applicable only from the sixth '
    'month after Ley 2340 took effect; their text is in force from 2004-01-13 and no typed applicability is '
    'recorded. The quoted chapter is printed with one opening and one closing quotation mark; both are removed.',
    'Ley 1334/1998, Ley 4974/2013 art. 22 repeals arts. 40, 41 and 42 "en lo atinente al Ministerio de Industria y '
    'Comercio" (the authority the articles name): a partial repeal that strikes no identifiable words. It is a '
    'commit with a note and no word change on 2013-08-29, credited to the three articles; their wording is kept.',
    'Ley 1334/1998, Ley 6624/2020 prints the new art. 30 as "Articulo 30. …" without an opening quotation mark and '
    'ends it with a closing one; the prefix and the mark are removed. Its art. 2 ("se aplicará desde el día '
    'siguiente de su publicación") agrees with the default rule: in force 2020-11-05.',
    'Ley 1334/1998 units: art-NNN headed "# Artículo N" (the law prints no epigraphs; the articles added by Ley '
    '2340/2003 open with an epigraph sentence, kept as text). Chapter headings are in indice.md, the closing formula '
    'in sancion.md.',
]


def main():
    if '--fetch' in sys.argv:
        from fetch import fetch
        for u in URLS:
            fetch(u)
        return
    act = ley_1334()
    mism = [m for m in MISMATCHES if m.startswith(SLUG + '/')]
    joins = list(parse.JOINS)
    part = {
        'laws': dict(sorted(LAWS.items())),
        'acts': [act],
        'decisions': DECISIONS + parse.DECISIONS + [
            f'Ley 1334/1998: {len(joins)} line joins (a paragraph broken by a stray <br>): ' + '; '.join(joins) + '.'
            if joins else 'Ley 1334/1998: no line joins were needed.'] + [
            'Ley 1334/1998, restated text: ' + m for m in mism],
        'ai_use': [
            'Defensa del consumidor part: Claude Opus 5.5 (claude-opus-5-5) in Claude Code wrote '
            'consumidor/consumidor.py, ran the BACN searches, screened the hits and read the amending laws to write '
            'the replay table (which article each law rewrites, adds, renumbers or concerns, and when). No model '
            'wrote or changed legal text: every provision is extracted by code from BACN pages.',
        ],
    }
    prev = act['versions'][0]['units']
    for v in act['versions'][1:]:
        cur = v.pop('units')
        ch = {k: u for k, u in cur.items() if prev.get(k) != u}
        ch.update({k: None for k in prev if k not in cur})
        v['changes'] = dict(sorted(ch.items()))
        prev = cur
    out = json.dumps(part, ensure_ascii=False, indent=1) + '\n'
    dest = (Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv
            else ROOT / 'corpus.d' / '61-consumidor.json')
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_name(dest.name + '.tmp')
    tmp.write_text(out, encoding='utf-8', newline='\n')
    tmp.replace(dest)
    print(SLUG, len(act['versions']), 'versions;', len(LAWS), 'laws;', len(mism), 'restated;', len(joins), 'joins ->',
          dest)


if __name__ == '__main__':
    main()
