"""Reads only .cache/ and writes corpus.json (scripts/gitlaw_common/SCHEMA.md) for Paraguay.

    python -X utf8 parse.py

Deterministic: the same cache gives the same bytes. No network.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from fetch import cache_path

HERE = Path(__file__).resolve().parent
SRC_FILE = next(p for p in (HERE / 'sources.json', HERE / 'repo' / 'tools' / 'sources.json') if p.exists())
SRC = json.loads(SRC_FILE.read_text(encoding='utf-8'))
RETRIEVED = SRC['retrieved']
AMEND_URLS = SRC['urls']

LAWS: dict[str, dict] = {}
DECISIONS: list[str] = []
MISMATCHES: list[str] = []
CODE_DECISIONS: list[str] = [
    'Código Civil: BACN publishes the Code only as enacted (Ley 1183/1985, five pages, no "Modificado por" notes) '
    'and no official consolidated text exists online. The first version is the enacted text, in force 1987-01-01 '
    '(art. 2813 "Este Código comenzará a regir el 1° de enero de 1987"). Every later version is rebuilt by applying, '
    'in order of entry into force, the text of each amending law as printed on its BACN page.',
    'Código Civil: the amending laws were found with the BACN full-text search (queries "1183", "1.183", "1183/85", '
    '"1183/1985", "codigo civil", "código civil") and its sitemap; the text of each hit was screened for articles '
    'that modify, repeal or add to the Code. Laws that amend Ley 805/1996 or Ley 1/1992 themselves (Leyes 985/1996, '
    '2835/2005, 3711/2009, 5329/2014, 5419/2015) change those laws, not the text of the Code, and are not applied.',
    'Código Civil: the current text cannot be checked against an official consolidation, because none is published; '
    'an amending law that the BACN search does not find would be missing here. This is the main limit of this act.',
    'Código Civil: units are art-NNNN (four digits; the Code has 2815 articles), headed "# Art. N", with the text '
    'after the BACN "Art.N.-" prefix as the first paragraph. Book/title/chapter/section/paragraph headings are kept '
    'verbatim in codigo-civil/indice.md, each prefixed with the first article that follows it. The closing formula '
    '("DADA EN LA SALA ...") is codigo-civil/sancion.md.',
    'Código Civil: the BACN transcription has no arts. 733, 1170, 1571, 2414 and 2566 (the numbering jumps); the '
    'scan BACN links has no text layer and no OCR is used, so these five articles are absent rather than typed in.',
    'Código Civil: an amending law quotes the new article between quotation marks; the marks are removed (a closing '
    'quote before a full stop keeps the full stop). Inciso-level changes (art. 39 inc. a repealed by Ley 2169/2003; art. 1898 inc. b '
    'rewritten by Ley 2559/2005) replace or drop that one line.',
    'Código Penal: BACN publishes the Code only as enacted (Ley 1160/1997, promulgated 26 November 1997); it is in '
    'force from 1998-11-26 (art. 325 "entrará en vigor un año después de su promulgación"). Later versions replay '
    'the amending laws, found with the BACN search (queries "1160", "1.160", "1160/97", "1160/1997", "codigo penal", '
    '"código penal") and the sitemap, exactly as for the Civil Code; the same limit applies: there is no official '
    'consolidation to check the current text against.',
    'Código Penal: units are art-NNN (art-129-b for lettered articles), headed "# Artículo N.- epigraph"; a final '
    'full stop or colon after an epigraph is dropped, because the amending laws print epigraphs with and without '
    'one. The book/title/chapter headings are not kept: Ley 3440/2008 "recapitulates" Title II of Book Two and '
    'Ley 6452/2019 adds a chapter, and the laws quote new headings next to the first article they rewrite rather '
    'than the first article of each chapter, so the structure cannot be replayed mechanically.',
    'Código Penal: when a law says it modifies art. N but gives only articles Na, Nb, ... (Ley 3440/2008 for 129 and '
    '184; Ley 6002/2017 for 135; Ley 6452/2019 for 191 and 268; Ley 7062/2023 for 105), art. N is removed and the '
    'lettered articles are added. Lettered articles a law adds without listing (Ley 4439/2011: 146b-d, 174b, 175b, '
    '248b) are insertions.',
    'Código Penal: laws found by the search that create offences in their own text, cite the Code, or amend other '
    'laws (for example Leyes 4005/2010, 4682/2012, 4728/2012, 5162/2014, 5876/2017) do not change its text and are '
    'not applied. Ley 1252 (1987) repeals arts. 107 and 108 of the 1914 Code, not of this one.',
    'Reconciliation (metadata only, no text read or copied; the repository has no licence): ypsoftware/leyes-'
    'paraguayas marks Penal Code articles as modified by 11 laws, all in this replay except Ley 4005/2010, which '
    'amends Ley 2849/2005 (antisecuestro), not the Code; it marks no Civil Code article as modified.',
    'Código Procesal Penal: BACN publishes it only as enacted (Ley 1286/1998, promulgated 8 July 1998). Ley '
    '1444/1999 replaced its own entry into force (art. 505): it applied in part from 9 July 1999 (art. 2) and in '
    'full from 1 March 2000 (art. 3). The first version (1999-07-09) is the Code as enacted, credited to Ley '
    '1286/1998; a second version on the same day (same_day) removes art. 17 inc. 15 and art. 505, credited to Ley '
    '1444/1999 art. 18 ("Desde el día 9 de julio de 1999, quedarán derogados"). The full application on 2000-03-01 '
    'is a commit credited to Ley 1444/1999 that changes no words.',
    'Código Procesal Penal: the amending laws were found with the BACN search ("1286/98", "1286/1998", "1.286", '
    '"procesal penal") and the sitemap, and screened as for the other codes; there is no official consolidation to '
    'check the current text against. Units are art-NNN headed "# Artículo N. EPIGRAPH"; the epigraph is the run of '
    'capital-letter sentences that opens the article in BACN (or the epigraph line the amending law gives); amended '
    'articles take the epigraph the amending law prints, and none when it prints none (Ley 2341/2003, art. 136).',
    'Código Procesal Penal, Ley 4669/2012 (arts. 136-137): it has no vigencia clause, so by the default rule it took '
    'effect on 2012-07-24, the day after publication, and changed the text in force until Ley 4734/2012 suspended it '
    'from 2012-09-12; it therefore has a version of its own, not only a note. The suspension is a version credited to '
    'Ley 4734/2012 with restores = Ley 4669/2012 (arts. 136-137 return to the 2341/2003 and 1998 wording). The '
    'extensions (Leyes 5276/2014, 5475/2015, 5671/2016: three, four and six years from 2012-09-12) each took effect '
    'before the running period ended, and Ley 6146/2018 repealed Ley 4669 on 2018-08-30, before the six years ran out, '
    'so the 4669 wording never applied again; those four laws are commits with a note and no word change. Ley '
    '5475/2015 calls Ley 4734 a suspension of the "entrada en vigencia" of Ley 4669; Ley 4734 itself says "la '
    'vigencia", and no text gives Ley 4669 a later start, so the default rule is kept. Ley 4669 also quotes the '
    'chapter heading "CAPITULO V / CONTROL DE LA DURACION DE PROCEDIMIENTO" (the 1998 heading without accents and '
    '"DE" for "DEL"); it is not applied to codigo-procesal-penal/indice.md.',
    'Código Procesal Penal, temporary wording: Ley 6353/2019 (arts. 129, 141, 251) and Ley 6418/2019 (art. 253) apply '
    '"hasta el 31 de enero de 2020" (temporary_until 2020-01-31); from 2020-02-01 "volverán a regir ... conforme a su '
    'redacción original". That return is a version credited to a separate entry ("Ley N° 6353/2019, fin de '
    'vigencia", key ley-6353-2019-fin; likewise for 6418) with restores set to the temporary law, and parse.py checks '
    'that the restored wording equals the 1999 text.',
    'Código Procesal Civil (Ley 1337/1988): BACN publishes it only as enacted; all 839 articles are in its HTML. '
    'Sanctioned 20 October 1988; promulgated 4 November 1988, a date read (by the model, see ai_use) from the last '
    'page of the signed original scan BACN links, because BACN metadata gives the sanción date; Ley 600/1995 cites '
    '"Ley Nº 1.337 del 4 de setiembre de 1988", which contradicts both. In force 1989-11-04 (art. 837 "al año de su '
    'promulgación", taken as the anniversary, as for the Penal Code). Amending laws found with the BACN search '
    '("1337/88", "1337/1988", "1.337", "procesal civil") and screened as for the other codes. Units are art-NNN '
    'headed "# Art. N.- epigraph" (the first sentence after BACN "Art.N.-"); Ley 600/1995 rewrites art. 582 without '
    'an epigraph, so it has none from 1995.',
    'Código Procesal Civil: Ley 7663/2026 (arts. 158, 159, 444, 448 and a new art. 501 bis) takes effect only once '
    'the Corte Suprema de Justicia issues its implementing Acordada (art. 7); no in-force day is known, so it is not '
    'applied. Ley 6059/2018 art. 8 repeals art. 684; Ley 4992/2013 art. 4 repeals art. 37 inc. c.',
    'Código de la Niñez y la Adolescencia (Ley 1680/2001): enacted text from BACN (all 259 articles; BACN prints '
    '"Arículo 199"), in force 2001-11-30 (art. 258: six months after promulgation on 30 May 2001). Amending laws '
    'found with the BACN search ("1680/01", "1680/2001", "1.680", "niñez y la adolescencia"): Leyes 2169/2003 (art. '
    '2, no epigraph in its text), 3879/2009 (169), 6083/2018 (12 articles) and 6174/2018 (repeals 39-41). Ley '
    '3929/2009 "amplía" Book IV Title II Chapter III with five articles of its own that are not numbered into the '
    'Code, so it is not applied.',
    'No article of the Código Procesal Civil or the Código de la Niñez exists only as a scan: both are complete in '
    'the BACN HTML.',
    'Código Aduanero (Ley 2422/2004), Ley 1034/1983 del Comerciante and Código Sanitario (Ley 836/1980): enacted '
    'texts from BACN, amending laws found with the BACN search ("2422/04", "2422/2004", "codigo aduanero", '
    '"1034/83", "1.034", "del comerciante", "836/80", "codigo sanitario") and screened as for the other codes. '
    'Their articles carry no separate epigraph in BACN (the Aduanero opens many articles with words such as '
    '"Contrabando. Concepto." that are kept as text), so units are headed "# Artículo N" / "# Art. N". In force: '
    'Aduanero 180 days after promulgation on 15 July 2004 (art. 397) = 2005-01-11; Comerciante and Sanitario have '
    'no vigencia clause, so the day after publication (1983-12-17; 1980-12-16).',
    'Ley del Comerciante: its headings are printed in mixed case ("Capìtulo I", "De los corredores"); parse.py '
    'treats as headings the short unpunctuated lines that open with Capítulo/Sección/Disposición/"De l…" and the line '
    'after a Capítulo/Sección line. Amended: art. 7 repealed by Ley 2169/2003, art. 76 by Ley 4924/2013, art. 122 '
    'repealed by Ley 5810/2017.',
    'Código Sanitario: BACN\'s HTML omits arts. 123-130 (Capítulos XII-XIII, cadáveres and ruidos); they exist only '
    'as images in the signed scan BACN links (/archivos/2399/20140423122211.pdf, page 15, checked by eye that they '
    'exist, not transcribed), so they are not in the repository. Art. 321 is also absent from the HTML; the scan '
    'was not checked for it. Amended: arts. 270 and 272 by Ley 115/1990; arts. 149, 231 and 237 repealed by Ley '
    '4995/2013 (Educación Superior).',
    'Código Aduanero: amended by Ley 6417/2019 (arts. 336, 345). Laws that grant exemptions "en el marco de" its '
    'arts. 239-240 do not change its text.',
    'HTML ordered lists (<ol>) on BACN pages carry their item numbers only when rendered; parse.py writes the numbers '
    'out ("1. ", "2. ", ...), as in Ley 7062/2023.',
]


def raw(url: str) -> bytes:
    p = cache_path(url)
    if not p.exists():
        sys.exit(f'not in cache, run fetch.py --plan: {url}')
    return p.read_bytes()


def sha(url: str) -> str:
    return hashlib.sha256(raw(url)).hexdigest()


def page_lines(url: str) -> list[str]:
    return bacn.lines(bacn.body(bacn.decode(raw(url))))


def law(key: str, **kw):
    LAWS[key] = {'label': kw.pop('label'), 'title': kw.pop('title', ''), 'kind': kw.pop('kind', 'law'),
                 'enacted': kw.pop('enacted', None), 'published': kw.pop('published', None),
                 'url': kw.pop('url', None), 'temporary_until': None, 'restores': None, **kw}


def unit(label: str, kind: str, heading: str, paras: list[str]) -> dict:
    text = '\n'.join([f'# {heading}', *paras]) + '\n'
    return {'label': label, 'kind': kind, 'text': text}


# ---------------------------------------------------------------- BACN pages

class bacn:  # noqa: N801  (namespace)
    pass


import codecs
import html
import re
import unicodedata

QUOTES = {'“': '"', '”': '"', '„': '"', '«': '"', '»': '"', '‘': "'", '’': "'",
          '´': "'", '–': '-', '—': '-', '‑': '-', '­': ''}


def _cp1252_fallback(err: UnicodeDecodeError):
    # BACN pages are UTF-8 with stray cp1252 bytes (dates, some names). Decode those bytes as cp1252.
    bad = err.object[err.start:err.end]
    return bad.decode('cp1252', errors='replace'), err.end


codecs.register_error('cp1252fallback', _cp1252_fallback)


def decode(raw: bytes) -> str:
    return raw.decode('utf-8', errors='cp1252fallback')


def norm(s: str) -> str:
    """Publisher typesetting normalised once: NBSP to space, one form of quotes and dashes, runs of spaces collapsed."""
    s = unicodedata.normalize('NFC', s)
    s = s.replace(' ', ' ').replace('​', '').replace('\t', ' ')
    for a, b in QUOTES.items():
        s = s.replace(a, b)
    s = re.sub(r' {2,}', ' ', s)
    return s.strip()


def body(page: str) -> str:
    """The law text block of a BACN /leyes-paraguayas/<id>/ page (between 'Descripción' and the Tags list)."""
    i = page.find('Descripción')
    if i < 0:
        i = page.find('Descripci&oacute;n')
    j = page.find('Tags:', i)
    if i < 0 or j < 0:
        raise ValueError('no Descripción … Tags: block')
    return page[i:j]


def lines(fragment: str) -> list[str]:
    """Block-level HTML to one line per paragraph."""
    s = re.sub(r'<!--.*?-->', '', fragment, flags=re.S)
    s = re.sub(r'(?is)<(script|style)\b.*?</\1>', '', s)
    s = re.sub(r'(?i)<br\s*/?>', '\n', s)

    def number_ol(m):
        # An HTML ordered list shows its numbers only when rendered; write them out ("1. ", "2. ", ...).
        assert not re.search(r'(?i)<ol\b', m.group(1)), 'nested <ol>'
        n = iter(range(1, 1000))
        return re.sub(r'(?i)<li\b[^>]*>', lambda _: f'<li>{next(n)}. ', m.group(1))
    s = re.sub(r'(?is)<ol\b[^>]*>(.*?)</ol\s*>', number_ol, s)
    s = re.sub(r'(?i)</(p|div|h[1-6]|li|tr|table|blockquote)\s*>', '\n', s)
    s = re.sub(r'(?i)<(p|div|h[1-6]|li|tr|table|blockquote)\b[^>]*>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    out = []
    for ln in s.split('\n'):
        ln = norm(ln)
        if ln and ln not in ('-->',):
            if out and re.fullmatch(r'\d+\.', out[-1]):
                out[-1] = out[-1] + ' ' + ln      # a numbered <li> whose text sits in its own <p>
            else:
                out.append(ln)
    return out

def meta(page: str) -> dict:
    """BACN page metadata printed above the text: 'Fecha de Promulgación: DD-MM-YYYY Fecha de Publicación: DD-MM-YYYY'."""
    t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', page)))
    out = {}
    for key, word in (('promulgated', 'Promulgaci'), ('published', 'Publicaci')):
        m = re.search(r'Fecha de ' + word + r'[^:]{0,3}:\s*(\d{2})-(\d{2})-(\d{4})', t)
        out[key] = f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else None
    return out


for _f in (decode, norm, body, lines, meta):
    setattr(bacn, _f.__name__, staticmethod(_f))


# ---------------------------------------------------------------- Constitución Nacional 1992

CONST_URL = 'https://www.bacn.gov.py/leyes-paraguayas/9580/constitucion-de-la-republica-del-paraguay'
ENM1_URL = 'https://www.bacn.gov.py/leyes-paraguayas/9581/ley-n-11112-enmienda-constitucional-n-1'
ENM1_PDF = 'https://www.bacn.gov.py/archivos/9580/ENMIENDA_CONSTITUCIONAL_N_1.pdf'

ART = re.compile(r'^ARTICULO (\d+) - (.+)$')
TRANS = re.compile(r'^ART[IÍ]CULO (\d+)\.-\s*(.*)$')
STRUCT = re.compile(r'^(PARTE|T[IÍ]TULO|CAP[IÍ]TULO|SECCI[OÓ]N) [IVXLC]+$')
MOD = re.compile(r'\s*\(Modificado por ([^)]+)\)\s*$')


def constitution() -> dict:
    L = page_lines(CONST_URL)
    assert L[0] == 'Descripción' and L[3] == 'PREAMBULO', L[:4]
    units: dict[str, dict] = {}
    index: list[str] = []
    modified: dict[str, str] = {}
    cur = None          # (key, label, kind, heading, paras)
    in_trans = False
    pending_struct = False

    def close():
        nonlocal cur
        if cur:
            key, label, kind, heading, paras = cur
            if key in units:
                # BACN prints transitional art. 16 twice (the second copy drops one comma). Keep the first; say so.
                MISMATCHES.append(f'constitucion/{key}: BACN prints this provision twice; the first copy is used. '
                                  f'Second copy: {" / ".join(paras)}')
            else:
                units[key] = unit(label, kind, heading, paras)
        cur = None

    i = 4
    preamble = []
    while not STRUCT.match(L[i]):
        preamble.append(L[i])
        i += 1
    units['preambulo'] = unit('Preámbulo', 'preamble', 'PREAMBULO', preamble)
    for ln in L[i:]:
        if ln.startswith('Queda sancionada esta Constitución.'):
            close()
            units['sancion'] = unit('Sanción', 'closing', 'SANCION', [ln])
            continue
        if STRUCT.match(ln):
            close()
            index.append(ln)
            pending_struct = True
            in_trans = in_trans or ln in ('TÍTULO V', 'TITULO V')
            continue
        m = ART.match(ln)
        if m and not in_trans:
            close()
            pending_struct = False
            n, head = int(m.group(1)), m.group(2)
            mm = MOD.search(head)
            if mm:
                modified[f'art-{n:03d}'] = mm.group(1)
                head = head[:mm.start()]
            heading = f'ARTICULO {n} - {head}'
            index.append(heading)
            cur = (f'art-{n:03d}', f'Art. {n}', 'art', heading, [])
            continue
        m = TRANS.match(ln) if in_trans else None
        if m:
            close()
            pending_struct = False
            n = int(m.group(1))
            heading = f'ARTÍCULO {n}'
            index.append(heading)
            cur = (f'disp-{n:03d}', f'Disposición final y transitoria, art. {n}', 'transitional', heading,
                   [m.group(2)] if m.group(2) else [])
            continue
        if pending_struct and cur is None:
            index[-1] = f'{index[-1]} - {ln}' if not index[-1].startswith(('ARTICULO', 'ARTÍCULO')) and ' - ' not in index[-1] else f'{index[-1]} / {ln}'
            continue
        assert cur is not None, ln
        cur[4].append(ln)
    close()
    units['indice'] = unit('Índice de partes, títulos, capítulos y secciones', 'index',
                           'PARTES, TITULOS, CAPITULOS Y SECCIONES', index)
    arts = sorted(k for k in units if k.startswith('art-'))
    assert arts == [f'art-{n:03d}' for n in range(1, 292)], 'articles 1..291 expected'
    assert sorted(k for k in units if k.startswith('disp-')) == [f'disp-{n:03d}' for n in range(1, 21)]
    assert modified == {'art-120': 'ENMIENDA CONSTITUCIONAL N° 1'}, modified

    law('cn-1992', label='Constitución Nacional 1992', kind='law', enacted='1992-06-20', published=None,
        title='Constitución de la República del Paraguay, sancionada y promulgada por la Convención Nacional '
              'Constituyente el 20 de junio de 1992', url=CONST_URL)
    v1 = {'from': '1992-06-20', 'source_url': CONST_URL, 'sha256': sha(CONST_URL), 'units': units, 'credits': {},
          'note': 'Text from the BACN page of the Constitution. Its art. 120 still prints the 1992 wording under a '
                  '"(Modificado por ENMIENDA CONSTITUCIONAL N° 1)" note; that wording is used here for 1992-2011.'}

    # Enmienda N° 1 (2011): art. 120, from the signed original's text layer, compared with BACN's HTML transcription.
    new120 = enmienda1_art120()
    units2 = dict(units)
    units2['art-120'] = unit('Art. 120', 'art', units['art-120']['text'].split('\n', 1)[0][2:], new120)
    law('enmienda-2011-1', label='Enmienda Constitucional N° 1 (2011)', kind='referendum',
        enacted='2011-10-17', published=None, url=ENM1_URL,
        title='Que enmienda el artículo 120 de la Constitución Nacional "De los electores". Aprobada por la Cámara '
              'de Diputados el 28 de octubre de 2010 y por la Cámara de Senadores el 14 de abril de 2011; aprobada '
              'en referéndum; tenida por sancionada y promulgada el 17 de octubre de 2011 (Acuerdo y Sentencia N° 23 '
              'del TSJE)')
    v2 = {'from': '2011-10-17', 'source_url': ENM1_URL, 'sha256': sha(ENM1_PDF), 'units': units2,
          'credits': {'art-120': ['enmienda-2011-1']}}
    if units['art-120']['text'] == units2['art-120']['text']:
        sys.exit('art. 120 did not change')
    MISMATCHES.append('constitucion/art-120: the BACN consolidated page (id 9580) still prints the 1992 wording under '
                      'its "(Modificado por ENMIENDA CONSTITUCIONAL N° 1)" note; the repository follows the Enmienda '
                      'itself from 2011-10-17.')
    return {'slug': 'constitucion', 'short': 'CN', 'title': 'Constitución de la República del Paraguay (1992)',
            'url': CONST_URL, 'first_law': 'cn-1992', 'earlier_laws': [], 'versions': [v1, v2]}


def enmienda1_art120() -> list[str]:
    """Art. 120 as worded by Enmienda N° 1, read from the text layer of the signed original (BACN scan)."""
    import fitz  # PyMuPDF; reads the cached PDF only
    doc = fitz.open(stream=raw(ENM1_PDF), filetype='pdf')
    blocks = [b[4] for b in doc[0].get_text('blocks')]
    i = next(k for k, b in enumerate(blocks) if b.startswith('"Artículo 120.- De los Electores'))
    paras = []
    for b in blocks[i + 1:]:
        if b.startswith('Artículo 2'):
            break
        paras.append(bacn.norm(' '.join(b.split())))
    assert len(paras) == 3, paras
    assert paras[-1].endswith('municipales."'), paras
    paras[-1] = paras[-1][:-1]   # the closing quote of the amending formula is not part of the article
    # Cross-check with BACN's HTML transcription of the Enmienda (page 9581).
    html_lines = page_lines(ENM1_URL)
    j = html_lines.index('"Artículo 120.- De los Electores')
    html_paras = html_lines[j + 1:j + 4]
    for a, b in zip(paras, html_paras):
        if a != b.rstrip('"'):
            MISMATCHES.append(f'constitucion/art-120 (Enmienda N° 1): signed original "{a}" vs BACN HTML "{b}"; '
                              'the signed original is used.')
    return paras


# ---------------------------------------------------------------- codes: shared replay engine

BACN = 'https://www.bacn.gov.py/leyes-paraguayas/'


def page_meta(url: str) -> dict:
    return bacn.meta(bacn.decode(raw(url)))


def day_after(d: str) -> str:
    import datetime as dt
    return (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()


def strip_quote(paras: list[str]) -> list[str]:
    """Drop the quotation marks of an amending formula ("Art. N.- …") from a block of paragraphs."""
    out = list(paras)
    if out and out[0].startswith('"'):
        out[0] = out[0][1:]
    if out:
        last = out[-1]
        for tail, repl in (('".', '.'), ('";', ''), ('"', '')):
            if last.endswith(tail):
                out[-1] = last[: -len(tail)] + repl
                break
    return [p.strip() for p in out]


class Replay:
    """Apply amending laws to an act's units, one version per in-force day, crediting every changed unit."""

    def __init__(self, slug: str, base: dict, first: dict):
        self.slug = slug
        self.units = dict(base)
        self.versions = [first]
        self.pending: dict[str, dict] = {}     # from -> {'units':…, 'credits':…, 'source_url', 'sha256', 'notes'}

    def _v(self, frm: str, url: str):
        if frm not in self.pending:
            self.pending[frm] = {'ops': [], 'source_url': url, 'sha_urls': [], 'notes': []}
        return self.pending[frm]

    def op(self, frm: str, law_key: str, url: str, kind: str, key: str, value=None, note=None):
        v = self._v(frm, url)
        v['ops'].append((kind, key, value, law_key))
        if url not in v['sha_urls']:
            v['sha_urls'].append(url)
        if note:
            v['notes'].append(note)

    def build(self) -> list[dict]:
        cur = dict(self.versions[0]['units'])
        out = list(self.versions)
        history = [(self.versions[0]['from'], cur)]
        for frm in sorted(self.pending):
            p = self.pending[frm]
            new = dict(cur)
            credits: dict[str, list[str]] = {}
            touched: set[str] = set()
            for kind, key, value, law_key in p['ops']:
                if kind == 'touch':        # an event that concerns the provision but changes no words
                    if key not in new:
                        sys.exit(f'{self.slug}: {law_key} concerns {key}, which is not in force')
                    touched.add(key)
                elif kind == 'restore':    # back to the wording in force the day before `value`
                    old = [u for d, u in history if d < value][-1]
                    if key not in old:
                        sys.exit(f'{self.slug}: {law_key} restores {key}, which was not in force before {value}')
                    new[key] = old[key]
                elif kind == 'set':
                    if key not in new:
                        sys.exit(f'{self.slug}: {law_key} rewrites {key}, which is not in force')
                    new[key] = value
                elif kind == 'add':
                    if key in new:
                        sys.exit(f'{self.slug}: {law_key} inserts {key}, which already exists')
                    new[key] = value
                elif kind == 'del':
                    if key not in new:
                        sys.exit(f'{self.slug}: {law_key} repeals {key}, which is not in force')
                    del new[key]
                elif kind == 'fn':
                    new[key] = value(new[key])
                credits.setdefault(key, [])
                if law_key not in credits[key]:
                    credits[key].append(law_key)
            for k in list(credits):
                if new.get(k) == cur.get(k) and k not in touched:
                    MISMATCHES.append(f'{self.slug}/{k}: {", ".join(credits[k])} restates the text in force; no change')
                    del credits[k]
            h = hashlib.sha256(b''.join(raw(u) for u in p['sha_urls'])).hexdigest()
            v = {'from': frm, 'source_url': p['source_url'], 'sha256': h, 'units': new, 'credits': credits}
            if len(p['sha_urls']) > 1:
                v['note'] = ('sha256 is over the concatenated cached bytes of: ' + ', '.join(p['sha_urls'])
                             + ('. ' + ' '.join(p['notes']) if p['notes'] else ''))
            elif p['notes']:
                v['note'] = ' '.join(p['notes'])
            out.append(v)
            cur = new
            history.append((frm, new))
        return out


