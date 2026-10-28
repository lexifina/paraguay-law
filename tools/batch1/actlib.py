"""Shared helpers for the batch parts (batch1/, batch2/, batch3/): a law printed article by article on BACN, read as
enacted, then replayed through its amending laws with ../parse.py's Replay engine.

Imported, not run. Reuses ../parse.py (BACN helpers, Replay, enacted_code, law registry) and ../datos/pages.py (the
list reader that numbers nested <ol> innermost-first; same lines as parse.py on pages without nested lists).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'datos'))

import pages  # noqa: E402
import parse  # noqa: E402
from parse import (GEN_ART, LAWS, MISMATCHES, Replay, bacn_law, enacted_code, join_broken, law, page_meta,  # noqa: E402
                   plain_unit, sha)

parse.page_lines = pages.page_lines
make = plain_unit('Artículo')
LABEL = re.compile(r'(?i)^(LIBRO|PARTE|T[IÍ]TULO|CAP[IÍ]TULO|SECCI[OÓ]N|DISPOSICI[OÓ]N(ES)? (FINAL|TRANSITORIA|GENERAL)ES?)\b')
# An article of the amended law inside a quotation: '"Art. 5º.- …', 'Art. 50.- …', '"Artículo 60.- …', '"Art. 1.070. …'
QART = re.compile(r'^"?Art(?:[ií]culo|\.)?\s*(\d{1,2}\.\d{3}|\d+)\s*[°º]?\s*(?:\.-|\.|-)\s*(.*)$')


def register(urls: list[str]):
    parse.AMEND_URLS.extend(u for u in urls if u not in parse.AMEND_URLS)


def url_of(pid: str) -> str:
    return next(u for u in parse.AMEND_URLS if f'/leyes-paraguayas/{pid}/' in u)


def lines(pid: str) -> list[str]:
    return parse.page_lines(url_of(pid))


def closing_index(L: list[str]) -> int:
    """The closing formula: the first "Aprobado…"/"DADA…" line after the last "Comuníquese" article (an article's
    own text may begin "Aprobada …")."""
    com = max(i for i, ln in enumerate(L) if GEN_ART.match(ln) and re.search(r'(?i)comun[ií]quese', ln))
    return next(i for i, ln in enumerate(L) if i > com and re.match(r'^(Aprobad[oa]|DADA|Dada) ', ln))


def heading_indices(L: list[str], head_n: int, end: int) -> set[int]:
    """Headings: a run of lines just before an article that opens with a label ("CAPÍTULO I", "Sección II") or an
    all-capitals line and goes on with all-capitals lines or short unpunctuated titles ("Del Municipio",
    "Disposiciones generales"; a title right after a label may end with a period). All-capitals lines inside an
    article (a list of repealed laws, say) are not followed by an article and stay text."""
    def starts(ln):
        return bool(LABEL.match(ln)) or not parse.LOWER.search(ln)

    def cont(k):
        ln = L[k]
        return (starts(ln) or (len(ln) < 150 and not ln.endswith(('.', ':', ';')))
                or (k > head_n and LABEL.match(L[k - 1]) and len(ln) < 150))
    heads: set[int] = set()
    i = head_n
    while i < end:
        if GEN_ART.match(L[i]) or not starts(L[i]):
            i += 1
            continue
        j = i
        while j < end and not GEN_ART.match(L[j]) and (j == i or cont(j)):
            j += 1
        if j < end and GEN_ART.match(L[j]):
            heads.update(range(i, j))
            i = j
        else:
            i += 1
    return heads


def enacted(pid: str, slug: str, head_n: int) -> dict:
    """Articles 1..n in order, headings to indice.md, the closing formula to sancion.md (as parse.enacted_code)."""
    L = lines(pid)
    end = closing_index(L)
    nums = [int(GEN_ART.match(ln).group(1)) for ln in L[head_n:end] if GEN_ART.match(ln)]
    assert nums == list(range(1, len(nums) + 1)), (slug, nums)
    heads = heading_indices(L, head_n, end)
    raw: dict[int, list[str]] = {}
    index: list[list] = []
    cur = None
    prev_heading = False
    for i in range(head_n, end):
        ln = L[i]
        m = GEN_ART.match(ln)
        if m:
            n = int(m.group(1))
            cur = raw[n] = [m.group(2)]
            for e in index:
                if e[0] is None:
                    e[0] = f'art-{n:03d}'
            prev_heading = False
        elif i in heads:
            if parse.CP_LABEL.match(ln) or not prev_heading:
                index.append([None, ln])
            else:
                index[-1][1] += (' - ' if parse.CP_LABEL.match(index[-1][1]) and ' - ' not in index[-1][1]
                                 else ' / ') + ln
            prev_heading = True
            cur = None
        else:
            assert cur is not None, (slug, ln)
            cur.append(ln)
            prev_heading = False
    units = {f'art-{n:03d}': make(n, v[0], join_broken(v[1:], f'{slug} art. {n}')) for n, v in raw.items()}
    units['indice'] = parse.unit('Índice de libros, títulos y capítulos', 'index', 'LIBROS, TITULOS Y CAPITULOS',
                                 [f'{k}: {t}' for k, t in index])
    units['sancion'] = parse.unit('Sanción', 'closing', 'SANCION', [L[end]])
    check_lines(slug, L[head_n:end + 1], units)
    return units


def check_lines(slug: str, page_lines: list[str], units: dict):
    """The verification of every first version: each line of the law's BACN text is in it (articles, headings in
    indice.md, the closing formula in sancion.md)."""
    text = '\n'.join(u['text'] for u in units.values())
    missing = []
    for ln in page_lines:
        m = GEN_ART.match(ln)
        if m:       # "Artículo 5°.- Rest" is stored as "# Artículo 5" + "Rest"
            n = int(m.group(1))
            u = units.get(f'art-{n:03d}')
            ok = u is not None and u['text'].startswith(f'# Artículo {n}\n' + m.group(2).strip())
        else:
            ok = ln in text
        if not ok:
            missing.append(ln)
    assert not missing, (slug, missing[:3])
    CHECKED.append(f'{slug}: {len(page_lines)} lines')


CHECKED: list[str] = []


def plus(day: str, *, days: int = 0, months: int = 0, years: int = 0) -> str:
    d = dt.date.fromisoformat(day)
    if months or years:
        m = d.month - 1 + months
        y = d.year + years + m // 12
        d = d.replace(year=y, month=m % 12 + 1)
    return (d + dt.timedelta(days=days)).isoformat()


def segment(L: list[str], intro: str) -> list[str]:
    """The lines after the amending law's article whose first line matches `intro`, up to its next own article."""
    i = next(k for k, ln in enumerate(L) if re.search(intro, ln))
    out = []
    for ln in L[i + 1:]:
        if re.match(r'^Art[ií]culo\s*\d+\s*[°º.o]*\s*[.-]', ln) or re.match(r'^(Aprobad|DADA|Dada)', ln):
            break
        out.append(ln)
    return out


