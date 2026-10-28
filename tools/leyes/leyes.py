"""Frequently consulted Paraguayan laws, one corpus.d part per act (scripts/gitlaw_common/SCHEMA.md). Each law is read
as enacted from its BACN page and replayed through its amending laws, each from its own BACN page (../batch1/actlib.py,
../parse.py Replay engine).

    python -X utf8 leyes/leyes.py              read the cache only, write every part listed in PARTS
    python -X utf8 leyes/leyes.py --out DIR    write the parts into DIR instead of corpus.d/
    python -X utf8 leyes/leyes.py --only NAME  write one part

Deterministic: the same cache gives the same bytes. No network.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'batch1'))

import actlib  # noqa: E402
from actlib import (ROOT, LAWS, MISMATCHES, Replay, bacn_law, enacted, first_version, law, page_meta, parse, plus,  # noqa: E402
                    qblocks, set_arts, unit_of, url_of)

URLS = json.loads((HERE / 'sources.json').read_text(encoding='utf-8'))['urls']
actlib.register(URLS)

AI = ('Claude Opus 5.5 (claude-opus-5-5) in Claude Code wrote Lexifina\'s code, ran the BACN searches, screened the hits '
      'and read the amending laws to write the replay table (which article each law rewrites or repeals, and from '
      'when). No model wrote or changed legal text: every provision is extracted by code from BACN pages.')
COMMON = [
    'BACN publishes this law only as enacted, with no consolidated text. The first version is the enacted text, '
    'checked line by line: every line of the law\'s BACN page from its first heading or article to its closing '
    'formula is in the first version (articles, headings in indice.md, the closing formula in sancion.md). Later '
    'versions replay the amending laws, each from its own BACN page, found with the BACN full-text search for the '
    'law\'s number in its printed forms and its name, and screened for a modifying formula that names it.',
    'Dates: the law\'s own vigencia clause where it has one, otherwise the day after publication (Código Civil art. '
    '1), or the day after promulgation where BACN gives no publication date. Units: art-NNN headed "# Artículo N"; an '
    'epigraph printed after the number stays as the first words of the text; headings in indice.md, the closing '
    'formula in sancion.md.',
]


PRE1987 = ('{who}: published before 1 January 1987, when the Código Civil of Ley 1183/1985 took effect (its art. '
           '2813). Laws of that period fell under the Civil Code adopted by the laws of 19 August 1876 and 27 July 1889 '
           '(repealed by Código Civil art. 2810), whose own rule for the day a law binds when it names none (in the '
           'Argentine text it was taken from, eight days after official publication) could not be confirmed from BACN '
           'or another Paraguayan official text. The first version therefore keeps the day after publication, the rule '
           'of Código Civil art. 1; under the earlier rule the law may have bound some days later.')


def act(slug, short, title, key, versions):
    return {'slug': slug, 'short': short, 'title': title, 'url': versions[0]['source_url'], 'first_law': key,
            'earlier_laws': [], 'versions': versions}


def laws_of(a: dict) -> list[str]:
    keys = {a['first_law']}
    for v in a['versions']:
        for ks in v.get('credits', {}).values():
            keys.update(ks)
    for k in list(keys):              # a lapse credited to "<law>-fin" restores that law
        r = LAWS[k].get('restores')
        if r:
            keys.add(r)
    return sorted(keys)


def write(dest: Path, a: dict, decisions: list[str], extra_laws: tuple[str, ...] = ()):
    keys = sorted(set(laws_of(a)) | set(extra_laws))
    joins = [j for j in parse.JOINS if j.startswith(a['slug'])]
    mism = [m for m in MISMATCHES if m.split('/')[0] == a['slug']]
    part = {
        'laws': {k: LAWS[k] for k in keys},
        'acts': [actlib.to_changes(a)],
        'decisions': COMMON + decisions + [
            (f'{len(joins)} line joins (a paragraph broken by a stray <br>): ' + '; '.join(joins) + '.')
            if joins else 'No line joins were needed.'] + ['Restated text: ' + m for m in mism],
        'ai_use': [f'{a["short"]} part: ' + AI],
    }
    out = json.dumps(part, ensure_ascii=False, indent=1) + '\n'
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_name(dest.name + '.tmp')
    tmp.write_text(out, encoding='utf-8', newline='\n')
    tmp.replace(dest)
    print(dest.name, len(a['versions']), 'versions,', len(keys), 'laws,', len(mism), 'restated,', len(joins), 'joins')


def run(fn):
    """Call one act builder; return (act, the parse.DECISIONS lines it added, plus its own)."""
    n0 = len(parse.DECISIONS)
    a, dec = fn()
    return a, dec + parse.DECISIONS[n0:]


def bad_pub(label: str, m: dict) -> str:
    """BACN metadata with a publication date before promulgation: the year is taken as a typo (day and month kept)
    when that gives a day on or after promulgation; the first version is the day after it."""
    fixed = m['promulgated'][:4] + m['published'][4:]
    assert m['published'] < m['promulgated'] <= fixed, (label, m)
    return fixed


# ------------------------------------------------------------------ Ley 5508/2015

def ley_5508():
    slug, key, pid = 'ley-lactancia-materna', 'ley-5508-2015', '4428'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2015-10-28', 'published': '2005-10-29'}, m
    pub = bad_pub('Ley 5508/2015', m)
    v1 = first_version(key, pid, 'Ley N° 5508/2015', 'Promoción, Protección de la Maternidad y Apoyo a la Lactancia '
                       'Materna', plus(pub, days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    LAWS[key]['published'] = pub      # the law record carries the corrected day, as the first version does
    rp = Replay(slug, units, v1)
    k = 'ley-6453-2019'
    url, L, frm = bacn_law(k, '9184', 'Ley N° 6453/2019')
    set_arts(rp, frm, k, url, L, r'^Artículo 1º\.- Modifícanse los Artículos 1°, 2°, 16, 17 y 19 de la Ley N° 5508',
             [1, 2, 16, 17, 19])
    k = 'ley-7534-2025'
    url, L, frm = bacn_law(k, '12838', 'Ley N° 7534/2025')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícanse y amplíanse los artículos 2º y 11 de la Ley Nº 5508',
             [2, 11])
    dec = [
        'Ley 5508/2015 (Promoción, Protección de la Maternidad y Apoyo a la Lactancia Materna, BACN 4428): BACN '
        'gives promulgation 28 October 2015 and publication "29-10-2005", ten years before its own sanction (10 '
        'September 2015). The year is taken as a typo: published 2015-10-29 (the law record carries that day), in '
        'force the day after (2015-10-30, Código Civil art. 1; the law has no vigencia clause). Art. 20 sets the '
        'maternity leave in stages counted from the in-force day; those stages are the law\'s own wording, not '
        'separate versions.',
        'Ley 5508/2015 amending laws: Ley 6453/2019 art. 1 (arts. 1, 2, 16, 17 and 19) and Ley 7534/2025 art. 1 '
        '(arts. 2 and 11; its art. 2 repeals Ley 5344/2014, which is not in this repository). BACN searches "5508/15", '
        '"5508/2015", "5.508" and "lactancia materna": no other law changes its words.',
    ]
    return act(slug, 'LPML', 'Ley N° 5508/2015 de Promoción, Protección de la Maternidad y Apoyo a la Lactancia '
               'Materna', key, rp.build()), dec


def single(slug, short, title, key, pid, label, ltitle, extra: list[str]):
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    v1 = first_version(key, pid, label, ltitle, plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    return act(slug, short, title, key, Replay(slug, units, v1).build()), extra


def ley_4788():
    return single('ley-trata-de-personas', 'LTP', 'Ley N° 4788/2012 Integral contra la Trata de Personas',
                  'ley-4788-2012', '3158', 'Ley N° 4788/2012', 'Integral contra la Trata de Personas', [
                      'Ley 4788/2012 Integral contra la Trata de Personas (BACN 3158): promulgated 13 December 2012, '
                      'published 18 December 2012, in force the day after publication (no vigencia clause). BACN '
                      'searches "4788/12", "4788/2012", "4.788" and "trata de personas": no law changes its words, so '
                      'it has one version. Its art. 52 repeals arts. 129b and 129c of the Código Penal (inserted by '
                      'Ley 3440/2008) from 2012-12-19. Known gap: the Código Penal in this repository does not yet '
                      'apply that repeal and still shows both articles after that day.'])


def subst(rp: Replay, frm: str, key: str, url: str, units: dict, old: str, new: str, skip: set[str]) -> list[str]:
    """A renaming formula ("Modifícanse las siguientes referencias: la X por la de Y"): every unit whose text holds
    the exact words `old` gets `new` in their place. Returns the unit keys changed."""
    keys = [k for k, u in sorted(units.items()) if k.startswith('art-') and old in u['text'] and k not in skip]
    for k in keys:
        rp.op(frm, key, url, 'fn', k, lambda u, o=old, n=new: dict(u, text=u['text'].replace(o, n)))
    return keys


def nums(keys: list[str]) -> str:
    return ', '.join(str(int(k.split('-')[1])) for k in keys)


def ley_4798():
    return bacn_law('ley-4798-2012', '3162', 'Ley N° 4798/2012')


def ley_4046(must: str):
    """Ley 4046/2010 art. 2 (BACN 554; published 2010-07-30, no vigencia clause, so in force 2010-07-31) repeals the
    article named by `must` among sixteen provisions; Ley 5456/2015 (BACN 4445) restates that art. 2 with the same
    article still listed. Returns (url, in-force day)."""
    url, L, frm = bacn_law('ley-4046-2010', '554', 'Ley N° 4046/2010')
    a2 = [ln for ln in L if ln.startswith('Artículo 2º.- Deróganse los Artículos 1º de la Ley Nº 2.421/04')]
    assert len(a2) == 1 and must in a2[0], must
    L5 = actlib.lines('4445')
    r2 = [ln for ln in L5 if ln.startswith('"Art. 2°.- Deróganse los Artículos 1° de la Ley N° 2421/04')]
    assert len(r2) == 1 and re.sub(r'Nº (\d)\.(\d{3})', r'N° \1\2', must).replace('Nº ', 'N° ') in r2[0], must
    return url, frm


L4046 = ('Ley 4046/2010 (contencioso-administrativo appeal deadline; BACN 554: promulgated 27 July 2010, published 30 '
         'July 2010, no vigencia clause, so in force 2010-07-31) art. 2 repeals, among sixteen provisions that set '
         'other appeal deadlines, {art}; the article is removed from 2010-07-31. Ley 4798/2012 then rewrites it '
         '("Modifícase ... queda redactado"): a re-enactment, so it returns from 2013-01-04 with its new text, '
         'credited to Ley 4798. Ley 5456/2015 (BACN 4445, published 21 July 2015) rewrites art. 2 of Ley 4046 and '
         'still lists the article: a restatement of the 2010 repeal, not a new one, so the re-enacted article stays '
         '(the same reading as for Código Aduanero art. 377).')


DINAPI = ('Ley 4798/2012 (crea la Dirección Nacional de Propiedad Intelectual, DINAPI; BACN 3162): promulgated 31 '
          'December 2012, published 3 January 2013, no vigencia clause, so in force 2013-01-04.')


def ley_1328():
    slug, key, pid = 'ley-derecho-de-autor', 'ley-1328-1998', '908'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    v1 = first_version(key, pid, 'Ley N° 1328/1998', 'DE DERECHO DE AUTOR Y DERECHOS CONEXOS',  # = corpus.json
                       plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    url, frm = ley_4046('Artículo 151 de la Ley Nº 1.328/98 "DE DERECHOS DE AUTOR Y DERECHOS CONEXOS"')
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-151')
    k = 'ley-4798-2012'
    url, L, frm = ley_4798()
    (n, paras), = qblocks(L, r'^Artículo 40\.- Modifícase el Artículo 151 de la Ley de Nº 1328/98')
    assert n == 151
    rp.op(frm, k, url, 'add', 'art-151', unit_of(151, paras, k))
    old, new = 'Dirección Nacional del Derecho de Autor', 'Dirección General del Derecho de Autor y Derechos Conexos'
    assert any(ln.startswith(f'a) La "{old}" por la de "{new}", de los Artículos de la Ley Nº 1328/98') for ln in L)
    renamed = subst(rp, frm, k, url, units, old, new, {'art-151'})
    k = 'ley-5247-2014'
    url, L, frm = bacn_law(k, '2994', 'Ley N° 5247/2014')
    set_arts(rp, frm, k, url, L, r'^Artículo 1\.° Modifícanse los artículos 126 y 130 de la Ley N° 1\.328/98',
             [126, 130])
    dec = [
        'Ley 1328/1998 de Derecho de Autor y Derechos Conexos (BACN 908): promulgated 15 October 1998, published 20 '
        'October 1998, in force the day after publication (no vigencia clause).',
        DINAPI + ' For Ley 1328 it rewrites art. 151 (art. 40) and, by art. 36 a), replaces "Dirección Nacional del '
        'Derecho de Autor" with "Dirección General del Derecho de Autor y Derechos Conexos" "de los Artículos de la Ley '
        'Nº 1328/98". The replacement is applied to those exact words wherever they stand in an article in force on '
        f'2013-01-04 (arts. {nums(renamed)}). Four places print "Dirección Nacional de Derecho de Autor" (without '
        '"del"); the law names the exact words, so those are left as printed. Headings are not changed.',
        L4046.format(art='art. 151 of Ley 1328/1998'),
        'Ley 1328/1998: Ley 5247/2014 art. 1 rewrites arts. 126 and 130 (fifty years become seventy). BACN searches '
        '"1328/98", "1328/1998", "1.328" and "derecho de autor": no other law changes its words.',
    ]
    return act(slug, 'LDA', 'Ley N° 1328/1998 de Derecho de Autor y Derechos Conexos', key, rp.build()), dec


def ley_1294():
    slug, key, pid = 'ley-de-marcas', 'ley-1294-1998', '862'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    v1 = first_version(key, pid, 'Ley N° 1294/1998', 'De Marcas', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    url, frm = ley_4046('Artículo 129 de la Ley Nº 1.294/98 "DE MARCAS"')
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-129')
    k = 'ley-4798-2012'
    url, L, frm = ley_4798()
    changed = [49, 118, 120, 125, 126, 127, 128, 129, 130]
    b = qblocks(L, r'^Modifícanse los Artículos 49, 118, 120, 125, 126, 127, 128, 129 y 130 de la Ley Nº 1294/98')
    assert [n for n, _ in b] == changed, [n for n, _ in b]
    for n, paras in b:            # art. 129 was repealed by Ley 4046/2010: re-enacted here
        rp.op(frm, k, url, 'add' if n == 129 else 'set', f'art-{n:03d}', unit_of(n, paras, k))
    assert any(ln.startswith('Deróganse el Artículo 44 de la Ley Nº 868/81 "DE DIBUJOS Y MODELOS INDUSTRIALES"; los '
                             'Artículos 119, 121 y 123 de la Ley Nº 1294/98') for ln in L)
    for n in (119, 121, 123):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    old, new = 'Dirección de la Propiedad Industrial', 'Dirección General de Propiedad Industrial'
    assert any(ln.startswith(f'b) La referencia de "{old}" contenida en las Leyes Nºs 868/81') for ln in L)
    renamed = subst(rp, frm, k, url, units, old, new,
                    {f'art-{n:03d}' for n in changed + [119, 121, 123]})
    k = 'ley-4923-2013'
    url, L, frm = bacn_law(k, '1138', 'Ley N° 4923/2013', in_force='2013-07-20',
                           why='art. 50: "entrará en vigencia luego de transcurridos un mes de su publicación" '
                               '(published 2013-06-20), counted to the same day of the next month')
    assert any(ln.startswith('Artículo 49.- DEROGACIÓN. Deróganse los artículos 57, 58, 59 y 60 de la Ley N° '
                             '1.294/98') for ln in L)
    for n in (57, 58, 59, 60):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    dec = [
        'Ley 1294/1998 de Marcas (BACN 862): promulgated 6 August 1998, published 30 September 1998, in force the day '
        'after publication (no vigencia clause).',
        DINAPI + ' For Ley 1294 it rewrites arts. 49, 118, 120 and 125-130 (art. 38) and repeals arts. 119, 121 and '
        '123 (art. 41). Its art. 36 b) replaces the reference "Dirección de la Propiedad Industrial" in Ley 1294 with '
        '"Dirección General de Propiedad Industrial" "a los efectos del Capítulo IV de la presente Ley"; read as a '
        'textual change (the qualifier names the chapter of Ley 4798 that creates that Dirección General), applied '
        f'to those exact words in the articles it did not rewrite or repeal (arts. {nums(renamed)}). Headings are '
        'not changed.',
        L4046.format(art='art. 129 of Ley 1294/1998'),
        'Ley 1294/1998: Ley 4923/2013 (indicaciones geográficas) art. 49 repeals arts. 57-60. BACN searches '
        '"1294/98", "1294/1998", "1.294" and "ley de marcas": no other law changes its words (Ley 1258 amends the '
        'earlier Ley 751/1979 de Marcas).',
    ]
    return act(slug, 'LM', 'Ley N° 1294/1998 de Marcas', key, rp.build()), dec


def ley_1015():
    slug, key, pid = 'ley-legitimacion-dinero', 'ley-1015-1997', '988'
    units = enacted(pid, slug, 5)
    split = 'a pedido de p arte, al inicio'       # one word broken over two lines on BACN ("p" / "arte")
    assert units['art-036']['text'].count(split) == 1
    units['art-036'] = dict(units['art-036'], text=units['art-036']['text'].replace(split, 'a pedido de parte, al inicio'))
    actlib.check_lines(slug, actlib.lines(pid)[5:actlib.closing_index(actlib.lines(pid)) + 1], units)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1997-01-10', 'published': '1997-01-10'}, m
    v1 = first_version(key, pid, 'Ley N° 1015/1997', 'QUE PREVIENE Y REPRIME LOS ACTOS ILÍCITOS DESTINADOS A LA '
                       'LEGITIMACIÓN DE DINERO O BIENES', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-3783-2009'
    url, L, frm = bacn_law(k, '1439', 'Ley N° 3783/2009')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícanse los Artículos 1°, 13, 19, 26, 27, 28, 29 y 30 de la '
             r'Ley N° 1\.015/97', [1, 13, 19, 26, 27, 28, 29, 30])
    assert any(ln.startswith('Artículo 2°.- Deróganse los Artículos 23 y 31 de la Ley N° 1.015/97') for ln in L)
    for n in (23, 31):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    k = 'ley-6497-2019'
    url, L, frm = bacn_law(k, '9095', 'Ley N° 6497/2019')
    set_arts(rp, frm, k, url, L, r'^Artículo 1\.° Modifícanse los Artículos 2°, 12, 14, 15, 16, 17, 18, 19, 22, 24, '
             r'27, 35, 36, 37 y 38 de la Ley N° 1015/1997', [2, 12, 14, 15, 16, 17, 18, 19, 22, 24, 27, 35, 36, 37, 38])
    k = 'ley-6797-2021'
    url, L, frm = bacn_law(k, '9652', 'Ley N° 6797/2021')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícase el Artículo 13 de la Ley Nº 1015/1997', [13])
    k = 'ley-6960-2022'
    url, L, frm = bacn_law(k, '10556', 'Ley N° 6960/2022')
    set_arts(rp, frm, k, url, L, r'^Artículo 1º\.- Modifícanse los Artículos 13, 25 y 28 de la Ley N° 1015/1997',
             [13, 25, 28])
    dec = [
        'Ley 1015/1997 que previene y reprime los actos ilícitos destinados a la legitimación de dinero o bienes '
        '(BACN 988): BACN gives promulgation and publication 10 January 1997; the law has no vigencia clause, so it is '
        'in force the day after publication (1997-01-11, Código Civil art. 1).',
        'Ley 1015/1997 art. 36: BACN breaks the word "parte" over two lines ("a pedido de p" / "arte, al inicio"); '
        'the two lines are joined without a space ("a pedido de parte"). Ley 6497/2019 later replaces the whole '
        'article.',
        'Ley 1015/1997 amending laws, each applied from its own BACN page and in force the day after its publication '
        '(none has a vigencia clause): Ley 3783/2009 art. 1 (arts. 1, 13, 19 and 26-30) and art. 2 (repeals arts. 23 '
        'and 31); Ley 6497/2019 art. 1 (arts. 2, 12, 14-19, 22, 24, 27 and 35-38); Ley 6797/2021 (art. 13); Ley '
        '6960/2022 (arts. 13, 25 and 28). BACN searches "1015/97", "1015/1997", "1.015/97" and "legitimación de '
        'dinero": the other hits only cite the law (Leyes 4503 and 6419 on frozen assets, 6167 and 6501 on party '
        'finance, 6769 on the Agencia Financiera de Desarrollo). Its penal articles (3-11) are not repealed by name by '
        'the Código Penal (Ley 1160/1997), whose art. 196 also punishes money laundering ("Lavado de dinero"); they '
        'are kept as printed.',
    ]
    return act(slug, 'LLD', 'Ley N° 1015/1997 que previene y reprime los actos ilícitos destinados a la legitimación '
               'de dinero o bienes', key, rp.build()), dec


def ley_1626():
    slug, key, pid = 'ley-funcion-publica', 'ley-1626-2000', '1711'
    orig = actlib.lines

    def fixed(p):                     # BACN prints "Artículo.12.-" (a full stop for the space)
        L = orig(p)
        if p == pid:
            assert sum(ln.startswith('Artículo.12.-') for ln in L) == 1
            L = ['Artículo 12.-' + ln[len('Artículo.12.-'):] if ln.startswith('Artículo.12.-') else ln for ln in L]
        return L
    actlib.lines = fixed
    try:
        units = enacted(pid, slug, 5)
    finally:
        actlib.lines = orig
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2000-12-27', 'published': '2000-12-28'}, m
    v1 = first_version(key, pid, 'Ley N° 1626/2000', 'DE LA FUNCIÓN PÚBLICA', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-3031-2006'
    url, L, frm = bacn_law(k, '2114', 'Ley N° 3031/2006')
    assert '"Art.14.- b) contar con mayoría de edad;"' in L
    rp.op(frm, k, url, 'fn', 'art-014', actlib.replace_line('b) ', 'b) contar con mayoría de edad;'))
    k = 'ley-3784-2009'
    url, L, frm = bacn_law(k, '1438', 'Ley N° 3784/2009')
    assert any(ln.startswith('Artículo 3°.- Suspender la vigencia del Artículo 16, Inciso f) de la Ley Nº 1626/00') for ln in L)
    LAWS[k]['note'] = ('Declares a 90-day health emergency (art. 1) and suspends art. 16 inc. f) for health care staff '
                       'only, for the length of the emergency (art. 3). The text of art. 16 does not change.')
    rp.op(frm, k, url, 'touch', 'art-016')
    k = 'ley-3856-2009'
    url, L, frm = bacn_law(k, '1487', 'Ley N° 3856/2009')
    assert any(ln.startswith('Derógase el Artículo 107 de la Ley Nº 1626/00') for ln in L)
    rp.op(frm, k, url, 'del', 'art-107')
    k = 'ley-3989-2010'
    url, L, frm = bacn_law(k, '3525', 'Ley N° 3989/2010')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícanse los Artículos 16 inciso f\) y 143 de la Ley Nº 1\.626',
             [16, 143])
    # Ley 4679/2012 arts. 7-9 (its Capítulo II) add to arts. 66, 68 and 69; in force 120 days after publication (art.
    # 20). Same law record as the batch 2 part that holds Ley 4679 itself.
    k, p4679 = 'ley-4679-2012', '1229'
    url = url_of(p4679)
    m4 = page_meta(url)
    if k not in LAWS:
        law(k, label='Ley N° 4679/2012', title='De Trámites Administrativos', kind='law', enacted=m4['promulgated'],
            published=m4['published'], url=url)
    L = parse.page_lines(url)
    assert any(ln.startswith('Artículo 20.- Los normas de los Capítulos II y III entrarán en vigencia a los ciento '
                             'veinte días') for ln in L)
    frm = plus(m4['published'], days=120)
    added = {}
    for art, target in (('Artículo 7°.- Incorpórase al Artículo 66', 66), ('Artículo 8°.- Incorpórase al Artículo 68', 68),
                        ('Artículo 9°.- Incorpórase al Artículo 69', 69)):
        i = next(j for j, ln in enumerate(L) if ln.startswith(art))
        added[target] = parse.strip_quote([L[i + 1]])
        assert len(added[target]) == 1
        rp.op(frm, k, url, 'fn', f'art-{target:03d}',
              lambda u, s=added[target][0]: dict(u, text=u['text'].rstrip('\n') + '\n' + s + '\n'))
    k = 'ley-5207-2014'
    url, L, frm = bacn_law(k, '2972', 'Ley N° 5207/2014')
    set_arts(rp, frm, k, url, L, r'^Artículo 1\.° Modifícase el artículo 144 de la Ley N° 1\.626/00', [144])
    k = 'ley-5766-2016'
    url, L, frm = bacn_law(k, '8312', 'Ley N° 5766/2016')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícanse los Artículos 54 y 56 de la Ley Nº 1626/00', [54, 56])
    k = 'ley-6849-2021'
    url, L, frm = bacn_law(k, '10057', 'Ley N° 6849/2021')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícase el Artículo 54 de la Ley Nº 1626/2000', [54])
    k = 'ley-7445-2025'
    url, L, frm = bacn_law(k, '12637', 'Ley N° 7445/2025', in_force='2025-07-16',
                           why='art. 146: "entrará en vigencia 6 (seis), meses después de su publicación en la Gaceta '
                               'Oficial" (published 2025-01-16), counted to the same day six months later')
    assert any(ln.startswith('A partir de la fecha de entrada en vigencia de la presente ley, queda abrogada la Ley N° '
                             '1.626/2000') for ln in L)
    n0 = len(MISMATCHES)
    whole = rp.build()[-1]['units']   # every unit in force the day before the abrogation (a dry run)
    del MISMATCHES[n0:]
    for u in sorted(whole):
        rp.op(frm, k, url, 'del', u)
    versions = rp.build()
    assert versions[-1]['units'] == {} and versions[-1]['from'] == '2025-07-16'
    dec = [
        'Ley 1626/2000 de la Función Pública (BACN 1711): promulgated 27 December 2000, published 28 December 2000, '
        'no vigencia clause, so in force 2000-12-29. BACN prints "Artículo.12.-"; read as "Artículo 12.-".',
        'Ley 1626/2000 amending laws, each from its own BACN page and in force the day after publication unless '
        'stated: Ley 3031/2006 (art. 14 inc. b); Ley 3784/2009 art. 3 (suspends art. 16 inc. f for health care staff '
        'during a 90-day emergency: a note, no word change); Ley 3856/2009 (repeals art. 107); Ley 3989/2010 (arts. 16 '
        'and 143); Ley 4679/2012 arts. 7-9 (add inc. e) to art. 66, inc. m) to art. 68 and a final paragraph to art. '
        '69), in force with its Capítulo II 120 days after publication (art. 20), 2012-12-19; Ley 5207/2014 (art. '
        '144); Ley 5766/2016 (arts. 54 and 56); Ley 6849/2021 (art. 54). The added incisos are appended after the '
        'last inciso as printed; the punctuation of the inciso before them is left as printed. Art. 68 as enacted ends '
        'at inciso k); Ley 4679 adds an inciso m) and its art. 9 cites "inciso m)", so it is kept as lettered (no law '
        'found adds an inciso l).',
        'Ley 1626/2000 abrogated: Ley 7445/2025 de la Función Pública y del Servicio Civil (BACN 12637) art. 147 '
        'abrogates Ley 1626 and its amending laws from the day Ley 7445 takes effect, which art. 146 sets six months '
        'after its publication (2025-01-16): 2025-07-16. The last version, from that day, is empty. BACN searches '
        '"7445", "7.445", "7445/2025", "7445/25" and "servicio civil": no law moves that day.',
        'Ley 1626/2000: BACN searches "1626/00", "1626/2000", "1.626" and "función pública" were screened for '
        'modifying formulas; Ley 3161/2007 extends Ley 1626 to the Armed Forces staff without changing its words, and '
        'the other hits only cite it.',
    ]
    return act(slug, 'LFP', 'Ley N° 1626/2000 de la Función Pública', key, versions), dec


# ------------------------------------------------------------------ Ley 438/1994

L5501_ARTS = [2, 3, 4, 5, 8, 29, 37, 38, 42, 45, 46, 49, 50, 51, 52, 59, 62, 69, 72, 74, 75, 76, 77, 107, 113, 126, 130]


def ley_438():
    slug, key, pid = 'ley-cooperativas', 'ley-438-1994', '2373'
    units = enacted(pid, slug, 5)
    split = 'puede ser declarada\nen cuarto intermedio'    # one sentence broken over two lines on BACN
    assert units['art-060']['text'].count(split) == 1
    units['art-060'] = dict(units['art-060'], text=units['art-060']['text'].replace(
        split, 'puede ser declarada en cuarto intermedio'))
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1994-10-21', 'published': None}, m
    v1 = first_version(key, pid, 'Ley N° 438/1994', 'DE COOPERATIVAS', plus(m['promulgated'], days=1), units,
                       'The law as enacted, from its BACN page; BACN gives no publication date, so it is dated the '
                       'day after promulgation.')
    rp = Replay(slug, units, v1)

    # Ley 2157/2003 (INCOOP) art. 37: the last sentence of art. 60 and arts. 115-117, 120-123, 125, 127-129.
    k = 'ley-2157-2003'
    url, L, frm = bacn_law(k, '2423', 'Ley N° 2157/2003')
    a37 = [ln for ln in L if ln.startswith('Artículo 37.- Derogaciones. Deróganse las siguientes normas de la Ley '
                                           '438/94 de Cooperativas: la última parte del Artículo 60 que dice: "La '
                                           'resolución que dicte este organismo podrá recurrirse')]
    assert len(a37) == 1 and a37[0].count('los Artículos 115, 116, 117, 120, 121, 122, 123, 125, 127, 128 y 129.') == 1

    def drop_60_last(u):
        last = (' La resolución que dicte este organismo podrá recurrirse dentro de los treinta días posteriores a '
                'la notificación, ante el Juzgado de Primera Instancia en lo Civil y Comercial de Turno.')
        assert u['text'].rstrip('\n').endswith(last), u['text'][-200:]
        return dict(u, text=u['text'].rstrip('\n')[:-len(last)] + '\n')
    rp.op(frm, k, url, 'fn', 'art-060', drop_60_last)
    for n in (115, 116, 117, 120, 121, 122, 123, 125, 127, 128, 129):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')

    k = 'ley-4596-2012'
    url, L, frm = bacn_law(k, '2703', 'Ley N° 4596/2012')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícase el Articulo 46 de la Ley N° 438/94', [46])

    # Ley 5501/2015 (27 articles), in force the day after publication; Ley 5551/2015 suspends it for six months.
    k5501 = 'ley-5501-2015'
    url5501, L, frm5501 = bacn_law(k5501, '4482', 'Ley N° 5501/2015')
    assert frm5501 == '2015-09-15', frm5501
    set_arts(rp, frm5501, k5501, url5501, L, r'^Artículo 1°\.- Modifícanse los Artículos 2°, 3°, 4°, 5°, 8°, 29, 37, '
             r'38, 42, 45, 46, 49, 50, 51, 52, 59, 62, 69, 72, 74, 75, 76, 77, 107, 113, 126 y 130 de la Ley N° 438/94',
             L5501_ARTS)
    k5551 = 'ley-5551-2015'
    url, L, frm = bacn_law(k5551, '4530', 'Ley N° 5551/2015')
    assert frm == '2015-12-31', frm
    assert any(ln.startswith('Artículo 1°.- Suspéndase por el plazo de seis meses la entrada en vigencia de la Ley Nº '
                             '5501/15') for ln in L)
    end = '2016-06-30'      # Código Civil arts. 339-341: a term of months begun on 31 December ends on 30 June
    LAWS[k5551].update(temporary_until=end, restores=k5501, note=(
        'Suspends Ley 5501/2015, already in force since 15 September 2015, for six months (art. 1), so the 27 '
        'articles it rewrote return to their earlier wording until 30 June 2016.'))
    for n in L5501_ARTS:
        rp.op(frm, k5551, url, 'restore', f'art-{n:03d}', frm5501)
    fin = k5551 + '-fin'
    law(fin, label='Ley N° 5551/2015, fin de la suspensión', kind='law', enacted=LAWS[k5551]['enacted'],
        published=LAWS[k5551]['published'], url=url, restores=k5551,
        title='Fin de la suspensión por seis meses de la Ley N° 5501/2015 (Ley N° 5551/2015, art. 1)',
        note='The six-month suspension of Ley 5501/2015 by Ley 5551/2015 ended on 30 June 2016; from 1 July 2016 the '
             'wording of Ley 5501/2015 applies again.')
    for n in L5501_ARTS:
        rp.op(plus(end, days=1), fin, url, 'restore', f'art-{n:03d}', frm)

    k = 'ley-6178-2018'
    url, L, frm = bacn_law(k, '9008', 'Ley N° 6178/2018')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícase el artículo 113 de la Ley N° 5501/15', [113])
    k = 'ley-6608-2020'
    url, L, frm = bacn_law(k, '9375', 'Ley N° 6608/2020')
    set_arts(rp, frm, k, url, L, r'^Artículo 1\.° Modifícanse los artículos 51 y 59 de la Ley N° 438/94', [51, 59])
    k = 'ley-7235-2023'
    url, L, frm = bacn_law(k, '12162', 'Ley N° 7235/2023')
    assert frm == '2023-12-15', frm
    i = L.index('1. A partir de la entrada en vigencia de la presente ley, quedan expresamente derogadas las '
                'siguientes disposiciones:')
    assert L[i - 1] == 'Artículo 44.- Derogaciones.' and L[i + 2] == 'b) El Artículo 105 de la Ley Nº 438/1994 "DE COOPERATIVAS".'
    assert 'La presente ley entrará en vigencia a partir del día siguiente a la fecha de su publicación.' in L
    rp.op(frm, k, url, 'del', 'art-105')

    versions = rp.build()
    v = {x['from']: x for x in versions}
    assert v['2016-07-01']['units'] == v['2015-09-15']['units'], 'Ley 5501 wording must come back whole'
    dec = [
        'Ley 438/1994 de Cooperativas (BACN 2373): promulgated 21 October 1994; BACN gives no publication date and '
        'the law has no vigencia clause, so it is dated the day after promulgation (1994-10-22). Art. 60: BACN breaks '
        'one sentence over two lines ("puede ser declarada" / "en cuarto intermedio"); the lines are joined with a '
        'space.',
        'Ley 438/1994: Ley 2157/2003 (Instituto Nacional de Cooperativismo; published 4 July 2003, in force 5 July) '
        'art. 37 repeals the last sentence of art. 60 (quoted in the law without the comma BACN prints before "ante '
        'el Juzgado"; the sentence is removed) and arts. 115, 116, 117, 120, 121, 122, 123, 125, 127, 128 and 129. Its '
        'general repeal of "todas las disposiciones que se opongan" names no article and is not applied.',
        'Ley 438/1994: Ley 4046/2010 art. 2 (and Ley 5456/2015, which restates it) also lists art. 129 among the '
        'provisions it repeals; art. 129 was already repealed by Ley 2157/2003, so neither changes the text.',
        'Ley 438/1994: Ley 5501/2015 (promulgated and published 14 September 2015, no vigencia clause) rewrites 27 '
        'articles and is in force from 15 September 2015. Ley 5551/2015 (published 30 December 2015, in force 31 '
        'December) "suspends for six months the entry into force" of Ley 5501, which was already in force: read as a '
        'suspension from 31 December 2015, so the 27 articles return to their earlier wording (art. 46 to that of Ley '
        '4596/2012). By Código Civil arts. 339-341 a term of months that begins on 31 December ends at midnight on 30 '
        'June, so the wording of Ley 5501 applies again from 1 July 2016 (a version credited to "Ley N° 5551/2015, fin '
        'de la suspensión"). No law extends the suspension (BACN searches "5501", "5501/15").',
        'Ley 438/1994: Ley 6178/2018 rewrites "el artículo 113 de la Ley N° 5501/15", i.e. art. 113 of Ley 438 as '
        'worded by Ley 5501 (Ley 5501 has only two articles of its own); applied to art. 113. Its text has no letter '
        'before the last paragraph ("Aranceles aduaneros ..."), kept as printed. Ley 6608/2020 rewrites arts. 51 and '
        '59. Ley 7235/2023 (jubilaciones y pensiones; in force the day after publication, art. 45) art. 44.1 b) '
        'repeals art. 105 from its entry into force.',
        'Ley 438/1994: BACN searches "438/94", "438/1994", "Ley 438", "cooperativas", "de cooperativas", "5501" and '
        '"5501/15". The other hits only cite the law: tax laws (2421/2004, 5061/2013, 6380/2019) and budget laws keep '
        'its exemptions "con los alcances" of the tax law, Ley 2329/2003 (housing cooperatives, amended by Ley '
        '7277/2024) and Ley 6841/2021 (worker cooperatives) refer to it, and Ley 6124 sets a national day.',
    ]
    return act(slug, 'LCOOP', 'Ley N° 438/1994 de Cooperativas', key, versions), dec


# ------------------------------------------------------------------ Ley 1863/2002 Estatuto Agrario

def ley_1863():
    slug, key, pid = 'estatuto-agrario', 'ley-1863-2002', '3124'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2002-01-30', 'published': '2002-01-31'}, m
    v1 = first_version(key, pid, 'Ley N° 1863/2002', 'QUE ESTABLECE EL ESTATUTO AGRARIO', plus(m['published'], days=1),
                       units, 'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)

    k = 'ley-2002-2002'
    url, L, frm = bacn_law(k, '4024', 'Ley N° 2002/2002')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícanse los Artículos 2°, 5°, 10, 16, 56, 57 y 74 de la Ley N° '
             r'1863 del 30 de enero de 2002', [2, 5, 10, 16, 56, 57, 74])
    k = 'ley-2531-2004'
    url, L, frm = bacn_law(k, '4023', 'Ley N° 2531/2004')
    set_arts(rp, frm, k, url, L, r'^Artículo 1º\.- Modifícase el Artículo 16 de la Ley N° 2002, que modifica varios '
             r'artículos de la Ley N° 1863', [16])
    set_arts(rp, frm, k, url, L, r'^Artículo 2°\.- Modifícanse los Artículos 17, 58, 90 y 93 de la Ley N° 1863', [17, 58, 90, 93])
    k = 'ley-4988-2013'
    url, L, frm = bacn_law(k, '4770', 'Ley N° 4988/2013')
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícase el Artículo 56 de la Ley N° 1863/02', [56])
    k = 'ley-5205-2014'
    url, L, frm = bacn_law(k, '2970', 'Ley N° 5205/2014')
    set_arts(rp, frm, k, url, L, r'^Artículo 1\.° Modifícase el artículo 53 de la Ley N° 1\.863/02', [53])
    k = 'ley-5881-2017'
    url, L, frm = bacn_law(k, '9778', 'Ley N° 5881/2017')
    set_arts(rp, frm, k, url, L, r'^Artículo 1\.° Modifícase el artículo 56 de la Ley N° 1\.863/02', [56])
    k = 'ley-6081-2018'
    url, L, frm = bacn_law(k, '8439', 'Ley N° 6081/2018')
    set_arts(rp, frm, k, url, L, r'^Artículo 1\.° Modifícase el artículo 53 de la Ley N° 1\.863/02', [53])
    k = 'ley-7424-2025'
    url, L, frm = parse.ley_7424()
    set_arts(rp, frm, k, url, L, r'^Artículo 193\.- Modifícase el artículo 57 de la Ley N° 1863/2002', [57])
    assert ('g. Los artículos 15, 38, 39 y 104 de la Ley N° 1863/2002 "ESTATUTO AGRARIO", así como sus respectivas '
            'modificaciones.') in L
    for n in (15, 38, 39, 104):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    dec = [
        'Ley 1863/2002 Estatuto Agrario (BACN 3124): promulgated 30 January 2002, published 31 January 2002, no '
        'vigencia clause, so in force the day after publication (2002-02-01).',
        'Ley 1863/2002: Ley 2002/2002 rewrites arts. 2, 5, 10, 16, 56, 57 and 74. Ley 2531/2004 art. 1 rewrites "el '
        'Artículo 16 de la Ley N° 2002", i.e. art. 16 of Ley 1863 as worded by Ley 2002 (Ley 2002 has no art. 16 of '
        'its own), applied to art. 16; its art. 2 rewrites arts. 17, 58, 90 and 93. Leyes 4988/2013 and 5881/2017 '
        'rewrite art. 56; Leyes 5205/2014 and 6081/2018 rewrite art. 53.',
        'Ley 1863/2002: Ley 7424/2025 (Sistema Nacional Unificado Registral y Catastral), in force 2026-01-15 (its art. '
        '187: "la media noche del mismo día y mes del año siguiente" to its publication on 14 January 2025; a year '
        'counted from the 14th ends at midnight of 14 January 2026, Código Civil arts. 339 and 341), rewrites art. 57 '
        '(art. 193) and repeals arts. 15, 38, 39 and 104 "así como sus respectivas modificaciones" (art. 200 g.; none '
        'of the four had been amended). Its art. 198 ("deberá entenderse sustituida") updates references in all '
        'laws without changing their words, so it is not applied as text.',
        'Ley 1863/2002: BACN searches "1863/02", "1863/2002", "1.863" and "estatuto agrario". The other hits only cite '
        'the law: Ley 2419/2004 creates the Instituto Nacional de Desarrollo Rural y de la Tierra as the authority '
        'that applies it (art. 116 named the Instituto de Bienestar Rural until such a law) without changing its '
        'words; Ley 4682 sets penalties for transfers in breach of it; expropriation, transfer and loan laws '
        'apply it. Ley 352/1994 amends the earlier Estatuto Agrario (Ley 854/1963, repealed by art. 114).',
    ]
    return act(slug, 'EA', 'Ley N° 1863/2002 Estatuto Agrario', key, rp.build()), dec


# ------------------------------------------------------------------ Ley 352/1994 Áreas Silvestres Protegidas

def ley_352():
    slug, key, pid = 'ley-areas-silvestres-protegidas', 'ley-352-1994', '2396'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1994-05-24', 'published': '1994-06-21'}, m
    v1 = first_version(key, pid, 'Ley N° 352/1994', 'DE AREAS SILVESTRES PROTEGIDAS', plus(m['published'], days=1),
                       units, 'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    url, frm = ley_4046('Artículo 59 de la Ley Nº 352/94 "DE ÁREAS SILVESTRES PROTEGIDAS"')
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-059')
    k = 'ley-6422-2019'
    pub = page_meta(url_of('9232'))['published']
    url, L, frm = bacn_law(k, '9232', 'Ley N° 6422/2019', in_force=plus(pub, days=90),
                           why=f'art. 2: "en un plazo de noventa días a partir de la publicación" ({pub})')
    assert ('Artículo 2.° Las disposiciones de esta ley entrarán en vigencia en un plazo de noventa días a partir de la '
            'publicación de la presente ley.') in L
    set_arts(rp, frm, k, url, L, r'^Artículo 1\.° Modifícanse los artículos 41, 42, 43, 44 y 45 de la Ley N° 352/1994',
             [41, 42, 43, 44, 45])
    k = 'ley-7633-2026'
    url, L, frm = bacn_law(k, '12960', 'Ley N° 7633/2026', in_force='2026-03-18',
                           why='art. 24: "se hará efectiva desde la promulgación y publicación" (both 18 March 2026)')
    assert page_meta(url) == {'promulgated': '2026-03-18', 'published': '2026-03-18'}
    i = L.index('Artículo 24. Vigencia.')
    assert L[i + 1] == ('La entrada en vigencia de la presente ley se hará efectiva desde la promulgación y '
                        'publicación de la presente ley en la Gaceta Oficial.'), L[i + 1]
    j = L.index('A partir de la entrada en vigencia de la presente ley, quedarán derogadas las siguientes disposiciones:')
    assert L[j - 1] == 'Artículo 21. Derogaciones.', L[j - 1]
    assert any(ln.startswith('g. El inciso e) del artículo 43 de la Ley Nº 352/1994 modificado por la Ley Nº '
                             '6422/2019') for ln in L)
    rp.op(frm, k, url, 'fn', 'art-043', actlib.drop_line('e) '))
    dec = [
        'Ley 352/1994 de Áreas Silvestres Protegidas (BACN 2396): promulgated 24 May 1994, published 21 June 1994, '
        'no vigencia clause, so in force the day after publication (1994-06-22). Its arts. 67-69 amend other laws '
        '(the earlier Estatuto Agrario, Ley 854/1963, and Ley 662/1960); they stay here as its own text.',
        L4046.format(art='art. 59 of Ley 352/1994 (sanctions)').replace(
            ' Ley 4798/2012 then rewrites it ("Modifícase ... queda redactado"): a re-enactment, so it returns from '
            '2013-01-04 with its new text, credited to Ley 4798.', ' No later law puts it back.').replace(
            'still lists the article: a restatement of the 2010 repeal, not a new one, so the re-enacted article stays',
            'still lists the article: a restatement of the 2010 repeal, not a new one, so no further change'),
        'Ley 352/1994: Ley 6422/2019 rewrites arts. 41-45 (Cuerpo Nacional de Guardaparques); its art. 2 puts it in '
        'force "en un plazo de noventa días a partir de la publicación" (19 November 2019), counted as ninety '
        'calendar days (2020-02-17), as for the other laws here with a term of days.',
        'Ley 352/1994: Ley 7633/2026 (reforma de la Caja Fiscal) art. 21 g. repeals inciso e) of art. 43 as worded by '
        'Ley 6422/2019 (retirement of public-sector park rangers) "a partir de la entrada en vigencia de la presente '
        'ley"; its art. 24 makes it effective "desde la promulgación y publicación", both on 18 March 2026, so the '
        'inciso is removed from that day. The other incisos keep their letters, as printed.',
        'Ley 352/1994: BACN searches "352/94", "352/1994" and "áreas silvestres protegidas". The other hits declare '
        'protected areas under it or cite it; Ley 1561/2000 (Sistema Nacional del Ambiente) names it among the laws '
        'its Secretaría applies and repeals only provisions on other bodies\' powers (art. 39), without changing its '
        'words.',
    ]
    return act(slug, 'LASP', 'Ley N° 352/1994 de Áreas Silvestres Protegidas', key, rp.build()), dec


# ------------------------------------------------------------------ Ley 2419/2004 INDERT

def ley_2419():
    slug, key, pid = 'ley-indert', 'ley-2419-2004', '2273'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2004-07-15', 'published': '2004-07-23'}, m
    L = actlib.lines(pid)
    i = L.index('Artículo 52.- VIGENCIA.')
    assert L[i + 1].startswith('El Poder Ejecutivo deberá nombrar al Presidente del Instituto'), L[i + 1]
    v1 = first_version(key, pid, 'Ley N° 2419/2004', 'QUE CREA EL INSTITUTO NACIONAL DE DESARROLLO RURAL Y DE LA '
                       'TIERRA', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    url, frm = ley_4046('Artículo 25 de la Ley Nº 2.419/04 "QUE CREA EL INSTITUTO NACIONAL DE DESARROLLO RURAL Y DE '
                        'LA TIERRA"')
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-025')
    L5 = actlib.lines('4738')       # Ley 5061/2013: held, see the decision below
    assert page_meta(url_of('4738')) == {'promulgated': '2013-10-04', 'published': '2013-10-08'}
    assert ('Artículo 13.- Deróganse los incisos f) y g) del Artículo 27 y a) y b) del Artículo 35 de la Ley N° 2419/04 '
            '"QUE CREA EL INSTITUTO NACIONAL DE DESARROLLO RURAL Y DE LA TIERRA".') in L5
    assert any(ln.startswith('Artículo 14.- Las disposiciones de la presente Ley entrarán en vigencia a partir de la '
                             'fecha que lo determine el Poder Ejecutivo, dentro de los 90 (noventa) días') for ln in L5)
    dec = [
        'Ley 2419/2004 (crea el Instituto Nacional de Desarrollo Rural y de la Tierra, INDERT; BACN 2273): promulgated '
        '15 July 2004, published 23 July 2004. Its art. 52, headed "VIGENCIA", only gives the Executive three months '
        'to appoint the Institute\'s president and board, so the law is in force the day after publication '
        '(2004-07-24). Its art. 50 rewrites art. 1 a) of Ley 1309/1998 and its art. 51 repeals Ley 852/1963; both '
        'stay here as its own text.',
        L4046.format(art='art. 25 of Ley 2419/2004 (recurso de reconsideración; acción contencioso-administrativa)'
                     ).replace(
            ' Ley 4798/2012 then rewrites it ("Modifícase ... queda redactado"): a re-enactment, so it returns from '
            '2013-01-04 with its new text, credited to Ley 4798.', ' No later law puts it back.').replace(
            'still lists the article: a restatement of the 2010 repeal, not a new one, so the re-enacted article stays',
            'still lists the article: a restatement of the 2010 repeal, not a new one, so no further change'),
        'Ley 2419/2004: held, with no day. Ley 5061/2013 (BACN 4738; promulgated 4 October 2013, published 8 October '
        '2013) art. 13 repeals incisos f) and g) of art. 27 and a) and b) of art. 35 (the Institute\'s and the FIDES\'s '
        'shares of the agricultural income tax and of the royalties). Its art. 14 '
        'puts the law in force "a partir de la fecha que lo determine el Poder Ejecutivo, dentro de los 90 (noventa) '
        'días contados a partir de su promulgación", and lets the Executive set different days for different '
        'provisions. The decree that set those days is not in BACN, so the day art. 13 took effect is not known from '
        'the source and the repeal is not applied: arts. 27 and 35 keep the four incisos here.',
        'Ley 2419/2004: BACN searches "2419", "2419/04", "2419/2004", "2.419", "Ley 2419", "INDERT" and "desarrollo '
        'rural y de la tierra". The other hits only cite the law or the Institute: expropriation, transfer and budget '
        'laws, and Ley 7424/2025 (registry), which sets duties for the Institute in its own articles.',
    ]
    return act(slug, 'INDERT', 'Ley N° 2419/2004 que crea el Instituto Nacional de Desarrollo Rural y de la Tierra',
               key, rp.build()), dec


# ------------------------------------------------------------------ Ley 7424/2025 Registro Unificado Nacional

def ley_7424_act():
    slug, key, pid = 'ley-registro-unificado-nacional', 'ley-7424-2025', '12672'
    url, L, frm = parse.ley_7424()        # the law record shared with the CPC, LOM and Estatuto Agrario parts
    assert frm == '2026-01-15', frm
    orig = actlib.lines

    def nested(p):                        # the page nests ordered lists: read it as parse.ley_7424 does
        return parse.nested_page_lines(url_of(p)) if p == pid else orig(p)

    orig_join = actlib.join_broken

    def join(paras, where):               # art. 142's table: items numbered value="50"/"1000" read "ax."/"all."
        out, chunk = [], []
        for p in paras:
            if p.startswith('all. ') and chunk:
                out += orig_join(chunk, where)
                chunk = []
            chunk.append(p)
        return out + orig_join(chunk, where) if chunk else out
    actlib.lines, actlib.join_broken = nested, join
    try:
        units = enacted(pid, slug, 5)
    finally:
        actlib.lines, actlib.join_broken = orig, orig_join
    t142 = units['art-142']['text']
    assert '\nax. Provisión de listado de inmuebles.\n' in t142 and '\nall. Provisión de copia autenticada' in t142
    v1 = first_version(key, pid, 'Ley N° 7424/2025', '', frm, units,
                       'The law as enacted, from its BACN page; in force 15 January 2026 (art. 187).')
    dec = [
        'Ley 7424/2025 (crea el Sistema Nacional Unificado Registral y Catastral y el Registro Unificado Nacional; '
        'BACN 12672): promulgated 9 January 2025, published 14 January 2025. Art. 187 puts it in force "a partir de '
        'la media noche del mismo día y mes del año siguiente al que se haya producido la referida publicación"; a '
        'year counted from the 14th ends at midnight of 14 January 2026 (Código Civil arts. 339 and 341), so the '
        'first version is dated 2026-01-15. Its arts. 188 and 189 set duties counted from that day (or six months '
        'before it); they are its own wording, not separate versions.',
        'Ley 7424/2025 art. 142 (tasas) is a table on BACN: each row is read as the item, then its amount, on the '
        'next line. List markers are kept as BACN\'s page draws them: in art. 142 the twelfth and thirteenth rows, '
        'and in art. 165 the twelfth and thirteenth incisos, carry list values 50 and 1000, so they read "ax." and '
        '"all." (not "l." and "m."); in art. 142 the row after "n." is a bullet with no letter. A paragraph is never '
        'joined to an "all." line.',
        'Ley 7424/2025: arts. 190-197 rewrite articles of other laws and art. 200 repeals provisions of other laws; '
        'they stay here as its own text. Where the other law is in this repository (Código Procesal Civil, Ley '
        'Orgánica Municipal, Estatuto Agrario) the change is also applied there, from the same day.',
        'Ley 7424/2025: BACN searches "7424", "7424/2025", "7424/25", "7.424", "Ley 7424", "registral y catastral", '
        '"Registro Unificado Nacional" and "Sistema Nacional Unificado Registral" find no law that changes its '
        'words; the other hits are municipal boundary laws whose coordinates contain the digits.',
    ]
    return act(slug, 'RUN', 'Ley N° 7424/2025 que crea el Sistema Nacional Unificado Registral y Catastral y el '
               'Registro Unificado Nacional', key, Replay(slug, units, v1).build()), dec


# ------------------------------------------------------------------ Ley 3239/2007 Recursos Hídricos

def ley_3239():
    pid = '2724'
    assert page_meta(url_of(pid)) == {'promulgated': '2007-07-10', 'published': '2007-07-10'}
    assert 'Artículo 55.- Deróganse las Leyes, Decretos y Resoluciones que se contrapongan a la presente Ley.' in \
        actlib.lines(pid)
    return single('ley-recursos-hidricos', 'LRH', 'Ley N° 3239/2007 de los Recursos Hídricos del Paraguay',
                  'ley-3239-2007', pid, 'Ley N° 3239/2007', 'DE LOS RECURSOS HIDRICOS DEL PARAGUAY', [
        'Ley 3239/2007 de los Recursos Hídricos del Paraguay (BACN 2724): BACN gives promulgation and publication '
        'both on 10 July 2007; the law has no vigencia clause, so it is in force the day after publication '
        '(2007-07-11). Its art. 53 sets terms counted from that day; they are its own wording, not versions.',
        'Ley 3239/2007: BACN searches "3239/07", "3239/2007", "3.239" and "recursos hídricos" find no law that '
        'changes its words. Ley 6123/2018 art. 3 makes the Ministerio del Ambiente y Desarrollo Sostenible its '
        'authority (art. 52 named the Secretaría del Ambiente "hasta tanto se defina el marco institucional") '
        'without changing its text; the other hits only cite it (protected areas, Chaco water, effluents, energy, '
        'aquaculture and treaty laws).',
    ])


# ------------------------------------------------------------------ Ley 96/1992 de Vida Silvestre

def ley_96():
    slug, key, pid = 'ley-vida-silvestre', 'ley-96-1992', '2391'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1992-12-11', 'published': None}, m
    orig = actlib.closing_index

    def closing(L):                       # the closing formula is printed in capitals ("APROBADA POR LA ...")
        com = max(i for i, ln in enumerate(L) if parse.GEN_ART.match(ln) and re.search(r'(?i)comun[ií]quese', ln))
        return next(i for i, ln in enumerate(L) if i > com and re.match(r'^(Aprobad[oa]|APROBAD[OA]|DADA|Dada) ', ln))
    actlib.closing_index = closing
    try:
        units = enacted(pid, slug, 5)
    finally:
        actlib.closing_index = orig
    L = actlib.lines(pid)
    assert sum(ln.startswith(('Art. 37.- Prohíbese, a partir de la promulgación', 'Art. 38.- Prohíbese, a partir de '
                              'la promulgación')) for ln in L) == 2
    assert any(ln.startswith('Art. 61.- Queda modificado el Inc. a) del Art. 2030 del Código Civil, en cuanto '
                             'contradiga lo dispuesto en la presente Ley') for ln in L)
    v1 = first_version(key, pid, 'Ley N° 96/1992', 'DE VIDA SILVESTRE', plus(m['promulgated'], days=1), units,
                       'The law as enacted, from its BACN page; BACN gives no publication date, so it is dated the '
                       'day after promulgation.')
    rp = Replay(slug, units, v1)
    url, frm = ley_4046('Artículo 16 de la Ley Nº 96/92 "DE VIDA SILVESTRE"')
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-016')
    dec = [
        'Ley 96/1992 de Vida Silvestre (BACN 2391): promulgated 11 December 1992; BACN gives no publication date and '
        'the law has no vigencia clause, so it is dated the day after promulgation (1992-12-12). Arts. 37 and 38 '
        'prohibit hunting, trade and keeping of wild fauna "a partir de la promulgación"; that is their own wording, '
        'not a separate version. BACN prints the closing formula in capitals.',
        L4046.format(art='art. 16 of Ley 96/1992 (powers of the wildlife inspectors)').replace(
            ' Ley 4798/2012 then rewrites it ("Modifícase ... queda redactado"): a re-enactment, so it returns from '
            '2013-01-04 with its new text, credited to Ley 4798.', ' No later law puts it back.').replace(
            'still lists the article: a restatement of the 2010 repeal, not a new one, so the re-enacted article stays',
            'still lists the article: a restatement of the 2010 repeal, not a new one, so no further change'),
        'Ley 96/1992 art. 61 changes other laws and stays here as its own text. Not applied to them: its first '
        'paragraph modifies inciso a) of Código Civil art. 2030 "en cuanto contradiga lo dispuesto en la presente '
        'Ley, quedando redactado en los términos del Art. 4º de esta Ley" (no replacement wording for the inciso), '
        'and its list b) repeals Ley 422/1973 (Forestal) art. 2 inciso g) "en lo que hace referencia a la caza '
        'únicamente" and art. 6 inciso d) and art. 12 inciso m) "en todo lo que concierne a la Vida Silvestre": '
        'repeals limited to a subject, which remove no definite words, so the Código Civil and the Ley Forestal '
        'keep those incisos as enacted.',
        'Ley 96/1992: BACN searches "96/92", "96/1992", "Ley 96", "vida silvestre" and "silvestre" (hits whose titles '
        'name a change or wildlife). Only Ley 4046/2010 changes its words. Ley 1561/2000 art. 14 makes the '
        'Secretaría del Ambiente its authority (art. 7 named the Dirección de Parques Nacionales y Vida Silvestre) '
        'without changing its text; the other hits only cite it (Leyes 1814/2001, 4631/2012, 5302/2014 and '
        '5875/2017).',
    ]
    return act(slug, 'LVS', 'Ley N° 96/1992 de Vida Silvestre', key, rp.build()), dec


# ------------------------------------------------------------------ Ley 4241/2010 Bosques Protectores

def ley_4241():
    pid = '2893'
    assert page_meta(url_of(pid)) == {'promulgated': '2010-12-20', 'published': '2010-12-22'}
    return single('ley-bosques-protectores', 'LBP', 'Ley N° 4241/2010 de Restablecimiento de Bosques Protectores de '
                  'Cauces Hídricos dentro del Territorio Nacional', 'ley-4241-2010', pid, 'Ley N° 4241/2010',
                  'DE RESTABLECIMIENTO DE BOSQUES PROTECTORES DE CAUCES HIDRICOS DENTRO DEL TERRITORIO NACIONAL', [
        'Ley 4241/2010 de Restablecimiento de Bosques Protectores de Cauces Hídricos (BACN 2893): promulgated 20 '
        'December 2010, published 22 December 2010, no vigencia clause, so in force the day after publication '
        '(2010-12-23). Its art. 18 exempts restoration projects from the procedure of Ley 294/1993 without changing '
        'that law\'s words; it stays here as its own text.',
        'Ley 4241/2010: BACN searches "4241", "4241/10", "4241/2010", "4.241", "bosques protectores" and "cauces '
        'hídricos" find no law that changes its words. The other hits only cite it: Leyes 7285/2024 and 7286/2024 '
        '(protected streams) apply its arts. 2, 4, 5 and 9; Leyes 4647, 5606 and 6911 (protected areas) set their '
        'own riverside strips.',
    ])


# ------------------------------------------------------------------ Ley 5428/2015 Efluentes Cloacales

def ley_5428():
    pid = '8189'
    assert page_meta(url_of(pid)) == {'promulgated': '2015-10-21', 'published': '2015-10-27'}
    return single('ley-efluentes-cloacales', 'LEC', 'Ley N° 5428/2015 de Efluentes Cloacales', 'ley-5428-2015', pid,
                  'Ley N° 5428/2015', 'DE EFLUENTES CLOACALES', [
        'Ley 5428/2015 de Efluentes Cloacales (BACN 8189): promulgated 21 October 2015, published 27 October 2015, '
        'no vigencia clause, so in force the day after publication (2015-10-28). Art. 14 gives the Executive ninety '
        'days from the day after promulgation to regulate it; that is its own wording, not a version.',
        'Ley 5428/2015: BACN searches "5428", "5428/15", "5428/2015", "5.428" and "efluentes cloacales" find no law '
        'that changes its words; the other hits are protected-area laws that forbid discharging effluents, Ley '
        '1614/2000 (water and sanitation services), and laws whose amounts or areas contain the digits.',
    ])


# ------------------------------------------------------------------ Ley 3956/2009 Residuos Sólidos

def ley_3956():
    slug, key, pid = 'ley-residuos-solidos', 'ley-3956-2009', '3208'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2009-12-24', 'published': '2009-12-28'}, m
    assert ('Artículo 45.- Esta Ley entrará en vigencia transcurridos 90 (noventa) días a partir de su promulgación, '
            'salvo en lo previsto en el artículo anterior.') in actlib.lines(pid)
    frm = plus(m['promulgated'], days=90)
    assert frm == '2010-03-24', frm
    v1 = first_version(key, pid, 'Ley N° 3956/2009', 'GESTION INTEGRAL DE LOS RESIDUOS SOLIDOS EN LA REPUBLICA DEL '
                       'PARAGUAY', frm, units,
                       'The law as enacted, from its BACN page; in force ninety days after promulgation (art. 45).')
    rp = Replay(slug, units, v1)
    k = 'ley-4188-2010'
    url, L, frm = bacn_law(k, '2877', 'Ley N° 4188/2010')
    assert frm == '2010-11-23', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícase el Artículo 44 de la Ley N° 3956/09', [44])
    k = 'ley-6488-2020'
    url, L, frm = bacn_law(k, '9105', 'Ley N° 6488/2020')
    assert frm == '2020-01-08', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1º\.- Modifícase el Artículo 27 de la Ley N° 3956/2009', [27])
    dec = [
        'Ley 3956/2009 de Gestión Integral de los Residuos Sólidos (BACN 3208): promulgated 24 December 2009, '
        'published 28 December 2009. Art. 45: "entrará en vigencia transcurridos 90 (noventa) días a partir de su '
        'promulgación, salvo en lo previsto en el artículo anterior", counted as ninety calendar days (2010-03-24), '
        'as for the other laws here with a term of days. The exception is art. 44 as enacted, which gives the '
        'municipalities six months from promulgation to regulate the law: a duty counted by its own words, not a '
        'separate version, so the first version holds the whole law from 2010-03-24.',
        'Ley 3956/2009: Ley 4188/2010 (published 22 November 2010, in force 23 November) rewrites art. 44 (the '
        'regulation is given to the Secretaría del Ambiente, six months from promulgation); Ley 6488/2020 (published '
        '7 January 2020, in force 8 January) rewrites art. 27 (imports of waste). Neither has a vigencia clause.',
        'Ley 3956/2009: BACN searches "3956", "3956/09", "3956/2009", "3.956", "Ley 3956", "residuos sólidos", '
        '"residuos solidos" and "gestión integral de los residuos". The other hits only cite it (Leyes 6562/2020, '
        '6925/2022 and 7014/2022 apply it; Ley 3361/2007 on health-care waste predates it) or contain the digits '
        'in amounts.',
    ]
    return act(slug, 'LGIRS', 'Ley N° 3956/2009 de Gestión Integral de los Residuos Sólidos en la República del '
               'Paraguay', key, rp.build()), dec


# ------------------------------------------------------------------ Ley 4050/2010 Acuicultura

def ley_4050():
    pid = '558'
    assert page_meta(url_of(pid)) == {'promulgated': '2010-08-10', 'published': '2010-08-11'}
    return single('ley-acuicultura', 'LDSA', 'Ley N° 4050/2010 del Desarrollo Sostenible de la Acuicultura',
                  'ley-4050-2010', pid, 'Ley N° 4050/2010', 'DEL DESARROLLO SOSTENIBLE DE LA ACUICULTURA', [
        'Ley 4050/2010 del Desarrollo Sostenible de la Acuicultura (BACN 558): promulgated 10 August 2010, published '
        '11 August 2010, no vigencia clause, so in force the day after publication (2010-08-12). Art. 5 lets the '
        'Executive set a ten-year term from promulgation for its incentive programmes; that is its own wording, not '
        'a version.',
        'Ley 4050/2010: BACN searches "4050", "4050/10", "4050/2010", "4.050", "acuicultura" and "desarrollo '
        'sostenible de la acuicultura" find no law that changes its words. Ley 7618/2025 (aquaculture licences) '
        'cites it in its own text and amends only Ley 3556/2008 (Pesca y Acuicultura, art. 31); the other hits only '
        'cite aquaculture or contain the digits in areas.',
    ])


# ------------------------------------------------------------------ Ley 3556/2008 de Pesca y Acuicultura

def ley_3556():
    slug, key, pid = 'ley-pesca-acuicultura', 'ley-3556-2008', '1088'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2008-08-07', 'published': '2008-08-12'}, m
    table = '(VER CUADRO DESCRIPTIVO - ADJUNTO PDF)'
    orig = actlib.heading_indices

    def heads(L, head_n, end):            # BACN's placeholder for art. 34's table is text of art. 34, not a heading
        return {i for i in orig(L, head_n, end) if L[i] != table}
    actlib.heading_indices = heads
    try:
        units = enacted(pid, slug, 5)
    finally:
        actlib.heading_indices = orig
    assert units['art-034']['text'].rstrip('\n').endswith('\n' + table), units['art-034']['text'][-200:]
    v1 = first_version(key, pid, 'Ley N° 3556/2008', 'DE PESCA Y ACUICULTURA', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-7618-2025'
    url, L, frm = bacn_law(k, '12937', 'Ley N° 7618/2025')
    assert frm == '2025-12-23', frm
    assert not any(re.search(r'(?i)vigencia', ln) for ln in L), 'Ley 7618 has a vigencia clause'
    set_arts(rp, frm, k, url, L, r'^Artículo 11\. Modifícase el artículo 31 de la Ley N° 3556/2008', [31])
    dec = [
        'Ley 3556/2008 de Pesca y Acuicultura (BACN 1088): promulgated 7 August 2008, published 12 August 2008, no '
        'vigencia clause, so in force the day after publication (2008-08-13). Its art. 57 repeals Ley 799/1996 (De '
        'Pesca), which is not in this repository.',
        'Ley 3556/2008 art. 34: the table of minimum fish sizes is not in BACN\'s text; the page prints "(VER CUADRO '
        'DESCRIPTIVO - ADJUNTO PDF)" in its place. That line is kept as the last line of art. 34 (not as a heading) '
        'and the table is left out rather than typed in.',
        'Ley 3556/2008: Ley 7618/2025 (licencia ambiental for exotic species in closed or semi-open waters; '
        'promulgated 19 December 2025, published 22 December 2025, no vigencia clause, so in force 23 December 2025) '
        'art. 11 rewrites art. 31.',
        'Ley 3556/2008: BACN searches "3556/08", "3556/2008", "3.556", "pesca y acuicultura", "7618" and "7618/2025". '
        'The other hits only cite it (protected-area laws, Ley 4050/2010 on aquaculture), are the repealed Ley '
        '799/1996 or a trade treaty, or contain the digits in amounts.',
    ]
    return act(slug, 'LPAC', 'Ley N° 3556/2008 de Pesca y Acuicultura', key, rp.build()), dec


# ------------------------------------------------------------------ Ley 7513/2025 de Bienestar y Protección Animal

def ley_7513():
    pid = '12783'
    assert page_meta(url_of(pid)) == {'promulgated': '2025-08-19', 'published': '2025-08-19'}
    L = actlib.lines(pid)
    assert any(ln.startswith('Artículo 75.- Deróganse las Leyes Nº 4840/2013') for ln in L)
    assert not any(re.search(r'(?i)entrar[áa] en vigencia|en vigor', ln) for ln in L)
    return single('ley-bienestar-animal', 'LBPA', 'Ley N° 7513/2025 de Bienestar y Protección Animal',
                  'ley-7513-2025', pid, 'Ley N° 7513/2025', 'DE BIENESTAR Y PROTECCIÓN ANIMAL', [
        'Ley 7513/2025 de Bienestar y Protección Animal (BACN 12783): BACN gives promulgation and publication both '
        'on 19 August 2025; the law has no vigencia clause, so it is in force the day after publication '
        '(2025-08-20). BACN prints its first heading "CAPÌTULO I" (with a grave accent); it is kept as printed.',
        'Ley 7513/2025 art. 75 repeals Ley 4840/2013 (Protección y Bienestar Animal) with its amending Leyes '
        '5892/2017 and 7364/2024. Ley 4840/2013 is not in this repository: Ley 7364/2024, which rewrote its arts. 32 '
        'and 38, is not on BACN, so its text from 2024 cannot be shown.',
        'Ley 7513/2025: BACN searches "7513", "7513/2025", "bienestar animal" and "bienestar y protección animal" '
        'find no law that changes its words. The other "7513" hits are municipal boundary laws whose coordinates '
        'contain the digits; the other "bienestar animal" hits are Ley 4840/2013 and Ley 5892/2017 (repealed by '
        'it), Ley 7221/2023 (animal identification), Ley 6810/2021 (veterinarians), a budget law, a land transfer '
        'and a national day.',
    ])


# ------------------------------------------------------------------ Ley 1630/2000 and Ley 868/1981 (DINAPI laws)

def state_before(rp: Replay, day: str) -> dict:
    """The units in force the day before `day`: the first version with every pending op dated earlier applied."""
    cur = dict(rp.versions[0]['units'])
    for frm in sorted(rp.pending):
        if frm >= day:
            break
        for kind, key, value, _ in rp.pending[frm]['ops']:
            if kind in ('set', 'add'):
                cur[key] = value
            elif kind == 'del':
                del cur[key]
            elif kind == 'fn':
                cur[key] = value(cur[key])
            else:
                raise AssertionError(kind)
    return cur


def rename_ip_office(rp: Replay, frm: str, key: str, url: str, skip: set[str]) -> list[str]:
    """Ley 4798/2012 art. 36 b): "Dirección de la Propiedad Industrial" becomes "Dirección General de Propiedad
    Industrial" in every article in force that holds those exact words, except the ones it rewrites or repeals."""
    old, new = 'Dirección de la Propiedad Industrial', 'Dirección General de Propiedad Industrial'
    cur = state_before(rp, frm)
    keys = [k for k in sorted(cur) if k.startswith('art-') and k not in skip and old in cur[k]['text']]
    for k in keys:
        rp.op(frm, key, url, 'fn', k, lambda u, o=old, n=new: dict(u, text=u['text'].replace(o, n)))
    return keys


