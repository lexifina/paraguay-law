"""BACN full-text search, cached through ../fetch.py (curl, 1 request/s, logged). Prints the law-page links.

    python -X utf8 electoral/search.py "codigo electoral" > electoral/.tmp/q.txt
"""
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fetch import fetch  # noqa: E402

q = sys.argv[1]
out: dict[str, int] = {}
page = 1
total = 0
while True:
    u = 'https://www.bacn.gov.py/paginacion/buscar.php?s=' + urllib.parse.quote(q) + f'&action=ajax&page={page}'
    p = fetch(u)
    s = p.read_bytes().decode('utf-8', 'replace')
    m = re.search(r'Encontramos:\s*(\d+)', re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)))
    total = int(m.group(1)) if m else 0
    links = re.findall(r'href="(https://www.bacn.gov.py/leyes-paraguayas/[^"]+)"', s)
    new = [x for x in links if x not in out]
    for x in links:
        out[x] = 1
    if not new or len(out) >= total or page > 40:
        break
    page += 1
print(q, 'total', total, 'pages', page, 'links', len(out), file=sys.stderr)
for x in out:
    print(x)
