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
    s = re.sub(r'(?i)</(p|div|h[1-6]|li|tr|table|blockquote)\s*>', '\n', s)
    s = re.sub(r'(?i)<(p|div|h[1-6]|li|tr|table|blockquote)\b[^>]*>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    out = []
    for ln in s.split('\n'):
        ln = norm(ln)
        if ln and ln not in ('-->',):
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
        for frm in sorted(self.pending):
            p = self.pending[frm]
            new = dict(cur)
            credits: dict[str, list[str]] = {}
            for kind, key, value, law_key in p['ops']:
                if kind == 'set':
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
                if new.get(k) == cur.get(k):
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
        return out


JOINS: list[str] = []


def join_broken(paras: list[str], where: str) -> list[str]:
    """BACN sometimes breaks a sentence over two paragraphs (a stray <br>). Rejoin when a paragraph ends without
    punctuation and the next starts with a lower-case word that is not an enumerator ("a)", "b)")."""
    out: list[str] = []
    for p in paras:
        if (out and not re.search(r'[.;:,"\')]$', out[-1]) and re.match(r'^[a-zñáéíóú]', p)
                and not re.match(r'^[a-zñ]{1,2}\)', p)):
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
CP_QART = re.compile(r'^"Art[ií]culo\.?\s+(\d+)\s*[°º]?\s*(?:\.-|\.|-)\s*(.*)$')
CP_LABEL = re.compile(r'^(LIBRO|PARTE|TITULO|T[IÍ]TULO|CAPITULO|CAP[IÍ]TULO|SECCION|SECCI[OÓ]N)\b')


def cp_key(n: int, suffix: str = '') -> str:
    return f'art-{n:03d}' + (f'-{suffix}' if suffix else '')


def cp_unit(n: int, title: str, paras: list[str], suffix: str = '') -> dict:
    num = f'{n}' + (f' {suffix}' if suffix else '')
    head = f'Artículo {num}.- {title}'.rstrip() if title else f'Artículo {num}'
    return unit(f'Art. {num}', 'art', head, paras)


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
    acts = [constitution(), civil_code()]
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
        ],
        'ai_use': [
            'Claude Opus 5.5 (claude-opus-5-5) in Claude Code wrote fetch.py, bacn.py and parse.py, chose the acts '
            'and read dates from official scans (the Enmienda N° 1 signature block). No model wrote or changed '
            'legal text: every provision is extracted by code from BACN pages or the text layer of BACN\'s PDF.',
            'No model runs at data-build or git-build time.',
        ],
        'mismatches': MISMATCHES,
    }
    out = json.dumps(corpus, ensure_ascii=False, indent=1, sort_keys=False) + '\n'
    (HERE / 'corpus.json').write_text(out, encoding='utf-8', newline='\n')
    for a in acts:
        print(a['slug'], len(a['versions']), 'versions', len(a['versions'][-1]['units']), 'units')
    print(len(LAWS), 'laws;', len(MISMATCHES), 'mismatches recorded')


if __name__ == '__main__':
    main()