QART_SP = re.compile(r'^"Art\.\s*(\d+)\s+(?=[A-ZÁÉÍÓÚ])(.*)$')     # Ley 2593/2005 prints '"Art. 23 De la ...'


def ley_1630():
    slug, key, pid = 'ley-patentes-invenciones', 'ley-1630-2000', '1709'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2000-11-29', 'published': '2000-11-29'}, m
    assert units['art-089']['text'] == ('# Artículo 89\nDe la vigencia. La presente ley entrará en vigencia dos meses '
                                        'después de su promulgación.\n'), units['art-089']['text']
    frm = plus(m['promulgated'], months=2)
    assert frm == '2001-01-29', frm
    v1 = first_version(key, pid, 'Ley N° 1630/2000', 'DE PATENTES DE INVENCIONES', frm, units,
                       'The law as enacted, from its BACN page; in force two months after promulgation (art. 89).')
    rp = Replay(slug, units, v1)
    k = 'ley-2047-2002'
    url, L, frm = bacn_law(k, '10046', 'Ley N° 2047/2002')
    assert frm == '2002-12-31', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modificase el Artículo 90 de la Ley N° 1630, del 29 de noviembre',
             [90])
    k = 'ley-2593-2005'
    url, L, frm = bacn_law(k, '4131', 'Ley N° 2593/2005')
    assert frm == '2005-07-09', frm
    seg = actlib.segment(L, r'^Artículo 1°\.- Modifícanse los Artículos 23, 25, 28, 38, 48, 70, 81 y 83 de la Ley Nº '
                            r'1630 del 29 de noviembre de 2000')
    blocks: list[tuple[int, list[str]]] = []
    for ln in seg:
        q = QART_SP.match(ln)
        if q:
            blocks.append((int(q.group(1)), [q.group(2)]))
        else:
            assert blocks, ln
            blocks[-1][1].append(ln)
    assert [n for n, _ in blocks] == [23, 25, 28, 38, 48, 70, 81, 83], [n for n, _ in blocks]
    for n, p in blocks:
        paras = parse.strip_quote(['"' + p[0]] + p[1:])
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, paras, k))
    assert any(ln.startswith('Artículo 2°.- Derogaciones. Deróganse el Artículo 75 de la Ley N° 1630 del 29 de '
                             'noviembre de 2000') for ln in L)
    rp.op(frm, k, url, 'del', 'art-075')
    url, frm = ley_4046('Artículo 65 de la Ley Nº 1.630/00 "DE PATENTES DE INVENCIONES"')
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-065')
    k = 'ley-4798-2012'
    url, L, frm = ley_4798()
    set_arts(rp, frm, k, url, L, r'^Artículo 39\.- Modifícanse los Artículos 63 y 85 de la Ley N° 1630/00', [63, 85])
    assert any(ln.startswith('Deróganse el Artículo 44 de la Ley Nº 868/81') and 'el Artículo 86 de la Ley N° 1630/00'
               in ln for ln in L)
    rp.op(frm, k, url, 'del', 'art-086')
    renamed = rename_ip_office(rp, frm, k, url, {'art-063', 'art-085', 'art-086'})
    dec = [
        'Ley 1630/2000 de Patentes de Invenciones (BACN 1709): promulgated and published 29 November 2000; art. 89 '
        '"La presente ley entrará en vigencia dos meses después de su promulgación": in force 2001-01-29. Art. 90 '
        'defers the patenting of pharmaceutical products to a later day (1 January 2005 after Ley 2047/2002); that is '
        'the law\'s own wording about what it covers, not a separate version.',
        'Ley 1630/2000: Ley 2047/2002 (published 30 December 2002, in force 31 December) rewrites art. 90; Ley '
        '2593/2005 (published 8 July 2005, in force 9 July) rewrites arts. 23, 25, 28, 38, 48, 70, 81 and 83 and '
        'repeals art. 75 (the same law repeals part of Código Penal art. 184). Ley 2593 prints each quoted article as '
        '"Art. 23 De la ..." without a full stop after the number; the words after the number are the text.',
        L4046.format(art='art. 65 of Ley 1630/2000').replace(
            ' Ley 4798/2012 then rewrites it ("Modifícase ... queda redactado"): a re-enactment, so it returns from '
            '2013-01-04 with its new text, credited to Ley 4798.', ' No later law puts it back.').replace(
            'still lists the article: a restatement of the 2010 repeal, not a new one, so the re-enacted article stays',
            'still lists the article: a restatement of the 2010 repeal, not a new one, so no further change'),
        DINAPI + ' For Ley 1630 it rewrites arts. 63 and 85 (art. 39) and repeals art. 86 (art. 41). Its art. 36 b) '
        'replaces the reference "Dirección de la Propiedad Industrial" in Ley 1630 "y sus modificaciones" with '
        '"Dirección General de Propiedad Industrial" "a los efectos del Capítulo IV de la presente Ley"; read as a '
        'textual change, as for Ley 1294/1998, and applied to those exact words in the articles in force that it did '
        f'not rewrite or repeal (arts. {nums(renamed)}). Variants such as "Dirección de Propiedad Industrial" '
        '(without "la") are left as printed. Headings are not changed.',
        'Ley 1630/2000: BACN searches "1630", "1630/00", "1630/2000", "1.630", "Ley 1630" and "patentes de '
        'invenciones". The other hits cite it without changing its words.',
    ]
    return act(slug, 'LPI', 'Ley N° 1630/2000 de Patentes de Invenciones', key, rp.build()), dec


