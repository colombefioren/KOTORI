"""Root entrypoint for hosts that expect ``app.py`` (Hugging Face Spaces, Docker).

Run it directly with ``python app.py``; the package launches the Gradio server.

Vercel's Python runtime imports the module and requires a top-level
``app``/``application``/``handler`` (a WSGI or ASGI callable), so the Gradio
app is also exposed here as ``app``. See:
https://vercel.com/docs/functions/runtimes/python#python-entrypoints
"""

from __future__ import annotations

from kotori.app import build_demo, main

app = build_demo().app

if __name__ == "__main__":
    main()