JOINS: list[str] = []


def join_broken(paras: list[str], where: str) -> list[str]:
    """BACN sometimes breaks a sentence over two paragraphs (a stray <br>). Rejoin when a paragraph ends without
    punctuation and the next starts with a lower-case word that is not an enumerator ("a)", "b)")."""
    out: list[str] = []
    for p in paras:
        if (out and not re.search(r'[.;:,"\')]$', out[-1])
                and ((re.match(r'^[a-zñáéíóú]', p) and not re.match(r'^[a-zñ]{1,2}(\)(?!,)|\.\s)', p))
                     or (re.search(r'\b(incisos?|numerales|artículos)$', out[-1]) and re.match(r'^\d+° al \d+°', p)))):
            JOINS.append(f'{where}: "{out[-1][-30:]}" + "{p[:30]}"')
            out[-1] = out[-1] + ' ' + p
        else:
            out.append(p)
    return out


def segments(L: list[str]) -> list[tuple[str, list[str]]]:
    """An amending law split into its own articles: [(the article's first line, the lines that follow)]."""
    out: list[tuple[str, list[str]]] = []
    for ln in L:
        if re.match(r'^Art[ií]culo\s*\d+\s*[°º.o]*\s*[.-]', ln) or re.match(r'^Artículo \d+\.', ln):
            out.append((ln, []))
        elif re.match(r'^(Aprobad|DADA|Dada)', ln):
            out.append((ln, []))
        elif out:
            out[-1][1].append(ln)
    return out