def ley_868():
    slug, key, pid = 'ley-dibujos-modelos-industriales', 'ley-868-1981', '2561'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1981-10-02', 'published': '1981-11-02'}, m
    L = actlib.lines(pid)
    assert L[actlib.closing_index(L)].startswith('DADA EN LA SALA DE SESIONES DEL CONGRESO NACIONAL A LOS VEINTE Y DOS '
                                                 'DÍAS DEL MES DE OCTUBRE DEL AÑO UN MIL NOVECIENTOS OCHENTA Y UNO')
    assert not any(re.search(r'(?i)entrar[áa] en vigencia|en vigor', ln) for ln in L)
    law(key, label='Ley N° 868/1981', title='DE DIBUJOS Y MODELOS INDUSTRIALES', kind='law', enacted=None,
        published=m['published'], url=url_of(pid))
    v1 = first_version(key, pid, 'Ley N° 868/1981', 'DE DIBUJOS Y MODELOS INDUSTRIALES', plus(m['published'], days=1),
                       units, 'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    url, frm = ley_4046('el Artículo 28 de la Ley Nº 868/81 "DE DIBUJOS Y MODELOS INDUSTRIALES"')
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-028')
    k = 'ley-4798-2012'
    url, L, frm = ley_4798()
    changed = [9, 28, 29, 43]
    b = qblocks(L, r'^Modifícanse los Artículos 9°, 28, 29 y 43 de la Ley Nº 868/81')
    assert [n for n, _ in b] == changed, [n for n, _ in b]
    for n, paras in b:            # art. 28 was repealed by Ley 4046/2010: re-enacted here
        rp.op(frm, k, url, 'add' if n == 28 else 'set', f'art-{n:03d}', unit_of(n, paras, k))
    rp.op(frm, k, url, 'del', 'art-044')
    renamed = rename_ip_office(rp, frm, k, url, {f'art-{n:03d}' for n in changed + [44]})
    dec = [
        'Ley 868/1981 de Dibujos y Modelos Industriales (BACN 2561): sanctioned 22 October 1981 (its closing '
        'formula). BACN gives promulgation "02-10-1981", twenty days before the sanction, which is impossible, so no '
        'promulgation day is recorded; BACN\'s publication day, 2 November 1981, comes after the sanction and is '
        'used. The law has no vigencia clause, so it is in force the day after publication (1981-11-03).',
        L4046.format(art='art. 28 of Ley 868/1981'),
        DINAPI + ' For Ley 868 it rewrites arts. 9, 29 and 43, re-enacts art. 28 (art. 37) and repeals art. 44 '
        '(art. 41). Its art. 36 b) replaces the reference "Dirección de la Propiedad Industrial" with "Dirección '
        'General de Propiedad Industrial", read as a textual change as for Ley 1294/1998 and applied to those exact '
        f'words in the articles in force that it did not rewrite or repeal (arts. {nums(renamed) or "none"}). BACN '
        'prints "Dirección de la Propiedad Industria" (without the final l) in some articles; those words are not the '
        'ones the law names and are left as printed.',
        'Ley 868/1981: BACN searches "868", "868/81", "868/1981", "Ley 868" and "dibujos y modelos". Only Leyes '
        '4046/2010 (with its 2015 restatement) and 4798/2012 change its words; the other hits cite it or contain the '
        'digits in other numbers.',
        PRE1987.format(who='Ley 868/1981'),
    ]
    return act(slug, 'LDMI', 'Ley N° 868/1981 de Dibujos y Modelos Industriales', key, rp.build()), dec


# ------------------------------------------------------------------ Ley 1725/2001 Estatuto del Educador

def ley_1725():
    slug, key, pid = 'ley-estatuto-educador', 'ley-1725-2001', '769'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2001-09-13', 'published': '2001-09-17'}, m
    L = actlib.lines(pid)
    assert not any(re.search(r'(?i)entrar[áa] en vigencia|en vigor', ln) for ln in L)
    assert units['art-066']['text'].startswith('# Artículo 66\nDeróganse el Decreto Ley N° 6436')
    assert units['art-067']['text'] == '# Artículo 67\nComuníquese al Poder Ejecutivo.\n'
    v1 = first_version(key, pid, 'Ley N° 1725/2001', 'QUE ESTABLECE EL ESTATUTO DEL EDUCADOR',
                       plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-2059-2003'
    url, L, frm = bacn_law(k, '774', 'Ley N° 2059/2003')
    assert frm == '2003-01-24', frm
    b = qblocks(L, r'^Artículo 1º\.- Amplíase la Ley N° 1725 del 13 de setiembre de 2001')
    assert [n for n, _ in b] == [66, 67, 68], [n for n, _ in b]
    for n, paras in b:            # the enacted law already has arts. 66 (repeals) and 67 (Comuníquese)
        u = unit_of(n, paras, k)
        rp.op(frm, k, url, 'add', f'art-{n:03d}-ley-2059', dict(u, label=f'Art. {n} (Ley 2059/2003)'))
    url, frm = ley_4046('Artículo 58 de la Ley Nº 1.725/')   # 5456 prints "1725/01"
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-058')
    k = 'ley-4893-2013'
    url, L, frm = bacn_law(k, '1121', 'Ley N° 4893/2013')
    assert frm == '2013-04-12', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícanse y amplíanse los artículos 28 y 36 de la Ley Nº 1\.725/01',
             [28, 36])
    dec = [
        'Ley 1725/2001 que establece el Estatuto del Educador (BACN 769): promulgated 13 September 2001, published 17 '
        'September 2001, no vigencia clause, so in force the day after publication (2001-09-18). Art. 65 phases in '
        'the pay rules from 1 January of the year after promulgation, by five-year groups, and art. 62 gives '
        'unqualified staff five years to qualify; those terms are the law\'s own wording, not separate versions.',
        'Ley 1725/2001: Ley 2059/2003 (published 23 January 2003, in force 24 January) "amplía" the law "con la '
        'inclusión de los siguientes artículos", numbered 66, 67 and 68, but the enacted law already has an art. 66 '
        '(repeal of Decreto Ley 6436/1941 and Ley 416/1973) and an art. 67 ("Comuníquese al Poder Ejecutivo"). No '
        'article is replaced: the enacted ones stay art-066 and art-067, and the three added ones are keyed '
        'art-066-ley-2059 to art-068-ley-2059, labelled "Art. N (Ley 2059/2003)" and headed "# Artículo N" as the law '
        'prints them (the same scheme as the added transitional articles of the Código Electoral).',
        L4046.format(art='art. 58 of Ley 1725/2001').replace(
            ' Ley 4798/2012 then rewrites it ("Modifícase ... queda redactado"): a re-enactment, so it returns from '
            '2013-01-04 with its new text, credited to Ley 4798.', ' No later law puts it back.').replace(
            'still lists the article: a restatement of the 2010 repeal, not a new one, so the re-enacted article stays',
            'still lists the article: a restatement of the 2010 repeal, not a new one, so no further change'),
        'Ley 1725/2001: Ley 4893/2013 (published 11 April 2013, in force 12 April) rewrites arts. 28 and 36 (its '
        'title says the law was "modificado por la Ley Nº 2.059/03", which added articles but did not change these '
        'two).',
        'Ley 1725/2001: BACN searches "1725", "1725/01", "1725/2001", "1.725" and "estatuto del educador". The other '
        'hits cite it (budget laws) or are Código Civil art. 1725.',
    ]
    return act(slug, 'LEE', 'Ley N° 1725/2001 que establece el Estatuto del Educador', key, rp.build()), dec


# ------------------------------------------------------------------ Ley 2157/2003 INCOOP

def ley_2157():
    slug, key, pid = 'ley-incoop', 'ley-2157-2003', '2423'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2003-07-01', 'published': '2003-07-04'}, m
    L = actlib.lines(pid)
    assert not any(re.search(r'(?i)entrar[áa] en vigencia|en vigor', ln) for ln in L)
    v1 = first_version(key, pid, 'Ley N° 2157/2003', 'QUE REGULA EL FUNCIONAMIENTO DEL INSTITUTO NACIONAL DE '
                       'COOPERATIVISMO Y ESTABLECE SU CARTA ORGÁNICA', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    url, frm = ley_4046('Artículo 27 de la Ley Nº 2.157/03 "QUE REGULA EL FUNCIONAMIENTO')   # 5456: "DE COOPERATIVISMO"
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-027')
    dec = [
        'Ley 2157/2003 que regula el funcionamiento del Instituto Nacional de Cooperativismo (INCOOP) y establece su '
        'Carta Orgánica (BACN 2423): promulgated 1 July 2003, published 4 July 2003, no vigencia clause, so in force '
        'the day after publication (2003-07-05). Its art. 37 repeals provisions of Ley 438/1994 de Cooperativas, '
        'which that law\'s own history in this repository shows.',
        L4046.format(art='art. 27 of Ley 2157/2003 (administrative appeals against INCOOP acts)').replace(
            ' Ley 4798/2012 then rewrites it ("Modifícase ... queda redactado"): a re-enactment, so it returns from '
            '2013-01-04 with its new text, credited to Ley 4798.', ' No later law puts it back.').replace(
            'still lists the article: a restatement of the 2010 repeal, not a new one, so the re-enacted article stays',
            'still lists the article: a restatement of the 2010 repeal, not a new one, so no further change'),
        'Ley 2157/2003: BACN searches "2157", "2157/03", "2157/2003", "2.157", "INCOOP" and "instituto nacional de '
        'cooperativismo". Only Ley 4046/2010 changes its words. Ley 3472/2008 de Mutuales art. 94 keeps "las normas '
        'originarias de la Ley N° 2157/2003" applicable until its own council is elected, a transitional rule that '
        'changes no words; the other hits cite it or are Código Civil art. 2157.',
    ]
    return act(slug, 'LINCOOP', 'Ley N° 2157/2003 que regula el funcionamiento del Instituto Nacional de '
               'Cooperativismo y establece su Carta Orgánica', key, rp.build()), dec


# ------------------------------------------------------------------ Ley 426/1994 Carta Orgánica del Gobierno Departamental

def insert_after(prefix: str, new: str):
    """fn op: `new` becomes a line of its own right after the one line of an article that starts with `prefix`."""
    def f(u):
        ls = u['text'].split('\n')
        hits = [i for i, x in enumerate(ls) if x.startswith(prefix)]
        assert len(hits) == 1, (prefix, hits, u['text'][:200])
        ls.insert(hits[0] + 1, new)
        return dict(u, text='\n'.join(ls))
    return f


def ley_426():
    slug, key, pid = 'ley-carta-organica-departamental', 'ley-426-1994', '2533'
    orig = actlib.heading_indices
    epis: list[str] = []

    def heads(L, head_n, end):            # mixed-case epigraphs printed on their own line before an article
        extra = {i for i in range(head_n, end - 1) if not actlib.GEN_ART.match(L[i]) and actlib.GEN_ART.match(L[i + 1])
                 and len(L[i]) < 100 and not L[i].endswith(('.', ';', ':', ','))}
        epis.extend(L[i] for i in sorted(extra - orig(L, head_n, end)))
        return orig(L, head_n, end) | extra
    actlib.heading_indices = heads
    try:
        units = enacted(pid, slug, 5)
    finally:
        actlib.heading_indices = orig
    assert len(epis) == 30 and epis[0] == 'Los Departamentos. Caracterización' and epis[-1] == 'Disposición Final', epis
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1994-12-07', 'published': None}, m
    L = actlib.lines(pid)
    assert not any(re.search(r'(?i)entrar[áa] en vigencia|en vigor', ln) for ln in L)
    assert len([k for k in units if k.startswith('art-')]) == 53
    v1 = first_version(key, pid, 'Ley N° 426/1994', 'QUE ESTABLECE LA CARTA ORGÁNICA DEL GOBIERNO DEPARTAMENTAL',
                       plus(m['promulgated'], days=1), units,
                       'The law as enacted, from its BACN page; BACN gives no publication date, so it is dated the '
                       'day after promulgation.')
    rp = Replay(slug, units, v1)
    k = 'ley-643-1995'
    url, L, frm = bacn_law(k, '11550', 'Ley N° 643/1995')
    assert frm == '1995-08-23', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1o\.- Modifícase el Artículo 38 de la Ley No\. 426 del 7 de diciembre de '
             r'1994', [38])
    k = 'ley-2862-2006'
    url, L, frm = bacn_law(k, '1945', 'Ley N° 2862/2006')
    assert frm == '2006-01-11', frm
    b = dict(qblocks(L, r'^Artículo 1°\.- Modifícanse y amplíanse los Artículos 17, inciso k\); 20, incisos b\), d\), '
                        r'g\), h\), k\) y l\); 27; 36; y 50 de la Ley N° 426/94'))
    assert sorted(b) == [17, 20, 27, 36, 50], sorted(b)
    # arts. 17 and 20: the law quotes each article's opening words (unchanged) and only the incisos it rewrites or adds
    for n, lead, incs, added in ((17, 'Son deberes y atribuciones del Gobernador:', ['k)'], ['x)']),
                                 (20, 'Son deberes y atribuciones de la Junta Departamental:',
                                  ['b)', 'd)', 'g)', 'h)', 'k)', 'l)'], [])):
        paras = b[n]
        assert paras[0] == lead and units[f'art-{n:03d}']['text'].startswith(f'# Artículo {n}\n{lead}\n'), paras[0]
        assert [p.split(' ')[0] for p in paras[1:]] == incs + added, paras
        for p in paras[1:]:
            inc = p.split(' ')[0]
            if inc in added:          # 17 x) follows the last enacted inciso, w)
                rp.op(frm, k, url, 'fn', f'art-{n:03d}', insert_after('w) ', p))
            else:
                rp.op(frm, k, url, 'fn', f'art-{n:03d}', actlib.replace_line(inc + ' ', p))
    for n in (27, 36, 50):
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, b[n], k))
    url, frm = ley_4046('Ley Nº 426/94 "QUE ESTABLECE LA CARTA ORGÁNICA DEL GOBIERNO DEPARTAMENTAL"')
    assert any('Artículo 7º de la Ley Nº 426/94 "QUE ESTABLECE LA CARTA' in ln for ln in actlib.lines('554'))
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-007')
    k = 'ley-3668-2008'
    url, L, frm = bacn_law(k, '1848', 'Ley N° 3668/2008')
    assert frm == '2008-12-13', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícase el Artículo 50 de la Ley Nº 426/94', [50])
    k = 'ley-6565-2020'
    url, L, frm = bacn_law(k, '9295', 'Ley N° 6565/2020')
    assert frm == '2020-07-11', frm
    i = next(j for j, ln in enumerate(L) if ln.startswith('Artículo 1.° Modifícase el artículo 13 de la Ley N° 426/1994'))
    # the quotation opens with the article's epigraph, unchanged and kept in indice.md: read from "Art. 13." on
    assert L[i + 1] == '"Sustitución del Gobernador' and 'art-013: Sustitución del Gobernador' in units['indice']['text']
    L2 = L[:i + 1] + ['"' + L[i + 2]] + L[i + 3:]
    set_arts(rp, frm, k, url, L2, r'^Artículo 1\.° Modifícase el artículo 13 de la Ley N° 426/1994', [13])
    dec = [
        'Ley 426/1994 que establece la Carta Orgánica del Gobierno Departamental (BACN 2533): sanctioned 8 September '
        '1994 (its closing formula), promulgated 7 December 1994; BACN gives no publication date and the law has no '
        'vigencia clause, so it is dated the day after promulgation (1994-12-08). Art. 51 (members elected for '
        '1993/1998) is the law\'s own transitional wording, not a separate version. It is a different law from Ley '
        '426/1973 (división política del territorio), whose amending laws (Leyes 1716, 2244, 3673, 4630, 5328) are '
        'not this law\'s.',
        'Ley 426/1994 prints most articles\' epigraphs ("Asiento del Gobierno Departamental", "Sustitución del '
        'Gobernador", "Disposición Final" ...) in mixed case on a line of their own before the article. A line right '
        'before an article that is under 100 characters and does not end in a full stop, semicolon, colon or comma '
        'is read as a heading and goes to indice.md with the other headings (30 lines); the four longer lines before '
        'an article that end in a full stop are the previous article\'s last paragraph.',
        'Ley 426/1994: Ley 643/1995 (promulgated 22 August 1995; BACN gives no publication date, so in force the day '
        'after promulgation) rewrites art. 38. Ley 3668/2008 (published 12 December 2008, in force 13 December) '
        'rewrites art. 50. Ley 6565/2020 (published 10 July 2020, in force 11 July) rewrites art. 13; its quotation '
        'opens with the article\'s epigraph "Sustitución del Gobernador", unchanged, which stays in indice.md.',
        'Ley 426/1994: Ley 2862/2006 (promulgated and published 10 January 2006, in force 11 January) "modifícanse y '
        'amplíanse" arts. 17 inciso k), 20 incisos b), d), g), h), k) and l), 27, 36 and 50. For arts. 17 and 20 it '
        'quotes each article\'s opening words, unchanged, and then only the incisos it rewrites: those incisos are '
        'replaced line by line and the other incisos stay as enacted. It also quotes a new inciso x) under art. 17, '
        'after the last enacted inciso w); it is added after w), and the connective "y," at the end of inciso v) '
        'stays as printed. Arts. 27, 36 and 50 are rewritten whole (art. 50 again by Ley 3668/2008).',
        L4046.format(art='art. 7 of Ley 426/1994 (appeals against acts of the departmental government)').replace(
            ' Ley 4798/2012 then rewrites it ("Modifícase ... queda redactado"): a re-enactment, so it returns from '
            '2013-01-04 with its new text, credited to Ley 4798.', ' No later law puts it back.').replace(
            'still lists the article: a restatement of the 2010 repeal, not a new one, so the re-enacted article stays',
            'still lists the article: a restatement of the 2010 repeal, not a new one, so no further change'),
        'Ley 426/1994: BACN searches "426/94", "426/1994", "Ley 426", "Ley N° 426", "2862", "643/95", "carta '
        'orgánica del gobierno departamental", "gobierno departamental", "gobiernos departamentales" and "juntas '
        'departamentales". Only Leyes 643/1995, 2862/2006, 3668/2008, 4046/2010 (with its 2015 restatement) and '
        '6565/2020 change its words. The yearly budget laws cite Leyes 643/1995 and 3668/2008 to apply them, and '
        'Ley 6185/2018 approves staff changes to comply with art. 11; none changes the wording.',
    ]
    return act(slug, 'LCOGD', 'Ley N° 426/1994 que establece la Carta Orgánica del Gobierno Departamental', key,
               rp.build()), dec


# ------------------------------------------------------------------ Ley 642/1995 de Telecomunicaciones

def lettered(n: int, letter: str, paras: list[str], where: str) -> dict:
    """An article numbered with a letter ("Art. 100a"): key art-NNN-x, label "Art. NNNx" (as Código Penal art. 129b)."""
    u = unit_of(n, paras, where)
    assert u['text'].startswith(f'# Artículo {n}\n'), u['text'][:40]
    return dict(u, label=f'Art. {n}{letter}', text=u['text'].replace(f'# Artículo {n}\n', f'# Artículo {n}{letter}\n', 1))