def qblocks(L: list[str], intro: str) -> list[tuple[int, list[str]]]:
    """Quoted articles inside one article of an amending law: [(number, paragraphs without the quotation marks)]."""
    out: list[tuple[int, list[str]]] = []
    for ln in segment(L, intro):
        m = QART.match(ln)
        if m:
            out.append((int(m.group(1).replace('.', '')), [m.group(2)]))
        else:
            assert out, (intro, ln)
            out[-1][1].append(ln)
    return [(n, parse.strip_quote(['"' + p[0]] + p[1:])) for n, p in out]


def unit_of(n: int, paras: list[str], where: str) -> dict:
    return make(n, paras[0], join_broken(paras[1:], f'{where} art. {n}'))


def set_arts(rp: Replay, frm: str, key: str, url: str, L: list[str], intro: str, expect: list[int], *,
             where: str = ''):
    b = qblocks(L, intro)
    assert [n for n, _ in b] == expect, (key, [n for n, _ in b])
    for n, paras in b:
        rp.op(frm, key, url, 'set', f'art-{n:03d}', unit_of(n, paras, where or key))


def replace_line(prefix: str, new: str, *, must_start: str | None = None):
    """fn op: the one line of an article that starts with `prefix` (an inciso such as "m)") becomes `new`."""
    def f(u):
        ls = u['text'].split('\n')
        hits = [i for i, x in enumerate(ls) if x.startswith(prefix)]
        assert len(hits) == 1, (prefix, hits, u['text'][:200])
        ls[hits[0]] = new
        return dict(u, text='\n'.join(ls))
    return f


def drop_line(prefix: str):
    def f(u):
        ls = u['text'].split('\n')
        hits = [i for i, x in enumerate(ls) if x.startswith(prefix)]
        assert len(hits) == 1, (prefix, hits, u['text'][:200])
        del ls[hits[0]]
        return dict(u, text='\n'.join(ls))
    return f


def first_version(key: str, pid: str, label: str, title: str, frm: str, units: dict, note: str) -> dict:
    url = url_of(pid)
    m = page_meta(url)
    if key not in LAWS:
        law(key, label=label, title=title, kind='law', enacted=m['promulgated'], published=m['published'], url=url)
    return {'from': frm, 'source_url': url, 'sha256': sha(url), 'units': units, 'credits': {}, 'note': note}


def to_changes(act: dict) -> dict:
    """Every version after the first as a delta (SCHEMA 'changes'), as in the other parts."""
    prev = act['versions'][0]['units']
    for v in act['versions'][1:]:
        cur = v.pop('units')
        ch = {k: u for k, u in cur.items() if prev.get(k) != u}
        ch.update({k: None for k in prev if k not in cur})
        v['changes'] = dict(sorted(ch.items()))
        prev = cur
    return act


def write_part(dest: Path, acts: list[dict], decisions: list[str], ai_use: list[str], slugs: set[str]):
    mism = [m for m in MISMATCHES if m.split('/')[0] in slugs]
    joins = list(parse.JOINS)
    part = {
        'laws': dict(sorted(LAWS.items())),
        'acts': [to_changes(a) for a in acts],
        'decisions': decisions + parse.DECISIONS + [
            (f'{len(joins)} line joins (a paragraph broken by a stray <br>): ' + '; '.join(joins) + '.')
            if joins else 'No line joins were needed.'] + ['Restated text: ' + m for m in mism],
        'ai_use': ai_use,
    }
    out = json.dumps(part, ensure_ascii=False, indent=1) + '\n'
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_name(dest.name + '.tmp')
    tmp.write_text(out, encoding='utf-8', newline='\n')
    tmp.replace(dest)
    print(len(acts), 'acts,', sum(len(a['versions']) for a in acts), 'versions,', len(LAWS), 'laws,', len(mism),
          'restated,', len(joins), 'joins ->', dest)