def amending_blocks(L: list[str], art_re: re.Pattern) -> list[tuple[int, list[str]]]:
    """Quoted article blocks in an amending law: [(article number, paragraphs)], in order of appearance."""
    out = []
    cur = None
    for ln in L:
        m = art_re.match(ln)
        if m:
            cur = (int(m.group(1).replace('.', '')), [m.group(2)] if m.group(2) else [])
            out.append(cur)
            continue
        if re.match(r'^Art[ií]culo \d+', ln) or re.match(r'^(Aprobad|DADA|Dada)', ln):
            cur = None
            continue
        if cur is not None:
            cur[1].append(ln)
    return [(n, strip_quote(['"' + p[0]] + p[1:]) if p else []) for n, p in out]


# ---------------------------------------------------------------- Código Civil (Ley 1183/1985)

CC_PAGES = [BACN + '5293/ley-n-1183-codigo-civil',
            BACN + '5299/ley-n-1183-codigo-civil-ii-parte-libro-segundo-br',
            BACN + '522/ley-n-1183-codigo-civil-iii-parte-libro-tercero-br',
            BACN + '524/ley-n-1183-codigo-civil-iv-parte-libro-cuarto-br',
            BACN + '528/ley-n-1183-codigo-civil-v-parte-libro-quinto-br']
CC_ART = re.compile(r'^Art\.\s*(\d{1,2}\.\d{3}|\d+)\s*[°º]?\s*\.?\s*-\s*(.*)$')
CC_QART = re.compile(r'^"Art\.?\s*(\d{1,2}\.\d{3}|\d+)\s*[°º]?\s*\.?\s*-?\s*(.*)$')
CC_LABEL = re.compile(r'^(LIBRO|TITULO|T[IÍ]TULO|CAPITULO|CAP[IÍ]TULO|SECCION|SECCI[OÓ]N|PARAGRAFO|PAR[AÁ]GRAFO)\b')


def cc_key(n: int) -> str:
    return f'art-{n:04d}'


def cc_unit(n: int, paras: list[str]) -> dict:
    return unit(f'Art. {n}', 'art', f'Art. {n}', paras)


def cc_heading_line(ln: str) -> bool:
    return not re.search(r'[a-zñáéíóúü]', ln)


def civil_code_enacted() -> tuple[dict, list[str]]:
    units: dict[str, dict] = {}
    index: list[list] = []          # [first article key or None, text]
    closing = None
    for url in CC_PAGES:
        L = page_lines(url)
        assert L[0] == 'Descripción' and L[1] in ('LEY N° 1.183', 'LEY N° 1183') and L[2] == 'CODIGO CIVIL', L[:3]
        assert L[3].startswith('EL CONGRESO DE LA NACION PARAGUAYA SANCIONA') and L[4] == 'LEY:', L[3:5]
        cur = None
        prev_heading = False
        for ln in L[5:]:
            if ln.startswith('DADA EN LA SALA DE SESIONES'):
                closing = closing or ln
                assert ln == closing
                cur = None
                continue
            m = CC_ART.match(ln)
            if m:
                n = int(m.group(1).replace('.', ''))
                k = cc_key(n)
                assert k not in units, k
                cur = [m.group(2)]
                units[k] = cur
                for e in index:
                    if e[0] is None:
                        e[0] = k
                prev_heading = False
                continue
            if cc_heading_line(ln):
                if CC_LABEL.match(ln) or not prev_heading:
                    index.append([None, ln])
                else:
                    index[-1][1] += ' - ' + ln if CC_LABEL.match(index[-1][1]) and ' - ' not in index[-1][1] else ' / ' + ln
                prev_heading = True
                cur = None
                continue
            assert cur is not None, ln
            cur.append(ln)
            prev_heading = False
    out = {k: cc_unit(int(k[4:]), v) for k, v in units.items()}
    missing = [n for n in range(1, 2816) if cc_key(n) not in out]
    idx = [f'{k}: {t}' for k, t in index]
    out['sancion'] = unit('Sanción', 'closing', 'SANCION', [closing])
    return out, idx, missing


def bacn_law(key: str, page_id: str, label: str, *, in_force: str | None = None, promulgated: str | None = None,
             why: str = '') -> tuple[str, list[str], str]:
    """Register an amending law from its BACN page; return (url, lines, in-force day).

    In force: the law's own clause (in_force, with `why`) or, by default, the day after publication (CC art. 1).
    When BACN gives no publication date, the day after promulgation is used and the decision says so."""
    url = next(u for u in AMEND_URLS if f'/leyes-paraguayas/{page_id}/' in u)
    L = page_lines(url)
    m = page_meta(url)
    prom = promulgated or m['promulgated']
    pub = m['published']
    if promulgated and promulgated != m['promulgated']:
        DECISIONS.append(f'{label}: promulgation date {promulgated} ({why}); BACN\'s page metadata says '
                         f'{m["promulgated"]}, which is impossible or contradicted.')
    if in_force:
        frm = in_force
        if why and not promulgated:
            DECISIONS.append(f'{label}: in force {in_force} ({why}).')
    elif pub and (not promulgated or pub >= promulgated):
        frm = day_after(pub)
    else:
        frm = day_after(prom)
        DECISIONS.append(f'{label}: BACN records no publication date, so the version is dated the day after '
                         f'promulgation ({prom}); the Gaceta Oficial could not be reached to confirm it.')
    title = L[2] if len(L) > 2 else ''
    law(key, label=label, title=title.rstrip('.'), kind='law', enacted=prom, published=pub, url=url)
    return url, L, frm


def cc_segment_blocks(L: list[str], intro_pat: str) -> list[tuple[int, list[str]]]:
    """Quoted 'Art. N' blocks inside the amending law's own article whose first line matches intro_pat."""
    segs = [s for s in segments(L) if re.search(intro_pat, s[0])]
    assert len(segs) == 1, (intro_pat, [s[0][:80] for s in segs])
    return amending_blocks(segs[0][1], CC_QART)


def cc_set_blocks(rp: 'Replay', frm: str, key: str, url: str, blocks, expect: list[int], *, renumber=None):
    got = [n for n, _ in blocks]
    if renumber:
        got = [renumber.get(n, n) for n in got]
    assert got == expect, (key, got, expect)
    for n, (_, paras) in zip(got, blocks):
        rp.op(frm, key, url, 'set', cc_key(n), cc_unit(n, join_broken(paras, f'{key} art. {n}')))