def ley_642():
    slug, key, pid = 'ley-telecomunicaciones', 'ley-642-1995', '2452'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1995-12-29', 'published': None}, m
    L = actlib.lines(pid)
    assert not any(re.search(r'(?i)entrar[áa] en vigencia|en vigor', ln) for ln in L)
    assert len([k for k in units if k.startswith('art-')]) == 139
    v1 = first_version(key, pid, 'Ley N° 642/1995', 'DE TELECOMUNICACIONES', plus(m['promulgated'], days=1), units,
                       'The law as enacted, from its BACN page; BACN gives no publication date, so it is dated the '
                       'day after promulgation.')
    rp = Replay(slug, units, v1)

    # Ley 2478/2004 and its same-day rectification Ley 2495/2004: arts. 12 inciso c), 73 inciso b), 131
    k1, k2 = 'ley-2478-2004', 'ley-2495-2004'
    url1, L1, frm = bacn_law(k1, '3689', 'Ley N° 2478/2004')
    assert frm == '2004-10-23', frm
    m2 = page_meta(url_of('3688'))
    assert m2 == {'promulgated': '2004-10-15', 'published': '2014-10-22'}, m2
    url2, L2, frm2 = bacn_law(k2, '3688', 'Ley N° 2495/2004', in_force=frm)
    LAWS[k2]['published'] = '2004-10-22'      # BACN's "2014" read as a typo for 2004 (decision)
    leads = {12: 'Los miembros de la Comisión Nacional de Telecomunicaciones cesarán en sus cargos por:',
             73: 'Las concesiones, licencias y autorizaciones otorgadas de acuerdo con la presente Ley tendrán un plazo '
                 'mínimo de:'}
    rect: dict[str, object] = {}         # Ley 2495's wording, applied in a same-day version after Ley 2478's
    for k, url, LL, intro in (
            (k1, url1, L1, r'^Artículo 1º\.- Modifícanse los Artículos 12, inciso c\); 73, inciso b\) y 131 de la Ley N° '
                           r'642/95'),
            (k2, url2, L2, r'^"Artículo 1º\.- Modifícanse los Artículos 12, inciso c\); 73, inciso b\) y 131 de la Ley '
                           r'N° 642/95')):
        b = qblocks(LL, intro)
        assert [n for n, _ in b] == [12, 73, 131], [n for n, _ in b]
        for n, paras in b[:2]:        # each quotes the article's lead line, then only the inciso it rewrites
            inc = 'c)' if n == 12 else 'b)'
            assert paras[0] == leads[n] and len(paras) == 2 and paras[1].startswith(inc + ' '), paras
            if k == k1:
                rp.op(frm, k, url, 'fn', f'art-{n:03d}', actlib.replace_line(inc + ' ', paras[1]))
            else:
                rect[f'art-{n:03d}'] = actlib.replace_line(inc + ' ', paras[1])
        if k == k1:
            rp.op(frm, k, url, 'set', 'art-131', unit_of(131, b[2][1], k))
        else:
            rect['art-131'] = unit_of(131, b[2][1], k)
    assert units['art-012']['text'].startswith('# Artículo 12\n' + leads[12] + '\n')
    assert units['art-073']['text'].startswith('# Artículo 73\nLas concesiones, licencias y autorizaciones otorgadas '
                                               'de acuerdo a la presente ley tendrán un plazo máximo de:\n')

    url, frm = ley_4046('Artículo 119 de la Ley Nº 642/95 "DE TELECOMUNICACIONES"')
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-119')

    # Ley 4179/2011: arts. 57, 58, 70, 73 rewritten; art. 100 restated as "Art. 100a" with a new "Art. 100b"
    k = 'ley-4179-2011'
    m4 = page_meta(url_of('3601'))
    assert m4 == {'promulgated': '2010-03-28', 'published': '2010-03-30'}, m4
    url, L, frm = bacn_law(k, '3601', 'Ley N° 4179/2011', in_force='2011-03-31', promulgated='2011-03-28',
                           why='BACN\'s day and month with the year 2011: its 2010 dates precede the law\'s own '
                               'sanction (28 October 2010) and the override of the veto (8 March 2011)')
    LAWS[k]['published'] = '2011-03-30'
    cl = L[actlib.closing_index(L)]
    assert 'veintiocho días del mes de octubre del año dos mil diez' in cl and 'el ocho de marzo de 2011' in cl, cl
    intro = r'^Artículo 1°\.- Modifícanse y Amplíanse los Artículos 57, 58, 70, 73 y 100 de la Ley Nº 642/95'
    seg = actlib.segment(L, intro)
    ia = next(i for i, ln in enumerate(seg) if ln.startswith('"Art. 100a.- '))
    ib = next(i for i, ln in enumerate(seg) if ln.startswith('"Art. 100b.- '))
    head = [ln for ln in L if re.search(intro, ln)]
    b = qblocks(L[:L.index(head[0]) + 1] + seg[:ia], intro)
    assert [n for n, _ in b] == [57, 58, 70, 73], [n for n, _ in b]
    for n, paras in b:
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, paras, k))
    pa = parse.strip_quote([seg[ia][len('"Art. 100a.- '):]] + seg[ia + 1:ib])
    pb = parse.strip_quote([seg[ib][len('"Art. 100b.- '):]] + seg[ib + 1:])
    rp.op(frm, k, url, 'del', 'art-100')
    rp.op(frm, k, url, 'add', 'art-100-a', lettered(100, 'a', pa, k))
    rp.op(frm, k, url, 'add', 'art-100-b', lettered(100, 'b', pb, k))
    assert any(ln.startswith('Artículo 2°.- Quedan derogadas todas las disposiciones contrarias') for ln in L)

    k = 'ley-4478-2011'
    url, L, frm = bacn_law(k, '3686', 'Ley N° 4478/2011')
    assert frm == '2011-10-28', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícase el Artículo 34 de la Ley N° 642/95', [34])
    k = 'ley-5177-2014'
    url, L, frm = bacn_law(k, '2953', 'Ley N° 5177/2014')
    assert frm == '2014-05-09', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Amplíase el artículo 93 de la Ley N° 642/95', [93])

    L6 = actlib.lines('8933')
    assert any(ln.startswith('A partir de la entrada en vigencia de la presente ley, las relaciones de la Comisión '
                             'Nacional de Telecomunicaciones (CONATEL) con el Poder Ejecutivo, se canalizarán a través '
                             'del Ministerio en sustitución del Ministerio de Obras Públicas y Comunicaciones, según lo '
                             'establecido en el artículo 6° de la Ley N° 642/1995') for ln in L6)
    L7 = actlib.lines('12913')
    assert any('Título XI "RÉGIMEN DE SANCIONES" de la Ley N° 642/1995' in ln for ln in L7)
    dec = [
        'Ley 642/1995 de Telecomunicaciones (BACN 2452): sanctioned 27 July 1995 (BACN\'s record of the bill), '
        'promulgated 29 December 1995; BACN gives no publication date and the law has no vigencia clause, so it is '
        'dated the day after promulgation (1995-12-30). Its terms counted from promulgation or from its vigencia '
        '(arts. 130, 131, 133, 135, 136) are the law\'s own wording, not separate versions.',
        'Ley 642/1995: Ley 2478/2004 (promulgated 14 October 2004, published 22 October 2004, in force 23 October) '
        'rewrites art. 12 inciso c), art. 73 inciso b) and art. 131. For arts. 12 and 73 it quotes the article\'s '
        'lead line and then only the inciso it rewrites; only that inciso is replaced. Its quoted lead of art. 73 '
        'reads "de acuerdo con la presente Ley tendrán un plazo mínimo de", where the enacted art. 73 reads "de '
        'acuerdo a la presente ley tendrán un plazo máximo de"; the law names only inciso b), so the lead line stays '
        'as enacted until Ley 4179 rewrites the whole article.',
        'Ley 642/1995: Ley 2495/2004 "rectifica el error material" of Ley 2478 and reproduces its art. 1 in full, '
        'with "período" for "periodo" in art. 73 inciso b) and "Radiodifusión Sonora, Televisión y Radiodistribución '
        'Televisiva" in art. 131. It was promulgated on 15 October 2004, the day after Ley 2478; BACN gives its '
        'publication as "22-10-2014", ten years later and after Ley 4179 had rewritten art. 73 whole, while Ley 2478 '
        'was published on 22 October 2004. The year is taken as a typo (published 2004-10-22, which the law record '
        'carries), so both laws take effect on 2004-10-23. That day has two versions: Ley 2478\'s own wording, then '
        '(same_day) Ley 2495\'s rectified wording of art. 73 inciso b) and art. 131, credited to Ley 2495; its art. 12 '
        'inciso c) is the same as Ley 2478\'s and changes nothing.',
        L4046.format(art='art. 119 of Ley 642/1995 (the deadline for the contencioso-administrativo action against '
                     'CONATEL resolutions)').replace(
            ' Ley 4798/2012 then rewrites it ("Modifícase ... queda redactado"): a re-enactment, so it returns from '
            '2013-01-04 with its new text, credited to Ley 4798.', ' No later law puts it back.').replace(
            'still lists the article: a restatement of the 2010 repeal, not a new one, so the re-enacted article stays',
            'still lists the article: a restatement of the 2010 repeal, not a new one, so no further change'),
        'Ley 642/1995: Ley 4179 (BACN 3601) "modifícanse y amplíanse" arts. 57, 58, 70, 73 and 100. It was sanctioned '
        'on 28 October 2010, vetoed by Decreto 5403 of 11 November 2010, and the veto was overridden on 9 December '
        '2010 and 8 March 2011 (its closing formula). BACN dates its promulgation 28 March 2010 and its publication '
        '30 March 2010, before the sanction, which is impossible; the day and month are kept and the year is read as '
        '2011 (the rule used for Ley 5508/2015): promulgated 2011-03-28, published 2011-03-30 (the law record carries '
        'it), in force 2011-03-31. It rewrites arts. 57, 58, 70 and 73 whole. For art. 100 it prints "Art. 100a" '
        '(the enacted art. 100, reworded) and a new "Art. 100b" (fines for unlicensed broadcasting): art. 100 is '
        'removed and the two articles are added as art-100-a and art-100-b, labelled "Art. 100a" and "Art. 100b" '
        '(as the Código Penal\'s art. 129b). Its art. 2 repeals "todas las disposiciones contrarias" and names none.',
        'Ley 642/1995: Ley 4478/2011 (published 27 October 2011, in force 28 October) rewrites art. 34; Ley 5177/2014 '
        '(published 8 May 2014, in force 9 May) "amplía" art. 93 by restating it whole with a new inciso h) on mobile '
        'credit.',
        'Ley 642/1995: two later laws refer to it without changing its words. Ley 6207/2018 (creates the Ministerio de '
        'Tecnologías de la Información y Comunicación) art. 26: CONATEL\'s relations with the Executive go through '
        'that Ministry "en sustitución del Ministerio de Obras Públicas y Comunicaciones, según lo establecido en el '
        'artículo 6° de la Ley N° 642/1995"; art. 6 is not rewritten, so its text stays as enacted. Ley 7549/2025 '
        '(retention of traffic data) applies the sanctions of Título XI of Ley 642 to its own obligations. Ley '
        '1932/2002 suspends Ley 1615/2000 until, among other things, "la promulgación de las modificaciones de la Ley '
        'N° 642/95"; neither changes its words.',
        'Ley 642/1995: BACN searches "642", "642/95", "642/1995", "Ley 642", "Ley N° 642", "telecomunicaciones", '
        '"Comisión Nacional de Telecomunicaciones", "CONATEL", "2478", "2495", "4179", "4478", "5177", "6207", '
        '"6207/2018", "7549" and "7549/2025". Only Leyes 2478/2004, 2495/2004, 4046/2010 (with its 2015 '
        'restatement), 4179/2011, 4478/2011 and 5177/2014 change its words; the other hits cite it (loan and budget '
        'laws, a concession contract) or contain the digits in amounts.',
    ]
    vs = rp.build()
    i = next(j for j, v in enumerate(vs) if v['from'] == '2004-10-23')
    before = vs[i]['units']
    after = dict(before)
    for uk, f in rect.items():
        after[uk] = f if isinstance(f, dict) else f(before[uk])
    assert after['art-012'] == before['art-012']          # Ley 2495 reproduces 12 c) unchanged
    changed = sorted(uk for uk in rect if after[uk] != before[uk])
    assert changed == ['art-073', 'art-131'], changed
    MISMATCHES.append(f'{slug}/art-012: ley-2495-2004 restates the text in force; no change')
    vs.insert(i + 1, {'from': '2004-10-23', 'same_day': True, 'source_url': url2, 'sha256': parse.sha(url2),
                      'units': after, 'credits': {uk: [k2] for uk in changed}})
    for v in vs[i + 2:]:          # later versions carry Ley 2495's wording until a law rewrites the article
        for uk in changed:
            if v['units'].get(uk) == before[uk]:
                v['units'] = dict(v['units'], **{uk: after[uk]})
    return act(slug, 'LTEL', 'Ley N° 642/1995 de Telecomunicaciones', key, vs), dec


# ------------------------------------------------------------------ Ley 904/1981 Estatuto de las Comunidades Indígenas

def ley_904():
    slug, key, pid = 'ley-comunidades-indigenas', 'ley-904-1981', '2400'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1981-12-10', 'published': '1981-12-18'}, m
    assert len([k for k in units if k.startswith('art-')]) == 76
    v1 = first_version(key, pid, 'Ley N° 904/1981', 'ESTATUTO DE LAS COMUNIDADES INDÍGENAS', plus(m['published'], days=1),
                       units, 'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    # Ley 919/1996: arts. 30, 31, 62 and 71 whole; art. 63 only its inciso d) (the quoted lead line is the enacted one)
    k = 'ley-919-1996'
    url, L, frm = bacn_law(k, '10878', 'Ley N° 919/1996')
    assert frm == '1996-08-01', frm
    intro = r'^Artículo 1°\.- Modifícanse y amplíanse los artículos 30, 31, 62, 63 inciso d\) y 71 de la Ley N° 904'
    head = next(ln for ln in L if re.search(intro, ln))
    seg = actlib.segment(L, intro)
    i63 = next(i for i, ln in enumerate(seg) if ln.startswith('"Art. 63.-'))
    assert seg[i63] == '"Art. 63.- Son funciones del Síndico:', seg[i63]
    assert units['art-063']['text'].split('\n')[1] == 'Son funciones del Síndico:'
    inc_d = seg[i63 + 1]
    assert inc_d.startswith('Inc. d) Presentar un informe anual'), inc_d
    new_d = inc_d[len('Inc. '):]
    whole = [head] + seg[:i63] + seg[i63 + 2:]      # the quoted whole articles, without art. 63's two lines
    set_arts(rp, frm, k, url, whole, intro, [30, 31, 62, 71])
    rp.op(frm, k, url, 'fn', 'art-063', actlib.replace_line('d) Presentar un informe anual', new_d))
    # Ley 2199/2003 art. 11: arts. 34 and 37-44 repealed, arts. 33, 36 and 45 rewritten (the Council is abolished)
    k = 'ley-2199-2003'
    url, L, frm = bacn_law(k, '940', 'Ley N° 2199/2003')
    assert frm == '2003-09-11', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 11\.- Deróganse los Artículos 34, 37, 38, 39, 40, 41, 42, 43 y 44 y '
             r'modifícanse los Artículos 33, 36 y 45 de la Ley N° 904/81', [33, 36, 45])
    for n in (34, 37, 38, 39, 40, 41, 42, 43, 44):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    dec = [
        'Ley 904/1981 Estatuto de las Comunidades Indígenas (BACN 2400): promulgated 10 December 1981, published 18 '
        'December 1981 (the date Ley 919/1996 gives it), no vigencia clause, so in force the day after publication '
        '(1981-12-19), as for the other laws here.',
        'Ley 904/1981: Ley 919/1996 (BACN 10878; promulgated 31 July 1996, no publication date, so in force the day '
        'after promulgation, 1996-08-01) rewrites arts. 30, 31, 62 and 71 (relations with the Executive through the '
        'Ministerio de Educación y Culto instead of Defensa Nacional) and only inciso d) of art. 63: that line is '
        'replaced and the article\'s other lines are kept; the law prints it as "Inc. d) ...", kept here as "d) ..." '
        'like the other incisos of the article.',
        'Ley 904/1981: Ley 2199/2003 (BACN 940; published 10 September 2003, in force 11 September) art. 11 '
        'reorganises the INDI\'s management: it repeals arts. 34 and 37 to 44 (the Council) and rewrites arts. 33, '
        '36 and 45 (a President alone). Other articles that still name the Council (for example arts. 31, 35 and 71) keep '
        'their words: Ley 2199 does not change them.',
        'Ley 904/1981: BACN searches "904/81", "904/1981", "Ley 904", "Ley N° 904", "comunidades indígenas", '
        '"estatuto de las comunidades", "919/96", "919/1996", "Ley 919" and "Instituto Paraguayo del Indígena", '
        'screened for a modifying formula naming it: only Leyes 919/1996 and 2199/2003 change its words. Hits for '
        'Ley 904/1963 (Ministerio de Industria y Comercio, amended by Leyes 2961/2006 and 5289/2014) are a different '
        'law with the same number; Ley 1561/2000 (Secretaría del Ambiente) and loan law 540 only cite it.',
        PRE1987.format(who='Ley 904/1981'),
    ]
    return act(slug, 'LECI', 'Ley N° 904/1981 Estatuto de las Comunidades Indígenas', key, rp.build()), dec


# ------------------------------------------------------------------ Ley 3361/2007 Residuos de establecimientos de salud

def ley_3361():
    pid = '3414'
    assert page_meta(url_of(pid)) == {'promulgated': '2007-11-19', 'published': '2007-11-21'}
    L = actlib.lines(pid)
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor', ln) for ln in L)
    return single('ley-residuos-establecimientos-salud', 'LRES', 'Ley N° 3361/2007 de Residuos generados en los '
                  'Establecimientos de Salud y Afines', 'ley-3361-2007', pid, 'Ley N° 3361/2007',
                  'DE RESIDUOS GENERADOS EN LOS ESTABLECIMIENTOS DE SALUD Y AFINES', [
        'Ley 3361/2007 de Residuos generados en los Establecimientos de Salud y Afines (BACN 3414): promulgated 19 '
        'November 2007, published 21 November 2007, no vigencia clause, so in force the day after publication '
        '(2007-11-22). Art. 50 gives the Executive ninety days from promulgation to regulate it; that is its own '
        'wording, not a version. Art. 53\'s glossary is kept as the text of art. 53.',
        'Ley 3361/2007: BACN searches "3361", "3361/07", "3361/2007", "3.361", "Ley 3361", "Ley N° 3361", '
        '"establecimientos de salud", "residuos generados en los establecimientos" and "residuos hospitalarios", '
        'screened for a modifying formula naming it, find no law that changes its words; the hits only cite it or '
        'contain the digits in numbers. Ley 3956/2009 on solid waste does not amend it.',
    ])


# ------------------------------------------------------------------ Ley 5810/2017 Mercado de Valores (repealed 2025)

def ley_5810():
    slug, key, pid = 'ley-mercado-valores', 'ley-5810-2017', '9710'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2017-07-18', 'published': '2017-07-25'}, m
    assert len([k for k in units if k.startswith('art-')]) == 234
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor|empezar[aá] a regir', ln)
                   for ln in actlib.lines(pid))
    v1 = first_version(key, pid, 'Ley N° 5810/2017', 'MERCADO DE VALORES', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-7162-2023'
    url, L, frm = bacn_law(k, '11931', 'Ley N° 7162/2023')
    assert 'Artículo 17.º La presente ley empezará a regir a partir del día siguiente de su publicación.' in L
    assert frm == '2023-09-02', frm
    assert ('Artículo 18.º Deróguense los artículos 164, 166, 169, 170, 171, 172, 173, 174, 175, y 176 de la Ley N° '
            '5.810/2017 "MERCADO DE VALORES", y todas las disposiciones que sean contrarias a la presente ley.') in L
    for n in (164, 166, 169, 170, 171, 172, 173, 174, 175, 176):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    k = 'ley-7572-2025'
    url, L, frm = bacn_law(k, '12910', 'Ley N° 7572/2025')
    assert frm == '2025-11-08', frm
    i = L.index('Artículo 328.- Entrada en vigor.')
    assert L[i + 1] == 'La presente ley entrará en vigor al día siguiente de su publicación.'
    i = L.index('Artículo 329.- Derogaciones.')
    assert L[i + 1].startswith('Derógase la Ley N° 7162/2023 ') and '; la Ley N° 5810/2017 "MERCADO DE VALORES";' in L[i + 1]
    n0 = len(MISMATCHES)
    whole = rp.build()[-1]['units']   # every unit in force the day before the repeal (a dry run)
    del MISMATCHES[n0:]
    for u in sorted(whole):
        rp.op(frm, k, url, 'del', u)
    versions = rp.build()
    assert versions[-1]['units'] == {} and versions[-1]['from'] == '2025-11-08'
    dec = [
        'Ley 5810/2017 Mercado de Valores (BACN 9710): promulgated 18 July 2017, published 25 July 2017, no vigencia '
        'clause, so in force the day after publication (2017-07-26). The page prints "TÍTULO X" twice and no TÍTULO '
        'IX; the headings are kept as printed in indice.md.',
        'Ley 5810/2017: Ley 7162/2023 (BACN 11931; published 1 September 2023, in force the next day by its art. 17) '
        'creates the Superintendencia de Valores of the Banco Central del Paraguay in place of the Comisión Nacional '
        'de Valores and its art. 18 repeals arts. 164, 166 and 169 to 176 (the Commission\'s status and board), '
        'removed from 2023-09-02. Its art. 7 passes every reference to the Commission to the Banco Central, acting '
        'through the Superintendencia; that changes no words of Ley 5810, whose other articles still name the '
        'Commission, and its repeal of "todas las disposiciones que sean contrarias" names no provision.',
        'Ley 5810/2017 repealed: Ley 7572/2025 de Mercado de Valores y Productos (BACN 12910; published 7 November '
        '2025, in force the next day by its art. 328) art. 329 repeals Ley 5810/2017 and Ley 7162/2023, so every '
        'provision is removed from 2025-11-08 and the folder is empty from then on.',
        'Ley 5810/2017: BACN searches "5810", "5810/2017", "5810/17", "5.810", "Ley 5810", "Ley N° 5810", "mercado de '
        'valores", "Comisión Nacional de Valores" and "Superintendencia de Valores", screened for a modifying or '
        'repealing formula naming it: only Leyes 7162/2023 and 7572/2025. The other hits only cite it.',
    ]
    return act(slug, 'LMV', 'Ley N° 5810/2017 de Mercado de Valores', key, versions), dec



# ------------------------------------------------------------------ Ley 7572/2025 Mercado de Valores y Productos

def ley_7572():
    slug, key, pid = 'ley-mercado-valores-productos', 'ley-7572-2025', '12910'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2025-11-07', 'published': '2025-11-07'}, m
    L = actlib.lines(pid)
    i = L.index('Artículo 328.- Entrada en vigor.')
    assert L[i + 1] == 'La presente ley entrará en vigor al día siguiente de su publicación.'
    orig = actlib.lines

    def fixed(p):                     # BACN prints "btko. 202.-" for "Artículo 202.-"
        L2 = orig(p)
        if p == pid:
            assert sum(ln.startswith('btko. 202.-') for ln in L2) == 1
            L2 = ['Artículo 202.-' + ln[len('btko. 202.-'):] if ln.startswith('btko. 202.-') else ln for ln in L2]
        return L2
    actlib.lines = fixed
    try:
        a, dec = single(slug, 'LMVP', 'Ley N° 7572/2025 de Mercado de Valores y Productos', key, pid,
                        'Ley N° 7572/2025', 'MERCADO DE VALORES Y PRODUCTOS', [
        'Ley 7572/2025 de Mercado de Valores y Productos (BACN 12910): promulgated and published 7 November 2025; '
        'art. 328: "entrará en vigor al día siguiente de su publicación", so in force 2025-11-08. Its art. 329 '
        'repeals Ley 5810/2017 (whose history ends that day in this repository) and Leyes 7162/2023, 5452/2015, '
        '5067/2013, 3899/2009, 1163/1997 and 1036/1997.',
        'Ley 7572/2025: arts. 323 and 324 exempt companies with book-entry shares from the share register of Ley '
        '1034/1983 and deem the duty in art. 5 of Ley 5895/2017 met by the Caja de Valores entry; they change no '
        'words of either law, so neither has a version for them.',
        'Ley 7572/2025: BACN searches "7572", "7572/2025", "7.572", "Ley 7572", "Ley N° 7572", "mercado de valores '
        'y productos", "mercado de valores" and "Superintendencia de Valores", screened for a modifying formula '
        'naming it, find no law that changes its words, so it has one version.',
        'Ley 7572/2025: BACN prints "btko. 202.-" before the epigraph of art. 202; read as "Artículo 202.-".',
    ])
    finally:
        actlib.lines = orig
    assert len([k for k in a['versions'][0]['units'] if k.startswith('art-')]) == 330
    assert len(a['versions']) == 1 and a['versions'][0]['from'] == '2025-11-08'
    return a, dec


# ------------------------------------------------------------------ Ley 7561/2025 de Arbitraje

def ley_7561():
    pid = '12917'
    assert page_meta(url_of(pid)) == {'promulgated': '2025-12-23', 'published': '2025-12-23'}
    L = actlib.lines(pid)
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor|empezar[aá] a regir', ln) for ln in L)
    i = L.index('Artículo 71.- Derogación de disposiciones legales.')
    assert L[i + 1].startswith('Queda derogada la Ley N° 1879/2002 "DE ARBITRAJE Y MEDIACIÓN", con excepción de sus '
                               'artículos 53 al 67'), L[i + 1]
    a, dec = single('ley-arbitraje', 'LARB', 'Ley N° 7561/2025 de Arbitraje', 'ley-7561-2025', pid,
                    'Ley N° 7561/2025', 'DE ARBITRAJE', [
        'Ley 7561/2025 de Arbitraje (BACN 12917): promulgated and published 23 December 2025, no vigencia clause, so '
        'in force the day after publication (2025-12-24). Its art. 71 repeals Ley 1879/2002 de Arbitraje y '
        'Mediación except arts. 53 to 67 (mediation), which is renamed "De Mediación"; Ley 1879 is not in this '
        'repository. It cites the Código Procesal Civil (art. 448 h) without changing its words.',
        'Ley 7561/2025: BACN searches "7561", "7561/2025", "7.561", "Ley 7561", "Ley N° 7561" and "arbitraje", '
        'screened for a modifying formula naming it, find no law that changes its words, so it has one version.',
    ])
    assert len([k for k in a['versions'][0]['units'] if k.startswith('art-')]) == 72
    return a, dec

# ------------------------------------------------------------------ Ley 1376/1988 Arancel de Honorarios de Abogados

def ley_1376():
    slug, key, pid = 'ley-arancel-honorarios-abogados', 'ley-1376-1988', '2444'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1988-12-20', 'published': '1988-12-22'}, m
    orig = actlib.lines

    def fixed(p):                     # a lone "." printed on its own line after art. 3, whose text ends with a period
        L2 = orig(p)
        if p == pid:
            i = L2.index('.')
            assert L2[i - 1].endswith('la procuración.') and L2[i + 1].startswith('Art. 4°.-'), L2[i - 1:i + 2]
            L2 = L2[:i] + L2[i + 1:]
        return L2
    actlib.lines = fixed
    try:
        units = enacted(pid, slug, 5)
        L = actlib.lines(pid)
    finally:
        actlib.lines = orig
    assert len([k for k in units if k.startswith('art-')]) == 76
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor|empezar[aá] a regir', ln) for ln in L)
    assert 'Art. 74.- La regulación y estimación de honorarios de los abogados y procuradores, se hará desde la ' \
           'vigencia de la presente Ley, de conformidad con la misma, en los asuntos iniciados a partir de su ' \
           'promulgación.' in L
    assert units['indice']['text'].split('\n')[1] == 'art-001: TITULO Y - NORMAS GENERALES'
    v1 = first_version(key, pid, 'Ley N° 1376/1988', 'ARANCEL DE HONORARIOS DE ABOGADOS Y PROCURADORES',
                       plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    # Ley 4590/2012: names art. 27 inciso e), 54 and 55; it quotes the whole of art. 27, but only inciso e) is changed
    k = 'ley-4590-2012'
    url, L, frm = bacn_law(k, '3098', 'Ley N° 4590/2012')
    assert frm == '2012-04-18', frm
    intro = (r'^Artículo 1º\.- Modifícanse los Artículos 27, inciso e\), 54 y 55 de la Ley N° 1376/88 "ARANCEL DE '
             r'HONORARIOS DE ABOGADOS Y PROCURADORES", cuyos textos quedan redactados de la siguiente manera:$')
    b = dict(qblocks(L, intro))
    assert sorted(b) == [27, 54, 55], sorted(b)
    q27 = b[27]
    e = next(i for i, p in enumerate(q27) if p.startswith('e) '))
    assert q27[e] == 'e) En las causas penales; se dividirán las etapas procesales en:', q27[e]
    new_e = q27[e:]
    assert new_e[-1].startswith('Si la causa concluyere con el sobreseimiento definitivo'), new_e[-1]

    def inc_e(u):
        ls = u['text'].split('\n')
        assert ls[-1] == '' and ls[-2].startswith('Si la causa concluyere en el sumario'), ls[-2:]
        i = ls.index('e) En las causas penales:')
        return dict(u, text='\n'.join(ls[:i] + new_e) + '\n')
    rp.op(frm, k, url, 'fn', 'art-027', inc_e)
    rp.op(frm, k, url, 'set', 'art-054', unit_of(54, b[54], k))
    rp.op(frm, k, url, 'set', 'art-055', unit_of(55, b[55], k))
    dec = [
        'Ley 1376/1988 Arancel de Honorarios de Abogados y Procuradores (BACN 2444): promulgated 20 December 1988, '
        'published 22 December 1988, no vigencia clause, so in force the day after publication (1988-12-23). Its art. '
        '74 applies it to matters begun from its promulgation; that is its own wording, not a version. BACN prints '
        'the first heading as "TITULO Y" (for "TITULO I"), kept as printed in indice.md, and a lone "." on its own '
        'line after the text of art. 3, which already ends with a period: that line is left out.',
        'Ley 1376/1988: Ley 4590/2012 (BACN 3098; promulgated 11 April 2012, published 17 April 2012, no vigencia '
        'clause, in force 2012-04-18) rewrites "los Artículos 27, inciso e), 54 y 55". It quotes the whole of art. '
        '27, but its incisos a) to d) differ from the enacted ones in small ways (no line on the partición of '
        'estates in a), "Etapa de pruebas", list markers) that the law does not name: only inciso e) and the lines '
        'after it (criminal cases, now by the stages of the 1998 Código Procesal Penal) are replaced; arts. 54 and '
        '55 are rewritten whole.',
        'Ley 1376/1988: Ley 1420/1999 (bank liquidation regime) art. 35 and Ley 2421/2004 art. 29 (fees in suits '
        'against the State, at most 50% of the legal minimum) set special rules for their own cases "de '
        'conformidad con lo que establece la Ley N° 1376/88, con las siguientes modificaciones" or in their own '
        'words; they change no words of Ley 1376, so neither has a version.',
        'Ley 1376/1988: BACN searches "1376", "1376/88", "1376/1988", "1.376", "Ley 1376", "Ley N° 1376", '
        '"honorarios de abogados" and "arancel de honorarios", screened for a modifying or repealing formula naming '
        'it: only Ley 4590/2012 changes its words.',
    ]
    return act(slug, 'LAHA', 'Ley N° 1376/1988 Arancel de Honorarios de Abogados y Procuradores', key,
               rp.build()), dec


# ------------------------------------------------------------------ Ley 4036/2010 Armas de Fuego (repealed 2025)

def ley_4036():
    slug, key, pid = 'ley-armas-de-fuego-2010', 'ley-4036-2010', '516'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2010-08-11', 'published': '2010-08-13'}, m
    assert len([k for k in units if k.startswith('art-')]) == 111
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor|empezar[aá] a regir', ln)
                   for ln in actlib.lines(pid))
    v1 = first_version(key, pid, 'Ley N° 4036/2010', 'DE ARMAS DE FUEGO, SUS PIEZAS Y COMPONENTES, MUNICIONES, '
                       'EXPLOSIVOS, ACCESORIOS Y AFINES', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-7411-2024'
    url, L, frm = bacn_law(k, '12639', 'Ley N° 7411/2024')
    assert frm == '2025-01-04', frm
    assert ('Artículo 283.- Quedan derogadas todas las disposiciones legales que se opongan a la presente ley y, '
            'particularmente, la Ley Nº 4036/2010 "DE ARMAS DE FUEGO, SUS PIEZAS Y COMPONENTES, MUNICIONES, '
            'EXPLOSIVOS, ACCESORIOS Y AFINES".') in L
    n0 = len(MISMATCHES)
    whole = rp.build()[-1]['units']   # every unit in force the day before the repeal (a dry run)
    del MISMATCHES[n0:]
    for u in sorted(whole):
        rp.op(frm, k, url, 'del', u)
    versions = rp.build()
    assert versions[-1]['units'] == {} and versions[-1]['from'] == '2025-01-04'
    dec = [
        'Ley 4036/2010 de Armas de Fuego (BACN 516): promulgated 11 August 2010, published 13 August 2010, no '
        'vigencia clause, so in force the day after publication (2010-08-14). It repeals Ley 1910/2002 (art. 110), '
        'which is not in this repository.',
        'Ley 4036/2010 repealed: Ley 7411/2024 (BACN 12639; promulgated 26 December 2024, published 3 January 2025, '
        'no vigencia clause, in force 2025-01-04) art. 283 repeals it by name, so every provision is removed from '
        '2025-01-04 and the folder is empty from then on. Ley 7411 art. 280 keeps permits granted under Ley 4036 '
        'until they expire; that is Ley 7411\'s own wording, not a version of Ley 4036.',
        'Ley 4036/2010: BACN searches "4036", "4036/10", "4036/2010", "4.036", "Ley 4036", "Ley N° 4036", "Ley N° '
        '4.036" and "armas de fuego", screened for a modifying or repealing formula naming it: only Ley 7411/2024 '
        '(the repeal). Ley 6452/2020 (Código Penal) and other hits only cite it.',
    ]
    return act(slug, 'LAFA', 'Ley N° 4036/2010 de Armas de Fuego, sus Piezas y Componentes, Municiones, '
               'Explosivos, Accesorios y Afines', key, versions), dec


# ------------------------------------------------------------------ Ley 7411/2024 Armas de Fuego

def ley_7411():
    pid = '12639'
    assert page_meta(url_of(pid)) == {'promulgated': '2024-12-26', 'published': '2025-01-03'}
    L = actlib.lines(pid)
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|empezar[aá] a regir|regir[aá] a partir', ln) for ln in L)
    a, dec = single('ley-armas-de-fuego', 'LAF', 'Ley N° 7411/2024 de Armas de Fuego, sus Componentes, Municiones '
                    'y sus Componentes, Accesorios Controlados, Explosivos, Accesorios de Explosivos, Precursores '
                    'Químicos de Explosivos, Afines de Explosivos y Artículos Pirotécnicos', 'ley-7411-2024', pid,
                    'Ley N° 7411/2024', L[2], [
        'Ley 7411/2024 de Armas de Fuego (BACN 12639): promulgated 26 December 2024, published 3 January 2025, no '
        'vigencia clause, so in force the day after publication (2025-01-04). Art. 279 gives the authority one year '
        'from publication to adapt its procedures, and art. 282 sets a grace period for registration; that is its '
        'own wording, not a version. Its art. 283 repeals Ley 4036/2010 (above, `ley-armas-de-fuego-2010/`).',
        'Ley 7411/2024: BACN searches "7411", "7411/2024", "7.411", "Ley 7411" and "Ley N° 7411", screened for a '
        'modifying formula naming it, find no law that changes its words, so it has one version.',
    ])
    assert len([k for k in a['versions'][0]['units'] if k.startswith('art-')]) == 284
    assert len(a['versions']) == 1 and a['versions'][0]['from'] == '2025-01-04'
    return a, dec


# ------------------------------------------------------------------ Ley 4457/2012 MIPYMES

def ley_4457():
    slug, key, pid = 'ley-mipymes', 'ley-4457-2012', '8272'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2012-05-16', 'published': '2012-05-17'}, m
    assert len([k for k in units if k.startswith('art-')]) == 55
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor|empezar[aá] a regir', ln)
                   for ln in actlib.lines(pid))
    v1 = first_version(key, pid, 'Ley N° 4457/2012', 'PARA LAS MICRO, PEQUEÑAS Y MEDIANAS EMPRESAS (MIPYMES)',
                       plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-7444-2025'
    url, L, frm = bacn_law(k, '12698', 'Ley N° 7444/2025')
    assert frm == '2025-01-08', frm
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor|empezar[aá] a regir', ln) for ln in L)
    named = [2, 3, 4, 5, 6, 8, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 30, 31, 33, 34,
             36, 37, 39, 40, 41, 42, 43, 45, 46, 47, 48, 49, 50, 51, 52]
    intro = r'^Artículo 1\.º Modifícanse los artículos 2°, 3°, 4°, 5°, 6°, 8°, 10, 11, '
    head = next(ln for ln in L if re.search(intro, ln))
    assert head.endswith(', 51, 52, de la Ley Nº 4.457/2012 "PARA LAS MICRO, PEQUEÑAS Y MEDIANAS EMPRESAS '
                         '(MIPYMES)", los cuales quedan redactados como sigue:'), head
    assert [int(x) for x in re.findall(r'\d+', head.split(' de la Ley')[0])[1:]] == named
    # the quotation re-states the chapter and section headings between the articles: not articles, set aside
    seg = actlib.segment(L, intro)
    heads = [ln for ln in seg if not actlib.QART.match(ln)
             and (actlib.LABEL.match(ln) or not re.search('[a-zñáéíóú]', ln))]
    assert len(heads) == 30, len(heads)
    blocks: list[tuple[int, list[str]]] = []
    for ln in seg:
        if ln in heads:
            continue
        q = actlib.QART.match(ln)
        if q:
            blocks.append((int(q.group(1)), [q.group(2)]))
        else:
            assert blocks, ln
            blocks[-1][1].append(ln)
    assert [n for n, _ in blocks] == named
    for n, paras in blocks:
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, parse.strip_quote(['"' + paras[0]] + paras[1:]), k))
    assert ('Se deroga el artículo 26 de la Ley Nº 4.457/2012 "PARA LAS MICRO, PEQUEÑAS Y MEDIANAS EMPRESAS '
            '(MIPYMES)".') in L
    rp.op(frm, k, url, 'del', 'art-026')
    dec = [
        'Ley 4457/2012 para las Micro, Pequeñas y Medianas Empresas (MIPYMES) (BACN 8272): promulgated 16 May 2012, '
        'published 17 May 2012, no vigencia clause, so in force the day after publication (2012-05-18).',
        'Ley 4457/2012: Ley 7444/2025 (BACN 12698; promulgated and published 7 January 2025, no vigencia clause, in '
        'force 2025-01-08) art. 1 rewrites 43 articles (2 to 6, 8, 10, 11, 13 to 25, 27 to 31, 33, 34, 36, 37, 39 to '
        '43 and 45 to 52) and its art. 4 repeals art. 26. Its quotation also re-states the chapter and section '
        'headings between the articles, four of them in new words (Capítulo III Sección II, Capítulo IV Sección II, '
        'Capítulo VIII and Capítulo X); art. 1 names only articles, so indice.md keeps the enacted headings. Its '
        'arts. 2 and 3 create a Consejo Asesor de MIPYMES in Ley 7444\'s own words, with no number in Ley 4457: not '
        'inserted. Art. 52 as rewritten gives the turnover limits of each category; the Executive\'s decrees that '
        'updated them before (Ley 7444 names Decreto 3698/2020) change no words of the law.',
        'Ley 4457/2012: BACN searches "4457", "4457/12", "4457/2012", "4.457", "Ley 4457", "Ley N° 4457", '
        '"mipymes" and "micro, pequeñas y medianas", screened for a modifying or repealing formula naming it: only '
        'Ley 7444/2025 (searched in turn as "7444", "7444/2025", "7.444", "Ley N° 7444": no amender). Ley '
        '5741/2016 (social security for micro-enterprises) only cites it.',
    ]
    return act(slug, 'LMIP', 'Ley N° 4457/2012 para las Micro, Pequeñas y Medianas Empresas (MIPYMES)', key,
               rp.build()), dec


