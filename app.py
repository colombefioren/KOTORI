"""Root entrypoint for hosts that expect ``app.py`` (Hugging Face Spaces, Docker).

Run it directly with ``python app.py``; the package does the rest.
"""

from __future__ import annotations

from ai_storyteller.app import main

if __name__ == "__main__":
    main()