def civil_code() -> dict:
    base, idx, missing = civil_code_enacted()
    assert missing == [733, 1170, 1571, 2414, 2566], missing
    base_units = dict(base)
    base_units['indice'] = unit('Índice de libros, títulos, capítulos, secciones y parágrafos', 'index',
                                'LIBROS, TITULOS, CAPITULOS, SECCIONES Y PARAGRAFOS', idx)
    for k, v in list(base_units.items()):
        if k.startswith('art-'):
            head, *paras = v['text'].rstrip('\n').split('\n')
            base_units[k] = cc_unit(int(k[4:]), join_broken(paras, f'cc art. {int(k[4:])}'))
    law('ley-1183-1985', label='Ley N° 1183/1985 (Código Civil)', kind='law', enacted='1985-12-18',
        published=None, url=CC_PAGES[0], title='Código Civil, sancionado por el Congreso Nacional el 18 de diciembre '
                                                'de 1985; rige desde el 1 de enero de 1987 (art. 2813)')
    sha_all = hashlib.sha256(b''.join(raw(u) for u in CC_PAGES)).hexdigest()
    first = {'from': '1987-01-01', 'source_url': CC_PAGES[0], 'sha256': sha_all, 'units': base_units, 'credits': {},
             'note': 'The Code as enacted, from BACN\'s five pages (sha256 over their concatenated cached bytes, in '
                     'order: ' + ', '.join(CC_PAGES) + '). BACN\'s transcription omits arts. 733, 1170, 1571, 2414 '
                     'and 2566; they are missing here too (the scan BACN offers has no text layer).'}
    rp = Replay('codigo-civil', base_units, first)

    # Ley 45/1991, divorcio vincular: art. 22 rewrites art. 163 (inline quotation).
    url, L, frm = bacn_law('ley-45-1991', '689', 'Ley N° 45/1991')
    a22 = next(s for s in segments(L) if s[0].startswith('Artículo 22'))
    m = re.match(r'^Artículo 22º\.- El artículo 163 del Código Civil queda redactado de la siguiente forma: "(.*)$', a22[0])
    rp.op(frm, 'ley-45-1991', url, 'set', 'art-0163', cc_unit(163, strip_quote(['"' + m.group(1)] + a22[1])))
    DECISIONS.append('Ley N° 45/1991 art. 23 and Ley N° 1/1992 art. 98 also repeal, without naming them, the '
                     'provisions of the Code that contradict them; only articles they name are changed here.')

    # Ley 1/1992, reforma parcial: art. 98 repeals 40 articles by number.
    url, L, frm = bacn_law('ley-1-1992', '695', 'Ley N° 1/1992', promulgated='1992-07-15',
                           why='Ley N° 985/1996 art. 1 cites "Ley No. 1 … promulgada el 15 de julio de 1992"; BACN '
                               'gives 9 April 1992, before its sanción on 25 June 1992')
    a98 = next(s for s in segments(L) if s[0].startswith('Artículo 98'))
    nums = [int(x) for x in re.findall(r'\d+', a98[0].split(':', 1)[1])]
    assert len(nums) == 40 and nums[0] == 15 and nums[-1] == 224, nums
    for n in nums:
        rp.op(frm, 'ley-1-1992', url, 'del', cc_key(n))

    url, L, frm = bacn_law('ley-204-1993', '690', 'Ley N° 204/1993')
    cc_set_blocks(rp, frm, 'ley-204-1993', url, cc_segment_blocks(L, r'^Artículo 1º'), [2582, 2590, 2591])

    url, L, frm = bacn_law('ley-388-1994', '684', 'Ley N° 388/1994')
    for i, n in zip(range(1, 7), [91, 93, 967, 1050, 1051, 1079]):
        cc_set_blocks(rp, frm, 'ley-388-1994', url, cc_segment_blocks(L, rf'^Artículo {i}º'), [n])

    url, L, frm = bacn_law('ley-701-1995', '692', 'Ley N° 701/1995')
    cc_set_blocks(rp, frm, 'ley-701-1995', url, cc_segment_blocks(L, r'^Artículo 1º'), [770])

    # Ley 805/1996: art. 19 gives art. 1725 a transitional text from promulgation to 1 Jan 1997 (art. 18-19);
    # arts. 1-5 take effect on 1 Jan 1997 (art. 17).
    url, L, frm = bacn_law('ley-805-1996', '694', 'Ley N° 805/1996', in_force='1997-01-01',
                           why='art. 17: "Los artículos 1° al 16 de esta Ley entrarán en vigencia el 1° de enero de 1997"')
    prom = LAWS['ley-805-1996']['enacted']
    cc_set_blocks(rp, prom, 'ley-805-1996', url, cc_segment_blocks(L, r'^Artículo 19'), [1725])
    DECISIONS.append(f'Ley N° 805/1996 art. 19: transitional wording of art. 1725 "a partir de la promulgación" '
                     f'({prom}) "y hasta el 1° de enero de 1997"; it is replaced on that day by the art. 3 wording.')
    for i, n in zip(range(1, 6), [1696, 1706, 1725, 1726, 1752]):
        cc_set_blocks(rp, '1997-01-01', 'ley-805-1996', url, cc_segment_blocks(L, rf'^Artículo {i}°'), [n])

    url, L, frm = bacn_law('ley-1328-1998', '908', 'Ley N° 1328/1998')
    a186 = next(s for s in segments(L) if s[0].startswith('Artículo 186'))
    assert 'Artículos 867 al 879, inclusive del Código Civil' in a186[0]
    for n in range(867, 880):
        rp.op(frm, 'ley-1328-1998', url, 'del', cc_key(n))

    url, L, frm = bacn_law('ley-1448-1999', '1588', 'Ley N° 1448/1999')
    cc_set_blocks(rp, frm, 'ley-1448-1999', url, cc_segment_blocks(L, r'^Artículo 4°'), [2328])

    url, L, frm = bacn_law('ley-2169-2003', '4845', 'Ley N° 2169/2003')
    cc_set_blocks(rp, frm, 'ley-2169-2003', url, cc_segment_blocks(L, r'^Artículo 1°'), [36])
    assert next(s for s in segments(L) if s[0].startswith('Artículo 2º'))[0].startswith(
        'Artículo 2º.- Deróganse el inciso a) del Artículo 39 de la Ley N° 1183/85')

    def drop_39a(u):
        lines_ = u['text'].split('\n')
        hit = [i for i, x in enumerate(lines_) if x.startswith('a) ')]
        assert len(hit) == 1, lines_
        del lines_[hit[0]]
        return {**u, 'text': '\n'.join(lines_)}
    rp.op(frm, 'ley-2169-2003', url, 'fn', 'art-0039', drop_39a)

    url, L, frm = bacn_law('ley-2170-2003', '683', 'Ley N° 2170/2003')
    cc_set_blocks(rp, frm, 'ley-2170-2003', url, cc_segment_blocks(L, r'^Artículo 1°'), [2073, 2074])

    url, L, frm = bacn_law('ley-2559-2005', '4095', 'Ley N° 2559/2005')
    q = next(s for s in segments(L) if s[0].startswith('Artículo 1°'))[1]
    assert len(q) == 1 and q[0].startswith('"Art. 1898 inc. b) Los ríos'), q
    new_b = 'b) ' + strip_quote([q[0]])[0].split('inc. b) ', 1)[1]

    def set_1898b(u):
        lines_ = u['text'].split('\n')
        hit = [i for i, x in enumerate(lines_) if x.startswith('b) ')]
        assert len(hit) == 1
        lines_[hit[0]] = new_b
        return {**u, 'text': '\n'.join(lines_)}
    rp.op(frm, 'ley-2559-2005', url, 'fn', 'art-1898', set_1898b)

    url, L, frm = bacn_law('ley-3120-2006', '687', 'Ley N° 3120/2006')
    cc_set_blocks(rp, frm, 'ley-3120-2006', url, cc_segment_blocks(L, r'^Artículo 1º'),
                  [2294, 2296, 2299, 2306, 2327, 2330, 2335, 2339, 2346, 2353])

    url, L, frm = bacn_law('ley-3228-2007', '688', 'Ley N° 3228/2007')
    cc_set_blocks(rp, frm, 'ley-3228-2007', url, cc_segment_blocks(L, r'^Artículo 1°'), [1051], renumber={5: 1051})
    DECISIONS.append('Ley N° 3228/2007 rewrites "el Artículo 5º de la Ley Nº 388/94, que modifica el artículo 1051" of '
                     'the Code; the article Ley 388 art. 5 wrote is art. 1051, so its new text is art. 1051.')

    url, L, frm = bacn_law('ley-4297-2011', '3675', 'Ley N° 4297/2011')
    cc_set_blocks(rp, frm, 'ley-4297-2011', url, cc_segment_blocks(L, r'^Artículo 1°'), [989])

    url, L, frm = bacn_law('ley-4586-2012', '3096', 'Ley N° 4586/2012')
    cc_set_blocks(rp, frm, 'ley-4586-2012', url, cc_segment_blocks(L, r'^Artículo 1°'), [108])

    url, L, frm = bacn_law('ley-5063-2013', '4732', 'Ley N° 5063/2013')
    cc_set_blocks(rp, frm, 'ley-5063-2013', url, cc_segment_blocks(L, r'^Artículo 1°'), [989])

    url, L, frm = bacn_law('ley-5895-2017', '9118', 'Ley N° 5895/2017')
    cc_set_blocks(rp, frm, 'ley-5895-2017', url, cc_segment_blocks(L, r'^Artículo 11\.'), [1050, 1069, 1070])

    # Ley 7371/2025: art. 27 rewrites arts. 36, 37, 40 and 73-90 and two chapter headings; art. 30: in force the
    # day after promulgation.
    url, L, frm0 = bacn_law('ley-7371-2025', '12775', 'Ley N° 7371/2025')
    frm = day_after(LAWS['ley-7371-2025']['enacted'])
    DECISIONS.append(f'Ley N° 7371/2025: in force {frm}, the day after promulgation (art. 30 "entrará en vigencia al '
                     f'día siguiente de su promulgación").')
    seg = next(s for s in segments(L) if s[0].startswith('Artículo 27.'))[1]
    heads = [i for i, x in enumerate(seg) if x.startswith('"CAPÍTULO')]
    assert [seg[i] for i in heads] == ['"CAPÍTULO II', '"CAPÍTULO VI'], heads
    new_heads = {36: f'CAPÍTULO II - {seg[heads[0] + 1].rstrip(chr(34))}', 73: f'CAPÍTULO VI - {seg[heads[1] + 1].rstrip(chr(34))}'}
    body_ = [x for i, x in enumerate(seg) if i not in heads and i - 1 not in heads]
    cc_set_blocks(rp, frm, 'ley-7371-2025', url, amending_blocks(body_, CC_QART), [36, 37, 40] + list(range(73, 91)))

    def retitle(u):
        lines_ = u['text'].split('\n')
        for n, new in new_heads.items():
            hit = [i for i, x in enumerate(lines_) if x.startswith(f'{cc_key(n)}: CAPITULO')]
            assert len(hit) == 1, (n, hit)
            lines_[hit[0]] = f'{cc_key(n)}: {new}'
        return {**u, 'text': '\n'.join(lines_)}
    rp.op(frm, 'ley-7371-2025', url, 'fn', 'indice', retitle)

    versions = rp.build()
    return {'slug': 'codigo-civil', 'short': 'CC', 'title': 'Código Civil (Ley N° 1183/1985)', 'url': CC_PAGES[0],
            'first_law': 'ley-1183-1985', 'earlier_laws': [], 'versions': versions}


# ---------------------------------------------------------------- Código Penal (Ley 1160/1997)

CP_URL = BACN + '3497/ley-n-1160-1997-c-digo-penal'
CP_ART = re.compile(r'^Art[ií]culo\.?\s+(\d+)\s*[°º]?\s*(?:\.-|\.|-)\s*(.*)$')
CP_QART = re.compile(r'^"Art(?:[ií]culo)?\.?\s*(\d+)\s*[°º]?\s*(?:\.?\s*([a-d])\b)?\s*(?:\.-|\.|-)?\s*(.*)$')
CP_LABEL = re.compile(r'^(LIBRO|PARTE|TITULO|T[IÍ]TULO|CAPITULO|CAP[IÍ]TULO|SECCION|SECCI[OÓ]N)\b')
DROPPED_HEADINGS: list[str] = []


def cp_key(n: int, suffix: str = '') -> str:
    return f'art-{n:03d}' + (f'-{suffix}' if suffix else '')


def cp_unit(n: int, title: str, paras: list[str], suffix: str = '') -> dict:
    num = f'{n}{suffix}'
    title = title.strip().rstrip('.:').strip() if paras else title.strip()
    head = f'Artículo {num}.- {title}' if title else f'Artículo {num}'
    return unit(f'Art. {num}', 'art', head, paras)


def cp_blocks(lines_: list[str], where: str, epigraph: str = 'line') -> list[tuple[int, str, str, list[str]]]:
    """Quoted 'Artículo N[a-d].- Title' blocks of an amending law: [(n, suffix, title, paragraphs)].
    Book/title/chapter headings quoted between articles are dropped (the Penal Code is kept without them).
    epigraph: 'line' (the rest of the article line is the title), 'upper' (its leading capital-letter sentences)
    or 'none' (the amending law gives no title; the rest of the line is the first paragraph)."""
    if epigraph != 'line':
        res = []
        for n, suf, title, paras in cp_blocks(lines_, where):
            whole = [title, *paras]       # quotes are already stripped by the plain call
            epi, first = split_upper(whole[0]) if epigraph == 'upper' else ('', whole[0])
            res.append((n, suf, epi, [p for p in [first, *whole[1:]] if p]))
        return res
    out = []
    cur = None
    for ln in lines_:
        m = CP_QART.match(ln)
        if m:
            cur = [int(m.group(1)), m.group(2) or '', m.group(3), []]
            out.append(cur)
            continue
        if not re.search(r'[a-zñáéíóúü]', ln):
            DROPPED_HEADINGS.append(f'{where}: {ln.strip(chr(34))}')
            continue
        assert cur is not None, (where, ln)
        cur[3].append(ln)
    res = []
    for n, suf, title, paras in out:
        if not paras:          # a one-line quotation: the closing quote sits on the title line
            title = title.rstrip('"')
        else:
            paras = strip_quote(['"' + paras[0]] + paras[1:])
        res.append((n, suf, title.rstrip('"'), join_broken(paras, f'{where} art. {n}{suf}')))
    return res


def cp_apply(rp: 'Replay', frm_of, key: str, url: str, blocks, modified: list[int]):
    """Apply quoted article blocks. An article the law lists as modified but quotes only as Na, Nb… is replaced by
    those (art. N is removed); a lettered article the law does not list is inserted."""
    plain = {n for n, s, _, _ in blocks if not s}
    for n in modified:
        if n not in plain:
            assert any(b[0] == n for b in blocks), (key, n)
            rp.op(frm_of(n), key, url, 'del', cp_key(n))
    for n, s, title, paras in blocks:
        k = cp_key(n, s)
        kind = 'set' if not s else 'add'
        rp.op(frm_of(n), key, url, kind, k, cp_unit(n, title, paras, s))


def segment_lines(L: list[str], intro_pat: str) -> list[str]:
    segs = [s for s in segments(L) if re.search(intro_pat, s[0])]
    assert len(segs) == 1, (intro_pat, [s[0][:80] for s in segs])
    return segs[0][1]


