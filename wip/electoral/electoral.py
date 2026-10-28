"""Código Electoral (Ley 834/1996) for Paraguay: writes corpus.d/50-electoral.json (scripts/gitlaw_common/SCHEMA.md).

    python -X utf8 electoral/electoral.py --fetch     fetch (or reuse) every page in electoral/sources.json
    python -X utf8 electoral/electoral.py             read the cache only, write corpus.d/50-electoral.json
    python -X utf8 electoral/electoral.py --out PATH  write a test part elsewhere

Reuses the Replay engine and the BACN helpers of ../parse.py (imported, not copied). Deterministic: the same cache
gives the same bytes. No network unless --fetch.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import parse  # noqa: E402
from parse import (BACN, LAWS, LOWER, MISMATCHES, Replay, bacn_law, join_broken, law, page_meta,  # noqa: E402
                   segment_lines, segments, sha, strip_quote, unit)

URLS = json.loads((HERE / 'sources.json').read_text(encoding='utf-8'))['urls']
parse.AMEND_URLS.extend(u for u in URLS if u not in parse.AMEND_URLS)
CODE_URL = next(u for u in URLS if '/leyes-paraguayas/2346/' in u)
SLUG = 'codigo-electoral'


# ---------------------------------------------------------------- page lines

def _unnumbered(m: re.Match) -> str:
    """An <ol> whose items are all styled list-style-type:none shows no numbers when rendered (Ley 6167/2018 wraps
    its own "a)", "b)" items in one); turn it into plain blocks so ../parse.py does not write numbers out."""
    lis = re.findall(r'(?i)<li\b([^>]*)>', m.group(1))
    none = ['list-style-type:none' in a.replace(' ', '').lower() for a in lis]
    if lis and all(none):
        return '<div>' + m.group(1) + '</div>'
    assert not any(none), 'an <ol> with some unnumbered items'
    return m.group(0)


def _table_rows(m: re.Match) -> str:
    """A table row becomes one line, its cells separated by a space (the D'Hondt example of art. 258): BACN puts a
    <p> in each cell, which would otherwise make every cell a line of its own."""
    rows = []
    for tr in re.findall(r'(?is)<tr\b[^>]*>(.*?)</tr\s*>', m.group(0)):
        cells = re.findall(r'(?is)<t[dh]\b[^>]*>(.*?)</t[dh]\s*>', tr)
        cells = [re.sub(r'(?i)</?(p|div|br)\b[^>]*/?>', ' ', c) for c in cells]
        rows.append('<p>' + re.sub(r'\s+', ' ', ' '.join(cells)) + '</p>')
    return '\n'.join(rows)


PDF_NOTE = 'VER PDDF'          # BACN's stand-in for the example table of art. 258, given only in its PDF
_KEEP = PDF_NOTE + ' \x00(text)'  # carried through parse.enacted_code as article text, not as a heading


def page_lines(url: str) -> list[str]:
    frag = parse.bacn.body(parse.bacn.decode(parse.raw(url)))
    frag = re.sub(r'(?is)<ol\b[^>]*>(.*?)</ol\s*>', _unnumbered, frag)
    frag = re.sub(r'(?is)<table\b.*?</table\s*>', _table_rows, frag)
    L = parse.bacn.lines(frag)
    if url == CODE_URL:
        assert L.count(PDF_NOTE) == 1
        L = [_KEEP if x == PDF_NOTE else x for x in L]
    return L


parse.page_lines = page_lines     # parse.enacted_code and parse.bacn_law look it up at call time


# ---------------------------------------------------------------- units

QART = re.compile(r'^"Art(?:[ií]culo|\.)?\s*-?\s*(\d+)(?:\s*[°º])?(?:\s+(bis|ter|quater|[a-z])(?=[.\s-]))?'
                  r'\s*(?:\.-|\.|-)?\s*(.*)$')


def key(n: int, suffix: str = '') -> str:
    return f'art-{n:03d}' + (f'-{suffix}' if suffix else '')


def art_unit(n: int, suffix: str, paras: list[str], note: str = '') -> dict:
    num = f'{n} {suffix}'.strip()
    return unit(f'Art. {num}' + note, 'art', f'Artículo {num}', [p for p in paras if p])


def make_base(n: int, rest: str, paras: list[str]) -> dict:
    assert _KEEP not in paras or n == 258, n
    return art_unit(n, '', [rest.strip(), *[PDF_NOTE if p == _KEEP else p for p in paras]])


def blocks(L: list[str], intro: str, where: str, heads_ok: bool = False) -> tuple[list[tuple[int, str, list[str]]], list[str]]:
    """The quoted articles inside the one article of an amending law whose first line matches `intro`:
    [(number, suffix, paragraphs)] plus the capital-letter heading lines quoted between them."""
    out: list[list] = []
    heads: list[str] = []
    for ln in segment_lines(L, intro):
        m = QART.match(ln)
        if m:
            out.append([int(m.group(1)), m.group(2) or '', [m.group(3)]])
        elif not LOWER.search(ln):
            heads.append(ln.strip('"'))
        else:
            assert out, (where, ln)
            out[-1][2].append(ln)
    res = []
    for n, suf, paras in out:
        paras = strip_quote(['"' + paras[0]] + paras[1:])
        res.append((n, suf, join_broken([p for p in paras if p], f'{where} art. {n}')))
    assert heads_ok or not heads, (where, heads)
    return res, heads


def set_arts(rp: Replay, frm: str, lk: str, url: str, got, expect: list, *, op: str = 'set', keyfn=key, label=''):
    nums = [(n, s) if s else n for n, s, _ in got]
    assert nums == expect, (lk, nums, expect)
    for n, s, paras in got:
        rp.op(frm, lk, url, op, keyfn(n, s), art_unit(n, s, paras, label))


# ---------------------------------------------------------------- the Code

def enacted() -> dict:
    return parse.enacted_code(CODE_URL, parse.GEN_ART, ('Descripción', 'LEY N° 834',
                                                        'QUE ESTABLECE EL CODIGO ELECTORAL PARAGUAYO'),
                              'Aprobada por la Honorable Cámara de Diputados', 348, make_base, SLUG)


def codigo_electoral() -> dict:
    base = enacted()
    m = page_meta(CODE_URL)
    assert m == {'promulgated': '1996-04-17', 'published': None}, m
    frm0 = parse.day_after(m['promulgated'])
    law('ley-834-1996', label='Ley N° 834/1996 (Código Electoral)', kind='law', enacted=m['promulgated'],
        published=None, url=CODE_URL, title='Que establece el Código Electoral Paraguayo')
    assert base['art-348']['text'] == '# Artículo 348\nComuníquese al Poder Ejecutivo.\n', base['art-348']
    first = {'from': frm0, 'source_url': CODE_URL, 'sha256': sha(CODE_URL), 'units': base, 'credits': {},
             'note': 'The Code as enacted, from its BACN page (Ley 834/1996, promulgated 17 April 1996). BACN '
                     'records no publication date and the Code has no vigencia clause, so it is dated the day after '
                     'promulgation.'}
    rp = Replay(SLUG, base, first)

    # Ley 1825/2001: suspends 14 articles only in the municipalities and polling places where electronic voting was
    # used at the municipal elections of 18 November 2001 (art. 2). No words change.
    url, L, frm = bacn_law('ley-1825-2001', '2493', 'Ley N° 1825/2001')
    a2 = next(s for s in segments(L) if s[0].startswith('Artículo 2°.- Suspéndese la vigencia de los Artículos'))[0]
    assert '103, 104, 170, 171, 174, 198 excepto incisos b), d) y e), 200, 203, 211 excepto la última línea' in a2 \
        and '222, 223, 224, 226 y 227 de la Ley N° 834/96' in a2, a2
    s1825 = [103, 104, 170, 171, 174, 198, 200, 203, 211, 222, 223, 224, 226, 227]
    LAWS['ley-1825-2001']['note'] = (
        'Introduces electronic voting for the municipal elections of 18 November 2001 in listed municipalities and '
        'polling places, and suspends arts. 103, 104, 170, 171, 174, 198 (except incisos b, d and e), 200, 203, 211 '
        '(except its last line), 222, 223, 224, 226 and 227 there only (art. 2). The text of the Code does not '
        'change; the law names no end day for the suspension.')
    for n in s1825:
        rp.op(frm, 'ley-1825-2001', url, 'touch', key(n))

    # Ley 1830/2001: art. 32 inc. e, 153, 154, 251, 254, 257, 290; art. 2 adds transitional arts. 348-350.
    url, L, frm1830 = bacn_law('ley-1830-2001', '2494', 'Ley N° 1830/2001')
    got, _ = blocks(L, r'^Artículo 1°\.- Modifícanse el inciso e\) del Artículo 32', 'ley-1830-2001')
    assert [n for n, _, _ in got] == [32, 153, 154, 251, 254, 257, 290]
    (_, _, p32), *rest = got
    assert len(p32) == 1 and p32[0].startswith('inciso e) La duración del mandato'), p32
    new_e = p32[0][len('inciso '):]

    def set_32e(u):
        lines_ = u['text'].split('\n')
        i = [j for j, x in enumerate(lines_) if x.startswith('e) ')]
        assert len(i) == 1 and lines_[i[0]].startswith('e) el tiempo y la forma de la elección'), i
        lines_[i[0]] = new_e
        return {**u, 'text': '\n'.join(lines_)}
    rp.op(frm1830, 'ley-1830-2001', url, 'fn', 'art-032', set_32e)
    set_arts(rp, frm1830, 'ley-1830-2001', url, rest, [153, 154, 251, 254, 257, 290])
    got, _ = blocks(L, r'^Artículo 2°\.- Amplíanse las Disposiciones Finales y Transitorias', 'ley-1830-2001')
    set_arts(rp, frm1830, 'ley-1830-2001', url, got, [348, 349, 350], op='add', keyfn=tkey, label=TLABEL)

    # Ley 1890/2002: 153, 154; art. 2 adds transitional arts. 351-353.
    url, L, frm = bacn_law('ley-1890-2002', '2495', 'Ley N° 1890/2002')
    got, _ = blocks(L, r'^Artículo1°\.- Modifícanse los Artículos 153 y 154', 'ley-1890-2002')
    set_arts(rp, frm, 'ley-1890-2002', url, got, [153, 154])
    got, _ = blocks(L, r'^Artículo 2°\.- Amplíanse las Disposiciones Finales y Transitorias', 'ley-1890-2002')
    set_arts(rp, frm, 'ley-1890-2002', url, got, [351, 352, 353], op='add', keyfn=tkey, label=TLABEL)

    simple = [  # (law key, BACN id, label, intro of the amending article, articles in order)
        ('ley-1975-2002', '2501', 'Ley N° 1975/2002', r'^Artículo1°\.- Modifícanse los Artículos 130, 154 y 155', [130, 154, 155]),
        ('ley-2096-2003', '2496', 'Ley N° 2096/2003', r'^Artículo 1°', [171]),
    ]
    for lk, pid, label, intro, arts in simple:
        url, L, frm = bacn_law(lk, pid, label)
        got, _ = blocks(L, intro, lk)
        set_arts(rp, frm, lk, url, got, arts)

    # Ley 2450/2004 rewrites transitional art. 348 (added by Ley 1830/2001 art. 2).
    url, L, frm = bacn_law('ley-2450-2004', '2497', 'Ley N° 2450/2004')
    got, _ = blocks(L, r'^Artículo 1°\.- Modifícase parcialmente el Artículo 2° de la Ley N° 1830', 'ley-2450-2004')
    set_arts(rp, frm, 'ley-2450-2004', url, got, [348], keyfn=tkey, label=TLABEL)

    for lk, pid, label, intro, arts in [
            ('ley-2582-2005', '2499', 'Ley N° 2582/2005', r'^Artículo 1º', [98]),
            ('ley-2783-2005', '2500', 'Ley N° 2783/2005', r'^Artículo 1°', [130])]:
        url, L, frm = bacn_law(lk, pid, label)
        got, _ = blocks(L, intro, lk)
        set_arts(rp, frm, lk, url, got, arts)

    # Ley 2858/2006 rewrites six articles; its art. 2 repeals Ley 2783/2005 and the Ley 1975/2002 wording of art. 130,
    # which its own art. 1 replaces anyway.
    url2858, L, frm2858 = bacn_law('ley-2858-2006', '1941', 'Ley N° 2858/2006')
    got, _ = blocks(L, r'^Artículo 1º\.- Modifícanse los Artículos 116, 117, 130, 140, 144 y 147', 'ley-2858-2006')
    t3273 = [116, 117, 130, 140, 144, 147]
    set_arts(rp, frm2858, 'ley-2858-2006', url2858, got, t3273)
    assert any(s[0].startswith('Artículo 2°.- Deróganse la Ley N° 2.783/05 y la modificación del Artículo 130') for s in segments(L))

    # Ley 3166/2007; it also quotes two chapter headings: Libro III, Título V, Capítulo III is renamed.
    url, L, frm = bacn_law('ley-3166-2007', '290', 'Ley N° 3166/2007')
    got, heads = blocks(L, r'^Artículo 1°\.- Modifícanse los Artículos 106, 170, 246, 247, 248 y 258', 'ley-3166-2007', heads_ok=True)
    set_arts(rp, frm, 'ley-3166-2007', url, got, [106, 170, 246, 247, 248, 258])
    assert heads == ['CAPITULO III', 'DE LA ELECCION DE SENADORES, DIPUTADOS Y PARLAMENTARIOS DEL MERCOSUR',
                     'CAPITULO VII', 'DE LA DISTRIBUCION DE ESCAÑOS'], heads
    old_iii = 'art-246: CAPITULO III - DE LA ELECCION DE SENADORES Y DIPUTADOS'
    old_vii = 'art-258: CAPITULO VII - DE LA DISTRIBUCION DE ESCAÑOS'

    def rename_iii(u):
        lines_ = u['text'].split('\n')
        assert old_iii in lines_ and old_vii in lines_, 'indice'
        lines_[lines_.index(old_iii)] = 'art-246: CAPITULO III - ' + heads[1]
        return {**u, 'text': '\n'.join(lines_)}
    rp.op(frm, 'ley-3166-2007', url, 'fn', 'indice', rename_iii)

    # Ley 3273/2007: temporary wording of the six articles of Ley 2858/2006, "durante el año 2007" (art. 3); then the
    # 2858 wording applies again ("restableciéndose la vigencia del texto modificado por la presente Ley").
    url, L, frm3273 = bacn_law('ley-3273-2007', '3319', 'Ley N° 3273/2007')
    got, _ = blocks(L, r'^Artículo 1º\.- La presente Ley suspende transitoriamente la vigencia', 'ley-3273-2007')
    set_arts(rp, frm3273, 'ley-3273-2007', url, got, t3273)
    a3 = next(s for s in segments(L) if s[0].startswith('Artículo 3º- Esta Ley tendrá vigencia durante el año 2007'))[0]
    assert 'Cumplidos dichos plazos, la misma quedará sin efecto, restableciéndose la vigencia del texto modificado' in a3
    LAWS['ley-3273-2007']['temporary_until'] = '2007-12-31'
    law('ley-3273-2007-fin', label='Ley N° 3273/2007, fin de vigencia', kind='law',
        enacted=LAWS['ley-3273-2007']['enacted'], published=LAWS['ley-3273-2007']['published'], url=url,
        restores='ley-3273-2007', title='Fin de la vigencia temporal de la Ley N° 3273/2007 (art. 3)',
        note='Ley 3273/2007 art. 3: it applied during 2007 only; from 1 January 2008 the wording of arts. 116, 117, '
             '130, 140, 144 and 147 set by Ley 2858/2006 applies again.')
    for n in t3273:
        rp.op('2008-01-01', 'ley-3273-2007-fin', url, 'restore', key(n), frm3273)

    for lk, pid, label, intro, arts in [
            ('ley-3872-2009', '1502', 'Ley N° 3872/2009', r'^Artículo 1º', [4]),
            ('ley-4260-2011', '2898', 'Ley N° 4260/2011', r'^Artículo 1°', [195])]:
        url, L, frm = bacn_law(lk, pid, label)
        got, _ = blocks(L, intro, lk)
        set_arts(rp, frm, lk, url, got, arts)

    # Ley 4584/2012 (arts. 247, 258, listas desbloqueadas) was to apply from the 2013 general elections (art. 2),
    # moved to 2015 by Ley 4662/2012, and was repealed by Ley 5350/2014 before then: its wording never applied.
    url4584, L, frm4584 = bacn_law('ley-4584-2012', '1267', 'Ley N° 4584/2012')
    got, _ = blocks(L, r'^Artículo 1º\.- Modifícanse los Artículos 247 y 258', 'ley-4584-2012')
    assert [n for n, _, _ in got] == [247, 258]
    assert any(s[0].startswith('Artículo 2º.- La presente Ley se aplicará a partir de las elecciones generales previstas para el año 2013') for s in segments(L))
    LAWS['ley-4584-2012']['note'] = (
        'Rewrites arts. 247 and 258 (unblocked lists), to apply from the 2013 general elections (art. 2). Ley '
        '4662/2012 moved that to the 2015 elections and Ley 5350/2014 repealed it before then, so its wording never '
        'applied and is not entered in the text.')
    url, L, frm = bacn_law('ley-4662-2012', '2733', 'Ley N° 4662/2012')
    got, _ = blocks(L, r'^Articulo 1°\.- Modifícase el Artículo 2° de la Ley N° 4584/12', 'ley-4662-2012')
    assert len(got) == 1 and 'a partir de las elecciones generales previstas para el año 2015' in got[0][2][0], got
    LAWS['ley-4662-2012']['note'] = ('Moves the application of Ley 4584/2012 (arts. 247 and 258) to the 2015 '
                                     'elections; the text in force does not change.')
    url5350, L, frm5350 = bacn_law('ley-5350-2014', '4569', 'Ley N° 5350/2014')
    assert segments(L)[0][0].startswith('Artículo 1°.- Deróganse la Ley Nº 4584/12')
    assert frm5350 < '2015-01-01'
    LAWS['ley-5350-2014']['note'] = ('Repeals Ley 4584/2012 and Ley 4662/2012 before they ever applied; the text '
                                     'of arts. 247 and 258 does not change.')
    for lk, u, f in (('ley-4584-2012', url4584, frm4584), ('ley-4662-2012', url, frm), ('ley-5350-2014', url5350, frm5350)):
        for n in (247, 258):
            rp.op(f, lk, u, 'touch', key(n))

    url, L, frm = bacn_law('ley-4743-2012', '1198', 'Ley N° 4743/2012')
    got, _ = blocks(L, r'^Artículo 3°\.- Modifícanse los artículos 62, 64', 'ley-4743-2012')
    set_arts(rp, frm, 'ley-4743-2012', url, got, [62, 64, 66, 68, 70, 71, 72, 276, 278, 279, 280, 281, 282, 330, 336])

    for lk, pid, label, intro, arts in [
            ('ley-4802-2012', '3164', 'Ley N° 4802/2012', r'^Artículo 1°', [135, 208]),
            ('ley-5286-2014', '3014', 'Ley N° 5286/2014', r'^Artículo 1\.°', [153]),
            ('ley-5376-2014', '3067', 'Ley N° 5376/2014', r'^Artículo 1\.°', [257]),
            ('ley-6019-2018', '9925', 'Ley N° 6019/2018', r'^Artículo 1°', [122]),
            ('ley-6167-2018', '8683', 'Ley N° 6167/2018', r'^Artículo 1\.°', [64, 66, 68, 157, 278, 280, 281, 282]),
            ('ley-6318-2019', '8850', 'Ley N° 6318/2019', r'^Artículo 1°', [241, 247, 249, 250, 258])]:
        url, L, frm = bacn_law(lk, pid, label)
        got, _ = blocks(L, intro, lk)
        set_arts(rp, frm, lk, url, got, arts)

    # Ley 6501/2020 art. 2 "modifies" 64, 66, 68, 278 and 281 but gives arts. 278 a and 278 b for 278.
    url, L, frm = bacn_law('ley-6501-2020', '9161', 'Ley N° 6501/2020')
    got, _ = blocks(L, r'^Artículo 2\.° Modificanse los artículos 64, 66, 68, 278 y 281', 'ley-6501-2020')
    assert [(n, s) for n, s, _ in got] == [(64, ''), (66, ''), (68, ''), (278, 'a'), (278, 'b'), (281, '')], got
    set_arts(rp, frm, 'ley-6501-2020', url, [g for g in got if not g[1]], [64, 66, 68, 281])
    rp.op(frm, 'ley-6501-2020', url, 'del', 'art-278')
    set_arts(rp, frm, 'ley-6501-2020', url, [g for g in got if g[1]], [(278, 'a'), (278, 'b')], op='add')

    # Ley 6547/2020: suspends art. 154 "temporal y parcialmente" for the 2020 municipal elections (art. 1); it
    # lapses once its periods have run and those elections are held (art. 4), on a day its text does not give.
    url, L, frm = bacn_law('ley-6547-2020', '9256', 'Ley N° 6547/2020')
    seg = segments(L)
    assert seg[0][0].startswith('Artículo 1°.- Suspéndase temporal y parcialmente el Artículo 154')
    assert seg[3][0].startswith('Artículo 4°.- Transcurrido los plazos establecidos y realizada las elecciones municipales, esta Ley quedará sin efecto')
    LAWS['ley-6547-2020']['note'] = (
        'Suspends art. 154 in part for the municipal elections due in 2020 (COVID-19), postpones them by up to one '
        'year and extends municipal mandates (arts. 1-3). It lapses once those periods have run and the elections are '
        'held (art. 4), on a day its text does not give, so no lapse is recorded. The text of art. 154 does not '
        'change.')
    rp.op(frm, 'ley-6547-2020', url, 'touch', 'art-154')

    url, L, frm = bacn_law('ley-6652-2020', '9447', 'Ley N° 6652/2020')
    got, _ = blocks(L, r'^Artículo 1º', 'ley-6652-2020')
    set_arts(rp, frm, 'ley-6652-2020', url, got, [266, 273])

    url, L, frm = bacn_law('ley-6918-2022', '10452', 'Ley N° 6918/2022')
    got, _ = blocks(L, r'^Artículo 1°', 'ley-6918-2022')
    set_arts(rp, frm, 'ley-6918-2022', url, got, [170, 246, 247, 248, 258])

    url, L, frm = bacn_law('ley-6922-2022', '10506', 'Ley N° 6922/2022')
    got, _ = blocks(L, r'^Artículo 1°', 'ley-6922-2022')
    set_arts(rp, frm, 'ley-6922-2022', url, got, [266])

    # Ley 6951/2022 art. 13 rewrites art. 2; art. 14: "entrará a regir inmediatamente luego de su promulgación y
    # publicación" (both on 17 August 2022).
    m6951 = page_meta(next(u for u in URLS if '/10569/' in u))
    assert m6951 == {'promulgated': '2022-08-17', 'published': '2022-08-17'}, m6951
    url, L, frm = bacn_law('ley-6951-2022', '10569', 'Ley N° 6951/2022', in_force='2022-08-17',
                           why='art. 14: "entrará a regir inmediatamente luego de su promulgación y publicación", '
                               'both dated 17 August 2022 on BACN')
    i = L.index('Artículo 13.- Adecuación del Código Electoral.')
    assert L[i + 1].startswith('Modifíquese el Artículo 2° de la Ley Nº 834/1996') and L[i + 3] == 'Artículo 14.- Vigencia.'
    assert L[i + 4] == 'La presente Ley entrará a regir inmediatamente luego de su promulgación y publicación.'
    m = QART.match(L[i + 2])
    assert m and int(m.group(1)) == 2, L[i + 2]
    rp.op(frm, 'ley-6951-2022', url, 'set', 'art-002', art_unit(2, '', strip_quote(['"' + m.group(3)])))

    url, L, frm = bacn_law('ley-6971-2022', '10623', 'Ley N° 6971/2022')
    got, _ = blocks(L, r'^Artículo 1°', 'ley-6971-2022')
    set_arts(rp, frm, 'ley-6971-2022', url, got, [91, 94, 207, 217])

    # Ley 6983/2022: 266 (art. 1), new 266 bis-quater (art. 2), 271 (art. 3); its arts. 4-5 amend Ley 3966/2010.
    url, L, frm = bacn_law('ley-6983-2022', '10742', 'Ley N° 6983/2022')
    got, _ = blocks(L, r'^Artículo 1°', 'ley-6983-2022')
    set_arts(rp, frm, 'ley-6983-2022', url, got, [266])
    got, _ = blocks(L, r'^Artículo 2°', 'ley-6983-2022')
    set_arts(rp, frm, 'ley-6983-2022', url, got, [(266, 'bis'), (266, 'ter'), (266, 'quater')], op='add')
    got, _ = blocks(L, r'^Artículo 3º', 'ley-6983-2022')
    set_arts(rp, frm, 'ley-6983-2022', url, got, [271])

    # Ley 7044/2022: suspends paragraph five of art. 154 so the Guairá governorship election can be held on
    # 15 January 2023 (art. 1), "vigencia exclusiva" for that vacancy (art. 2).
    url, L, frm = bacn_law('ley-7044-2022', '11228', 'Ley N° 7044/2022')
    seg = segments(L)
    assert seg[0][0].startswith('Artículo 1°.- Suspéndase, temporalmente el parágrafo quinto del Artículo 154')
    assert seg[1][0].startswith('Artículo 2°.- La presente Ley tendra vigencia exclusiva para cubrir la vacancia en la Gobernación del Departamento Guairá')
    LAWS['ley-7044-2022']['note'] = (
        'Suspends paragraph five of art. 154 (removal of governors and intendentes) so that the election to fill the '
        'Guairá governorship is held on 15 January 2023 (art. 1); it applies only to that vacancy (art. 2) and gives '
        'no end day, so no lapse is recorded. The text of art. 154 does not change.')
    rp.op(frm, 'ley-7044-2022', url, 'touch', 'art-154')

    url, L, frm = bacn_law('ley-7135-2023', '11862', 'Ley N° 7135/2023')
    got, _ = blocks(L, r'^Artículo 1\.º', 'ley-7135-2023')
    set_arts(rp, frm, 'ley-7135-2023', url, got, [290])

    # Ley 7176/2023: suspends art. 149 to purge the San Alfredo district register.
    url, L, frm = bacn_law('ley-7176-2023', '11989', 'Ley N° 7176/2023')
    assert segments(L)[0][0].startswith('Artículo 1°.- Suspéndase temporalmente la vigencia del Artículo 149')
    LAWS['ley-7176-2023']['note'] = (
        'Suspends art. 149 (when the electoral register may be purged) so that the register of the San Alfredo '
        'district (Concepción) can be purged ahead of the party and municipal elections of 8 July and 10 September '
        '2023 (art. 1). It was promulgated after both dates and names no end day, so no lapse is recorded. The text '
        'of art. 149 does not change.')
    rp.op(frm, 'ley-7176-2023', url, 'touch', 'art-149')

    url, L, frm = bacn_law('ley-7491-2025', '12759', 'Ley N° 7491/2025')
    got, _ = blocks(L, r'^Artículo 1\.º', 'ley-7491-2025')
    set_arts(rp, frm, 'ley-7491-2025', url, got, [130])

    # Ley 7524/2025 rewrites "art. 278" (as modified by Ley 6501/2020, which had split it into 278 a and 278 b).
    url, L, frm = bacn_law('ley-7524-2025', '12823', 'Ley N° 7524/2025')
    got, _ = blocks(L, r'^Artículo 1°', 'ley-7524-2025')
    set_arts(rp, frm, 'ley-7524-2025', url, [g for g in got if g[0] != 278], [64, 66])
    (g278,) = [g for g in got if g[0] == 278]
    rp.op(frm, 'ley-7524-2025', url, 'del', 'art-278-a')
    rp.op(frm, 'ley-7524-2025', url, 'del', 'art-278-b')
    set_arts(rp, frm, 'ley-7524-2025', url, [g278], [278], op='add')

    versions = rp.build()
    last = versions[-1]['units']
    by_day = {v['from']: v for v in versions}
    # Ley 3273/2007 art. 3: the Ley 2858/2006 wording is back from 2008.
    v2858 = by_day[frm2858]['units']
    for n in t3273:
        assert by_day['2008-01-01']['units'][key(n)] == v2858[key(n)], n
    assert 'art-278' in last and 'art-278-a' not in last
    return {'slug': SLUG, 'short': 'CE', 'title': 'Código Electoral Paraguayo (Ley N° 834/1996)', 'url': CODE_URL,
            'first_law': 'ley-834-1996', 'earlier_laws': [], 'versions': versions}


TLABEL = ' transitorio'


def tkey(n: int, s: str = '') -> str:
    assert not s
    return f'art-{n:03d}-transitorio'


def decisions() -> list[str]:
    return [
        'Código Electoral (Ley 834/1996): BACN publishes it only as enacted (348 articles, no "Modificado por" notes) '
        'and no official consolidated text exists online. The first version is the enacted text, dated 1996-04-18: '
        'BACN records promulgation on 17 April 1996 and no publication date, and the Code has no vigencia clause, so '
        'the day after promulgation is used (Código Civil art. 1). Every later version is rebuilt by applying, in '
        'order of entry into force, the text of each amending law as printed on its BACN page.',
        'Código Electoral: the amending laws were found with the BACN full-text search (queries "834/96", '
        '"834/1996", "codigo electoral", "código electoral", "electoral paraguayo", "834") and the BACN sitemap '
        '(law pages whose address names "electoral", "834", "sufragio", "registro cívico" or "partidos políticos"), '
        'and the text of every hit was screened for articles that modify, add to, repeal or suspend the Code. Because '
        'there is no official consolidation, the current text cannot be checked against one; an amending law the '
        'search does not find would be missing here.',
        'Código Electoral: units are art-NNN headed "# Artículo N" (the Code has no epigraphs); added articles are '
        'art-266-bis, art-266-ter, art-266-quater, art-278-a and art-278-b. Book/title/chapter headings are kept '
        'verbatim in codigo-electoral/indice.md; the closing formula is codigo-electoral/sancion.md.',
        'Código Electoral, transitional articles: Ley 1830/2001 art. 2 and Ley 1890/2002 art. 2 "amplían las '
        'Disposiciones Finales y Transitorias" with articles numbered 348 to 353, but the enacted art. 348 is '
        '"Comuníquese al Poder Ejecutivo", so two different articles carry the number 348. The enacted art. 348 stays '
        'art-348; the six added articles are keyed art-348-transitorio ... art-353-transitorio (one scheme for the '
        'whole block, though only 348 clashes), labelled "Art. N transitorio" and headed "# Artículo N" as the laws '
        'print them. Ley 2450/2004 rewrites the added art. 348 ("en lo referente al Artículo 348" of Ley 1830 art. '
        '2), so it changes art-348-transitorio.',
        'Código Electoral, Ley 1830/2001 art. 1 rewrites only "inciso e) del Artículo 32": that one line of art. 32 is '
        'replaced and the other incisos stay.',
        'Código Electoral, Ley 1825/2001 (electronic voting at the municipal elections of 18 November 2001): its art. '
        '2 suspends 14 articles only in the listed municipalities and polling places; it changes no words, so it is '
        'a commit with a note and no word change, credited to those 14 articles. Leyes 1890/2002 and 1975/2002 call '
        'the Code "modificado por las Leyes 1825 y 1830/01"; this suspension is the only change Ley 1825 makes. Ley '
        '3017/2006 (electronic ballot boxes, citing the added art. 351) repeals Ley 1825 "en cuanto se contrapongan" '
        'and changes no Code text.',
        'Código Electoral, Ley 1975/2002: the BACN "Antecedente" (the bill) names arts. 130, 154, 155 and 352, but the '
        'enacted text modifies only 130, 154 and 155, so only those are applied. Ley 2858/2006 art. 2 repeals Ley '
        '2783/2005 and the Ley 1975/2002 wording of art. 130; its art. 1 rewrites art. 130 the same day, so that '
        'wording replaces it.',
        'Código Electoral, Ley 3166/2007 quotes two chapter headings with its articles: Libro III, Título V, Capítulo III becomes '
        '"DE LA ELECCION DE SENADORES, DIPUTADOS Y PARLAMENTARIOS DEL MERCOSUR" (applied to indice.md, credited to '
        'it); the Capítulo VII heading it quotes is unchanged. Ley 6918/2022 removes the Mercosur members from arts. '
        '246-248 and 258 but quotes no heading, so the Capítulo III heading keeps the Mercosur wording.',
        'Código Electoral, Ley 3273/2007 (temporary): it replaces arts. 116, 117, 130, 140, 144 and 147 "durante el '
        'año 2007" (art. 3), so temporary_until is 2007-12-31; "cumplidos dichos plazos ... restableciéndose la '
        'vigencia del texto modificado", so on 2008-01-01 a version credited to a separate entry ("Ley N° 3273/2007, '
        'fin de vigencia", key ley-3273-2007-fin, restores ley-3273-2007) brings back the Ley 2858/2006 wording, which '
        'electoral.py checks.',
        'Código Electoral, Ley 4584/2012 (arts. 247 and 258, unblocked lists): it was to apply from the 2013 general '
        'elections (art. 2); Ley 4662/2012 moved that to the 2015 elections; Ley 5350/2014 repealed both on '
        '2014-11-11, before any election under it. Its wording therefore never applied and is not entered in the '
        'text: Leyes 4584/2012, 4662/2012 and 5350/2014 are commits with a note and no word change, credited to arts. '
        '247 and 258. Ley 6318/2019 later enacted unblocked lists in its own wording.',
        'Código Electoral, Leyes 6547/2020, 7044/2022 and 7176/2023 suspend the application of art. 154 (in part, for '
        'the 2020 municipal elections), of paragraph five of art. 154 (for the Guairá governorship election of 15 '
        'January 2023) and of art. 149 (for the San Alfredo district register) without changing their words. Each is '
        'a commit with a note and no word change on the day it took effect. None of them gives an end day in its '
        'text (6547 lapses once its periods have run and the elections are held; 7044 serves one vacancy; 7176 names '
        'elections that had already been held when it was promulgated), so temporary_until is left empty and no '
        'lapse commit is made rather than guessing a day.',
        'Código Electoral, Ley 6501/2020 art. 2 says it modifies art. 278 but gives "Art. 278 a" and "Artículo 278 b": '
        'art. 278 is removed and art-278-a and art-278-b are added (as for the Código Penal). Ley 7524/2025 then '
        'rewrites "art. 278 ... modificado por las Leyes 4743/2012, 6167/2018 y 6501/2020" as one article whose text '
        'covers both lettered articles, so it removes art-278-a and art-278-b and restores a single art-278.',
        'Código Electoral, Ley 6318/2019 (unblocked lists) applies "a partir de las elecciones inmediatamente '
        'posteriores a su entrada en vigencia" (art. 4); its wording is in force from the default day, and no typed '
        'applicability is recorded.',
        'Código Electoral, Ley 6951/2022 art. 13 rewrites art. 2; its art. 14 puts it in force "inmediatamente luego de '
        'su promulgación y publicación", both on 17 August 2022, so it is dated 2022-08-17 rather than the day after.',
        'Código Electoral, not applied: Leyes 3212/2007 and 7528/2025 "amplían las disposiciones del Código Electoral" '
        'with articles of their own (concertaciones) that are not numbered into the Code; Leyes 859/1996, 1065/1997 '
        'and 1576/2000 (expired identity cards for registration and voting) and Ley 1620/2000 (registration period '
        'extended to 28 February 2001) set one-off rules "de conformidad con" arts. 98 and 130 without modifying or '
        'suspending them; Ley 4743/2012 arts. 4-12 and Ley 6501/2020 arts. 1 and 3 amend Ley 4743 itself; Ley '
        '6983/2022 arts. 4-5 amend the Ley Orgánica Municipal; Leyes 4559/2012, 5583/2016, 6768/2021 and 635/1995 '
        'have provisions of their own or only cite the Code.',
        'Código Electoral, art. 258 as enacted: BACN\'s page prints "VER PDDF" (see the PDF) where the Code gives its '
        'D\'Hondt example table; the line is kept verbatim. The linked PDF (/archivos/2346/20140320134709.pdf, the '
        'signed original, 57 pages) has no text layer and no OCR is used, so the 1996 table is not in the text. Leyes 3166/2007, '
        '6318/2019 and 6918/2022 print the table in their HTML; each table row is one line, cells separated by a space.',
        'Código Electoral: BACN wraps the incisos of Ley 6167/2018 (arts. 68 and 157) in HTML ordered lists styled '
        '"list-style-type:none", which show no numbers when rendered; electoral.py reads those lists as plain '
        'paragraphs instead of writing numbers out (../parse.py writes the numbers of other ordered lists).',
    ]


def main():
    if '--fetch' in sys.argv:
        from fetch import fetch
        for u in URLS:
            fetch(u)
        return
    act = codigo_electoral()
    mism = [m for m in MISMATCHES if m.startswith(SLUG + '/')]
    joins = [j for j in parse.JOINS]
    part = {
        'laws': dict(sorted(LAWS.items())),
        'acts': [act],
        'decisions': decisions() + parse.DECISIONS + [
            f'Código Electoral: {len(joins)} line joins (a paragraph broken by a stray <br>): ' + '; '.join(joins) + '.'
            if joins else 'Código Electoral: no line joins were needed.'] + [
            'Código Electoral, restated text: ' + m for m in mism],
        'ai_use': [
            'Código Electoral part: Claude Opus 5.5 (claude-opus-5-5) in Claude Code wrote electoral/electoral.py and '
            'electoral/search.py, ran the BACN searches, read the amending laws to write the replay table (which '
            'article each law rewrites, adds, suspends or repeals, and when) and the notes. No model wrote or changed '
            'legal text: every provision is extracted by code from BACN pages.',
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
    dest = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else ROOT / 'corpus.d' / '50-electoral.json'
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_name(dest.name + '.tmp')
    tmp.write_text(out, encoding='utf-8', newline='\n')
    tmp.replace(dest)
    print(SLUG, len(act['versions']), 'versions;', len(LAWS), 'laws;', len(mism), 'restated;', len(joins), 'joins ->', dest)


if __name__ == '__main__':
    main()