# ------------------------------------------------------------------ Ley 1590/2000 Sistema Nacional de Transporte

def ley_1590():
    slug, key, pid = 'ley-sistema-nacional-transporte', 'ley-1590-2000', '1669'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2000-09-16', 'published': '2000-09-18'}, m
    assert len([k for k in units if k.startswith('art-')]) == 47
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor|empezar[aá] a regir', ln)
                   for ln in actlib.lines(pid))
    v1 = first_version(key, pid, 'Ley N° 1590/2000', 'QUE REGULA EL SISTEMA NACIONAL DE TRANSPORTE Y CREA LA '
                       'DIRECCION NACIONAL DE TRANSPORTE (DINATRAN) Y LA SECRETARIA METROPOLITANA DE TRANSPORTE (SMT)',
                       plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-1818-2001'
    url, L, frm = bacn_law(k, '10156', 'Ley N° 1818/2001')
    assert frm == '2001-11-09', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modificase el Artículo 11 de la Ley N° 1590', [11])
    k = 'ley-3698-2009'
    url, L, frm = bacn_law(k, '1876', 'Ley N° 3698/2009')
    assert frm == '2009-08-12', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícanse los Artículos 37 y 38 de la Ley N° 1590', [37, 38])
    k = 'ley-3850-2009'
    url, L, frm = bacn_law(k, '2585', 'Ley N° 3850/2009')
    assert frm == '2009-10-17', frm
    assert any(ln.startswith('Artículo 21.- Derógase lo dispuesto en el Inciso k) del Artículo 26 de la Ley Nº '
                             '1590/00 ') for ln in L)
    rp.op(frm, k, url, 'fn', 'art-026', actlib.drop_line('k) regular, proveer y conceder los servicios de revisión '
                                                          'técnica'))
    k = 'ley-4090-2010'
    url, L, frm = bacn_law(k, '591', 'Ley N° 4090/2010')
    assert frm == '2010-09-09', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1°\.- Modifícanse los Artículos 28, 29, 34 y 35 de la Ley N° 1\.590',
             [28, 29, 34, 35])
    k = 'ley-5152-2014'
    url, L, frm = bacn_law(k, '4653', 'Ley N° 5152/2014')
    assert frm == '2014-04-09', frm
    assert L[5].startswith('Artículo 1°.- Derógase el Capítulo IV de la Ley N° 1590 de fecha 16 de setiembre de '
                           '2000 '), L[5]
    idx = units['indice']['text']
    assert 'art-022: CAPÍTULO IV - SECRETARIA DE TRANSPORTE DEL ÁREA METROPOLITANA DE ASUNCIÓN' in idx
    assert 'art-037: CAPÍTULO V - CONCESIONES DE SERVICIOS' in idx
    for n in range(22, 37):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    k = 'ley-7617-2026'
    url, L, frm = bacn_law(k, '12961', 'Ley N° 7617/2026')
    assert frm == '2026-01-08', frm
    i = L.index('Artículo 121. Derogación.')
    assert L[i + 3].startswith('b. Los artículos 13, inciso a) y 15, inciso b), de la Ley Nº 1590/2000 '), L[i + 3]
    rp.op(frm, k, url, 'fn', 'art-013', actlib.drop_line('a) establecer políticas y delineamientos técnicos'))
    rp.op(frm, k, url, 'fn', 'art-015', actlib.drop_line('b) establecer los lineamientos necesarios'))
    dec = [
        'Ley 1590/2000 que regula el Sistema Nacional de Transporte y crea la DINATRAN y la SMT (BACN 1669): '
        'promulgated 16 September 2000, published 18 September 2000, no vigencia clause, so in force the day after '
        'publication (2000-09-19). Its Chapter IV creates the metropolitan secretariat under the name SETAMA.',
        'Ley 1590/2000: Ley 1818/2001 (BACN 10156; published 8 November 2001, in force 2001-11-09) rewrites art. 11; '
        'Ley 3698/2009 (BACN 1876; in force 2009-08-12) arts. 37 and 38; Ley 3850/2009 (BACN 2585; vehicle '
        'inspection, in force 2009-10-17) art. 21 repeals inciso k) of art. 26, so that line is removed and the '
        'other incisos keep their letters; Ley 4090/2010 (BACN 591; in force 2010-09-09) rewrites arts. 28, 29, 34 '
        'and 35. All dated the day after publication (no vigencia clauses).',
        'Ley 1590/2000: Ley 5152/2014 (BACN 4653; published 8 April 2014, in force 2014-04-09) art. 1 repeals '
        'Chapter IV (arts. 22 to 36, the SETAMA) "y sus leyes modificatorias", so those articles are removed from '
        'that day; indice.md keeps the chapter heading as enacted. Its art. 2 (the Ministry of Public Works takes on '
        'the SETAMA\'s functions) is in its own words, and Ley 7617/2026 art. 121 a. later repeals it; neither '
        'restores Chapter IV.',
        'Ley 1590/2000: Ley 7617/2026 (BACN 12961; promulgated and published 7 January 2026, no vigencia clause, in '
        'force 2026-01-08) art. 121 b. repeals inciso a) of art. 13 and inciso b) of art. 15: those lines are '
        'removed and the other incisos keep their letters. Its other provisions on the transport system (rectoría '
        'of the Ministry, art. 120\'s changes to the Ley Orgánica Municipal and Ley 6925/2022) are in its own words '
        'and change no other words of Ley 1590.',
        'Ley 1590/2000: BACN searches "1590", "1590/00", "1590/2000", "1.590", "Ley 1590", "Ley N° 1590", "sistema '
        'nacional de transporte" and "dinatran", screened for a modifying or repealing formula naming it: Leyes '
        '1818/2001, 3698/2009, 3850/2009, 4090/2010, 5152/2014 and 7617/2026. Ley 5253/2014 only cites Ley 5152.',
    ]
    return act(slug, 'LSNT', 'Ley N° 1590/2000 que regula el Sistema Nacional de Transporte y crea la Dirección '
               'Nacional de Transporte (DINATRAN) y la Secretaría Metropolitana de Transporte (SMT)', key,
               rp.build()), dec


# ------------------------------------------------------------------ Ley 1340/1988 estupefacientes

GAP = '[La fuente no da el texto vigente en esta fecha.]'


def ley_1340():
    slug, key, pid = 'ley-estupefacientes', 'ley-1340-1988', '2562'
    units = enacted(pid, slug, 5)
    L0 = actlib.lines(pid)
    m = page_meta(url_of(pid))
    # BACN's metadata precedes the law's own sanction line; the amending laws give its promulgation day
    assert m == {'promulgated': '1988-09-30', 'published': '1988-10-14'}, m
    assert L0[-1] == ('DADA EN LA SALA DE SESIONES DEL CONGRESO NACIONAL, A LOS VEINTE DIAS DEL MES DE OCTUBRE '
                      'DEL AÑO UN MIL NOVECIENTOS OCHENTA Y OCHO.'), L0[-1]
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor\b|empezar[aá] a regir', ln) for ln in L0)
    arts = [k for k in units if k.startswith('art-')]
    assert arts == [f'art-{n:03d}' for n in range(1, 84)], arts
    v1 = first_version(key, pid, 'Ley N° 1340/1988', L0[2], '1988-11-23', units,
                       'The law as enacted, from its BACN page; in force the day after promulgation.')
    LAWS[key]['enacted'], LAWS[key]['published'] = '1988-11-22', None
    rp = Replay(slug, units, v1)
    # Ley 108/1991 (SENAD) art. 3: art. 58
    k = 'ley-108-1991'
    url, L, frm = bacn_law(k, '11734', 'Ley N° 108/1991')
    assert frm == '1991-12-28', frm
    pre = 'Artículo 3º.- Modíficase el Artículo 58 de la Ley Nº 1340/88 que queda redactado de la siguiente manera: "'
    ln = next(x for x in L if x.startswith(pre))
    assert ln.endswith('".'), ln
    rp.op(frm, k, url, 'set', 'art-058', unit_of(58, [ln[len(pre):-2]], k))
    # Decreto-Ley 9/1992 (17 February 1992) rewrote art. 2; its own wording is not on BACN (gap marker, uncredited);
    # Ley 68/1992 approves it with modifications and gives the text from its own in-force day
    k = 'ley-68-1992'
    url, L, frm = bacn_law(k, '5342', 'Ley N° 68/1992')
    assert frm == '1992-11-17', frm
    assert L[2].startswith('QUE APRUEBA CON MODIFICACIONES EL DECRETO-LEY Nº 9 DEL 17 DE FEBRERO DE 1992, POR EL '
                           'CUAL SE MODIFICA EL ARTICULO 2º DE LA LEY Nº 1.340 DE FECHA 22 DE NOVIEMBRE DE 1988.'), L[2]
    rp.op('1992-02-18', 'decreto-ley-9-1992', url, 'set', 'art-002', unit_of(2, [GAP], 'decreto-ley-9-1992'))
    b = qblocks(L, r'^Artículo 1º\.- Apruébase con modificaciones el Decreto-Ley Nº 9 de 17 de febrero de 1992')
    assert [n for n, _ in b] == [1], b
    rp.op(frm, k, url, 'set', 'art-002', unit_of(2, b[0][1], k))
    # Ley 1881/2002
    k = 'ley-1881-2002'
    url, L, frm = bacn_law(k, '4423', 'Ley N° 1881/2002')
    assert frm == '2002-07-09', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1º\.- Modifícanse los Artículos 19, 21, 23, 53 y 54 de la Ley N° 1340 ',
             [19, 21, 23, 53, 54])
    i = L.index('Artículo 2º.- Ampliase la Ley N° 1340 del 22 de noviembre de 1988, con las siguiente disposiciones:')
    j = L.index('Artículo 3º.- Renuméranse los Artículos 72 a 83 de la originaria Ley N° 1340 del 22 de noviembre de '
                '1988 con los números 99 a 111.')
    assert L[j + 1] == ('Artículo 4º.- Deróganse los Artículos 27, 56, 57 y 58 modificado por el Artículo 3° de la Ley '
                        'N° 108 del 27 de diciembre de 1991; 59 y 60 de la Ley N° 1340 del 22 de noviembre de 1988.')
    # art. 3: the original arts. 72 to 83 (twelve) become 99 to 110; Ley 6902/2022's arts. 101 (landing strips, the
    # original 74) and 105 (registration fees, the original 78) confirm the shift of 27
    for n in range(72, 84):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    for n in range(72, 84):
        u = units[f'art-{n:03d}']
        assert u['text'].startswith(f'# Artículo {n}\n'), u['text'][:40]
        rp.op(frm, k, url, 'add', f'art-{n + 27:03d}',
              dict(u, label=f'Art. {n + 27}', text=f'# Artículo {n + 27}\n' + u['text'][len(f'# Artículo {n}\n'):]))
    # art. 2: Chapters X to XVI, new arts. 72 to 98
    heads: list[tuple[int, list[str]]] = []
    blocks: list[tuple[int, list[str]]] = []
    for ln in L[i + 1:j]:
        a = re.match(r'^Artículo (\d+)\.-\s*(.*)$', ln)
        if a:
            blocks.append((int(a.group(1)), [a.group(2)]))
        elif re.match(r'^CAP[IÍ]TULO [XVI]+$', ln):
            heads.append((len(blocks), [ln]))
        elif heads and heads[-1][0] == len(blocks):
            heads[-1][1].append(ln)
        else:
            blocks[-1][1].append(ln)
    assert [n for n, _ in blocks] == list(range(72, 99)), [n for n, _ in blocks]
    for n, paras in blocks:
        rp.op(frm, k, url, 'add', f'art-{n:03d}', unit_of(n, paras, k))
    lines = [f'art-{blocks[p][0]:03d}: {h[0]} - {h[1]}' + ''.join(' / ' + x for x in h[2:]) for p, h in heads]
    assert len(lines) == 7 and lines[0] == 'art-072: CAPITULO X - DE LA ASISTENCIA JUDICIAL RECIPROCA', lines
    old_x = 'art-072: CAPITULO X - DISPOSICIONES FINALES'

    def idx(u):
        ls = u['text'].split('\n')
        assert ls.count(old_x) == 1, ls
        p = ls.index(old_x)
        return dict(u, text='\n'.join(ls[:p] + lines + ['art-099: CAPITULO X - DISPOSICIONES FINALES'] + ls[p + 1:]))
    rp.op(frm, k, url, 'fn', 'indice', idx)
    for n in (27, 56, 57, 58, 59, 60):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    # Ley 5434/2015: art. 23
    k = 'ley-5434-2015'
    url, L, frm = bacn_law(k, '4422', 'Ley N° 5434/2015')
    assert frm == '2015-06-05', frm
    set_arts(rp, frm, k, url, L, r'^Artículo 1\.° Modifícase el artículo 23 de la Ley Nº 1\.340/88 ', [23])
    # Ley 5876/2017 art. 59 1): art. 53 repealed
    k = 'ley-5876-2017'
    url, L, frm = bacn_law(k, '9306', 'Ley N° 5876/2017')
    assert frm == '2017-09-27', frm
    assert any(x.startswith('Artículo 59. Derogaciones. Deróganse 1) el artículo 53 de la Ley N° 1.340/88 ') for x in L)
    rp.op(frm, k, url, 'del', 'art-053')
    # Ley 6902/2022: arts. 2, 3, 4, 23, 47, 101, 105 (quotation labels "Art. 2.°" and "Art.- 101." normalised)
    k = 'ley-6902-2022'
    url, L, frm = bacn_law(k, '10256', 'Ley N° 6902/2022')
    assert frm == '2022-04-12', frm
    L2 = [re.sub(r'^"Art\. (\d)\.° ', r'"Art. \1.- ', x).replace('"Art.- 101. ', '"Art. 101. ') for x in L]
    assert sum(a != b for a, b in zip(L, L2)) == 4
    set_arts(rp, frm, k, url, L2, r'^Artículo 1\.° Modifícanse los artículos 2º, 3º, 4º, 23, 47, 101 y 105, de la Ley',
             [2, 3, 4, 23, 47, 101, 105])
    versions = rp.build()
    gap = next(v for v in versions if v['from'] == '1992-02-18')
    assert list(gap['credits']) == ['art-002'], gap['credits']
    gap['credits'] = {}               # the publisher's gap: committed as an unexplained change
    gap['note'] = ('Decreto-Ley N° 9 of 17 February 1992 rewrote art. 2; its own wording is not in the source, so '
                   'art. 2 reads "' + GAP + '" until Ley N° 68/1992 approved it with modifications.')
    dec = [
        'Ley 1340/1988 (BACN 2562) que modifica, adiciona y actualiza la Ley 357/72 (narcotics): sanctioned 20 October '
        '1988 (its closing formula). BACN\'s page gives promulgation 30 September 1988 and publication 14 October '
        '1988, both before that sanction, so they are not used. Leyes 68/1992, 1881/2002, 5434/2015 and 6902/2022 '
        'all name it "Ley N° 1340 del 22 de noviembre de 1988": that is taken as its promulgation day, and with no '
        'publication day in an official text, the first version is the day after (1988-11-23; no vigencia clause). '
        'Its art. 81 repeals Ley 357/72 (not in this repository); art. 82 incorporates it into the Código Penal of '
        'that time, which changes no words.',
        'Ley 1340/1988: Ley 108/1991 (creates the SENAD, BACN 11734; promulgated 27 December 1991, no publication '
        'day, in force 1991-12-28) art. 3 rewrites art. 58.',
        'Ley 1340/1988 art. 2: Decreto-Ley N° 9 of 17 February 1992 rewrote it; the decree-law is known only from '
        'Ley 68/1992 (BACN 5342, the same text also at BACN 10257), which approves it "con modificaciones" and '
        'gives the approved wording. The decree-law\'s own wording is not on BACN, so from the day after its date '
        '(1992-02-18; no publication day found) art. 2 reads "' + GAP + '", committed by the publisher as an '
        'unexplained change, and from Ley 68\'s in-force day (promulgated 16 November 1992, no publication day, '
        '1992-11-17) it reads Ley 68\'s text, quoted there as the decree-law\'s "Art. 1º".',
        'Ley 1340/1988: Ley 1881/2002 (BACN 4423; promulgated 24 June 2002, published 8 July 2002, no vigencia '
        'clause, in force 2002-07-09) art. 1 rewrites arts. 19, 21, 23, 53 and 54; art. 2 adds Chapters X to XVI '
        '(new arts. 72 to 98: mutual legal assistance, extradition, undercover operations, controlled deliveries, '
        'agents and informants, and the SENAD as the authority that replaces the DINAR); art. 4 repeals arts. 27, '
        '56, 57, 58 (as worded by Ley 108), 59 and 60. Its art. 3 renumbers "los Artículos 72 a 83 de la originaria '
        'Ley" "con los números 99 a 111": twelve articles and thirteen numbers. They are numbered 99 to 110 (each '
        'number plus 27), which Ley 6902/2022 confirms: it rewrites art. 101 on landing strips (the original art. '
        '74) and art. 105 on registration fees (the original art. 78). No art. 111 exists. References between the '
        'renumbered articles keep their old numbers (art. 3 does not order them changed). indice.md adds the new '
        'chapter headings at arts. 72 to 98 and moves the original "CAPITULO X - DISPOSICIONES FINALES" to art. 99, '
        'so two chapters are numbered X, as printed.',
        'Ley 1340/1988: Ley 5434/2015 (BACN 4422; published 4 June 2015, in force 2015-06-05) rewrites art. 23; Ley '
        '5876/2017 (BACN 9306; published 26 September 2017, in force 2017-09-27) art. 59 1) repeals art. 53; Ley '
        '6902/2022 (BACN 10256; published 11 April 2022, in force 2022-04-12) rewrites arts. 2, 3, 4, 23, 47, 101 '
        'and 105. None has a vigencia clause.',
        'Ley 1340/1988: the Código Penal (Ley 1160/1997), Código Procesal Penal and other laws that repeal '
        '"disposiciones contrarias" without naming its articles, and laws that cite it or set rules in their own '
        'words (Leyes 1015/1997, 3440/2008, 5757/2016, 6007/2017, 6167/2018, 6452/2019, 6501/2020, 7062/2023, '
        '7280/2024), change no words of it. Leyes 1340/1998 (expropriation), 381/1972 (on a Ley 1.340 of 1968) and '
        '1608/2000 are other laws with the same number.',
        'Ley 1340/1988: BACN searches "1340", "1340/88", "1340/1988", "1.340", "Ley 1340", "Ley N° 1340", "Ley N° '
        '1.340", "Ley Nº 1340", "estupefacientes", "drogas peligrosas", "1881", "1881/02", "1881/2002", "1.881", '
        '"Ley N° 1881", "357/72", "farmacodependencia" and "antidrogas", screened for a modifying or repealing '
        'formula naming it or Ley 1881: Leyes 108/1991, 68/1992, 1881/2002, 5434/2015, 5876/2017 and 6902/2022.',
    ]
    return act(slug, 'LEST', 'Ley N° 1340/1988 que reprime el tráfico ilícito de estupefacientes y drogas '
               'peligrosas y otros delitos afines y establece medidas de prevención y recuperación de '
               'farmacodependientes', key, versions), dec


# ------------------------------------------------------------------ Ley 117/1991 de Inversiones

def ley_117():
    pid = '785'
    assert page_meta(url_of(pid)) == {'promulgated': '1992-01-07', 'published': '1992-01-07'}
    L = actlib.lines(pid)
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|en vigor|empezar[aá] a regir|regir[aá] a partir', ln)
                   for ln in L)
    a, dec = single('ley-inversiones', 'LINV', 'Ley N° 117/1991 de Inversiones', 'ley-117-1991', pid,
                    'Ley N° 117/1991', 'DE INVERSIONES', [
        'Ley 117/1991 de Inversiones (BACN 785): sanctioned 18 December 1991, promulgated and published 7 January '
        '1992, no vigencia clause, so in force the day after publication (1992-01-08). Its number keeps the year of '
        'sanction (1991).',
        'Ley 117/1991: BACN searches "117/91", "117/1991", "117/92", "117/1992", "Ley 117", "Ley N° 117", "Nº '
        '117/91", "ley de inversiones" and "riesgo compartido", screened for a modifying or repealing formula naming '
        'it: no law changes its words, so it has one version. Ley 1561/2000 art. 15 e) (the environment '
        'secretariat\'s role under it) and the laws that exclude investments from their own regimes "y sus '
        'modificaciones" (Ley 7599/2025 and the amender of Ley 7434/2025) only cite it.',
    ])
    assert len([k for k in a['versions'][0]['units'] if k.startswith('art-')]) == 19
    assert len(a['versions']) == 1 and a['versions'][0]['from'] == '1992-01-08'
    return a, dec


# ------------------------------------------------------------------ Ley 6925/2022 Transporte Eléctrico

def ley_6925():
    slug, key, pid = 'ley-transporte-electrico', 'ley-6925-2022', '11279'
    units = enacted(pid, slug, 5)
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2022-10-25', 'published': '2022-10-26'}, m
    assert len([k for k in units if k.startswith('art-')]) == 42
    assert not any(re.search(r'(?i)entrar[aá] en vigencia|empezar[aá] a regir|regir[aá] a partir', ln)
                   for ln in actlib.lines(pid))
    v1 = first_version(key, pid, 'Ley N° 6925/2022', 'DE INCENTIVOS Y PROMOCIÓN DEL TRANSPORTE ELÉCTRICO EN EL '
                       'PARAGUAY', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-7617-2026'
    url, L, frm = bacn_law(k, '12961', 'Ley N° 7617/2026')
    assert frm == '2026-01-08', frm
    i = L.index('Artículo 120. Modificaciones.')
    b = L[i + 3]
    pre = ('b. El artículo 30 de la Ley Nº 6925/2022 "DE INCENTIVOS Y PROMOCIÓN DEL TRANSPORTE ELÉCTRICO EN EL '
           'PARAGUAY", que en su primer párrafo queda sustituido por el siguiente: "')
    assert b.startswith(pre) and b.endswith('"'), b
    new = b[len(pre):-1]
    assert new.startswith('La infraestructura y material rodante') and new.endswith('la Constitución y las leyes.')

    def first_par(u):
        ls = u['text'].split('\n')
        assert ls[:2] == ['# Artículo 30', 'Concesiones de Itinerarios.'] and len(ls) == 5 and ls[-1] == '', ls
        assert ls[2].startswith('La infraestructura y transporte eléctrico cuyas obras') and \
            ls[2].endswith('por imperio de la Ley.'), ls[2]
        return dict(u, text='\n'.join(ls[:2] + [new] + ls[3:]))
    rp.op(frm, k, url, 'fn', 'art-030', first_par)
    dec = [
        'Ley 6925/2022 de Incentivos y Promoción del Transporte Eléctrico en el Paraguay (BACN 11279): sanctioned 1 '
        'June 2022, wholly vetoed by Decreto 7364 of 8 July 2022, the veto rejected by both chambers (6 and 14 '
        'September 2022), promulgated 25 October 2022 and published 26 October 2022; no vigencia clause, so in '
        'force the day after publication (2022-10-27). Its tax exemptions run for terms counted from publication '
        '(arts. 10, 11) and its targets for the public fleet by year; those are its own wording, not versions.',
        'Ley 6925/2022: Ley 7617/2026 (BACN 12961; promulgated and published 7 January 2026, no vigencia clause, in '
        'force 2026-01-08) art. 120 b. replaces the first paragraph of art. 30. The epigraph printed after the '
        'number ("Concesiones de Itinerarios.") is not a paragraph, so the first paragraph is the one that follows '
        'it, both of its sentences (the second kept the workers of replaced transport systems in the new '
        'companies); the second paragraph (the fleet replacement plan) is unchanged. Ley 7617\'s other references '
        'to Ley 6925 (art. 51, vehicles; art. 68 b., the Fondo de Promoción del Transporte Eléctrico as a resource '
        'of its trust) are in its own words and change no words of Ley 6925.',
        'Ley 6925/2022: BACN searches "6925", "6925/2022", "6925/22", "6.925", "Ley N° 6925", "transporte '
        'eléctrico" and "vehículos eléctricos", screened for a modifying or repealing formula naming it: only Ley '
        '7617/2026.',
    ]
    return act(slug, 'LTE', 'Ley N° 6925/2022 de Incentivos y Promoción del Transporte Eléctrico en el Paraguay',
               key, rp.build()), dec


VIG = re.compile(r'(?i)entrar[aá] en vigencia|en vigor|empezar[aá] a regir|regir[aá] a partir|tendr[aá] vigencia')


# ------------------------------------------------------------------ Ley 45/1991 Divorcio vincular

def quoted_arts(L: list[str], start: int, stop: str) -> dict[int, list[str]]:
    """Quoted articles printed one paragraph per line after L[start], each opening with '"Art. N.°', '"Art. Nº' or
    '"Art. N.' (or '"Art. N°.-'), up to the first line starting with `stop`; quotation marks removed (parse.strip_quote)."""
    out: dict[int, list[str]] = {}
    cur = None
    for ln in L[start + 1:]:
        if ln.startswith(stop):
            break
        m = re.match(r'^"Art\. (\d+)\.?\s*[°º]?(?:\s+|\.-\s*)(.*)$', ln)
        if m:
            cur = int(m.group(1))
            assert cur not in out, cur
            out[cur] = [m.group(2)]
        else:
            assert cur is not None, ln
            out[cur].append(ln)
    return {n: parse.strip_quote(['"' + p[0]] + p[1:]) for n, p in out.items()}


def ley_45():
    slug, key, pid = 'ley-divorcio-vincular', 'ley-45-1991', '689'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1991-10-01', 'published': '1991-10-01'}, m
    L = actlib.lines(pid)
    assert not any(VIG.search(ln) for ln in L)
    assert ('Artículo 22º.- El artículo 163 del Código Civil queda redactado de la siguiente forma: "El matrimonio '
            'válido celebrado en la República se disuelve por la muerte de uno de los esposos y por el divorcio '
            'vincular. Igualmente, se disuelve en el caso del matrimonio celebrado por el cónyuge del declarado '
            'presuntamente fallecido".') in L
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 24
    v1 = first_version(key, pid, 'Ley N° 45/1991', 'QUE ESTABLECE EL DIVORCIO VINCULAR DEL MATRIMONIO',
                       plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    # Ley 5422/2015: rewrites arts. 4, 5, 6, 7 and 13 whole
    k = 'ley-5422-2015'
    url, L2, frm = bacn_law(k, '3879', 'Ley N° 5422/2015')
    assert frm == '2015-05-12', frm
    i = L2.index('Artículo 1.° Modifícanse los artículos 4º, 5º, 6º, 7º, y 13 de la Ley Nº 45/91 "Que establece el '
                 'divorcio vincular del matrimonio", que quedan redactados de la siguiente manera:')
    b = quoted_arts(L2, i, 'Artículo 2.°')
    assert sorted(b) == [4, 5, 6, 7, 13], sorted(b)
    assert b[4][0] == 'Son causales de divorcio:' and b[4][-1].startswith('i) cualquier otra causa'), b[4]
    assert b[5][0] == 'Los cónyuges podrán solicitar conjuntamente al juez su divorcio vincular.', b[5][0]
    assert len(b[4]) == 10 and len(b[5]) == 5 and len(b[6]) == len(b[7]) == len(b[13]) == 1
    j = L2.index('Artículo 2.° Deróguense todas las disposiciones contrarias a la presente ley.')
    assert L2[j + 1] == 'Artículo 3.° Comuníquese al Poder Ejecutivo.', L2[j + 1]
    for n in (4, 5, 6, 7, 13):
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, b[n], k))
    dec = [
        'Ley 45/1991 que establece el divorcio vincular del matrimonio (BACN 689): sanctioned 19 September 1991, '
        'promulgated and published 1 October 1991, no vigencia clause, so in force the day after publication '
        '(1991-10-02). Its art. 22 rewrites Código Civil art. 163; that change is in the Código Civil '
        '(`codigo-civil/`), credited to this law, and art. 22 stays here as the law\'s own text. Art. 23 repeals '
        'without naming them the articles of the Código Civil that contradict it, which changes no named words.',
        'Ley 45/1991: Ley 5422/2015 (BACN 3879; promulgated 5 May 2015, published 11 May 2015, no vigencia clause, '
        'in force 2015-05-12) art. 1 rewrites arts. 4, 5, 6, 7 and 13 whole (the grounds for divorce; the joint '
        'petition, no longer after three years of marriage; the spouse who petitions on the ground of '
        'interdicción). Its art. 2 repeals, without naming them, the provisions contrary to it, which changes no '
        'named words.',
        'Ley 45/1991: BACN searches "45/91", "45/1991", "Ley N° 45", "Ley Nº 45", "divorcio vincular" and '
        '"divorcio", and for its amender "5422", "5422/2015", "5422/15", "5.422" and "Ley N° 5422", screened for a '
        'modifying or repealing formula naming them: only Ley 5422/2015 changes its words.',
    ]
    versions = rp.build()
    assert [v['from'] for v in versions] == ['1991-10-02', '2015-05-12']
    return act(slug, 'LDV', 'Ley N° 45/1991 que establece el Divorcio Vincular del Matrimonio', key, versions), dec


# ------------------------------------------------------------------ Ley 1066/1997 Reuniones y manifestaciones

def ley_1066():
    pid = '9511'
    assert page_meta(url_of(pid)) == {'promulgated': '1997-06-17', 'published': '1997-06-23'}
    orig = actlib.lines

    def fixed(p):                     # art. 14's sentence is broken over two lines: "frente al" / "Palacio de ..."
        L2 = orig(p)
        if p == pid:
            i = L2.index('Artículo 14.- No se podrán realizar reuniones y manifestaciones públicas frente al')
            assert L2[i + 1].startswith('Palacio de Gobierno o a los cuarteles militares y policiales.'), L2[i + 1]
            L2 = L2[:i] + [L2[i] + ' ' + L2[i + 1]] + L2[i + 2:]
        return L2
    actlib.lines = fixed
    try:
        L = actlib.lines(pid)
        assert not any(VIG.search(ln) for ln in L)
        a, dec = single('ley-reuniones-publicas', 'LRP', 'Ley N° 1066/1997 que reglamenta el Artículo 32 de la '
                        'Constitución Nacional', 'ley-1066-1997', pid, 'Ley N° 1066/1997',
                        'QUE REGLAMENTA EL ARTICULO 32 DE LA CONSTITUCIÓN NACIONAL', [
            'Ley 1066/1997 que reglamenta el artículo 32 de la Constitución Nacional (freedom of assembly and '
            'demonstration; BACN 9511): promulgated 17 June 1997, published 23 June 1997, no vigencia clause, so in '
            'force the day after publication (1997-06-24). Its art. 17 repeals Ley 14/1990, which is not in this '
            'repository. BACN breaks the first sentence of art. 14 over two lines ("frente al" / "Palacio de '
            'Gobierno ..."); they are joined into one paragraph.',
            'Ley 1066/1997: BACN searches "1066", "1066/97", "1066/1997", "1.066", "Ley N° 1066" and "artículo 32 '
            'de la Constitución", screened for a modifying or repealing formula naming it: no law changes its '
            'words, so it has one version. The hits that name a "Ley No. 1.066" (Ley 419/1994) mean a 1965 law; '
            'others are amounts.',
        ])
    finally:
        actlib.lines = orig
    assert len([k for k in a['versions'][0]['units'] if k.startswith('art-')]) == 18
    assert len(a['versions']) == 1 and a['versions'][0]['from'] == '1997-06-24'
    return a, dec