def penal_code() -> dict:
    base, _idx = penal_code_enacted()
    base = {k: (cp_unit(int(k[4:]), v['text'].split('\n', 1)[0][2:].split('.- ', 1)[1] if '.- ' in v['text'].split('\n', 1)[0] else '',
                        join_broken(v['text'].rstrip('\n').split('\n')[1:], f'cp art. {int(k[4:])}'))
                if k.startswith('art-') else v) for k, v in base.items()}
    prom = page_meta(CP_URL)['promulgated']
    assert prom == '1997-11-26', prom
    law('ley-1160-1997', label='Ley N° 1160/1997 (Código Penal)', kind='law', enacted=prom, published=None,
        url=CP_URL, title='Código Penal, promulgado el 26 de noviembre de 1997; entra en vigor un año después de su '
                          'promulgación (art. 325)')
    first = {'from': '1998-11-26', 'source_url': CP_URL, 'sha256': sha(CP_URL), 'units': base, 'credits': {},
             'note': 'The Code as enacted, from the BACN page of Ley 1160/1997.'}
    rp = Replay('codigo-penal', base, first)
    one = lambda frm: (lambda n: frm)   # noqa: E731

    url, L, frm = bacn_law('ley-2212-2003', '4879', 'Ley N° 2212/2003')
    b = cp_blocks(segment_lines(L, r'^Artículo 1°'), 'ley-2212-2003')
    assert [x[0] for x in b] == [126]
    cp_apply(rp, one(frm), 'ley-2212-2003', url, b, [126])

    url, L, frm = bacn_law('ley-2593-2005', '4131', 'Ley N° 2593/2005')
    a2 = next(s for s in segments(L) if s[0].startswith('Artículo 2°'))[0]
    assert 'el numeral 2 del inciso 3° del Artículo 184 de la Ley N° 1160/97' in a2

    def drop_184_3_2(u):
        t = u['text'].split('\n')
        i = t.index('3º Con la misma pena será castigado el que falsificara, imitara o, sin autorización del titular:')
        assert t[i + 2].startswith('2. utilizara una invención protegida por patente')
        del t[i + 2]
        return {**u, 'text': '\n'.join(t)}
    rp.op(frm, 'ley-2593-2005', url, 'fn', 'art-184', drop_184_3_2)

    # Ley 3440/2008: two in-force days (art. 3).
    url, L, _ = bacn_law('ley-3440-2008', '3485', 'Ley N° 3440/2008')
    early = {104, 148, 154, 165, 181, 182, 316}
    prom3440, pub3440 = LAWS['ley-3440-2008']['enacted'], LAWS['ley-3440-2008']['published']
    late_day = f'{int(prom3440[:4]) + 1}{prom3440[4:]}'
    early_day = day_after(max(prom3440, pub3440))
    DECISIONS.append(f'Ley N° 3440/2008 art. 3: in force one year after promulgation ({prom3440} -> {late_day}), '
                     f'except arts. 104, 148, 154, 165, 181, 182 and 316, in force the day after promulgation and '
                     f'publication ({early_day}).')
    a1 = segments(L)[0]
    assert a1[0].startswith('Artículo 1º.- Modifícanse los artículos 2º, 3º, 6º')
    listed = [int(x) for x in re.findall(r'\d+', a1[0].split('Modifícanse los artículos')[1].split('recapitúlese')[0])]
    b = cp_blocks(a1[1], 'ley-3440-2008')
    assert sorted({x[0] for x in b}) == sorted(listed), (sorted({x[0] for x in b}) , listed)
    cp_apply(rp, lambda n: early_day if n in early else late_day, 'ley-3440-2008', url, b, listed)
    DECISIONS.append('Ley N° 3440/2008 also "recapitulates" Title II of Book Two (new chapter headings) and repeals '
                     'the penal provisions of six other laws and arts. 349-353 of the 1914 Code (which art. 323 had '
                     'kept); none of that changes an article of this Code.')

    url, L, frm = bacn_law('ley-4439-2011', '3777', 'Ley N° 4439/2011')
    b = cp_blocks(segment_lines(L, r'^Artículo 1°'), 'ley-4439-2011')
    assert [f'{x[0]}{x[1]}' for x in b] == ['140', '146b', '146c', '146d', '174b', '175', '175b', '188', '248b'], b
    cp_apply(rp, one(frm), 'ley-4439-2011', url, b, [140, 175, 188])

    for key, pid, label, n in (('ley-4614-2012', '3103', 'Ley N° 4614/2012', [236, 309]),
                               ('ley-4628-2012', '2710', 'Ley N° 4628/2012', [229]),
                               ('ley-4770-2012', '3152', 'Ley N° 4770/2012', [202]),
                               ('ley-5378-2014', '3685', 'Ley N° 5378/2014', [229])):
        url, L, frm = bacn_law(key, pid, label)
        b = cp_blocks(segment_lines(L, r'^Art[ií]culo 1°'), key)
        assert [x[0] for x in b] == n and not any(x[1] for x in b), (key, b)
        cp_apply(rp, one(frm), key, url, b, n)

    # Ley 5016/2014 (tránsito) art. 153 rewrites art. 217; the new text is given unquoted, with a closing quote.
    url, L, frm = bacn_law('ley-5016-2014', '4418', 'Ley N° 5016/2014')
    seg = next(s for s in segments(L) if s[0].startswith('Artículo 153.'))
    assert 'Modifícase el Artículo 217, numeral 1) de la Ley N° 1160/97' in seg[0]
    paras = strip_quote(seg[1])
    assert paras[0] == 'El que dolosa o culposamente:' and len(paras) == 6, paras
    rp.op(frm, 'ley-5016-2014', url, 'set', 'art-217',
          cp_unit(217, 'Exposición a peligro del tránsito terrestre', paras))
    DECISIONS.append('Ley N° 5016/2014 art. 153 says it modifies "el Artículo 217, numeral 1)" but gives the whole '
                     'article (intro, numerals 1-4 and the penalty); that text replaces art. 217, keeping its title.')

    url, L, frm = bacn_law('ley-6002-2017', '9906', 'Ley N° 6002/2017')
    b = cp_blocks(segment_lines(L, r'^Artículo 1°'), 'ley-6002-2017')
    assert [f'{x[0]}{x[1]}' for x in b] == ['135a', '135b'], b
    cp_apply(rp, one(frm), 'ley-6002-2017', url, b, [135])

    url, L, frm = bacn_law('ley-6452-2019', '9058', 'Ley N° 6452/2019')
    b = cp_blocks(segment_lines(L, r'^Artículo 1\.'), 'ley-6452-2019')
    assert [f'{x[0]}{x[1]}' for x in b] == ['91', '191a', '191b', '196', '268a', '268b', '268c'], b
    cp_apply(rp, one(frm), 'ley-6452-2019', url, b, [91, 191, 196, 268])

    for key, pid, label, n, pat in (('ley-6535-2020', '9215', 'Ley N° 6535/2020', [103], r'^Artículo 1°'),
                                    ('ley-6771-2021', '9629', 'Ley N° 6771/2021', [107], r'^Artículo 1\.'),
                                    ('ley-6830-2021', '9670', 'Ley N° 6830/2021', [142], r'^Artículo 1°'),
                                    ('ley-6934-2022', '10525', 'Ley N° 6934/2022', [229], r'^Artículo 1°'),
                                    ('ley-7220-2024', '12473', 'Ley N° 7220/2024', [172], r'^Artículo 1º'),
                                    ('ley-7300-2024', '12443', 'Ley N° 7300/2024', [173], r'^Artículo 4\.')):
        url, L, frm = bacn_law(key, pid, label)
        b = cp_blocks(segment_lines(L, pat), key)
        assert [x[0] for x in b] == n and not any(x[1] for x in b), (key, b)
        cp_apply(rp, one(frm), key, url, b, n)
    DECISIONS.append('Ley N° 6934/2022 art. 2 also repeals Leyes 4628/2012 and 5378/2014, whose wording of art. 229 '
                     'it has just replaced; that changes no text.')

    url, L, frm = bacn_law('ley-7062-2023', '11358', 'Ley N° 7062/2023')
    b = cp_blocks(segment_lines(L, r'^Artículo 1\.'), 'ley-7062-2023')
    assert [f'{x[0]}{x[1]}' for x in b] == ['8', '105a', '105b'], b
    cp_apply(rp, one(frm), 'ley-7062-2023', url, b, [8, 105])
    b = cp_blocks(segment_lines(L, r'^Artículo 2\.'), 'ley-7062-2023')
    assert [x[0] for x in b] == [240]
    cp_apply(rp, one(frm), 'ley-7062-2023', url, b, [240])

    versions = rp.build()
    return {'slug': 'codigo-penal', 'short': 'CP', 'title': 'Código Penal (Ley N° 1160/1997)', 'url': CP_URL,
            'first_law': 'ley-1160-1997', 'earlier_laws': [], 'versions': versions}


def penal_code_enacted() -> tuple[dict, list[str]]:
    L = page_lines(CP_URL)
    assert L[:3] == ['Descripción', 'LEY N° 1160', 'CODIGO PENAL'] and L[4] == 'LEY', L[:5]
    units: dict[str, list] = {}
    index: list[list] = []
    cur = None
    prev_heading = False
    closing = None
    nxt = 1
    for ln in L[5:]:
        if ln.startswith('Aprobada por la Honorable'):
            closing = ln
            cur = None
            continue
        m = CP_ART.match(ln)
        if m and not m.group(2).startswith('"') and int(m.group(1)) == nxt:
            n = nxt
            nxt += 1
            cur = [m.group(2)]
            units[cp_key(n)] = cur
            for e in index:
                if e[0] is None:
                    e[0] = cp_key(n)
            prev_heading = False
            continue
        if not re.search(r'[a-zñáéíóúü]', ln):
            if CP_LABEL.match(ln) or not prev_heading:
                index.append([None, ln])
            else:
                index[-1][1] += (' - ' if CP_LABEL.match(index[-1][1]) and ' - ' not in index[-1][1] else ' ') + ln
            prev_heading = True
            cur = None
            continue
        assert cur is not None, ln
        cur.append(ln)
        prev_heading = False
    assert nxt == 327 and closing, (nxt, closing)
    out = {k: cp_unit(int(k[4:]), v[0], v[1:]) for k, v in units.items()}
    out['sancion'] = unit('Sanción', 'closing', 'SANCION', [closing])
    return out, [f'{k}: {t}' for k, t in index]


# ---------------------------------------------------------------- Código Procesal Penal (Ley 1286/1998)

CPP_URL = BACN + '203/ley-n-1286-c-digo-procesal-penal-br'
CPP_ART = re.compile(r'^Art[ií]culo\s+(\d+)\s*[°º]?\.\s*(.*)$')
CPP_QART = re.compile(r'^"Art(?:[ií]culo)?\.?\s*(\d+)\s*[°º]?\s*(?:\.-|\.|-|:)\s*(.*)$')
LOWER = re.compile(r'[a-zñáéíóúü]')


def split_upper(rest: str) -> tuple[str, str]:
    """'ACCIÓN PRIVADA. Serán …' -> ('ACCIÓN PRIVADA', 'Serán …'): the epigraph is the leading sentences without
    lower-case letters."""
    pos = 0
    end = 0
    for m in re.finditer(r'\.(\s+|$)', rest):
        seg = rest[pos:m.start()]
        if LOWER.search(seg) or not seg.strip():
            break
        end = m.start()
        pos = m.end()
    return (rest[:end].strip(), rest[pos:].strip()) if end else ('', rest.strip())


def cpp_key(n: int) -> str:
    return f'art-{n:03d}'


def cpp_unit(n: int, epigraph: str, paras: list[str]) -> dict:
    epigraph = epigraph.strip().rstrip('.:').strip()
    return unit(f'Art. {n}', 'art', f'Artículo {n}. {epigraph}' if epigraph else f'Artículo {n}',
                [p for p in paras if p])


def cpp_enacted() -> dict:
    L = page_lines(CPP_URL)
    assert L[:3] == ['Descripción', 'LEY N° 1.286', 'CÓDIGO PROCESAL PENAL'] and L[4] == 'LEY:', L[:5]
    units: dict[str, list] = {}
    index: list[list] = []
    cur = None
    prev_heading = False
    closing = None
    nxt = 1
    for ln in L[5:]:
        if ln.startswith('Aprobado el Proyecto de Ley por la Honorable'):
            closing = ln
            break
        m = CPP_ART.match(ln)
        if m and int(m.group(1)) == nxt:
            epi, text = split_upper(m.group(2))
            cur = [epi, text]
            units[cpp_key(nxt)] = cur
            for e in index:
                if e[0] is None:
                    e[0] = cpp_key(nxt)
            nxt += 1
            prev_heading = False
            continue
        if not LOWER.search(ln):
            if CP_LABEL.match(ln) or not prev_heading:
                index.append([None, ln])
            else:
                index[-1][1] += (' - ' if CP_LABEL.match(index[-1][1]) and ' - ' not in index[-1][1] else ' / ') + ln
            prev_heading = True
            cur = None
            continue
        assert cur is not None, ln
        cur.append(ln)
        prev_heading = False
    assert nxt == 507 and closing, (nxt, closing)
    out = {k: cpp_unit(int(k[4:]), v[0], join_broken(v[1:], f'cpp art. {int(k[4:])}')) for k, v in units.items()}
    out['indice'] = unit('Índice de partes, libros, títulos y capítulos', 'index',
                         'PARTES, LIBROS, TITULOS Y CAPITULOS', [f'{k}: {t}' for k, t in index])
    out['sancion'] = unit('Sanción', 'closing', 'SANCION', [closing])
    return out


