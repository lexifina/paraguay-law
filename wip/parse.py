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
    acts = [constitution()]
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