# ------------------------------------------------------------------ Ley 5453/2015 Pedido de informes

def ley_5453():
    pid = '4442'
    assert page_meta(url_of(pid)) == {'promulgated': '2015-07-21', 'published': '2015-07-21'}
    slug, key = 'ley-pedido-de-informes', 'ley-5453-2015'
    L = actlib.lines(pid)
    assert not any(VIG.search(ln) for ln in L)
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 7
    assert units['art-003']['text'].startswith('# Artículo 3\nDe la forma y contenido de los informes.\n')
    v1 = first_version(key, pid, 'Ley N° 5453/2015', 'QUE REGLAMENTA EL ARTÍCULO 192 DE LA CONSTITUCIÓN NACIONAL, '
                       'DEL PEDIDO DE INFORMES', '2015-07-22', units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    # Ley 7199/2024: rewrites art. 3 whole
    k = 'ley-7199-2024'
    url, L2, frm = bacn_law(k, '12489', 'Ley N° 7199/2024')
    assert frm == '2024-08-06', frm
    i = L2.index('Artículo 1º Modifícase el artículo 3º de la Ley Nº 5453/2015 "QUE REGLAMENTA EL ARTÍCULO 192 DE LA '
                 'CONSTITUCIÓN NACIONAL, DEL PEDIDO DE INFORMES", que queda redactado de la siguiente manera:')
    b = quoted_arts(L2, i, 'Artículo 2º')
    assert sorted(b) == [3] and len(b[3]) == 3, b
    assert b[3][0] == 'De la forma y contenido de los informes.' and b[3][2].endswith('tales documentos'), b[3]
    rp.op(frm, k, url, 'set', 'art-003', unit_of(3, b[3], k))
    dec = [
        'Ley 5453/2015 del pedido de informes (BACN 4442): sanctioned 1 July 2015, promulgated and published 21 '
        'July 2015, no vigencia clause, so in force the day after publication (2015-07-22). Its art. 6 repeals art. '
        '1 of Ley 2648/2005 (plazos legislativos), which is not in this repository.',
        'Ley 5453/2015: Ley 7199/2024 (BACN 12489; sanctioned 12 June 2024 after the Senate accepted the '
        'Executive\'s partial objection (Decreto 694/2023) and sanctioned the part not objected to; promulgated 2 '
        'August 2024, published 5 August 2024, no vigencia clause, in force 2024-08-06) rewrites art. 3 whole '
        '(replies in electronic form with a qualified electronic signature). The text is BACN\'s, as printed: the '
        'quotation ends without a final full stop, and "documenlos" and "fÍsico" are kept.',
        'Ley 5453/2015: BACN searches "5453", "5453/2015", "5453/15", "5.453", "Ley N° 5453", "pedido de informes" '
        'and "artículo 192", and for its amender "7199", "7199/2024", "7.199" and "Ley N° 7199", screened for a '
        'modifying or repealing formula naming them: only Ley 7199/2024 changes its words.',
    ]
    versions = rp.build()
    assert [v['from'] for v in versions] == ['2015-07-22', '2024-08-06']
    return act(slug, 'LPINF', 'Ley N° 5453/2015 que reglamenta el Artículo 192 de la Constitución Nacional, del '
               'Pedido de Informes', key, versions), dec


# ------------------------------------------------------------------ Ley 4295/2011 Maltrato infantil

def ley_4295():
    pid = '3673'
    assert page_meta(url_of(pid)) == {'promulgated': '2011-05-03', 'published': '2011-05-04'}
    L = actlib.lines(pid)
    assert not any(VIG.search(ln) for ln in L)
    a, dec = single('ley-maltrato-infantil', 'LMI', 'Ley N° 4295/2011 que establece el Procedimiento Especial para '
                    'el Tratamiento del Maltrato Infantil en la Jurisdicción Especializada', 'ley-4295-2011', pid,
                    'Ley N° 4295/2011', 'QUE ESTABLECE EL PROCEDIMIENTO ESPECIAL PARA EL TRATAMIENTO DEL MALTRATO '
                    'INFANTIL EN LA JURISDICCION ESPECIALIZADA', [
        'Ley 4295/2011 del procedimiento especial para el maltrato infantil (BACN 3673): sanctioned 31 March 2011, '
        'promulgated 3 May 2011, published 4 May 2011, no vigencia clause, so in force the day after publication '
        '(2011-05-05). Its art. 13 routes the procedure of Código de la Niñez y la Adolescencia art. 191 through '
        'this law; that is its own wording and changes no words of the Code.',
        'Ley 4295/2011: BACN searches "4295", "4295/2011", "4295/11", "4.295", "Ley N° 4295" and "maltrato '
        'infantil", screened for a modifying or repealing formula naming it: no law changes its words, so it has '
        'one version.',
    ])
    assert len([k for k in a['versions'][0]['units'] if k.startswith('art-')]) == 14
    assert len(a['versions']) == 1 and a['versions'][0]['from'] == '2011-05-05'
    return a, dec


# ------------------------------------------------------------------ Ley 5189/2014 Remuneraciones (información pública)

def ley_5189():
    slug, key, pid = 'ley-informacion-remuneraciones', 'ley-5189-2014', '2962'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2014-05-20', 'published': '2014-05-21'}, m
    assert not any(VIG.search(ln) for ln in actlib.lines(pid))
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 10
    v1 = first_version(key, pid, 'Ley N° 5189/2014', 'QUE ESTABLECE LA OBLIGATORIEDAD DE LA PROVISIÓN DE '
                       'INFORMACIONES EN EL USO DE LOS RECURSOS PÚBLICOS SOBRE REMUNERACIONES Y OTRAS RETRIBUCIONES '
                       'ASIGNADAS AL SERVIDOR PÚBLICO DE LA REPÚBLICA DEL PARAGUAY', plus(m['published'], days=1),
                       units, 'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-5747-2016'
    url, L, frm = bacn_law(k, '8293', 'Ley N° 5747/2016')
    assert frm == '2016-11-25', frm
    i = next(n for n, ln in enumerate(L) if ln.startswith('Artículo 1°.- Modifícase el Artículo 8° de la Ley N° 5189 '
                                                            'de fecha 20 de mayo de 2014'))
    assert L[i].endswith('quedando redactado de la siguiente forma:'), L[i]
    b = quoted_arts(L, i, 'Artículo 2°')
    assert sorted(b) == [8] and len(b[8]) == 2, b
    assert b[8][0].startswith('Los Organismos y Entidades mencionadas en los incisos a), b), c) y d) del Artículo 2° '
                              'de la Ley N° 5189/14 "QUE ESTABLECE') and b[8][1].endswith('cobro judicial.'), b[8]
    rp.op(frm, k, url, 'set', 'art-008', unit_of(8, b[8], k))
    dec = [
        'Ley 5189/2014 (information on the remuneration of public servants; BACN 2962): sanctioned 8 May 2014, '
        'promulgated 20 May 2014, published 21 May 2014, no vigencia clause, so in force the day after publication '
        '(2014-05-22). Its art. 6 sets sixty days from publication to publish the data; that is its own wording, '
        'not a version.',
        'Ley 5189/2014: Ley 5747/2016 (BACN 8293; promulgated 22 November 2016, published 24 November 2016, no '
        'vigencia clause, in force 2016-11-25) rewrites art. 8 whole (the fine falls on the bodies, no longer on '
        'their heads, and the Secretaría de la Función Pública\'s resolution is an enforceable title).',
        'Ley 5189/2014: BACN searches "5189", "5189/2014", "5189/14", "5.189", "Ley N° 5189" and "remuneraciones", '
        'and for its amender "5747", "5747/2016", "5747/16", "5.747" and "Ley N° 5747", screened for a modifying or '
        'repealing formula naming them: only Ley 5747/2016 changes its words. Ley 6800/2021 (municipal addiction '
        'councils) makes the funds they administer subject to Ley 5189 in its own words; that changes no words of '
        'Ley 5189.',
    ]
    versions = rp.build()
    assert [v['from'] for v in versions] == ['2014-05-22', '2016-11-25']
    return act(slug, 'LIR', 'Ley N° 5189/2014 que establece la Obligatoriedad de la Provisión de Informaciones en el '
               'Uso de los Recursos Públicos sobre Remuneraciones y otras Retribuciones asignadas al Servidor Público',
               key, versions), dec


# ------------------------------------------------------------------ Ley 4601/2012 Vehículos eléctricos

def ley_4601():
    slug, key, pid = 'ley-vehiculos-electricos', 'ley-4601-2012', '2958'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2012-04-30', 'published': '2012-05-03'}, m
    assert not any(VIG.search(ln) for ln in actlib.lines(pid))
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 6
    v1 = first_version(key, pid, 'Ley N° 4601/2012', 'DE INCENTIVOS A LA IMPORTACION DE VEHICULOS ELECTRICOS',
                       plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    k = 'ley-5183-2014'
    url, L, frm = bacn_law(k, '2957', 'Ley N° 5183/2014')
    assert frm == '2014-05-27', frm
    assert not any(VIG.search(ln) for ln in L)
    i = L.index('Artículo 1°.- Modifícanse los artículos 1°, 2°, 3° y 4° de la Ley N° 4.601/12 "DE INCENTIVOS A LA '
                'IMPORTACIÓN DE VEHÍCULOS ELÉCTRICOS", cuyos textos quedan redactados de la siguiente manera:')
    b = quoted_arts(L, i, 'Artículo 2°')
    assert sorted(b) == [1, 2, 3, 4], sorted(b)
    # art. 1: BACN closes the quotation after its first paragraph and again after the second, which continues art. 1
    # before "Art. 2°" opens; the stray closing mark is dropped
    p1 = b[1]
    assert len(p1) == 2 and p1[0].endswith('vehículos eléctricos y vehículos híbridos nuevos."'), p1
    assert p1[1] == ('El presente beneficio tendrá una duración de diez años, contados a partir de la promulgación de '
                     'la presente ley.'), p1[1]
    b[1] = [p1[0][:-2] + '.', p1[1]]
    assert len(b[2]) == 1 and len(b[3]) == 2 and len(b[4]) == 2, b
    for n in (1, 2, 3, 4):
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, b[n], k))
    dec = [
        'Ley 4601/2012 de incentivos a la importación de vehículos eléctricos (BACN 2958): sanctioned 28 March 2012, '
        'promulgated 30 April 2012, published 3 May 2012, no vigencia clause, so in force the day after publication '
        '(2012-05-04).',
        'Ley 4601/2012: Ley 5183/2014 (BACN 2957; promulgated 22 May 2014, published 26 May 2014, no vigencia '
        'clause, in force 2014-05-27) rewrites arts. 1 to 4 whole (the exemption extended to new hybrid vehicles '
        'and limited to new vehicles, for ten years "contados a partir de la promulgación de la presente ley"; the '
        'Ministerio de Industria y Comercio\'s standards and charging points). BACN prints a closing quotation mark '
        'after the first paragraph of the new art. 1 and another after its second paragraph, which continues art. '
        '1 before "Art. 2°" opens: the first mark is taken as a misprint and both paragraphs are art. 1. The '
        'ten-year term is the exemption\'s own wording; no text lapses with it, so it is not a version.',
        'Ley 4601/2012: BACN searches "4601", "4601/2012", "4601/12", "4.601", "Ley N° 4601" and "vehículos '
        'eléctricos", and for its amender "5183", "5183/2014", "5183/14", "5.183" and "Ley N° 5183", screened for a '
        'modifying or repealing formula naming them: only Ley 5183/2014 changes its words. Ley 6925/2022 '
        '(electric transport) says it does not repeal the rules for other clean technologies, including those of '
        'Ley 4601; that changes no words of Ley 4601.',
    ]
    versions = rp.build()
    assert [v['from'] for v in versions] == ['2012-05-04', '2014-05-27']
    return act(slug, 'LVE', 'Ley N° 4601/2012 de Incentivos a la Importación de Vehículos Eléctricos', key,
               versions), dec


# ------------------------------------------------------------------ Ley 6202/2018 Abuso sexual de menores

def ley_6202():
    pid = '8927'
    assert page_meta(url_of(pid)) == {'promulgated': '2018-11-01', 'published': '2018-11-15'}
    assert not any(VIG.search(ln) for ln in actlib.lines(pid))
    a, dec = single('ley-prevencion-abuso-sexual', 'LPAS', 'Ley N° 6202/2018 que adopta normas para la Prevención '
                    'del Abuso Sexual y la Atención Integral de los Niños, Niñas y Adolescentes Víctimas de Abuso '
                    'Sexual', 'ley-6202-2018', pid, 'Ley N° 6202/2018', actlib.lines(pid)[2], [
        'Ley 6202/2018 (prevention of sexual abuse and care of child victims; BACN 8927): promulgated 1 November '
        '2018, published 15 November 2018, no vigencia clause, so in force the day after publication (2018-11-16).',
        'Ley 6202/2018: BACN searches "6202", "6202/2018", "6202/18", "6.202", "Ley N° 6202" and "abuso sexual", '
        'screened for a modifying or repealing formula naming it: no law changes its words, so it has one version.',
    ])
    assert len([k for k in a['versions'][0]['units'] if k.startswith('art-')]) == 11
    assert len(a['versions']) == 1 and a['versions'][0]['from'] == '2018-11-16'
    return a, dec


# ------------------------------------------------------------------ Ley 4013/2010 Objeción de conciencia

def ley_4013():
    pid = '3546'
    assert page_meta(url_of(pid)) == {'promulgated': '2010-06-17', 'published': '2010-06-18'}
    assert not any(VIG.search(ln) for ln in actlib.lines(pid))
    a, dec = single('ley-objecion-de-conciencia', 'LOC', 'Ley N° 4013/2010 que reglamenta el ejercicio del Derecho '
                    'a la Objeción de Conciencia al Servicio Militar Obligatorio y establece el Servicio Sustitutivo '
                    'al mismo en beneficio de la Población Civil', 'ley-4013-2010', pid, 'Ley N° 4013/2010',
                    actlib.lines(pid)[2], [
        'Ley 4013/2010 (conscientious objection to compulsory military service and the substitute civil service; '
        'BACN 3546): promulgated 17 June 2010, published 18 June 2010, no vigencia clause, so in force the day after '
        'publication (2010-06-19). Its art. 25 asks the Executive to set up the national council once the law is '
        'promulgated; that is its own wording, not a version.',
        'Ley 4013/2010: BACN searches "4013", "4013/2010", "4013/10", "4.013", "Ley N° 4013", "objeción de '
        'conciencia" and "servicio sustitutivo", screened for a modifying or repealing formula naming it: no law '
        'changes its words, so it has one version.',
    ])
    assert len([k for k in a['versions'][0]['units'] if k.startswith('art-')]) == 26
    assert len(a['versions']) == 1 and a['versions'][0]['from'] == '2010-06-19'
    return a, dec


# ------------------------------------------------------------------ Ley 1100/1997 Polución sonora (repealed 2020)

def ley_1100():
    slug, key, pid = 'ley-polucion-sonora', 'ley-1100-1997', '9414'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1997-08-26', 'published': None}, m
    L = actlib.lines(pid)
    assert not any(VIG.search(ln) for ln in L)
    assert 'Artículo 9º.- Se consideran ruidos y sonidos molestos a los que sobrepasen los niveles promedios que se ' \
           'especifican en el siguiente cuadro:' in L and 'DURACION POR HORAS Y DIAS' in L
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 15
    v1 = first_version(key, pid, 'Ley N° 1100/1997', 'DE PREVENCION DE LA POLUCION SONORA',
                       plus(m['promulgated'], days=1), units,
                       'The law as enacted, from its BACN page; BACN gives no publication date, so in force the '
                       'day after promulgation.')
    rp = Replay(slug, units, v1)
    k = 'ley-6390-2020'
    url, L2, frm = bacn_law(k, '9413', 'Ley N° 6390/2020')
    assert frm == '2020-01-14', frm
    assert not any(VIG.search(ln) for ln in L2 if not ln.startswith(('Las municipalidades establecerán',
                                                                      'Artículo 15.-')))
    assert 'Artículo 16.- Derógase la Ley N° 1100/97 "DE PREVENCIÓN DE LA POLUCIÓN SONORA".' in L2
    n0 = len(MISMATCHES)
    whole = rp.build()[-1]['units']   # every unit in force the day before the repeal (a dry run)
    del MISMATCHES[n0:]
    for u in sorted(whole):
        rp.op(frm, k, url, 'del', u)
    versions = rp.build()
    assert versions[-1]['units'] == {} and [v['from'] for v in versions] == ['1997-08-27', '2020-01-14']
    dec = [
        'Ley 1100/1997 de prevención de la polución sonora (BACN 9414): '
        'promulgated 26 August 1997; BACN gives no publication date and the law has no vigencia clause, so it is '
        'dated from the day after promulgation (1997-08-27). BACN has a second page for it (BACN 10406) with the '
        'same articles, where the two tables of arts. 9 and 10 read only "VER PDF"; page 9414 prints them as text '
        'and is the one used. Each table cell is one line, in BACN\'s order (row and column headings, then the '
        'values row by row).',
        'Ley 1100/1997 repealed: Ley 6390/2020 que regula la emisión de ruidos (BACN 9413; promulgated 9 January '
        '2020, published 13 January 2020, no vigencia clause, in force 2020-01-14) art. 16 repeals it by name, so '
        'every provision is removed from 2020-01-14 and the folder is empty from then on.',
        'Ley 1100/1997: BACN searches "1100", "1100/97", "1100/1997", "1.100", "Ley N° 1100" and "polución '
        'sonora", screened for a modifying or repealing formula naming it: only Ley 6390/2020 (the repeal). Other '
        'hits are amounts or Código Civil art. 1100.',
    ]
    return act(slug, 'LPS', 'Ley N° 1100/1997 de Prevención de la Polución Sonora', key, versions), dec


# ------------------------------------------------------------------ Ley 489/1995 Orgánica del Banco Central del Paraguay

B6104 = [3, 4, 5, 7, 8, 10, 13, 14, 17, 18, 19, 22, 26, 27, 29, 31, 32, 34, 35, 36, 37, 40, 42, 57, 58, 59, 60, 61, 65,
         68, 69, 70, 74, 81, 82, 83, 84, 89, 90, 91, 93, 94, 95, 96, 97, 106, 107, 109, 115, 117, 122]


def ley_489():
    slug, key, pid = 'ley-banco-central', 'ley-489-1995', '699'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1995-06-29', 'published': None}, m
    L = actlib.lines(pid)
    assert [ln for ln in L if VIG.search(ln)] == [
        'El cumplimiento de la remuneración de los encajes legales establecidos en los artículos 68 y 70 entrará en '
        'vigencia dentro de los 365 (trescientos sesenta y cinco) días, a partir de la promulgación de la presente '
        'ley.'], [ln for ln in L if VIG.search(ln)]
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 130
    v1 = first_version(key, pid, 'Ley N° 489/1995', 'ORGANICA DEL BANCO CENTRAL DEL PARAGUAY',
                       plus(m['promulgated'], days=1), units,
                       'The law as enacted, from its BACN page; BACN gives no publication date, so in force the '
                       'day after promulgation.')
    rp = Replay(slug, units, v1)
    # Ley 2226/2003: art. 29
    k = 'ley-2226-2003'
    url, L2, frm = bacn_law(k, '4892', 'Ley N° 2226/2003')
    assert frm == '2003-10-04', frm
    assert not any(VIG.search(ln) for ln in L2)
    set_arts(rp, frm, k, url, L2, r'^Artículo 1°\.- Modifícase el Artículo 29 de la Ley N° 489 del 29 de junio', [29])
    # Ley 2339/2003: art. 44
    k = 'ley-2339-2003'
    url, L2, frm = bacn_law(k, '5034', 'Ley N° 2339/2003')
    assert frm == '2004-01-13', frm
    assert not any(VIG.search(ln) for ln in L2)
    set_arts(rp, frm, k, url, L2, r'^Artículo 1º\.- Modifícase el Artículo 44 de la Ley N° 489/95', [44])
    # Ley 2598/2005: arts. 68 and 70 (BACN gives no publication date: bacn_law dates it from promulgation + 1)
    k = 'ley-2598-2005'
    url, L2, frm = bacn_law(k, '4134', 'Ley N° 2598/2005')
    assert frm == '2005-06-21', frm
    assert not any(VIG.search(ln) for ln in L2)
    set_arts(rp, frm, k, url, L2, r'^Artículo 1°\.- Modifícanse los Artículos 68 y 70 de la Ley N° 489/95', [68, 70])
    # Ley 4046/2010 art. 2: repeals art. 108; Ley 5456/2015's restatement of that art. 2 no longer lists it
    url, L2, frm = bacn_law('ley-4046-2010', '554', 'Ley N° 4046/2010')
    assert frm == '2010-07-31', frm
    a2 = [ln for ln in L2 if ln.startswith('Artículo 2º.- Deróganse los Artículos 1º de la Ley Nº 2.421/04')]
    assert len(a2) == 1 and 'Artículo 108 de la Ley Nº 489/95 "ORGÁNICA DEL BANCO CENTRAL DEL PARAGUAY"' in a2[0]
    r2 = [ln for ln in actlib.lines('4445') if ln.startswith('"Art. 2°.- Deróganse los Artículos 1° de la Ley N° '
                                                              '2421/04')]
    assert len(r2) == 1 and '489' not in r2[0] and 'Artículo 129 de la Ley N° 438/94' in r2[0], r2
    rp.op(frm, 'ley-4046-2010', url, 'del', 'art-108')
    # Ley 6104/2018: art. 1 rewrites 51 articles; art. 14 repeals arts. 110 to 114
    k = 'ley-6104-2018'
    url, L2, frm = bacn_law(k, '8424', 'Ley N° 6104/2018')
    assert frm == '2018-07-07', frm
    assert not any(VIG.search(ln) for ln in L2)
    i = next(j for j, ln in enumerate(L2) if ln.startswith('Artículo 1°.- Modifícanse los Artículos 3°, 4°, 5°, 7°'))
    assert L2[i].endswith(', 117 y 122, y amplíase la Ley N° 489/95 "ORGÁNICA DEL BANCO CENTRAL DEL PARAGUAY", cuyo '
                          'texto queda redactado de la siguiente manera:'), L2[i]
    assert [int(x) for x in re.findall(r'\d+', L2[i].split(' y amplíase')[0])[1:]] == B6104
    b = quoted_arts(L2, i, 'DE LA AMPLIACIÓN DE LA LEY N° 489/95')
    assert sorted(b) == B6104, sorted(b)
    assert L2[L2.index('DE LA AMPLIACIÓN DE LA LEY N° 489/95 "ORGÁNICA DEL BANCO CENTRAL DEL PARAGUAY"') + 2] == \
        'Artículo 2°.- Capital, Reservas y Resultados.'
    assert b[68][0] == 'Encajes Legales obre Operaciones en Moneda Nacional.', b[68][0]
    for n in B6104:
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, b[n], k))
    a14 = L2[L2.index('Artículo 14.- Derogaciones.') + 1]
    assert a14.startswith('Quedan derogadas todas las disposiciones contrarias a la presente Ley. Asimismo, quedan '
                          'derogados los Artículos 110, 111, 112, 113 y 114 de la Ley N° 489/95 '), a14
    for n in (110, 111, 112, 113, 114):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    # Ley 7066/2023: art. 7
    k = 'ley-7066-2023'
    url, L2, frm = bacn_law(k, '11459', 'Ley N° 7066/2023')
    assert frm == '2023-04-20', frm
    assert not any(VIG.search(ln) for ln in L2)
    i = L2.index('Artículo 1.º Modifícase el artículo 7° de la Ley N° 489/1995 "ORGÁNICA DEL BANCO CENTRAL DEL '
                 'PARAGUAY", modificado por la Ley Nº 6104/2018, el cual queda redactado de la siguiente manera:')
    b = quoted_arts(L2, i, 'Artículo 2.º')
    assert sorted(b) == [7] and len(b[7]) == 14, b
    rp.op(frm, k, url, 'set', 'art-007', unit_of(7, b[7], k))
    versions = rp.build()
    assert [v['from'] for v in versions] == ['1995-06-30', '2003-10-04', '2004-01-13', '2005-06-21', '2010-07-31',
                                             '2018-07-07', '2023-04-20'], [v['from'] for v in versions]
    dec = [
        'Ley 489/1995 Orgánica del Banco Central del Paraguay (BACN 699, 130 articles): sanctioned 15 November 1994, '
        'promulgated 29 June 1995 (the date its amenders cite: "Ley N° 489 del 29 de junio de 1995"); BACN gives no '
        'publication date and the law has no vigencia clause for the whole law (art. 126 only defers the payment '
        'of interest on reserve requirements by 365 days), so it is dated from the day after promulgation '
        '(1995-06-30).',
        'Ley 489/1995: Ley 2226/2003 (BACN 4892; promulgated 18 September 2003, published 3 October 2003, in force '
        '2003-10-04) rewrites art. 29; Ley 2339/2003 (BACN 5034; promulgated 26 December 2003, published 12 January '
        '2004, in force 2004-01-13) art. 44 (interest rates); Ley 2598/2005 (BACN 4134; promulgated 20 June 2005, '
        'no publication date on BACN, so dated 2005-06-21) arts. 68 and 70 (reserve requirements). None has a '
        'vigencia clause.',
        'Ley 489/1995: Ley 4046/2010 (contencioso-administrativo appeal deadline; BACN 554: promulgated 27 July '
        '2010, published 30 July 2010, no vigencia clause, so in force 2010-07-31) art. 2 repeals, among sixteen '
        'provisions that set other appeal deadlines, art. 108 (Recurso de Reconsideración, Acción '
        'Contencioso-Administrativa y sus Efectos); the article is removed from 2010-07-31. Ley 5456/2015 (BACN '
        '4445, published 21 July 2015) rewrites art. 2 of Ley 4046 and no longer lists art. 108 of Ley 489, but it '
        'gives the article no words and does not say it restores it, so art. 108 stays removed. Ley 6104/2018 '
        'agrees: its new art. 107 (Recursos de Reconsideración, Jerárquico y Acción Contencioso-Administrativa) '
        'covers the subject of the old art. 108 and it does not rewrite art. 108.',
        'Ley 489/1995: Ley 6104/2018 que modifica y amplía la Ley N° 489/95 (BACN 8424; promulgated 3 July 2018, '
        'published 6 July 2018, no vigencia clause, so in force 2018-07-07) art. 1 rewrites 51 articles whole (3, '
        '4, 5, 7, 8, 10, 13, 14, 17, 18, 19, 22, 26, 27, 29, 31, 32, 34, 35, 36, 37, 40, 42, 57 to 61, 65, 68, 69, '
        '70, 74, 81 to 84, 89, 90, 91, 93 to 97, 106, 107, 109, 115, 117 and 122), each printed with its epigraph, '
        'which stays as the first words of the text as in the enacted articles; and its art. 14 repeals arts. 110 '
        'to 114, which are removed from that day. BACN prints the new art. 68\'s epigraph "Encajes Legales obre '
        'Operaciones en Moneda Nacional": kept as printed. Its arts. 2 to 12 (the "ampliación": capital and '
        'reserves, services of third parties, discipline of the Bank\'s staff, electronic means, the insurance '
        'market) and its transitional art. 13 are in its own words with no number in Ley 489, so they are not '
        'inserted; indice.md keeps the enacted chapter headings (art. 1 names only articles).',
        'Ley 489/1995: Ley 7066/2023 (BACN 11459; promulgated and published 19 April 2023, no vigencia clause, in '
        'force 2023-04-20) rewrites art. 7 (exceptions to banking secrecy) as rewritten by Ley 6104.',
        'Ley 489/1995: other laws only cite it or act within it and change none of its words: the budget laws for '
        '2019, 2020, 2021 and 2023 (on the use of art. 58), Ley 3974/2010 (the monetary policy budget), Ley '
        '6809/2021 art. 33 (an exception to art. 60 for the 2021 Special Drawing Rights), Ley 7503/2025 (Sistema '
        'Nacional de Pagos, which acts under art. 45 and repeals Ley 4595/2012, not this law), Ley 7162/2023 '
        '(Superintendencia de Valores), Ley 5787/2016 and Ley 6769/2021.',
        'Ley 489/1995: BACN searches "489", "489/95", "489/1995", "489/95.", "Ley N° 489", "Ley Nº 489", "Ley No '
        '489", "Ley 489", "4.89", "Orgánica del Banco Central", "Carta Orgánica", "Banco Central del Paraguay", '
        '"Superintendencia de Bancos" and other subject words, and for its amenders "6104", "6104/2018", "6.104", '
        '"Ley Nº 6104", "2226/03", "2339/03", "2598/05", "7066" and "7066/2023", screened for a modifying or '
        'repealing formula naming it (by number or by name): Leyes 2226/2003, 2339/2003, 2598/2005, 4046/2010, '
        '6104/2018 and 7066/2023. The search for "Banco Central del Paraguay" lists only its first 147 of 389 hits; '
        'every amender found names Ley 489 by number.',
    ]
    return act(slug, 'LBCP', 'Ley N° 489/1995 Orgánica del Banco Central del Paraguay', key, versions), dec


# ------------------------------------------------------------------ Ley 861/1996 General de Bancos, Financieras y otras Entidades de Crédito

B5787 = [3, 11, 12, 14, 21, 26, 35, 36, 37, 38, 43, 45, 47, 48, 49, 50, 51, 52, 53, 55, 56, 58, 71, 86, 89, 91]
D5787 = [54, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69]


