# Prompt for Codex

Set up this local Reddita Browser Guarded project in a NEW project-local .venv, not
in the earlier browser-free fork's environment. Read README.md, AGENTS.md and
SECURITY-REVIEW.md. Check Python is 3.12+ and the OS is macOS/Linux. On Windows,
use WSL2 Ubuntu and a Linux home directory; if unavailable, stop and explain.

Run with the virtual environment's Python:

python -m pip install --require-hashes --only-binary=:all: -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .

Then run the venv's patchright install chromium, followed by:

python -m unittest discover -s tests -v

Report actual test outcomes. This intentionally keeps Chromium, JavaScript, native
browser networking, original reddita commands, persistent unauthenticated profile
and six-hour cache. Do not convert it to browser-free fetching. Use .venv/bin/reddita.

No Reddit account, passwords, API keys or personal browser profiles are required.
Do not use sudo/admin, import credentials or relax the request guard/hash checks.
If browser system dependencies are missing, explain the exact requirement before
changing anything outside the project. Ask before a live query: queries/IP go to Reddit.
If Reddit returns 403 or login walls, report it. Do not bypass blocking.
