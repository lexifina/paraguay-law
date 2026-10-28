# Paraguay: law history

This repository will hold the legislation of Paraguay (PY) as a history: one file per provision and one commit per law taking effect, dated by the day it took force, with the law that made each change as the commit author. It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `py/` in the world tree.

**Status:** no law yet. This first commit records where the law of Paraguay can be read and what a build would need.

**Can it be built?** Only current text or the gazette is online, so a history has to be rebuilt by applying each amending act.

**This commit is a placeholder.** The first real build must replace this history from scratch and force-push. It must never append law commits on top of it: they are dated by when each law took effect, often decades earlier, so dates in `main` would run backwards and break every on-date lookup. Builders should refuse to append when the root commit is this placeholder (its subject ends "sources, before any law").

**Official sources**

- [BACN (Congress library)](https://www.bacn.gov.py): A volunteer git repo holds 6,300+ laws.

**Existing open projects to check first**

- [leyes-paraguayas](https://github.com/ypsoftware/leyes-paraguayas): 6,300+ laws in git.

These are volunteer projects. Reconcile any of them against the official text before relying on it: a transcription is not the law (c3e/grundgesetz, for example, differs from the official gazette in 43 article texts on 20 July 2017).

All sources, with their status, are in [SOURCES.md](SOURCES.md). How these files were made is in [REPRODUCE.md](REPRODUCE.md).

This repository describes sources; it is not legal advice and holds no legal text yet.