def ley_861():
    slug, key, pid = 'ley-general-de-bancos', 'ley-861-1996', '4135'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1996-06-24', 'published': '1996-06-24'}, m
    L = actlib.lines(pid)
    assert not any(VIG.search(ln) for ln in L)
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 164
    idx = units['indice']['text']
    for h in ('art-100: TITULO VIII - LA PROTECCION AL DEPOSITO EN EL SISTEMA FINANCIERO',
              'art-102: TITULO IX - CONTROL DE LAS ENTIDADES DEL SISTEMA FINANCIERO', 'art-110: CAPITULO II - RÉGIMEN '
              'DE VIGILANCIA', 'art-117: CAPITULO III - INTERVENCION', 'art-122: TITULO X - VENTA, DISOLUCIÓN Y '
              'LlQUIDACION', 'art-153: CAPITULO VI - DISOLUCIÓN Y LIQUIDACIÓN VOLUNTARIA',
              'art-155: DISPOSICIONES TRANSITORIAS'):
        assert h in idx, h
    v1 = first_version(key, pid, 'Ley N° 861/1996', 'GENERAL DE BANCOS, FINANCIERAS Y OTRAS ENTIDADES DE CREDITO',
                       plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    # Ley 1420/1999: suspends arts. 112, 114 and 115 for its one-year term; no word changes (a note)
    k = 'ley-1420-1999'
    url, L2, frm = bacn_law(k, '1616', 'Ley N° 1420/1999')
    assert frm == '1999-05-22', frm
    assert 'Durante la vigencia de esta ley quedarán suspendidas las disposiciones establecidas en los artículos 112, ' \
           '114 y 115 de la Ley N° 861/96.' in L2
    assert 'Esta ley estará vigente por el plazo de un año a partir de su promulgación.' in L2
    LAWS[k]['note'] = (
        'Sets a special one-year regime for the restructuring of the financial system (art. 1: in force for one year '
        'from its promulgation, 18 May 1999, and longer for restructurings begun and not finished) and, while it is in '
        'force, suspends arts. 112, 114 and 115 of the Ley General de Bancos. Their text does not change, and no '
        'lapse is recorded because the regime goes on for unfinished restructurings.')
    rp.op(frm, k, url, 'touch', 'art-112')
    # Ley 2334/2003 art. 36: "La promulgación de esta Ley reemplaza y deroga" Título VIII, Título IX caps. II-III and
    # Título X caps. I-VI (arts. 100-101, 110-121 and 122-154)
    k = 'ley-2334-2003'
    url, L2, frm = bacn_law(k, '2513', 'Ley N° 2334/2003', in_force='2003-12-12',
                            why='art. 36: "La promulgación de esta Ley reemplaza y deroga" the replaced titles and '
                                'chapters; promulgated and published 12 December 2003')
    assert ('Artículo 36.- La promulgación de esta Ley reemplaza y deroga las siguientes secciones de la Ley N° 861/96 '
            '"Ley General de Bancos, Financieras y Otras Entidades de Crédito": (a) Título VIII; (b) Capítulos II y '
            'III del Título IX; y (c) Capítulos I al VI del Título X.') in L2
    for n in [*range(100, 102), *range(110, 122), *range(122, 155)]:
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    # Ley 2451/2004: art. 66
    k = 'ley-2451-2004'
    url, L2, frm = bacn_law(k, '3960', 'Ley N° 2451/2004')
    assert frm == '2004-09-17', frm
    set_arts(rp, frm, k, url, L2, r'^Artículo 1º\.- Modifícase el Artículo 66 de la Ley N° 861/96', [66])
    # Ley 3899/2009 art. 25: art. 106
    k = 'ley-3899-2009'
    url, L2, frm = bacn_law(k, '1528', 'Ley N° 3899/2009')
    assert frm == '2009-11-24', frm
    set_arts(rp, frm, k, url, L2, r'^Artículo 25\.- Modifícase el Artículo 106 de la Ley Nº 861/96', [106])
    # Ley 4851/2013: art. 36
    k = 'ley-4851-2013'
    url, L2, frm = bacn_law(k, '3174', 'Ley N° 4851/2013')
    assert frm == '2013-01-11', frm
    set_arts(rp, frm, k, url, L2, r'^Artículo 1°\.- Modifícase el Artículo 36 de la Ley N° 861/96', [36])
    # Ley 5787/2016: art. 1 rewrites 26 articles; art. 4 repeals 12 articles (and Ley 4851/2013)
    k = 'ley-5787-2016'
    url, L2, frm = bacn_law(k, '8367', 'Ley N° 5787/2016')
    assert frm == '2016-12-27', frm
    i = next(j for j, ln in enumerate(L2) if ln.startswith('Artículo 1°.- Modifícanse los Artículos 3°, 11, 12, 14,'))
    assert [int(x) for x in re.findall(r'\d+', L2[i].split(' de la Ley N° 861')[0])[1:]] == B5787, L2[i]
    heads = ['CAPÍTULO II', 'GOBIERNO DE LA ENTIDAD. DIRECTORIO', 'RESPONSABILIDADES']
    h0 = L2.index(heads[0])
    assert L2[h0:h0 + 3] == heads and L2[h0 + 3].startswith('"Art. 35.-'), L2[h0:h0 + 4]
    b = quoted_arts(L2[:h0] + L2[h0 + 3:], i, 'Artículo 2°.- Disposiciones Transitorias.')
    assert sorted(b) == B5787, sorted(b)
    for n in B5787:
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, b[n], k))
    a4 = L2[L2.index('Artículo 4°.- Derogaciones.') + 1]
    assert a4.startswith('Deróganse los Artículos: 54, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68 y 69, de la Ley N° 861/96 ')
    for n in D5787:
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    versions = rp.build()
    assert [v['from'] for v in versions] == ['1996-06-25', '1999-05-22', '2003-12-12', '2004-09-17', '2009-11-24',
                                             '2013-01-11', '2016-12-27'], [v['from'] for v in versions]
    dec = [
        'Ley 861/1996 General de Bancos, Financieras y otras Entidades de Crédito (BACN 4135, 164 articles): '
        'promulgated and published 24 June 1996, no vigencia clause, so in force the day after publication '
        '(1996-06-25).',
        'Ley 861/1996: Ley 1420/1999 (special regime for restructuring the financial system; BACN 1616: promulgated 18 '
        'May 1999, published 21 May 1999) suspends arts. 112, 114 and 115 while it is in force (one year from its '
        'promulgation, longer for restructurings begun and not finished). It changes no words: a commit with a note '
        'on art. 112, dated the day after publication (1999-05-22), and no lapse commit, because its own text keeps it '
        'in force for unfinished restructurings with no end day.',
        'Ley 861/1996: Ley 2334/2003 de Garantía de Depósitos (BACN 2513; promulgated and published 12 December 2003) '
        'art. 36: "La promulgación de esta Ley reemplaza y deroga" Título VIII (arts. 100-101), Capítulos II and III '
        'of Título IX (arts. 110-121) and Capítulos I to VI of Título X (arts. 122-154), so those articles are removed '
        'from 12 December 2003, the day of promulgation the article names. The article ranges are those of the '
        'enacted headings (indice.md, which keeps them).',
        'Ley 861/1996: Ley 2451/2004 (BACN 3960; published 16 September 2004, in force 2004-09-17) rewrites art. 66; '
        'Ley 3899/2009 de sociedades calificadoras de riesgo (BACN 1528; published 23 November 2009, in force '
        '2009-11-24) art. 25 rewrites art. 106; Ley 4851/2013 (BACN 3174; published 10 January 2013, in force '
        '2013-01-11) rewrites art. 36. None has a vigencia clause. Ley 7572/2025 later repeals Ley 3899/2009 as a '
        'whole and Ley 5787/2016 repeals Ley 4851/2013; repealing an amending law does not undo the wording it already '
        'gave art. 106 and art. 36, so neither changes them (Ley 5787 rewrites art. 36 itself).',
        'Ley 861/1996: Ley 5787/2016 de modernización y fortalecimiento del sistema financiero (BACN 8367; promulgated '
        '19 December 2016, published 26 December 2016, no vigencia clause, so in force 2016-12-27) art. 1 rewrites 26 '
        'articles (3, 11, 12, 14, 21, 26, 35 to 38, 43, 45, 47 to 53, 55, 56, 58, 71, 86, 89 and 91) and art. 4 '
        'repeals arts. 54 and 59 to 69 (with art. 66 as worded by Ley 2451/2004). Its quotation also prints the '
        'headings "CAPÍTULO II", "GOBIERNO DE LA ENTIDAD. DIRECTORIO" and "RESPONSABILIDADES" before art. 35; art. 1 '
        'names only articles, so indice.md keeps the enacted heading. Its arts. 2 (transitional risk weights) and 3 '
        '(systemically important entities) are in its own words, with no number in Ley 861: not inserted.',
        'Ley 861/1996: Ley 1957/2002 (BACN 4370), titled "que amplía la Ley N° 861", sets a one-off refund of deposits '
        'of entities in liquidation in its own articles, with no number in Ley 861, so it changes no words; Ley '
        '2094/2003 repeals it. Other laws only cite Ley 861 or subject entities to it: Ley 1295/1998 (leasing), Ley '
        '2640/2005 and Leyes 3330 and 6769 (Agencia Financiera de Desarrollo), Ley 2723/2005, Ley 5542/2015, Ley '
        '7235/2023 and Ley 7503/2025.',
        'Ley 861/1996: BACN searches "861", "861/96", "861/1996", "Ley N° 861", "Ley Nº 861", "Ley No 861", "8.61", '
        '"General de Bancos", "Ley General de Bancos", "entidades de crédito", "entidades financieras" and, for its '
        'largest amender, "5787", "5.787" and "Ley Nº 5787", screened for a modifying, repealing or suspending formula '
        'naming it by number or by name: Leyes 1420/1999, 2334/2003, 2451/2004, 3899/2009, 4851/2013 and 5787/2016.',
    ]
    return act(slug, 'LGB', 'Ley N° 861/1996 General de Bancos, Financieras y otras Entidades de Crédito', key,
               versions), dec


# ------------------------------------------------------------------ Ley 2334/2003 Garantía de Depósitos

def ley_2334():
    slug, key, pid = 'ley-garantia-depositos', 'ley-2334-2003', '2513'
    url0, L, frm0 = bacn_law(key, pid, 'Ley N° 2334/2003', in_force='2003-12-12',
                             why='art. 36: "La promulgación de esta Ley reemplaza y deroga" the replaced titles and '
                                 'chapters; promulgated and published 12 December 2003')
    assert page_meta(url0) == {'promulgated': '2003-12-12', 'published': '2003-12-12'}
    assert [ln[:40] for ln in L if VIG.search(ln)] == [   # deadlines counted from it, "reglamentos en vigor"
        '1.- Aportes del Estado por un monto equi', 'f) incumplimiento reiterado de las medid',
        'Artículo 34.- Las contribuciones de las '], [ln[:40] for ln in L if VIG.search(ln)]
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 37
    v1 = first_version(key, pid, 'Ley N° 2334/2003', L[2].rstrip('.'), frm0, units,
                       'The law as enacted, from its BACN page; in force from its promulgation (art. 36).')
    rp = Replay(slug, units, v1)
    # Ley 2723/2005: rewrites inciso a) of art. 1 only
    k = 'ley-2723-2005'
    url, L2, frm = bacn_law(k, '4278', 'Ley N° 2723/2005')
    assert frm == '2005-09-28', frm
    assert not any(VIG.search(ln) for ln in L2)
    i = L2.index('Artículo 1°.- Modifícase el inciso a) del Artículo 1º de la Ley N° 2334/03 "De Garantía de Depósitos '
                 'y Resolución de Entidades de Intermediación Financiera Sujetos de la Ley General de Bancos, '
                 'Financieras y Otras Entidades de Crédito", el que queda redactado como sigue:')
    assert L2[i + 1] == '"Art. 1°.- Régimen de Garantía Legal de los Depósitos del Sistema Financiero.', L2[i + 1]
    new_a = L2[i + 2]
    assert new_a.startswith('a) Naturaleza. ') and new_a.endswith('Préstamo para la Vivienda."'), new_a
    assert L2[i + 3].startswith('Artículo 2°.- Modifícase el Artículo 2º de la Ley N° 1896'), L2[i + 3]
    new_a = new_a[:-1]
    old_a = next(p for p in units['art-001']['text'].split('\n') if p.startswith('a) Naturaleza. '))

    def put_a(u, o=old_a, n=new_a):
        assert u['text'].count(o) == 1
        return dict(u, text=u['text'].replace(o, n))
    rp.op(frm, k, url, 'fn', 'art-001', put_a)
    versions = rp.build()
    assert [v['from'] for v in versions] == ['2003-12-12', '2005-09-28'], [v['from'] for v in versions]
    dec = [
        'Ley 2334/2003 de Garantía de Depósitos y Resolución de Entidades de Intermediación Financiera (BACN 2513, 37 '
        'articles): sanctioned 27 November 2003, promulgated and published 12 December 2003. It has no general '
        'vigencia clause, but its art. 36 says "La promulgación de esta Ley reemplaza y deroga" Título VIII, '
        'Capítulos II and III of Título IX and Capítulos I to VI of Título X of Ley 861/1996, which this law\'s '
        'chapters replace; so the law is dated from its promulgation (2003-12-12), the same day those parts of Ley '
        '861/1996 are removed in `ley-general-de-bancos/`, rather than the day after publication. Art. 34 counts six '
        'months from "la entrada en vigor de esta Ley" for the first contributions to the fund; that is its own '
        'wording, not a version.',
        'Ley 2334/2003: Ley 2723/2005 (BACN 4278; promulgated and published 27 September 2005, no vigencia clause, in '
        'force 2005-09-28) art. 1 rewrites inciso a) of art. 1 (the guarantee covers the private entities supervised '
        'by the Superintendencia de Bancos listed in art. 11 of Ley 861/1996). Its quotation repeats the article\'s '
        'number and epigraph ("Régimen de Garantía Legal ..."), but the law amends only inciso a), so the enacted '
        'epigraph and the other incisos stay.',
        'Ley 2334/2003: Ley 2502/2004 (BACN 2512; promulgated 30 December 2004, published 4 January 2005) art. 2 '
        'exempts the Banco Nacional de Fomento from this law ("Exceptúase ... del alcance y aplicación") in its own '
        'words; it changes no words of this law.',
        'Ley 2334/2003: other laws only cite it or act within it: the budget laws for 2012, 2014, 2019 to 2023 and Ley '
        '5248 authorise the Fondo de Garantía de Depósitos to invest or receive state contributions, and Leyes '
        '6769/2021 and 7503/2025 refer to its resolution procedure.',
        'Ley 2334/2003: BACN searches "2334", "2334/03", "2334/2003", "2.334", "Ley N° 2334", "Ley Nº 2334", '
        '"Garantía de Depósitos" and "Fondo de Garantía de Depósitos", and for its amenders "2723/05", "2723/2005", '
        '"2502/04" and "2502/2004", screened for a modifying, repealing or suspending formula naming it by number or '
        'by name: Leyes 2723/2005 and 2502/2004 (an exemption, no word change).',
    ]
    return act(slug, 'LGD', 'Ley N° 2334/2003 de Garantía de Depósitos y Resolución de Entidades de Intermediación '
               'Financiera sujetos de la Ley General de Bancos, Financieras y otras Entidades de Crédito', key,
               versions), dec


# ------------------------------------------------------------------ Ley 2640/2005 Agencia Financiera de Desarrollo

B6769 = [1, 2, 3, 4, 5, 6, 7, 10, 11, 13, 14, 16, 17, 20]


def ley_2640():
    slug, key, pid = 'ley-agencia-financiera-desarrollo', 'ley-2640-2005', '3380'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2005-07-27', 'published': '2005-07-29'}, m
    L = actlib.lines(pid)
    assert ('El Poder Ejecutivo reglamentará la presente ley que entrará en vigencia al día siguiente de su '
            'publicación. La AFD creada por esta ley entrará a operar en un plazo máximo de un año contados a partir de '
            'la vigencia de esta ley.') in L
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 23
    v1 = first_version(key, pid, 'Ley N° 2640/2005', 'QUE CREA LA AGENCIA FINANCIERA DE DESARROLLO',
                       plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication (art. 21).')
    rp = Replay(slug, units, v1)
    # Ley 3330/2007: arts. 1, 3, 5, 6 and 14
    k = 'ley-3330-2007'
    url, L2, frm = bacn_law(k, '3379', 'Ley N° 3330/2007')
    assert frm == '2007-10-30', frm
    assert not any(VIG.search(ln) for ln in L2)
    set_arts(rp, frm, k, url, L2, r'^Artículo 1º\.- Modifícanse los Artículos 1º, 3º, 5º, 6º y 14 de la Ley Nº 2640/05',
             [1, 3, 5, 6, 14])
    # Ley 3655/2008: art. 22
    k = 'ley-3655-2008'
    url, L2, frm = bacn_law(k, '1837', 'Ley N° 3655/2008')
    assert frm == '2008-11-28', frm
    set_arts(rp, frm, k, url, L2, r'^Artículo 1°\.- Modifícase el Artículo 22 de la Ley Nº 2640/05', [22])
    # Ley 6524/2020 (COVID-19 emergency) arts. 28-29: art. 5's limit may be exceeded and art. 15 is partly suspended
    # while the emergency measures last; no word changes (a note)
    k = 'ley-6524-2020'
    url, L2, frm = bacn_law(k, '9156', 'Ley N° 6524/2020')
    assert frm == '2020-03-27', frm
    assert 'Artículo 54.- Esta Ley entrará en vigencia desde el día siguiente a su publicación.' in L2
    a29 = [ln for ln in L2 if 'Agencia Financiera de Desarrollo' in ln and 'Ley N° 2640' in ln]
    assert len(a29) == 1 and a29[0].startswith('Artículo 29.- Autorízase la suspensión parcial de la aplicación '
                                               'estricta del Artículo 15 de la Ley N° 2640/2005'), a29
    assert any(ln.startswith('Artículo 28.- Autorízase a la Agencia Financiera de Desarrollo (AFD) a sobrepasar el '
                             'límite porcentual establecido en el Artículo 5°, in fine') for ln in L2)
    LAWS[k]['note'] = NOTE_6524                    # shared with part 99-38 (Ley 5098 art. 47 suspension)
    rp.op(frm, k, url, 'touch', 'art-005')
    rp.op(frm, k, url, 'touch', 'art-015')
    # Ley 6769/2021: 14 articles; its arts. 2-4 are its own words; art. 5 abrogates Ley 3330/2007
    k = 'ley-6769-2021'
    url, L2, frm = bacn_law(k, '9627', 'Ley N° 6769/2021')
    assert frm == '2021-07-17', frm
    assert not any(VIG.search(ln) for ln in L2)
    set_arts(rp, frm, k, url, L2, r'^Artículo 1°\.- Modifícanse los Artículos 1°, 2°, 3°, 4°, 5°, 6°, 7°, 10, 11, 13, '
             r'14, 16, 17 y 20 de la Ley N° 2640/2005', B6769)
    assert L2[L2.index('Artículo 5°.- Abrogaciones.') + 1].startswith('Abrógase la Ley N° 3330/2007 ')
    versions = rp.build()
    assert [v['from'] for v in versions] == ['2005-07-30', '2007-10-30', '2008-11-28', '2020-03-27', '2021-07-17'], \
        [v['from'] for v in versions]
    dec = [
        'Ley 2640/2005 que crea la Agencia Financiera de Desarrollo (BACN 3380, 23 articles): sanctioned 21 July 2005, '
        'promulgated 27 July 2005, published 29 July 2005; art. 21: "entrará en vigencia al día siguiente de su '
        'publicación", so in force 2005-07-30. The year within which the AFD had to begin operating is its own '
        'wording, not a version.',
        'Ley 2640/2005: Ley 3330/2007 (BACN 3379; promulgated 18 October 2007, published 29 October 2007, no vigencia '
        'clause, in force 2007-10-30) rewrites arts. 1, 3, 5, 6 and 14 whole; Ley 3655/2008 (BACN 1837; published 27 '
        'November 2008, in force 2008-11-28) rewrites art. 22 whole (dissolution of the entities absorbed by the AFD, '
        'now also the Banco Nacional de la Vivienda; the dates inside it, "desde la promulgación de la presente Ley", '
        'are its own wording).',
        'Ley 2640/2005: Ley 6524/2020 (COVID-19 emergency; BACN 9156: promulgated and published 26 March 2020, art. '
        '54: in force the day after publication, 2020-03-27) art. 28 authorises the AFD to exceed the percentage limit '
        'at the end of art. 5 and art. 29 authorises a partial suspension of the strict application of art. 15, both '
        'while the emergency measures last. They change no words: a commit with a note on arts. 5 and 15, and no '
        'lapse commit, because the end of the measures has no day in the law.',
        'Ley 2640/2005: Ley 6769/2021 (BACN 9627; promulgated and published 16 July 2021, no vigencia clause, in force '
        '2021-07-17) art. 1 rewrites arts. 1 to 7, 10, 11, 13, 14, 16, 17 and 20 whole. Its arts. 2 to 4 (the '
        'Gerencia General, its functions, the staff) are in its own words with no number in Ley 2640, so they are not '
        'inserted. Its art. 5 abrogates Ley 3330/2007; repealing an amending law does not undo the wording it gave, '
        'and Ley 6769 rewrites every article Ley 3330 had changed, so no text changes by the abrogation.',
        'Ley 2640/2005: other laws only cite it or act within it and change none of its words: budget laws (bond '
        'issues and guarantees "en concordancia con" it), loan and budget-extension laws for the AFD, Ley 5638 '
        '(housing), Ley 6873 and later budget laws (the Fondo Fiduciario de Garantía y Liquidez), Ley 7444/2025 '
        '(FONAMIPYMES), Ley 7504/2025 and Ley 7617/2026 (trusts that may be placed with the AFD).',
        'Ley 2640/2005: BACN searches "2640", "2640/05", "2640/2005", "2.640", "Ley N° 2640", "Ley Nº 2640" and '
        '"Agencia Financiera de Desarrollo", and for its amenders "3330/07", "3330/2007", "3655/08", "3655/2008" and '
        '"6769/2021", screened for a modifying, repealing or suspending formula naming it by number or by name: Leyes '
        '3330/2007, 3655/2008, 6524/2020 (a suspension) and 6769/2021.',
    ]
    return act(slug, 'LAFD', 'Ley N° 2640/2005 que crea la Agencia Financiera de Desarrollo', key, versions), dec


# ------------------------------------------------------------------ Ley 5097/2013 Cuenta Única y Títulos de Deuda del Tesoro

def ley_5097():
    slug, key, pid = 'ley-cuenta-unica-tesoro', 'ley-5097-2013', '4670'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2013-10-29', 'published': '2013-10-31'}, m
    L = actlib.lines(pid)
    assert not any(VIG.search(ln) for ln in L)
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 23
    v1 = first_version(key, pid, 'Ley N° 5097/2013', L[2].rstrip('.'), plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    # Ley 6104/2018 art. 14: repeals arts. 10 and 20
    k = 'ley-6104-2018'
    url, L2, frm = bacn_law(k, '8424', 'Ley N° 6104/2018')
    assert frm == '2018-07-07', frm
    a14 = L2[L2.index('Artículo 14.- Derogaciones.') + 1]
    assert ', así como los Artículos 10 y 20 de la Ley N° 5097/13 "QUE DISPONE MEDIDAS DE MODERNIZACIÓN' in a14, a14
    for n in (10, 20):
        rp.op(frm, k, url, 'del', f'art-{n:03d}')
    # Ley 6638/2020 art. 1: arts. 17, 18 and 22; its arts. 2-6 are its own words
    k = 'ley-6638-2020'
    url, L2, frm = bacn_law(k, '9436', 'Ley N° 6638/2020')
    assert frm == '2020-11-19', frm
    assert not any(VIG.search(ln) for ln in L2)
    i = next(j for j, ln in enumerate(L2) if ln.startswith('Artículo 1.º Modifícanse y amplíanse los artículos 17, 18 '
                                                            'y 22 de la Ley N° 5.097/2013'))
    assert L2[i].endswith('que quedan redactados de la siguiente forma:'), L2[i]
    b = quoted_arts(L2, i, 'CAPÍTULO I')
    assert sorted(b) == [17, 18, 22] and len(b[17]) == 3 and len(b[18]) == 3 and len(b[22]) == 1, b
    assert L2[L2.index('CAPÍTULO I') + 1].startswith('DISPOSICIONES COMPLEMENTARIAS A LA LEY N° 5.097/2013')
    for n in (17, 18, 22):
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, b[n], k))
    versions = rp.build()
    assert [v['from'] for v in versions] == ['2013-11-01', '2018-07-07', '2020-11-19'], [v['from'] for v in versions]
    dec = [
        'Ley 5097/2013 que dispone medidas de modernización de la administración financiera del Estado y establece el '
        'régimen de cuenta única y de los títulos de deuda del Tesoro Público (BACN 4670, 23 articles): sanctioned 17 '
        'October 2013, promulgated 29 October 2013, published 31 October 2013, no vigencia clause, so in force the day '
        'after publication (2013-11-01). Its art. 21 rewrites an article of Ley 1535/1999 (Administración Financiera '
        'del Estado), which is not in this repository; the quotation stays here as the law\'s own text.',
        'Ley 5097/2013: Ley 6104/2018 que modifica y amplía la Ley N° 489/95 (BACN 8424; published 6 July 2018, in '
        'force 2018-07-07) art. 14 repeals arts. 10 (investment of the Treasury\'s surpluses) and 20 (the Banco '
        'Central\'s remuneration of Treasury deposits), which are removed from that day; indice.md keeps the enacted '
        'heading of Capítulo V at art. 20.',
        'Ley 5097/2013: Ley 6638/2020 (BACN 9436; promulgated 10 November 2020, published 18 November 2020, no '
        'vigencia clause, in force 2020-11-19) art. 1 "Modifícanse y amplíanse" arts. 17, 18 and 22, which it prints '
        'whole (placement and payment of Treasury bonds; debt management operations; the budget and accounting '
        'mechanisms). Its arts. 2 to 6 ("Disposiciones complementarias a la Ley N° 5.097/2013" and administrative '
        'measures) are in its own words with no number in Ley 5097, so they are not inserted.',
        'Ley 5097/2013: other laws only cite it or make exceptions to it for one fiscal year, which change none of its '
        'words: the budget laws for 2019 to 2023 (financial reports under art. 4, the use of art. 7, bond issues '
        '"de conformidad con" it), Ley 6985/2022, Ley 6809/2021 art. 38 and Ley 7218/2023 art. 5 (exceptions to art. '
        '12).',
        'Ley 5097/2013: BACN searches "5097", "5097/13", "5097/2013", "5.097", "Ley N° 5097", "Ley Nº 5097", '
        '"Cuenta Única" and "Títulos de Deuda del Tesoro", and for its amender "6638", "6638/2020", "6638/20", '
        '"6.638" and "Ley N° 6638", screened for a modifying, repealing or suspending formula naming it by number or '
        'by name: Leyes 6104/2018 and 6638/2020.',
    ]
    return act(slug, 'LCUT', 'Ley N° 5097/2013 que dispone Medidas de Modernización de la Administración Financiera '
               'del Estado y establece el Régimen de Cuenta Única y de los Títulos de Deuda del Tesoro Público', key,
               versions), dec


# ------------------------------------------------------------------ Ley 1682/2001 Información de carácter privado (repealed 2020)

def ley_1682():
    slug, key, pid = 'ley-informacion-caracter-privado', 'ley-1682-2001', '1760'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2001-01-16', 'published': '2001-01-19'}, m
    L = actlib.lines(pid)
    vig = [ln for ln in L if VIG.search(ln)]
    assert len(vig) == 1 and vig[0].startswith('Artículo 11.- La presente ley entrará en vigencia a los seis meses de '
                                               'su publicación,'), vig
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 12
    v1 = first_version(key, pid, 'Ley N° 1682/2001', 'QUE REGLAMENTA LA INFORMACIÓN DE CARÁCTER PRIVADO',
                       plus(m['published'], months=6), units,
                       'The law as enacted, from its BACN page; in force six months after publication (art. 11).')
    rp = Replay(slug, units, v1)
    # Ley 1969/2002: arts. 1, 2, 5, 7, 9 and 10
    k = 'ley-1969-2002'
    url, L2, frm = bacn_law(k, '2539', 'Ley N° 1969/2002')
    assert frm == '2002-09-07', frm
    assert not any(VIG.search(ln) for ln in L2)
    set_arts(rp, frm, k, url, L2, r'^Artículo 1°\.- Modifícanse los Artículos 1°, 2°, 5°, 7°, 9° y 10 de la Ley N° '
             r'1682/2001', [1, 2, 5, 7, 9, 10])
    # Ley 5543/2015: arts. 5 and 9
    k = 'ley-5543-2015'
    url, L2, frm = bacn_law(k, '4524', 'Ley N° 5543/2015')
    assert frm == '2015-12-17', frm
    assert not any(VIG.search(ln) for ln in L2)
    i = next(j for j, ln in enumerate(L2) if ln.startswith('Artículo 1.° Modifícanse los artículos 5° y 9° de la Ley '
                                                            'N° 1.682/01'))
    b = quoted_arts(L2, i, 'Artículo 2.°')          # '"Art. 5.° ...': the number, then a full stop and the degree sign
    assert sorted(b) == [5, 9] and len(b[5]) == 5 and len(b[9]) == 5, b
    assert b[5][0].startswith('Los datos de personas') and b[9][0].startswith('Las empresas, personas'), b
    for n in (5, 9):
        rp.op(frm, k, url, 'set', f'art-{n:03d}', unit_of(n, b[n], k))
    # Ley 6534/2020 art. 30: repeals the law (record as in part 60-datos-crediticios)
    k = 'ley-6534-2020'
    url = url_of('9417')
    m6 = page_meta(url)
    assert m6 == {'promulgated': '2020-10-27', 'published': '2020-10-27'}, m6
    L2 = actlib.lines('9417')
    assert ('Artículo 30.- DEROGACIONES. Queda derogada la Ley N° 1682/2001 "QUE REGLAMENTA LA INFORMACIÓN DE CARÁCTER '
            'PRIVADO" y sus respectivas Leyes modificatorias.') in L2
    if k not in LAWS:
        law(k, label='Ley N° 6534/2020', title='De Protección de Datos Personales Crediticios', kind='law',
            enacted=m6['promulgated'], published=m6['published'], url=url)
    frm = plus(m6['published'], days=1)
    n0 = len(MISMATCHES)
    whole = rp.build()[-1]['units']   # every unit in force the day before the repeal (a dry run)
    del MISMATCHES[n0:]
    for u in sorted(whole):
        rp.op(frm, k, url, 'del', u)
    versions = rp.build()
    assert versions[-1]['units'] == {} and [v['from'] for v in versions] == [
        '2001-07-19', '2002-09-07', '2015-12-17', '2020-10-28'], [v['from'] for v in versions]
    dec = [
        'Ley 1682/2001 que reglamenta la información de carácter privado (BACN 1760, 12 articles): sanctioned 28 '
        'December 2000, promulgated 16 January 2001, published 19 January 2001; art. 11: "entrará en vigencia a los '
        'seis meses de su publicación", so in force 2001-07-19 (the same day six months on, Código Civil arts. 339 to '
        '341).',
        'Ley 1682/2001: Ley 1969/2002 que modifica, amplía y deroga varios artículos (BACN 2539; promulgated 2 '
        'September 2002, published 6 September 2002, no vigencia clause, in force 2002-09-07) art. 1 rewrites arts. 1, '
        '2, 5, 7, 9 and 10 whole. Its new art. 2 takes in the enacted art. 1 sentence, and its new art. 9 prints only '
        'incisos b), c) and h) with their original letters: incisos a) and d) to g) are not in the new wording, so they '
        'go, and the letters are kept as printed; its new art. 10 has incisos a) to c) only, so the enacted inciso d) '
        'and the closing paragraphs (the competent court, the share of the fines, other actions) go too. The '
        'quotations close with the quotation mark before the final full stop; the stop is kept.',
        'Ley 1682/2001: Ley 5543/2015 (BACN 4524; promulgated 11 December 2015, published 16 December 2015, no '
        'vigencia clause, in force 2015-12-17) rewrites arts. 5 (adds inciso d)) and 9 (data no longer reported once a '
        'debt is paid) as worded by Ley 1969/2002.',
        'Ley 1682/2001 repealed: Ley 6534/2020 de Protección de Datos Personales Crediticios (BACN 9417; in force '
        '2020-10-28, see `ley-datos-crediticios/`) art. 30 repeals it "y sus respectivas Leyes modificatorias", so every '
        'provision is removed from 2020-10-28 and the folder is empty from then on.',
        'Ley 1682/2001: BACN searches "1682", "1682/01", "1682/2001", "1.682", "Ley N° 1682", "Ley Nº 1682" and '
        '"información de carácter privado", screened for a modifying or repealing formula naming it by number or by '
        'name: Leyes 1969/2002, 5543/2015 and 6534/2020 (the repeal). Other hits are a loan contract numbered 1682 '
        'and amounts.',
    ]
    return act(slug, 'LICP', 'Ley N° 1682/2001 que reglamenta la Información de Carácter Privado', key, versions), dec


# ------------------------------------------------------------------ Ley 2523/2004 Enriquecimiento ilícito

def ley_2523():
    pid = '4020'
    assert page_meta(url_of(pid)) == {'promulgated': '2004-12-13', 'published': '2004-12-30'}
    assert not any(VIG.search(ln) for ln in actlib.lines(pid))
    a, dec = single('ley-enriquecimiento-ilicito', 'LEIFP', 'Ley N° 2523/2004 que previene, tipifica y sanciona el '
                    'Enriquecimiento Ilícito en la Función Pública y el Tráfico de Influencias', 'ley-2523-2004', pid,
                    'Ley N° 2523/2004', actlib.lines(pid)[2], [
        'Ley 2523/2004 (illicit enrichment in public office and influence peddling; BACN 4020): sanctioned 25 November '
        '2004, promulgated 13 December 2004, published 30 December 2004, no vigencia clause, so in force the day after '
        'publication (2004-12-31). Its art. 10 repeals Decreto-Ley 448/1940, which is not in this repository.',
        'Ley 2523/2004: BACN searches "2523", "2523/2004", "2.523", "Ley N° 2523", "Ley Nº 2523", "enriquecimiento '
        'ilícito" and "tráfico de influencias", screened for a modifying or repealing formula naming it by number or by '
        'name: no law changes its words, so it has one version.',
    ])
    assert len([k for k in a['versions'][0]['units'] if k.startswith('art-')]) == 11
    assert len(a['versions']) == 1 and a['versions'][0]['from'] == '2004-12-31'
    return a, dec


# ------------------------------------------------------------------ Ley 827/1996 de Seguros

LEY_2421_ART_38 = ('Artículo 38.- Las disposiciones de la presente ley entrarán en vigencia en la fecha que lo '
                   'determine el Poder Ejecutivo, dentro del año de la sanción, promulgación y publicación de la Ley.')