def cpp_block(L: list[str], intro_pat: str, epigraph: str, where: str) -> list[tuple[int, dict]]:
    """Quoted articles of one article of an amending law. epigraph: 'upper' (capitals up to the first sentence
    with lower case), 'line' (the rest of the article line), 'sentence' (its first sentence) or 'none'."""
    lines_ = segment_lines(L, intro_pat)
    out = []
    for ln in lines_:
        m = CPP_QART.match(ln)
        if m:
            out.append([int(m.group(1)), m.group(2), []])
        elif not LOWER.search(ln):
            DROPPED_HEADINGS.append(f'{where}: {ln.strip(chr(34))}')
        else:
            assert out, (where, ln)
            out[-1][2].append(ln)
    res = []
    for n, rest, more in out:
        if epigraph == 'upper':
            epi, first = split_upper(rest)
        elif epigraph == 'line':
            epi, first = rest, ''
        elif epigraph == 'sentence':
            epi, first = rest.split('. ', 1)
        else:
            epi, first = '', rest
        paras = strip_quote(['"' + x for x in [first]][:1] + more) if first else strip_quote(['"' + more[0]] + more[1:])
        res.append((n, cpp_unit(n, epi, join_broken(paras, f'{where} art. {n}'))))
    return res


def codigo_procesal_penal() -> dict:
    base = cpp_enacted()
    prom = page_meta(CPP_URL)['promulgated']
    assert prom == '1998-07-08', prom
    law('ley-1286-1998', label='Ley N° 1286/1998 (Código Procesal Penal)', kind='law', enacted=prom,
        published=page_meta(CPP_URL)['published'], url=CPP_URL,
        title='Código Procesal Penal, promulgado el 8 de julio de 1998; art. 505: entra en vigor un año después de '
              'su promulgación')
    # Ley 1444/1999 (transition): partial application from 9 July 1999 (art. 2), full from 1 March 2000 (art. 3);
    # art. 18 repeals art. 17 inc. 15 and art. 505 from 9 July 1999, the first day the Code applied.
    url1444, L1444, _ = bacn_law('ley-1444-1999', '1592', 'Ley N° 1444/1999')
    a18 = next(l for l in L1444 if l.startswith('Desde el día 9 de julio de 1999, quedarán derogados'))
    assert '2) el inciso 15) del artículo 17 de la Ley No. 1286/98' in a18 and '3) el artículo 505 de la Ley No. 1286/98' in a18
    assert any(l.startswith('A partir del día 9 de julio de 1999, la aplicación de la Ley No. 1286/98') for l in L1444)
    assert any(l.startswith('A partir del 1 de marzo del año 2000, entrará plenamente en vigencia la Ley No. 1286/98') for l in L1444)
    first_units = dict(base)
    t17 = first_units['art-017']['text'].split('\n')
    i15 = t17.index('15) violación del derecho de autor o inventor.')
    assert t17[i15 - 1] == '14) uso no autorizado de vehículo automotor; y', t17
    del t17[i15]
    first_units['art-017'] = {**first_units['art-017'], 'text': '\n'.join(t17)}
    del first_units['art-505']
    LAWS['ley-1444-1999']['note'] = (
        'Ley 1444/1999 (transition to the new procedure): the Code applied in part from 9 July 1999 (art. 2) and in '
        'full from 1 March 2000 (art. 3, "vigencia plena"); art. 18 repealed art. 17 inc. 15 and art. 505 (the '
        'entry-into-force article of the Code) from 9 July 1999.')
    enacted = {'from': '1999-07-09', 'source_url': CPP_URL, 'sha256': sha(CPP_URL), 'units': dict(base), 'credits': {},
               'note': 'The Code as enacted (BACN page of Ley 1286/1998), on the day it first applied in part under '
                       'Ley 1444/1999 art. 2. Ley 1444/1999 art. 18 repeals art. 17 inc. 15 and art. 505 the same day '
                       '(next commit); full application followed on 1 March 2000 (art. 3).'}
    repeal1444 = {'from': '1999-07-09', 'same_day': True, 'source_url': url1444, 'sha256': sha(url1444),
                  'units': first_units, 'credits': {'art-017': ['ley-1444-1999'], 'art-505': ['ley-1444-1999']}}
    first = {'from': '1999-07-09', 'source_url': url1444, 'sha256': sha(url1444), 'units': first_units, 'credits': {}}
    rp = Replay('codigo-procesal-penal', first_units, first)
    for k in first_units:
        if k.startswith('art-'):
            rp.op('2000-03-01', 'ley-1444-1999', url1444, 'touch', k)

    url, L, frm = bacn_law('ley-2341-2003', '5046', 'Ley N° 2341/2003')
    (n, u), = cpp_block(L, r'^Artículo 1º', 'none', 'ley-2341-2003')
    assert n == 136
    rp.op(frm, 'ley-2341-2003', url, 'set', 'art-136', u)

    url, L, frm = bacn_law('ley-2493-2004', '3997', 'Ley N° 2493/2004')
    (n, u), = cpp_block(L, r'^Artículo 1º', 'upper', 'ley-2493-2004')
    assert n == 245
    rp.op(frm, 'ley-2493-2004', url, 'set', 'art-245', u)

    url, L, frm = bacn_law('ley-4431-2011', '3773', 'Ley N° 4431/2011')
    (n, u), = cpp_block(L, r'^Artículo 1°', 'upper', 'ley-4431-2011')
    assert n == 245
    rp.op(frm, 'ley-4431-2011', url, 'set', 'art-245', u)

    # Ley 4669/2012 rewrites arts. 136-137; no vigencia clause, so in force the day after publication. Ley 4734/2012
    # suspends it (2 years, extended to 3, 4 and 6 years); Ley 6146/2018 repeals it before the suspension ends.
    url4669, L, frm4669 = bacn_law('ley-4669-2012', '3119', 'Ley N° 4669/2012')
    b = cpp_block(L, r'^Artículo 1°', 'upper', 'ley-4669-2012')
    assert [n for n, _ in b] == [136, 137]
    for n, u in b:
        rp.op(frm4669, 'ley-4669-2012', url4669, 'set', cpp_key(n), u)
    url, L, frm = bacn_law('ley-4734-2012', '1202', 'Ley N° 4734/2012')
    assert segments(L)[0][0].startswith('Artículo 1º.- Suspéndase por el plazo de dos años la vigencia de la Ley N° 4.669/12')
    LAWS['ley-4734-2012'].update(restores='ley-4669-2012', note=(
        'Suspends Ley 4669/2012 for two years (art. 1), so arts. 136 and 137 return to the wording in force before it. '
        'Leyes 5276/2014, 5475/2015 and 5671/2016 extend the suspension to three, four and six years; Ley 6146/2018 '
        'repeals Ley 4669/2012.'))
    for k in ('art-136', 'art-137'):
        rp.op(frm, 'ley-4734-2012', url, 'restore', k, frm4669)
    susp_end = frm
    for key, pid, label, years in (('ley-5276-2014', '3007', 'Ley N° 5276/2014', 'tres'),
                                   ('ley-5475-2015', '4460', 'Ley N° 5475/2015', 'cuatro'),
                                   ('ley-5671-2016', '5184', 'Ley N° 5671/2016', 'seis')):
        url, L, frm = bacn_law(key, pid, label)
        q = segment_lines(L, r'^Art[ií]culo 1')[0]
        assert f'Suspéndase por el plazo de {years} años la vigencia de la Ley' in q, q
        n_prev = {'tres': 2, 'cuatro': 3, 'seis': 4}[years]
        end_prev = f'{int(susp_end[:4]) + n_prev}{susp_end[4:]}'
        assert frm <= end_prev, (key, frm, end_prev)     # each extension takes effect before the suspension ends
        LAWS[key]['note'] = (f'Extends the suspension of Ley 4669/2012 (Ley 4734/2012 art. 1) to {dict(tres="three", cuatro="four", seis="six")[years]} years, '
                             f'before the previous period ended ({end_prev}); the wording of arts. 136 and 137 does not '
                             'change.')
        for k in ('art-136', 'art-137'):
            rp.op(frm, key, url, 'touch', k)
    url, L, frm = bacn_law('ley-6146-2018', '8655', 'Ley N° 6146/2018')
    assert frm <= f'{int(susp_end[:4]) + 6}{susp_end[4:]}'
    assert segments(L)[0][0].startswith('Artículo 1.° Derógase la Ley N° 4.669/2012')
    LAWS['ley-6146-2018']['note'] = ('Repeals Ley 4669/2012, which was suspended, and confirms Ley 2341/2003 (art. 2); '
                                     'the wording of arts. 136 and 137 does not change.')
    for k in ('art-136', 'art-137'):
        rp.op(frm, 'ley-6146-2018', url, 'touch', k)

    url, L, frm = bacn_law('ley-4685-2012', '1225', 'Ley N° 4685/2012')
    (n, u), = cpp_block(L, r'^Artículo 1º', 'upper', 'ley-4685-2012')
    assert n == 57
    rp.op(frm, 'ley-4685-2012', url, 'set', 'art-057', u)

    url, L, frm = bacn_law('ley-6350-2019', '8902', 'Ley N° 6350/2019')
    (n, u), = cpp_block(L, r'^Artículo 1\.', 'upper', 'ley-6350-2019')
    assert n == 245
    rp.op(frm, 'ley-6350-2019', url, 'set', 'art-245', u)

    # Temporary wording (Leyes 6353/2019 and 6418/2019, art. 2): until 31 January 2020; from 1 February 2020 the
    # original wording applies again. The return is a version credited to a "fin de vigencia" entry with `restores`.
    for key, pid, label, arts, mode in (('ley-6353-2019', '8900', 'Ley N° 6353/2019', [129, 141, 251], 'line'),
                                        ('ley-6418-2019', '9045', 'Ley N° 6418/2019', [253], 'sentence')):
        url, L, frm = bacn_law(key, pid, label)
        a2 = next(s for s in segments(L) if s[0].startswith('Artículo 2.'))
        assert 'tendrán vigencia hasta el 31 de enero de 2020' in a2[0]
        assert a2[1][0].startswith('A partir del 1 de febrero de 2020, volverán a regir') and 'conforme a su redacción original' in a2[1][0]
        b = cpp_block(L, r'^Artículo 1\.', mode, key)
        assert [n for n, _ in b] == arts, (key, b)
        for n, u in b:
            rp.op(frm, key, url, 'set', cpp_key(n), u)
        LAWS[key]['temporary_until'] = '2020-01-31'
        fin = key + '-fin'
        law(fin, label=f'{label}, fin de vigencia', kind='law', enacted=LAWS[key]['enacted'],
            published=LAWS[key]['published'], url=url, restores=key,
            title=f'Fin de la vigencia temporal de la {label} (art. 2)',
            note=f'{label} art. 2: its wording applied until 31 January 2020; from 1 February 2020 the original '
                 f'wording of art. {", ".join(map(str, arts))} applies again.')
        for n in arts:
            rp.op('2020-02-01', fin, url, 'restore', cpp_key(n), frm)

    versions = rp.build()
    assert versions[0] is first
    versions = [enacted, repeal1444] + versions[1:]     # the replay started from the state after Ley 1444 art. 18
    last = versions[-1]['units']
    for k in ('art-129', 'art-141', 'art-251', 'art-253'):     # "conforme a su redacción original"
        assert last[k] == first_units[k], k
    return {'slug': 'codigo-procesal-penal', 'short': 'CPP', 'title': 'Código Procesal Penal (Ley N° 1286/1998)',
            'url': CPP_URL, 'first_law': 'ley-1286-1998', 'earlier_laws': [], 'versions': versions}


# ---------------------------------------------------------------- shared parser for codes printed article by article

