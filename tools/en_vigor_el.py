"""Prints the law of Paraguay as it stood on a given day, read from this repository's history.

    python tools/en_vigor_el.py 2011-10-16 constitucion art-120   # art. 120 the day before Enmienda N° 1
    python tools/en_vigor_el.py 2011-10-17 constitucion 120       # the same article, by number, as amended
    python tools/en_vigor_el.py 2000-01-01 constitucion           # the whole Constitution on 1 January 2000
    python tools/en_vigor_el.py --law 2020-01-01 constitucion 120 # also name the law behind that wording

A thin wrapper around tools/on.py: the version is chosen by each commit's `In-force:` trailer, never by its commit
date, and branches named wip* are ignored. Standard library only.
"""
import runpy
import sys
from pathlib import Path

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.argv[0] = str(Path(__file__).with_name('on.py'))
    runpy.run_path(sys.argv[0], run_name='__main__')