def ley_827():
    slug, key, pid = 'ley-seguros', 'ley-827-1996', '703'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1995-12-18', 'published': '1996-02-12'}, m
    L = actlib.lines(pid)
    # the definitions are printed before art. 1, under their own headings
    d0 = L.index('CAPITULO ÚNICO')
    assert d0 == 5 and L[d0 + 1:d0 + 4] == ['De los Aseguradores y Reaseguradores', 'DEFINICIONES',
                                           'Para los efectos de esta Ley se entenderá por:'], L[d0:d0 + 4]
    d1 = L.index('CAPITULO I')
    assert L[d1 + 1:d1 + 5] == ['De los Aseguradores y Reaseguradores', 'SECCION I', 'Ambito de Aplicación',
                                L[d1 + 4]] and L[d1 + 4].startswith('Artículo 1°.- Actividades comprendidas.'), L[d1:]
    defs = L[d0 + 3:d1]
    assert defs[1].startswith('a) Autoridad de Control:') and defs[-1].startswith('n) Sección de seguro'), defs
    orig = actlib.lines

    def without_defs(p):
        return orig(p)[:d0] + orig(p)[d1:] if p == pid else orig(p)
    actlib.lines = without_defs
    try:
        units = enacted(pid, slug, 5)
    finally:
        actlib.lines = orig
    assert len([k for k in units if k.startswith('art-')]) == 137
    units['definiciones'] = parse.unit('Definiciones', 'definitions', 'Definiciones', defs)
    idx = units['indice']['text'].split('\n')
    assert idx[1] == 'art-001: CAPITULO I - De los Aseguradores y Reaseguradores', idx[1]
    idx.insert(1, 'definiciones: CAPITULO ÚNICO - De los Aseguradores y Reaseguradores / DEFINICIONES')
    units['indice'] = dict(units['indice'], text='\n'.join(idx))
    actlib.check_lines(slug, L[5:actlib.closing_index(L) + 1], units)
    vig = [ln[:40] for ln in L if VIG.search(ln)]
    assert vig == ['1) Provisiones para riesgos en curso por', 'Artículo 134°.- Plazo para la acreditaci'], vig
    v1 = first_version(key, pid, 'Ley N° 827/1996', 'DE SEGUROS', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    # Ley 3899/2009 art. 26: art. 61 inciso d)
    k = 'ley-3899-2009'
    url, L2, frm = bacn_law(k, '1528', 'Ley N° 3899/2009')
    assert frm == '2009-11-24', frm
    i = L2.index('Artículo 26.- Modifícase el Artículo 61, inciso d) de la Ley Nº 827/96 "DE SEGUROS", que queda '
                 'redactado de la siguiente manera:')
    new_d = L2[i + 1]
    assert new_d.startswith('"d) publicar los principales') and new_d.endswith('de la capital;"'), new_d
    assert L2[i + 2] == 'Artículo 27.- Comuníquese al Poder Ejecutivo.', L2[i + 2]
    new_d = new_d[1:-1]

    def repl(prefix, new):
        def f(u):
            ps = [p for p in u['text'].split('\n') if p.startswith(prefix)]
            assert len(ps) == 1, (prefix, ps)
            t = u['text'].replace(ps[0] + '\n', (new + '\n') if new is not None else '')
            assert t != u['text']
            return dict(u, text=t)
        return f
    rp.op(frm, k, url, 'fn', 'art-061', repl('d) Clasificar las empresas de seguro', new_d))
    # Ley 6104/2018 art. 14: repeals art. 49 inciso b)
    k = 'ley-6104-2018'
    url, L2, frm = bacn_law(k, '8424', 'Ley N° 6104/2018')
    assert frm == '2018-07-07', frm
    a14 = L2[L2.index('Artículo 14.- Derogaciones.') + 1]
    assert a14.endswith(', y el Artículo 49, inciso b) de la Ley N° 827/96 "DE SEGUROS".'), a14
    assert units['art-049']['text'].split('\n')[4].startswith('El o los liquidadores serán funcionarios')
    rp.op(frm, k, url, 'fn', 'art-049', repl('b) Designará liquidador o liquidadores', None))
    versions = rp.build()
    assert [v['from'] for v in versions] == ['1996-02-13', '2009-11-24', '2018-07-07'], [v['from'] for v in versions]
    dec = [
        'Ley 827/1996 de Seguros (BACN 703, 137 articles): sanctioned 18 December 1995 (the date BACN also gives as '
        'promulgation), published 12 February 1996, no vigencia clause (arts. 133 and 134 count deadlines from its '
        'entry into force), so in force the day after publication (1996-02-13). Laws cite it as "Ley N° 827/96".',
        'Ley 827/1996: the definitions are printed before art. 1, under the headings "CAPITULO ÚNICO", "De los '
        'Aseguradores y Reaseguradores" and "DEFINICIONES", with no article number; they are the unit '
        'definiciones.md (its opening line and incisos a) to n)), and the headings are in indice.md.',
        'Ley 827/1996: Ley 3899/2009 de sociedades calificadoras de riesgo (BACN 1528; published 23 November 2009, '
        'in force 2009-11-24) art. 26 rewrites inciso d) of art. 61 (the Superintendent publishes the insurers\' '
        'main financial indicators every two months, no longer a classification by solvency margin). Ley 7572/2025 '
        'later repeals Ley 3899/2009 as a whole; repealing an amending law does not undo the wording it already '
        'gave, so art. 61 d) keeps it.',
        'Ley 827/1996: Ley 6104/2018 que modifica y amplía la Ley N° 489/95 (BACN 8424; published 6 July 2018, in '
        'force 2018-07-07) art. 14 repeals "el Artículo 49, inciso b)": the line lettered b) (the liquidators '
        'appointed by the Autoridad de Control) is removed from that day. The unlettered paragraph printed after it '
        '("El o los liquidadores serán funcionarios ...") is not lettered b), so it stays. Its arts. 11 and 12 (the '
        'Banco Central may revoke the Superintendencia de Seguros\' resolutions; orderly exit of insurers) are in its '
        'own words and change no words of this law.',
    ]
    # Ley 2421/2004 art. 36 inc. 11) rewrites arts. 38 and 39 on a day its art. 38 leaves to the Executive: no-day hold
    pid21 = '2275'
    assert page_meta(url_of(pid21)) == {'promulgated': '2004-07-05', 'published': '2004-07-07'}
    L21 = actlib.lines(pid21)
    i = L21.index('11) Los Artículos 38 y 39 de la Ley Nº 827, del 12 de febrero de 1996 "De Seguros y Reaseguros", los '
                  'que quedan redactados como sigue:')
    assert L21[i + 1].startswith('"Art. 38.- Las empresas comprendidas en la fusión') and         L21[i + 2].startswith('"Art. 39.- Transferencia de carteras.'), L21[i + 1:i + 3]
    a38 = [ln for ln in L21 if ln.startswith('Artículo 38.- ')]
    assert len(a38) == 1 and a38[0].startswith(LEY_2421_ART_38), a38
    assert units['art-038']['text'] != L21[i + 1] and units['art-039']['text'] != L21[i + 2]
    dec.append(
        'Ley 827/1996: Ley 2421/2004 de Reordenamiento Administrativo y de Adecuación Fiscal (BACN 2275; promulgated '
        '2004-07-05, published 2004-07-07) art. 36 inc. 11) rewrites arts. 38 (publication of an authorised merger) '
        'and 39 (transfer of portfolios), but its art. 38 reads: "' + LEY_2421_ART_38[len('Artículo 38.- '):] + '" The '
        'decree that set that day is not on BACN (a collection of laws), so the change has no day it can be dated '
        'from and is not applied (no-day hold): arts. 38 and 39 keep their enacted wording.')
    return act(slug, 'LSEG', 'Ley N° 827/1996 de Seguros', key, versions), dec


# ------------------------------------------------------------------ Ley 5102/2013 Inversión en infraestructura (APP)

def ley_5102():
    slug, key, pid = 'ley-inversion-infraestructura-publica', 'ley-5102-2013', '4669'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2013-11-01', 'published': '2013-11-04'}, m
    L = actlib.lines(pid)
    vig = [ln for ln in L if VIG.search(ln)]
    assert vig == ['La presente Ley entrará en vigencia al día siguiente de su publicación, y será aplicable a los '
                   'procedimientos de contratación en el marco de proyectos iniciados con posterioridad a dicha '
                   'fecha.'], vig
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 57
    v1 = first_version(key, pid, 'Ley N° 5102/2013', L[2], plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication (art. 54).')
    rp = Replay(slug, units, v1)
    # Ley 7452/2025 art. 55 repeals the law; art. 53: in force the day after publication
    k = 'ley-7452-2025'
    url = url_of('12703')
    m7 = page_meta(url)
    assert m7 == {'promulgated': '2025-01-27', 'published': '2025-01-27'}, m7
    L2 = actlib.lines('12703')
    i = L2.index('Artículo 53.- Vigencia.')
    assert L2[i + 1].startswith('La presente ley entrará en vigencia al día siguiente de su publicación.'), L2[i + 1]
    i = L2.index('Artículo 55.- Derogaciones.')
    assert L2[i + 1] == ('Derógase la Ley Nº 5102/2013 "DE PROMOCIÓN DE LA INVERSIÓN EN INFRAESTRUCTURA PÚBLICA Y '
                         'AMPLIACIÓN Y MEJORAMIENTO DE LOS BIENES Y SERVICIOS A CARGO DEL ESTADO", y todas aquellas '
                         'disposiciones contrarias a la presente ley, en el ejercicio fiscal vigente a la fecha de '
                         'promulgación de la presente ley.'), L2[i + 1]
    law(k, label='Ley N° 7452/2025', title='De Modernización del Régimen de Promoción de la Inversión en '
        'Infraestructura Pública y Ampliación y Mejoramiento de los Bienes y Servicios a cargo del Estado',
        kind='law', enacted=m7['promulgated'], published=m7['published'], url=url)
    frm = plus(m7['published'], days=1)
    assert frm == '2025-01-28', frm
    n0 = len(MISMATCHES)
    whole = rp.build()[-1]['units']   # every unit in force the day before the repeal (a dry run)
    del MISMATCHES[n0:]
    for u in sorted(whole):
        rp.op(frm, k, url, 'del', u)
    versions = rp.build()
    assert [v['from'] for v in versions] == ['2013-11-05', '2025-01-28'], [v['from'] for v in versions]
    assert not versions[-1]['units'], versions[-1]['units'].keys()
    dec = [
        'Ley 5102/2013 de Promoción de la Inversión en Infraestructura Pública y Ampliación y Mejoramiento de los '
        'Bienes y Servicios a cargo del Estado (public-private partnerships; BACN 4669, 57 articles): sanctioned 28 '
        'October 2013, promulgated 1 November 2013, published 4 November 2013; art. 54: "entrará en vigencia al día '
        'siguiente de su publicación", so in force 2013-11-05. That it applies only to contracting procedures begun '
        'after that day is its own wording, not a version.',
        'Ley 5102/2013: repealed by Ley 7452/2025 de Modernización del Régimen de Promoción de la Inversión en '
        'Infraestructura Pública (BACN 12703; promulgated and published 27 January 2025). Its art. 55 repeals Ley 5102 '
        '"en el ejercicio fiscal vigente a la fecha de promulgación de la presente ley" (the 2025 fiscal year), and '
        'its art. 53 puts it in force the day after publication, so the repeal takes effect on 2025-01-28 and the '
        'folder is empty from then on. Art. 53 also applies Ley 7452 to procedures under way and contracts in force '
        'on that day, as far as compatible with their agreed terms; that is Ley 7452\'s own wording, not a version '
        'of this law.',
        'Ley 5102/2013: BACN searches "5102", "5102/13", "5102/2013", "5.102", "Ley N° 5102", "Ley Nº 5102", "Ley N° '
        '5.102", "5.102/13", "5.102/2013", "Ley 5102", "Ley N° 5102/2013", "Ley N° 5102/13", "modifica la Ley N° '
        '5102", "infraestructura pública", "inversión en infraestructura", "participación público-privada", '
        '"público-privada", "7452" and its forms, screened for a modifying, repealing or suspending formula naming it '
        'by number or by name: no law changes its words before Ley 7452 repeals it. Budget laws 2019-2023 only order '
        'payments for projects "ejecutados bajo la Ley N° 5102/2013 ... y sus modificaciones"; Ley 7434/2025 (tren de '
        'cercanías) art. 23 excludes its application to that project (a scope rule, no change of its words); Leyes '
        '6355/2019 and 6769/2021 cite it.',
    ]
    return act(slug, 'LAPP', 'Ley N° 5102/2013 de Promoción de la Inversión en Infraestructura Pública y Ampliación y '
               'Mejoramiento de los Bienes y Servicios a cargo del Estado', key, versions), dec


NOTE_6524 = (
    'Declares a national emergency over COVID-19. Its art. 28 lets the Agencia Financiera de Desarrollo exceed the '
    'percentage limit at the end of art. 5 of Ley 2640/2005, and its art. 29 partly suspends the strict application '
    'of art. 15 of that law, while its emergency measures last. Its art. 47 suspends, for the 2020 fiscal year, '
    'numerals 1) and 2) of art. 7 and arts. 9, 10 and 11 of Ley 5098/2013 de Responsabilidad Fiscal. The text of '
    'those articles does not change.')


# ------------------------------------------------------------------ Ley 5098/2013 de Responsabilidad Fiscal

def ley_5098():
    slug, key, pid = 'ley-responsabilidad-fiscal', 'ley-5098-2013', '4671'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '2013-10-29', 'published': '2013-10-31'}, m
    L = actlib.lines(pid)
    assert not any(VIG.search(ln) for ln in L)
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 15
    v1 = first_version(key, pid, 'Ley N° 5098/2013', 'DE RESPONSABILIDAD FISCAL', plus(m['published'], days=1), units,
                       'The law as enacted, from its BACN page; in force the day after publication.')
    rp = Replay(slug, units, v1)
    # Suspensions for one fiscal year (art. 11 lets Congress suspend art. 7 1) and 2) and art. 9 "por el año fiscal
    # correspondiente"): no word changes, so each is a commit with a note (the suspension rule)
    plan = [  # (key, pid, label, line prefix, units, note)
        ('ley-6444-2019', '9197', 'Ley N° 6444/2019',
         'Artículo 1°.- Autorízase al Poder Ejecutivo, a aplicar las excepciones establecidas en el Artículo 11 de la '
         'Ley Nº 5098/2013', ['art-011'],
         'Authorises the Executive to apply the exceptions of art. 11 of the Ley de Responsabilidad Fiscal to the '
         '2019 budget (Ley 6258/2019), with the deficit capped at 3% of GDP. The text of that law does not change.'),
        ('ley-6672-2021', '9492', 'Ley N° 6672/2021',
         'Artículo 266.- Suspéndase por el presente Ejercicio Fiscal, la aplicación de lo establecido en el numeral 1 '
         'del Artículo 7º y el Artículo 11 de la Ley Nº 5098/2013', ['art-007', 'art-011'],
         'The 2021 budget law. Its art. 266 suspends, for the 2021 fiscal year, numeral 1 of art. 7 and art. 11 of the '
         'Ley de Responsabilidad Fiscal, with the deficit capped at 4% of GDP. The text of that law does not change.'),
        ('ley-6873-2022', '10179', 'Ley N° 6873/2022',
         'Artículo 265.- Suspéndase por el presente Ejercicio Fiscal, la aplicación de lo establecido en el numeral 1 '
         'del Artículo 7º y el Artículo 11 de la Ley Nº 5098/2013', ['art-007', 'art-011'],
         'The 2022 budget law. Its art. 265 suspends, for the 2022 fiscal year, numeral 1 of art. 7 and art. 11 of the '
         'Ley de Responsabilidad Fiscal, with the deficit capped at 3% of GDP. The text of that law does not change.'),
        ('ley-7050-2023', '11239', 'Ley N° 7050/2023',
         'Artículo 93. Suspéndase por el presente Ejercicio Fiscal, la aplicación de lo establecido en el numeral 1 del '
         'artículo 7º de la Ley Nº 5098/2013', ['art-007'],
         'The 2023 budget law. Its art. 93 suspends, for the 2023 fiscal year, numeral 1 of art. 7 of the Ley de '
         'Responsabilidad Fiscal, with the deficit capped at 2.3% of GDP. The text of that law does not change.'),
        ('ley-7218-2023', '12089', 'Ley N° 7218/2023',
         'Artículo 6.º A partir de la vigencia de la presente ley y a efectos de su cumplimiento, suspéndase la '
         'aplicación de lo dispuesto en el artículo 93 de la Ley N° 7050/2023', ['art-007', 'art-011'],
         'Sets extraordinary measures for the public finances. Its art. 6 suspends, from its entry into force, art. 93 '
         'of the 2023 budget law "y en consecuencia, lo establecido en los numerales 1) y 2), del artículo 7° y el '
         'artículo 11" of the Ley de Responsabilidad Fiscal. The text of that law does not change.'),
    ]
    frms = {}
    for k, p, label, prefix, us, note in plan:
        url = url_of(p)
        mk = page_meta(url)
        Lk = actlib.lines(p)
        hit = [ln for ln in Lk if ln.startswith(prefix)]
        assert len(hit) == 1, (k, hit)
        if k == 'ley-7218-2023':
            assert hit[0].endswith('y en consecuencia, lo establecido en los numerales 1) y 2), del artículo 7° y el '
                                   'artículo 11 de la Ley N° 5098/2013 "DE RESPONSABILIDAD FISCAL".'), hit[0]
            assert ('Artículo 14. La presente ley entrará en vigencia a partir del día siguiente al de su publicación en '
                    'la Gaceta Oficial.') in Lk
        else:
            assert not [ln for ln in Lk if re.search(r'(?i)(presente ley|esta ley).{0,40}(entrar[aá] en vigencia|'
                                                      r'regir[aá] a partir)', ln)], k
        law(k, label=label, title=Lk[2].rstrip('.'), kind='law', enacted=mk['promulgated'], published=mk['published'],
            url=url, note=note)
        frms[k] = frm = plus(mk['published'], days=1)
        for u in us:
            rp.op(frm, k, url, 'touch', u)
    assert frms == {'ley-6444-2019': '2019-11-27', 'ley-6672-2021': '2021-01-10', 'ley-6873-2022': '2022-01-07',
                    'ley-7050-2023': '2023-01-06', 'ley-7218-2023': '2023-11-17'}, frms
    # Ley 6524/2020 art. 47 (record shared with part 99-32: same note, NOTE_6524)
    k = 'ley-6524-2020'
    url, L2, frm = bacn_law(k, '9156', 'Ley N° 6524/2020')
    assert frm == '2020-03-27', frm
    assert ('Artículo 47.- Suspéndase por el presente ejercicio fiscal la aplicación de los numerales 1) y 2) del '
            'Artículo 7° y los Artículos 9°, 10 y 11 de la Ley N° 5098/2013 "DE RESPONSABILIDAD FISCAL", el cual deberá '
            'estar explicado por las medidas de ingresos y gastos implementadas por esta Ley para atender la '
            'emergencia.') in L2
    LAWS[k]['note'] = NOTE_6524
    for u in ('art-007', 'art-009', 'art-010', 'art-011'):
        rp.op(frm, k, url, 'touch', u)
    versions = rp.build()
    assert [v['from'] for v in versions] == ['2013-11-01', '2019-11-27', '2020-03-27', '2021-01-10', '2022-01-07',
                                             '2023-01-06', '2023-11-17'], [v['from'] for v in versions]
    dec = [
        'Ley 5098/2013 de Responsabilidad Fiscal (BACN 4671, 15 articles): sanctioned 22 October 2013, promulgated 29 '
        'October 2013, published 31 October 2013, no vigencia clause, so in force the day after publication '
        '(2013-11-01).',
        'Ley 5098/2013: no law changes its words. Its art. 11 lets Congress suspend the fiscal rules of art. 7 1) and '
        '2) and art. 9 for one fiscal year, and later laws did so; a suspension changes no words, so each is a commit '
        'with a note on the articles it names (no lapse commit at the end of the fiscal year, since the text is the '
        'same before and after): Ley 6444/2019 (art. 11 exceptions for the 2019 budget; in force 2019-11-27), Ley '
        '6524/2020 art. 47 (COVID-19 emergency: art. 7 1) and 2) and arts. 9, 10 and 11 for 2020; in force '
        '2020-03-27), the budget laws Ley 6672/2021 art. 266 (2021-01-10), Ley 6873/2022 art. 265 (2022-01-07) and '
        'Ley 7050/2023 art. 93 (2023-01-06), and Ley 7218/2023 art. 6 (2023-11-17; quoted in its note), each dated '
        'the day after its publication (the budget laws and Ley 6444 have no vigencia clause).',
        'Ley 5098/2013: the budget laws on BACN were read one by one for the 2014 (Ley 5142), 2019 (Ley 6258), 2020 '
        '(Ley 6469), 2021, 2022 and 2023 fiscal years; those for 2014, 2019 and 2020 only cite the law (multi-year '
        'fiscal programme "conforme a las disposiciones de la Ley N° 5098"). The budget laws for 2015 (Ley 5386), 2016 '
        'and 2017 (Ley 5554), 2018 (Ley 6026), 2024 (Ley 7228), 2025 (Ley 7408) and 2026 (Ley 7609) are not on BACN, '
        'so any suspension they make is not shown.',
        'Ley 5098/2013: BACN searches "5098", "5098/13", "5098/2013", "5.098", "Ley N° 5098", "Ley Nº 5098", "Ley N° '
        '5.098", "5.098/13", "5.098/2013", "responsabilidad fiscal", "Ley de Responsabilidad Fiscal" and "déficit '
        'fiscal", and every budget-year title from 2014 to 2026, screened for a modifying, repealing or suspending '
        'formula naming it by number or by name. Other laws only cite it (Ley 6622/2020 on spending, Ley 7278/2024 '
        'on the organisation of the State, the 2023 budget law\'s exception to its art. 12).',
    ]
    return act(slug, 'LRF', 'Ley N° 5098/2013 de Responsabilidad Fiscal', key, versions), dec


# ------------------------------------------------------------------ Ley 1535/1999 de Administración Financiera del Estado

LEY_6620_ART_7 = ('Artículo 7.° Las disposiciones de esta ley se aplicarán a partir del Ejercicio Fiscal que determine el '
                  'Ministerio de Hacienda, conforme al grado de avance de las adecuaciones tecnológicas, procedimientos e '
                  'instrumentos requeridos para la implementación efectiva del Presupuesto por Resultados.')


def ley_1535():
    slug, key, pid = 'ley-administracion-financiera-estado', 'ley-1535-1999', '3000'
    m = page_meta(url_of(pid))
    assert m == {'promulgated': '1999-12-31', 'published': '2000-01-03'}, m
    L = actlib.lines(pid)
    vig = [ln for ln in L if VIG.search(ln)]
    assert vig == ['La presente ley entrará en vigencia el 1 de enero del año 2000.'], vig
    units = enacted(pid, slug, 5)
    assert len([k for k in units if k.startswith('art-')]) == 89
    # art. 87 sets 1 January 2000, two days before publication: retroactive clause -> the publication day
    v1 = first_version(key, pid, 'Ley N° 1535/1999', L[2], m['published'], units,
                       'The law as enacted, from its BACN page; dated the day it was published (its art. 87 sets 1 '
                       'January 2000, before publication).')
    rp = Replay(slug, units, v1)
    # Ley 1636/2000 regulates the application of art. 88 (zero-base budgeting from the 2002 budget): no word change
    k = 'ley-1636-2000'
    url, L2, frm = bacn_law(k, '1716', 'Ley N° 1636/2000')
    assert frm == '2000-12-01' and not any(VIG.search(ln) for ln in L2), frm
    assert L2[5].startswith('Artículo 1°.- Dispónese que la técnica "Base Cero", prevista en el Artículo 88 de la Ley N° '
                            '1535 del 31 de diciembre de 1999, deberá ser empleada inexcusablemente'), L2[5]
    LAWS[k]['note'] = ('Orders that the zero-base technique of art. 88 of the Ley de Administración Financiera del '
                       'Estado be used by every body of the central and decentralised administration from the 2002 '
                       'budget on. The text of that article does not change.')
    rp.op(frm, k, url, 'touch', 'art-088')
    # Ley 1954/2002 art. 1: art. 23
    k = 'ley-1954-2002'
    url, L2, frm = bacn_law(k, '8217', 'Ley N° 1954/2002')
    assert frm == '2002-08-02' and not any(VIG.search(ln) for ln in L2), frm
    set_arts(rp, frm, k, url, L2, r'^Artículo 1°\.- Modifícase el Artículo 23 de la Ley N° 1535', [23])
    # Ley 2515/2004 art. 1: art. 70
    k = 'ley-2515-2004'
    url, L2, frm = bacn_law(k, '4013', 'Ley N° 2515/2004')
    assert frm == '2004-12-17' and not any(VIG.search(ln) for ln in L2), frm
    set_arts(rp, frm, k, url, L2, r'^Artículo 1º\.- Modifícase el Artículo 70 de la Ley N° 1535/99', [70])
    # Ley 4767/2012 art. 1: art. 21
    k = 'ley-4767-2012'
    url, L2, frm = bacn_law(k, '1313', 'Ley N° 4767/2012')
    assert frm == '2012-11-01' and not any(VIG.search(ln) for ln in L2), frm
    set_arts(rp, frm, k, url, L2, r'^Artículo 1º\.- Modifícase el artículo 21 de la Ley N° 1\.535/99', [21])
    # Ley 5097/2013 art. 21: inciso b) of art. 41 (the article is reprinted whole; only b) is changed by it)
    k, p5 = 'ley-5097-2013', '4670'
    url = url_of(p5)
    m5 = page_meta(url)
    L2 = actlib.lines(p5)
    assert m5 == {'promulgated': '2013-10-29', 'published': '2013-10-31'} and not any(VIG.search(ln) for ln in L2), m5
    law(k, label='Ley N° 5097/2013', title=L2[2].rstrip('.'), kind='law', enacted=m5['promulgated'],
        published=m5['published'], url=url)     # the same record as part 99-33's first law
    frm = plus(m5['published'], days=1)
    i = L2.index('Artículo 21.- Modifícase el inciso b) del artículo 41 de la Ley N° 1.535/99 "DE ADMINISTRACIÓN '
                 'FINANCIERA DEL ESTADO", que quedará redactado de la siguiente forma:')
    new41 = parse.strip_quote(L2[i + 1:i + 10])
    assert new41[0] == 'Art. 41.- Deuda Pública.' and L2[i + 10].startswith('Artículo 22.-'), L2[i + 1:i + 11]
    old41 = units['art-041']['text'].rstrip('\n').split('\n')[2:]
    assert len(old41) == len(new41) - 1, (old41, new41)
    diff = [(a, b) for a, b in zip(old41, new41[1:]) if a != b]

    def norm(s):
        return re.sub(r'[\s,;.]+', ' ', s.lower()).strip()
    assert [a[:3] for a, b in diff if norm(a) != norm(b)] == ['b) '], diff   # other lines: punctuation/case only
    new_b = new41[3]
    assert new_b == 'b) la emisión y colocación de Bonos y Letras del Tesoro;', new_b
    rp.op(frm, k, url, 'fn', 'art-041', actlib.replace_line('b) la emisión y colocación de bonos', new_b))
    versions = rp.build()
    assert [v['from'] for v in versions] == ['2000-01-03', '2000-12-01', '2002-08-02', '2004-12-17', '2012-11-01',
                                             '2013-11-01'], [v['from'] for v in versions]
    # Ley 3480/2008 art. 7: partial repeal of art. 35, limited to its subject (no definite words): decision only
    L34 = actlib.lines('154')
    a7 = [ln for ln in L34 if ln.startswith('Artículo 7°.- Esta Ley, de acuerdo al artículo anterior, deroga '
                                            'parcialmente la Ley N° 1535/99')]
    assert len(a7) == 1 and 'en su artículo 35, el cual establece que' in a7[0], a7
    # Ley 6620/2020 art. 8 repeals art. 88, but its art. 7 applies the law from a fiscal year the Ministry sets
    L66 = actlib.lines('9394')
    assert page_meta(url_of('9394')) == {'promulgated': '2020-10-02', 'published': None}
    assert L66.count(LEY_6620_ART_7) == 1, L66
    assert [ln for ln in L66 if ln.startswith('Artículo 8.°')] == [
        'Artículo 8.° Derógase el artículo 88 de la Ley Nº 1535/1999 "DE ADMINISTRACIÓN FINANCIERA DEL ESTADO", '
        'modificado por la Ley Nº 1.636/2000 "QUE REGULA LA APLICACION DEL ARTICULO 88 DE LA LEY Nº 1535 DEL 31 DE '
        'DICIEMBRE DE 1999 "DE ADMINISTRACIÓN FINANCIERA DEL ESTADO".'], [ln for ln in L66 if ln.startswith('Artículo 8')]
    assert 'art-088' in versions[-1]['units']
    dec = [
        'Ley 1535/1999 de Administración Financiera del Estado (BACN 3000, 89 articles): sanctioned 20 December '
        '1999, promulgated 31 December 1999, published 3 January 2000. Its art. 87 reads "La presente ley entrará en '
        'vigencia el 1 de enero del año 2000", two days before publication. Under the rule for retroactive clauses '
        'the first version is dated the day of publication, 2000-01-03; the law\'s own stated start, 1 January 2000, '
        'is recorded here.',
        'Ley 1535/1999 amending laws, each dated the day after its publication (none has a vigencia clause): Ley '
        '1954/2002 art. 1 (art. 23, budget extensions; 2002-08-02), Ley 2515/2004 art. 1 (art. 70, the Comisión '
        'Bicameral; 2004-12-17), Ley 4767/2012 art. 1 (art. 21, the financial plan; 2012-11-01) and Ley 5097/2013 '
        'art. 21 (inciso b) of art. 41, public debt; 2013-11-01). Ley 5097 says it amends inciso b) and reprints '
        'the whole article; its other lines differ from the enacted text only in punctuation and capitals, so only '
        'line b) is changed and the rest keeps its enacted print.',
        'Ley 1535/1999: Ley 1636/2000 (BACN 1716; published 30 November 2000, in force 2000-12-01) orders that the '
        'zero-base technique of art. 88 be used from the 2002 budget on. It changes no words, so it is a commit with '
        'a note on art. 88.',
        'Ley 1535/1999: Ley 6620/2020 que dispone la implementación gradual del Presupuesto por Resultados (BACN '
        '9394; promulgated 2 October 2020, no publication date on BACN) art. 8 repeals art. 88, but its art. 7 reads: '
        '"' + LEY_6620_ART_7[len('Artículo 7.° '):] + '" That fiscal year is set by the Ministry of Finance and is '
        'not on BACN, so the repeal has no day it can be dated from and is not applied (no-day hold): art. 88 keeps '
        'its wording.',
        'Ley 1535/1999: Ley 3480/2008 que amplía la tarifa social de energía eléctrica (BACN 154) art. 7 "deroga '
        'parcialmente" art. 35, quoting its rule that public revenue is deposited in full "sin deducción alguna", so '
        'that the electricity company can offset the social tariff against the VAT it collects. The repeal is '
        'limited to that case and removes no definite words, so no text changes.',
        'Ley 1535/1999: BACN searches "1535", "1535/99", "1535/1999", "1.535", "1.535/99", "Ley N° 1535", "Ley Nº '
        '1535", "Ley N° 1.535" and "Administración Financiera del Estado", every cached BACN law page (2,575, '
        'including every budget law on BACN) and the titles of every law in the BACN list were screened for a '
        'modifying, repealing or suspending formula naming the law by number or by name. Budget laws and their '
        'amendments make one-off exceptions to arts. 21, 23, 24 and 25 or apply them; these change no words and are '
        'not shown. Some BACN searches return more hits than they list, so a change made inside a law not reached by '
        'these screens may be missing.',
    ]
    return act(slug, 'LAFE', 'Ley N° 1535/1999 de Administración Financiera del Estado', key, versions), dec


PARTS: dict[str, object] = {
    '80-lactancia-materna': ley_5508,
    '81-trata-de-personas': ley_4788,
    '82-derecho-de-autor': ley_1328,
    '83-marcas': ley_1294,
    '84-legitimacion-dinero': ley_1015,
    '85-funcion-publica': ley_1626,
    '86-cooperativas': ley_438,
    '87-estatuto-agrario': ley_1863,
    '88-areas-silvestres-protegidas': ley_352,
    '89-indert': ley_2419,
    '90-registro-unificado-nacional': ley_7424_act,
    '91-recursos-hidricos': ley_3239,
    '92-vida-silvestre': ley_96,
    '93-bosques-protectores': ley_4241,
    '94-efluentes-cloacales': ley_5428,
    '95-residuos-solidos': ley_3956,
    '96-acuicultura': ley_4050,
    '97-pesca-acuicultura': ley_3556,
    '98-bienestar-animal': ley_7513,
    '99-01-patentes-invenciones': ley_1630,     # 99-NN: parts after 98 that still sort after it by file name
    '99-02-dibujos-modelos-industriales': ley_868,
    '99-03-estatuto-educador': ley_1725,
    '99-04-incoop': ley_2157,
    '99-05-carta-organica-departamental': ley_426,
    '99-06-telecomunicaciones': ley_642,
    '99-07-comunidades-indigenas': ley_904,
    '99-08-residuos-establecimientos-salud': ley_3361,
    '99-09-mercado-valores': ley_5810,
    '99-10-mercado-valores-productos': ley_7572,
    '99-11-arbitraje': ley_7561,
    '99-12-arancel-honorarios-abogados': ley_1376,
    '99-13-armas-de-fuego-2010': ley_4036,
    '99-14-armas-de-fuego': ley_7411,
    '99-15-mipymes': ley_4457,
    '99-16-sistema-nacional-transporte': ley_1590,
    '99-17-estupefacientes': ley_1340,
    '99-18-inversiones': ley_117,
    '99-19-transporte-electrico': ley_6925,
    '99-20-divorcio-vincular': ley_45,
    '99-21-reuniones-publicas': ley_1066,
    '99-22-pedido-de-informes': ley_5453,
    '99-23-maltrato-infantil': ley_4295,
    '99-24-informacion-remuneraciones': ley_5189,
    '99-25-vehiculos-electricos': ley_4601,
    '99-26-prevencion-abuso-sexual': ley_6202,
    '99-27-objecion-de-conciencia': ley_4013,
    '99-28-polucion-sonora': ley_1100,
    '99-29-banco-central': ley_489,
    '99-30-general-de-bancos': ley_861,
    '99-31-garantia-depositos': ley_2334,
    '99-32-agencia-financiera-desarrollo': ley_2640,
    '99-33-cuenta-unica-tesoro': ley_5097,
    '99-34-informacion-caracter-privado': ley_1682,
    '99-35-enriquecimiento-ilicito': ley_2523,
    '99-36-seguros': ley_827,
    '99-37-inversion-infraestructura-publica': ley_5102,
    '99-38-responsabilidad-fiscal': ley_5098,
    '99-39-administracion-financiera-estado': ley_1535,
}


def main():
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    outdir = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else ROOT / 'corpus.d'
    for name, fn in PARTS.items():
        if only and name != only:
            continue
        a, dec = run(fn)
        write(outdir / f'{name}.json', a, dec)
    print('checked:', '; '.join(actlib.CHECKED))


if __name__ == '__main__':
    main()