def enacted_code(url: str, art_re: re.Pattern, head: tuple[str, ...], closing_prefix: str, n_last: int,
                 make_unit, where: str, skip: tuple[int, ...] = (), heading_lines: tuple[str, ...] = ()) -> dict:
    """Articles numbered 1..n_last in order (numbers in `skip` are absent from BACN), headings to `indice`,
    the closing formula to `sancion`. make_unit(n, rest_of_article_line, paragraphs) -> unit."""
    L = page_lines(url)
    assert tuple(L[:len(head)]) == head, L[:len(head) + 1]
    units: dict[str, dict] = {}
    raw_units: dict[int, list] = {}
    index: list[list] = []
    cur = None
    prev_heading = False
    closing = None
    nxt = 1
    for ln in L[len(head):]:
        if ln.startswith(closing_prefix):
            closing = ln
            break
        m = art_re.match(ln)
        while nxt in skip:
            nxt += 1
        if m and int(m.group(1).replace('.', '')) == nxt:
            cur = [m.group(2)]
            raw_units[nxt] = cur
            for e in index:
                if e[0] is None:
                    e[0] = f'art-{nxt:03d}'
            nxt += 1
            prev_heading = False
            continue
        if not LOWER.search(ln) or ln in heading_lines:
            if CP_LABEL.match(ln) or not prev_heading:
                index.append([None, ln])
            else:
                index[-1][1] += (' - ' if CP_LABEL.match(index[-1][1]) and ' - ' not in index[-1][1] else ' / ') + ln
            prev_heading = True
            cur = None
            continue
        assert cur is not None, (where, ln)
        cur.append(ln)
        prev_heading = False
    assert nxt == n_last + 1 and closing, (where, nxt, closing)
    for n, v in raw_units.items():
        units[f'art-{n:03d}'] = make_unit(n, v[0], join_broken(v[1:], f'{where} art. {n}'))
    units['indice'] = unit('Índice de libros, títulos y capítulos', 'index', 'LIBROS, TITULOS Y CAPITULOS',
                           [f'{k}: {t}' for k, t in index])
    units['sancion'] = unit('Sanción', 'closing', 'SANCION', [closing])
    return units


# ---------------------------------------------------------------- Código de la Niñez y la Adolescencia (Ley 1680/2001)

CNA_URL = BACN + '5261/ley-n-1680-codigo-de-la-ni-ez-y-la-adolescencia-br'
CNA_ART = re.compile(r'^Ar[tí]*culo\s+(\d+)\s*[°º]?\s*(?:\.-|\.|-)\s*(.*)$')


def cna_unit(n: int, title: str, paras: list[str]) -> dict:
    return cp_unit(n, title, paras)


def cna_enacted() -> dict:
    return enacted_code(CNA_URL, CNA_ART, ('Descripción', 'LEY N° 1680', 'CODIGO DE LA NIÑEZ Y LA ADOLESCENCIA',
                                           'EL CONGRESO DE LA NACION PARAGUAYA SANCIONA CON FUERZA DE', 'LEY:'),
                        'Aprobado el Proyecto de Ley por la Honorable', 259, cna_unit, 'cna')


def codigo_ninez() -> dict:
    base = cna_enacted()
    m = page_meta(CNA_URL)
    assert m['promulgated'] == '2001-05-30', m
    t258 = base['art-258']['text']
    assert 'El presente Código entrará en vigencia a partir de los seis meses de su promulgación.' in t258
    law('ley-1680-2001', label='Ley N° 1680/2001 (Código de la Niñez y la Adolescencia)', kind='law',
        enacted=m['promulgated'], published=m['published'], url=CNA_URL,
        title='Código de la Niñez y la Adolescencia, promulgado el 30 de mayo de 2001; entra en vigencia a los seis '
              'meses de su promulgación (art. 258)')
    first = {'from': '2001-11-30', 'source_url': CNA_URL, 'sha256': sha(CNA_URL), 'units': base, 'credits': {},
             'note': 'The Code as enacted, from the BACN page of Ley 1680/2001 (BACN prints "Arículo 199").'}
    rp = Replay('codigo-ninez-adolescencia', base, first)
    one = lambda frm: (lambda n: frm)   # noqa: E731

    url, L, frm = bacn_law('ley-2169-2003', '4845', 'Ley N° 2169/2003')    # already a Civil Code amender
    b = cp_blocks(segment_lines(L, r'^Artículo 4°'), 'ley-2169-2003 (cna)', 'none')
    assert [x[0] for x in b] == [2], b
    cp_apply(rp, one(frm), 'ley-2169-2003', url, b, [2])

    url, L, frm = bacn_law('ley-3879-2009', '1509', 'Ley N° 3879/2009')
    b = cp_blocks(segment_lines(L, r'^Artículo 1°'), 'ley-3879-2009', 'upper')
    assert [x[0] for x in b] == [169], b
    cp_apply(rp, one(frm), 'ley-3879-2009', url, b, [169])

    url, L, frm = bacn_law('ley-6083-2018', '8441', 'Ley N° 6083/2018')
    listed = [29, 41, 92, 93, 94, 95, 96, 158, 159, 165, 167, 175]
    b = cp_blocks(segment_lines(L, r'^Artículo 1\.'), 'ley-6083-2018')
    assert [x[0] for x in b] == listed and not any(x[1] for x in b), b
    cp_apply(rp, one(frm), 'ley-6083-2018', url, b, listed)

    url, L, frm = bacn_law('ley-6174-2018', '8805', 'Ley N° 6174/2018')
    a12 = next(s for s in segments(L) if s[0].startswith('Artículo 12.'))[0]
    assert 'Quedan derogados los artículos 39, 40 y 41 de la Ley N° 1.680/2001' in a12
    for n in (39, 40, 41):
        rp.op(frm, 'ley-6174-2018', url, 'del', cp_key(n))

    versions = rp.build()
    return {'slug': 'codigo-ninez-adolescencia', 'short': 'CNA',
            'title': 'Código de la Niñez y la Adolescencia (Ley N° 1680/2001)', 'url': CNA_URL,
            'first_law': 'ley-1680-2001', 'earlier_laws': [], 'versions': versions}


# ---------------------------------------------------------------- Código Procesal Civil (Ley 1337/1988)

CPC_URL = BACN + '3038/ley-n-1337-codigo-procesal-civil-br'
CPC_SCAN = 'https://www.bacn.gov.py/archivos/3038/20150225135017.pdf'
CPC_ART = re.compile(r'^Art\.\s*(\d{1,2}\.\d{3}|\d+)\s*[°º]?\s*(?:\.-|\.|-)\s*(.*)$')
CPC_QART = re.compile(r'^"Art\.?\s*(\d{1,2}\.\d{3}|\d+)\s*[°º]?\s*(?:\.-|\.|-)\s*(.*)$')


def cpc_split(rest: str) -> tuple[str, str]:
    """'Aplicación de este Código. Las disposiciones …' -> epigraph, text (the epigraph is the first sentence)."""
    m = re.match(r'^(.+?)\s*\.-?\s*(?=[A-ZÁÉÍÓÚÑ¿"(]|$)', rest)
    if not m or not rest[m.end():].strip():
        return '', rest.strip()
    return m.group(1).strip(), rest[m.end():].strip()


def cpc_unit(n: int, rest: str, paras: list[str]) -> dict:
    epi, first = cpc_split(rest)
    return unit(f'Art. {n}', 'art', f'Art. {n}.- {epi}' if epi else f'Art. {n}', [p for p in [first, *paras] if p])


def cpc_blocks(L: list[str], intro_pat: str, where: str, epigraph: bool = True) -> list[tuple[int, dict]]:
    out = []
    for ln in segment_lines(L, intro_pat):
        m = CPC_QART.match(ln)
        if m:
            out.append([int(m.group(1).replace('.', '')), m.group(2), []])
        elif not LOWER.search(ln):
            DROPPED_HEADINGS.append(f'{where}: {ln.strip(chr(34))}')
        else:
            assert out, (where, ln)
            out[-1][2].append(ln)
    res = []
    for n, rest, more in out:
        paras = strip_quote(['"' + rest] + more)
        if epigraph:
            res.append((n, cpc_unit(n, paras[0], join_broken(paras[1:], f'{where} art. {n}'))))
        else:
            res.append((n, unit(f'Art. {n}', 'art', f'Art. {n}', join_broken(paras, f'{where} art. {n}'))))
    return res


def codigo_procesal_civil() -> dict:
    base = enacted_code(CPC_URL, CPC_ART, ('Descripción', 'LEY N° 1.337', 'CODIGO PROCESAL CIVIL',
                                           'EL CONGRESO DE LA NACION PARAGUAYA SANCIONA CON FUERZA DE', 'LEY'),
                        'Dada en la Sala de sesiones del Congreso Nacional', 839, cpc_unit, 'cpc')
    assert base['art-837']['text'].split('\n')[1].startswith('Las disposiciones de este Código entrará en vigencia al '
                                                              'año de su promulgación'), base['art-837']['text']
    law('ley-1337-1988', label='Ley N° 1337/1988 (Código Procesal Civil)', kind='law', enacted='1988-11-04',
        published=None, url=CPC_URL,
        title='Código Procesal Civil, sancionado el 20 de octubre de 1988 y promulgado el 4 de noviembre de 1988; '
              'entra en vigencia al año de su promulgación (art. 837)')
    first = {'from': '1989-11-04', 'source_url': CPC_URL, 'sha256': sha(CPC_URL), 'units': base, 'credits': {},
             'note': 'The Code as enacted, from the BACN page of Ley 1337/1988. The promulgation date (4 November 1988) '
                     'is read from the signed original scan BACN links (' + CPC_SCAN + ', last page).'}
    rp = Replay('codigo-procesal-civil', base, first)

    url, L, frm = bacn_law('ley-600-1995', '11593', 'Ley N° 600/1995')
    a1 = segments(L)[0]
    assert a1[0].startswith('Artículo 1º.- Derógase el Artículo 580, Título II "DEL JUICIO DE AMPARO" de la Ley Nº 1.337')
    rp.op(frm, 'ley-600-1995', url, 'del', 'art-580')
    (n, u), = cpc_blocks(L, r'^Artículo 1º', 'ley-600-1995', epigraph=False)
    assert n == 582
    rp.op(frm, 'ley-600-1995', url, 'set', 'art-582', u)

    for key, pid, label, arts, pat in (('ley-1493-2000', '1568', 'Ley N° 1493/2000', [530, 716, 717], r'^Artículo 1º'),
                                       ('ley-4419-2011', '3769', 'Ley N° 4419/2011', [409], r'^Artículo 1°'),
                                       ('ley-4867-2013', '3177', 'Ley N° 4867/2013', [173], r'^Artículo 1°'),
                                       ('ley-5330-2014', '3037', 'Ley N° 5330/2014', [701], r'^Artículo 1\.'),
                                       ('ley-6979-2022', '10672', 'Ley N° 6979/2022', [621], r'^Artículo 1º')):
        url, L, frm = bacn_law(key, pid, label)
        b = cpc_blocks(L, pat, key)
        assert [n for n, _ in b] == arts, (key, [n for n, _ in b])
        for n, u in b:
            rp.op(frm, key, url, 'set', f'art-{n:03d}', u)

    url, L, frm = bacn_law('ley-4992-2013', '4767', 'Ley N° 4992/2013')
    a4 = next(s for s in segments(L) if s[0].startswith('Artículo 4°'))[0]
    assert a4.startswith('Artículo 4°.- Derógase el inciso c) del Artículo 37 de la Ley N° 1337/88')

    def drop_37c(u):
        t = u['text'].split('\n')
        hit = [i for i, x in enumerate(t) if x.startswith('c) ')]
        assert len(hit) == 1, t
        del t[hit[0]]
        return {**u, 'text': '\n'.join(t)}
    rp.op(frm, 'ley-4992-2013', url, 'fn', 'art-037', drop_37c)

    url, L, frm = bacn_law('ley-6059-2018', '8503', 'Ley N° 6059/2018')
    a8 = next(s for s in segments(L) if s[0].startswith('Artículo 8.'))[0]
    assert 'el Artículo 684 del Título XIII del Libro IV, de la Ley N° 1337/88 "CÓDIGO PROCESAL CIVIL"' in a8
    rp.op(frm, 'ley-6059-2018', url, 'del', 'art-684')

    versions = rp.build()
    return {'slug': 'codigo-procesal-civil', 'short': 'CPC', 'title': 'Código Procesal Civil (Ley N° 1337/1988)',
            'url': CPC_URL, 'first_law': 'ley-1337-1988', 'earlier_laws': [], 'versions': versions}


# ---------------------------------------------------------------- Código Aduanero, Ley del Comerciante, Código Sanitario

GEN_ART = re.compile(r'^Art(?:[ií]culo|\.+)\s*(\d+)\s*[°º]?\s*(?:\.-|\.|-)\s*(.*)$')


def plain_unit(word: str):
    """Articles without an epigraph: '# Art. N' (or '# Artículo N'), the text after the number as the first line."""
    def make(n: int, rest: str, paras: list[str]) -> dict:
        return unit(f'Art. {n}', 'art', f'{word} {n}', [p for p in [rest.strip(), *paras] if p])
    return make


def epigraph_unit(n: int, rest: str, paras: list[str]) -> dict:
    epi, first = cpc_split(rest)
    return unit(f'Art. {n}', 'art', f'Artículo {n}.- {epi}' if epi else f'Artículo {n}',
                [p for p in [first, *paras] if p])


