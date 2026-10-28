"""BACN page lines for pages whose ordered lists nest (Leyes 6534/2020 and 7593/2025).

../parse.py writes the marker of each <ol> item as the page's CSS shows it, but stops on a nested <ol>. BACN wraps
many incisos of these laws in nested lists whose outer items are styled "list-style-type:none" (no marker); a
browser shows only the innermost list's markers. lines() here numbers the innermost lists first, with the same
marker rules as parse.py (start=, value=, list-style-type), then the lists around them, so every item shows exactly
the marker a browser draws. Pages without nested lists give the same lines as parse.bacn.lines.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import parse  # noqa: E402
from parse import _attr, _list_type, _marker, norm  # noqa: E402

_DONE_LI = '<\x02li>'          # an item already numbered; turned back into <li> once every list is numbered
_INNER_OL = re.compile(r'(?is)<ol\b([^>]*)>((?:(?!<ol\b).)*?)</ol\s*>')


def _number_ol(m: re.Match) -> str:
    k = int(_attr(m.group(1), 'start') or 1) - 1
    ol_type = _list_type(m.group(1)) or 'decimal'

    def item(li):
        nonlocal k
        k = int(_attr(li.group(1), 'value') or k + 1)
        t = _list_type(li.group(1)) or ol_type
        return _DONE_LI if t == 'none' else f'{_DONE_LI}\x01{_marker(k, t)}. '
    return re.sub(r'(?i)<li\b([^>]*)>', item, m.group(2))


def lines(fragment: str) -> list[str]:
    s = re.sub(r'<!--.*?-->', '', fragment, flags=re.S)
    s = re.sub(r'(?is)<(script|style)\b.*?</\1>', '', s)
    s = re.sub(r'(?i)<br\s*/?>', '\n', s)
    while True:
        s2 = _INNER_OL.sub(_number_ol, s)
        if s2 == s:
            break
        s = s2
    assert not re.search(r'(?i)<ol\b', s), 'unbalanced <ol>'
    s = s.replace(_DONE_LI, '<li>')
    s = re.sub(r'(?i)</(p|div|h[1-6]|li|tr|table|blockquote)\s*>', '\n', s)
    s = re.sub(r'(?i)<(p|div|h[1-6]|li|tr|table|blockquote)\b[^>]*>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    out = []
    for ln in s.split('\n'):
        ln = norm(ln)
        if ln and ln not in ('-->',):
            if out and re.fullmatch(r'\d+\.|\x01[^ ]+\.', out[-1]):
                out[-1] = out[-1] + ' ' + ln      # a numbered <li> whose text sits in its own <p>
            else:
                out.append(ln)
    return [ln.replace('\x01', '') for ln in out]


def page_lines(url: str) -> list[str]:
    return lines(parse.bacn.body(parse.bacn.decode(parse.raw(url))))