def quoted(L: list[str], intro_pat: str, make, where: str) -> list[tuple[int, dict]]:
    """'"Art. N.- …"' blocks inside one article of an amending law, made into units with `make`."""
    out = []
    for n, paras in amending_blocks(segment_lines(L, intro_pat), CC_QART):
        out.append((n, make(n, paras[0], join_broken(paras[1:], f'{where} art. {n}'))))
    return out


def simple_code(slug, short, title, url, head, closing, n_last, make, law_key, law_label, law_title, frm, note,
                amendments, skip=(), heading_lines=()) -> dict:
    base = enacted_code(url, GEN_ART, head, closing, n_last, make, slug, skip, heading_lines)
    m = page_meta(url)
    law(law_key, label=law_label, kind='law', enacted=m['promulgated'], published=m['published'], url=url,
        title=law_title)
    first = {'from': frm, 'source_url': url, 'sha256': sha(url), 'units': base, 'credits': {}, 'note': note}
    rp = Replay(slug, base, first)
    for a in amendments:
        a(rp, make)
    return {'slug': slug, 'short': short, 'title': title, 'url': url, 'first_law': law_key, 'earlier_laws': [],
            'versions': rp.build()}


def set_from(key, pid, label, intro, arts):
    def apply(rp, make):
        url, L, frm = bacn_law(key, pid, label)
        b = quoted(L, intro, make, key)
        assert [n for n, _ in b] == arts, (key, [n for n, _ in b])
        for n, u in b:
            rp.op(frm, key, url, 'set', f'art-{n:03d}', u)
    return apply


def repeal_from(key, pid, label, intro, must, arts):
    def apply(rp, make):
        url, L, frm = bacn_law(key, pid, label)
        a = next(s for s in segments(L) if re.search(intro, s[0]))[0]
        assert must in a, (key, a)
        for n in arts:
            rp.op(frm, key, url, 'del', f'art-{n:03d}')
    return apply


ADU_URL = BACN + '2276/ley-n-2422-codigo-aduanero-br'
COM_URL = BACN + '2538/ley-n-1034-del-comerciante'
SAN_URL = BACN + '2399/ley-n-836-c-digo-sanitario-br'
SAN_SCAN = 'https://www.bacn.gov.py/archivos/2399/20140423122211.pdf'


def codigo_aduanero() -> dict:
    import datetime as dt
    m = page_meta(ADU_URL)
    assert m['promulgated'] == '2004-07-15', m
    frm = (dt.date.fromisoformat(m['promulgated']) + dt.timedelta(days=180)).isoformat()
    a = simple_code('codigo-aduanero', 'CA', 'Código Aduanero (Ley N° 2422/2004)', ADU_URL,
                    ('Descripción', 'LEY Nº 2422', 'CODIGO ADUANERO',
                     'EL CONGRESO DE LA NACIÓN PARAGUAYA, SANCIONA CON FUERZA DE', 'L E Y :'),
                    'Aprobado el Proyecto de Ley por la Honorable', 398, plain_unit('Artículo'),
                    'ley-2422-2004', 'Ley N° 2422/2004 (Código Aduanero)',
                    'Código Aduanero; entra en vigencia a los ciento ochenta días de su promulgación (art. 397)', frm,
                    'The Code as enacted, from the BACN page of Ley 2422/2004.',
                    [set_from('ley-6417-2019', '9046', 'Ley N° 6417/2019', r'^Artículo 1\.', [336, 345])])
    assert 'Este Código entrará en vigencia a los ciento ochenta días de su promulgación' in \
        a['versions'][0]['units']['art-397']['text']
    return a


def ley_comerciante() -> dict:
    return simple_code('ley-del-comerciante', 'LC', 'Ley N° 1034/1983 del Comerciante', COM_URL,
                       ('Descripción', 'LEY N° 1034', 'DEL COMERCIANTE',
                        'EL CONGRESO DE LA NACION PARAGUAYA SANCIONAN CON FUERZA DE', 'LEY :'),
                       'DADA EN LA SALA DE SESIONES DEL CONGRESO NACIONAL', 123, plain_unit('Art.'),
                       'ley-1034-1983', 'Ley N° 1034/1983 (Del Comerciante)', 'Del Comerciante',
                       day_after(page_meta(COM_URL)['published']),
                       'The law as enacted, from its BACN page. In force the day after publication (Código Civil art. 1; '
                       'the law has no vigencia clause).',
                       [repeal_from('ley-2169-2003', '4845', 'Ley N° 2169/2003', r'^Artículo 2º',
                                    'el Artículo 7° de la Ley N° 1034/83 "Del Comerciante"', [7]),
                        set_from('ley-4924-2013', '1139', 'Ley N° 4924/2013', r'^Artículo 1°', [76]),
                        repeal_from('ley-5810-2017', '9710', 'Ley N° 5810/2017', r'^Artículo 233\.',
                                    'el artículo 122 de la Ley N° 1.034/83 "DEL COMERCIANTE"', [122])],
                       heading_lines=comerciante_headings())


def comerciante_headings() -> tuple[str, ...]:
    """Ley 1034 prints its title/chapter/section headings in mixed case ("Capìtulo I", "De los corredores"): short
    lines with no final punctuation that open with Cap/Secc/Disposici/Diposici/De l/Del."""
    L = page_lines(COM_URL)
    out, prev = [], False
    for l in L[5:]:
        short = not GEN_ART.match(l) and len(l) < 90 and not re.search(r'[.;:,]$', l)
        hit = short and (prev or re.match(r'^(Cap[ií]tulo|Cap[ìi]tulo|Secci[oóò]n|Disposici|Diposici|De l|Del )', l))
        if hit:
            out.append(l)
        prev = bool(hit) and bool(re.match(r'^(Cap|Secc)', l))
    return tuple(out)


def codigo_sanitario() -> dict:
    return simple_code('codigo-sanitario', 'CS', 'Código Sanitario (Ley N° 836/1980)', SAN_URL,
                       ('Descripción', 'LEY N° 836', 'CODIGO SANITARIO',
                        'EL CONGRESO DE LA NACION PARAGUAYA SANCIONA CON FUERZA DE', 'LEY :'),
                       'Dada en la Sala de Sesiones del Congreso Nacional', 328, plain_unit('Artículo'),
                       'ley-836-1980', 'Ley N° 836/1980 (Código Sanitario)', 'Código Sanitario',
                       day_after(page_meta(SAN_URL)['published']),
                       'The Code as enacted, from its BACN page, in force the day after publication (no vigencia '
                       'clause). BACN\'s HTML omits arts. 123-130, which exist only in the signed scan BACN links '
                       '(' + SAN_SCAN + ', page 15), and art. 321; they are not in this repository.',
                       [set_from('ley-115-1990', '5341', 'Ley N° 115/1990', r'^Artículo 1º', [270, 272]),
                        repeal_from('ley-4995-2013', '4401', 'Ley N° 4995/2013', r'^Artículo 97\.',
                                    'los Artículos 149, 231, 237 de la Ley N° 836/80 "CODIGO SANITARIO"',
                                    [149, 231, 237])],
                       skip=tuple(range(123, 131)) + (321,))


# ---------------------------------------------------------------- corpus

def sources() -> list[dict]:
    """The sources in sources.json, with request counts per host from .cache/requests.jsonl."""
    counts: dict[str, int] = {}
    log = HERE / '.cache' / 'requests.jsonl'
    if log.exists():
        for line in log.read_text(encoding='utf-8').splitlines():
            u = json.loads(line)['url']
            host = u.split('/')[2]
            counts[host] = counts.get(host, 0) + 1
    out = []
    for s in SRC['sources']:
        s = dict(s)
        s['requests'] = sum(n for h, n in counts.items() if h in s.get('hosts', []))
        s.pop('hosts', None)
        out.append(s)
    return out


def main():
    acts = [constitution(), civil_code(), penal_code(), codigo_procesal_penal(), codigo_procesal_civil(), codigo_ninez(),
            codigo_aduanero(), ley_comerciante(), codigo_sanitario()]
    corpus = {
        'country': {
            'code': 'PY', 'name': 'Paraguay', 'slug': 'paraguay', 'lang': 'es', 'tz': 'America/Asuncion',
            'future_branch': 'futuro',
            'publisher': {'name': 'Biblioteca y Archivo Central del Congreso Nacional (BACN)',
                          'email': 'bacn@bacn.invalid'},
            'default_in_force_rule': {
                'text': 'Código Civil (Ley 1183/1985), Título preliminar, art. 1: "Las leyes son obligatorias en todo '
                        'el territorio de la República desde el día siguiente al de su publicación, o desde el día que '
                        'ellas determinen." Constitución Nacional art. 213: a law binds only once promulgated and '
                        'published. A law\'s own vigencia clause overrides the default.',
                'source': 'https://www.bacn.gov.py/leyes-paraguayas/5293/ley-n-1183-codigo-civil'},
            'licence_note': 'Legal texts of the Republic of Paraguay as published by the Biblioteca y Archivo Central '
                            'del Congreso Nacional (www.bacn.gov.py). Official legal texts are public; BACN states no '
                            'licence for its pages.',
        },
        'sources': sources(),
        'laws': LAWS,
        'acts': acts,
        'applies': [],
        'decisions': DECISIONS + [
            'Constitution in force from 1992-06-20: its Disposición final y transitoria art. 1 says it "entra en '
            'vigencia desde la fecha" (20 June 1992); the first commit is the Constitution as enacted.',
            'Enmienda Constitucional N° 1 (art. 120, votes of Paraguayans abroad) is dated 2011-10-17, the day the '
            'Tribunal Superior de Justicia Electoral declared it "sancionada y promulgada" and incorporated into the '
            'text (art. 290 CN: an approved amendment is sanctioned and promulgated on an affirmative referendum). '
            'The date is read from the signed original scan on BACN. Kind: referendum.',
            'The 1992 art. 120 wording comes from BACN\'s Constitution page, which still prints it (with a '
            '"Modificado por" note) after the 2011 amendment; the amended wording comes from the Enmienda itself.',
            'Unit headings are BACN\'s article headings verbatim; the "(Modificado por …)" note is removed from the '
            'heading and used only as the credit.',
            'The Partes/Títulos/Capítulos/Secciones headings, which are not articles, are kept verbatim in '
            'constitucion/indice.md together with each article heading, so the structure is not lost.',
            'BACN prints transitional art. 16 twice; the first copy is used and the duplicate is recorded as a '
            'mismatch. BACN also prints "CAPITULO VIII" twice in Part I (the first should read VII); kept verbatim.',
            'SILpy (silpy.congreso.gov.py) is not crawled: its robots.txt disallows every agent except Googlebot.',
        ] + CODE_DECISIONS + [
            'Line joins: BACN sometimes breaks one sentence over two paragraphs; parse.py rejoins a paragraph that '
            'ends without punctuation when the next begins with a lower-case word that is not an enumerator. '
            f'Joins made: {len(JOINS)} ({"; ".join(JOINS)}).',
        ],
        'ai_use': [
            'Claude Opus 5.5 (claude-opus-5-5) in Claude Code wrote fetch.py and parse.py, chose the acts, found the '
            'amending laws through BACN\'s own search and read them to write the replay table in parse.py (which '
            'article each law rewrites or repeals, and when), and read dates from official scans (the Enmienda N° 1 '
            'signature block; the promulgation date "Asunción 4 de Noviembre de 1988" on the last page of the Código '
            'Procesal Civil scan, viewed as an image). No model wrote or changed '
            'legal text: every provision is extracted by code from BACN pages or the text layer of BACN\'s PDF.',
            'No model runs at data-build or git-build time.',
        ],
        'mismatches': MISMATCHES,
    }
    # SCHEMA.md "Large acts": after the first version, store each version's delta (`changes`: unit, or null to
    # remove) instead of every provision again. The builder expands it; the repository comes out identical.
    for a in acts:
        prev = a['versions'][0]['units']
        for v in a['versions'][1:]:
            cur = v.pop('units')
            ch = {k: u for k, u in cur.items() if prev.get(k) != u}
            ch.update({k: None for k in prev if k not in cur})
            v['changes'] = dict(sorted(ch.items()))
            prev = cur
    out = json.dumps(corpus, ensure_ascii=False, indent=1, sort_keys=False) + '\n'
    # --out PATH writes a test corpus elsewhere; the default write is atomic (autopush builds every change).
    dest = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else HERE / 'corpus.json'
    tmp = dest.with_name(dest.name + '.tmp')
    tmp.write_text(out, encoding='utf-8', newline='\n')
    tmp.replace(dest)
    for a in acts:
        print(a['slug'], len(a['versions']), 'versions', len(a['versions'][0]['units']), 'units in the first')
    print(len(LAWS), 'laws;', len(MISMATCHES), 'mismatches recorded')


if __name__ == '__main__':
    main()
