"""Drive the running studio through its real API, end to end.

A developer helper, not a test: it starts the app on a spare port in demo mode
(no credentials, so nothing is sent anywhere), then exercises the same endpoints
the browser uses and prints what came back.

    uv run python scripts/smoke.py            # demo mode, port 7981
    uv run python scripts/smoke.py --port 7999
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gradio_client import Client

from kotori.app import build_demo, launch_options
from kotori.config import Settings


def wait_for(url: str, timeout: float = 90.0) -> None:
    """Block until the server answers, so the client never races the boot."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2).read(1)
            return
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    raise SystemExit(f"{url} never answered")


def pick(outputs, marker: str) -> str:
    """The one output that mentions ``marker`` (streams arrive as a tuple)."""
    for value in outputs:
        text = value if isinstance(value, str) else ""
        if marker in text:
            return text
    return ""


def cards(ledger: str) -> int:
    return ledger.count('class="story-card"')


def first_story_id(data_dir: Path) -> str | None:
    """Read the newest story id straight out of the archive."""
    archive = data_dir / "library.jsonl"
    if not archive.exists():
        return None
    lines = [line for line in archive.read_text(encoding="utf-8").splitlines() if line.strip()]
    return json.loads(lines[-1])["story_id"] if lines else None


def main() -> int:
    parser = argparse.ArgumentParser(description="smoke-test the running studio")
    parser.add_argument("--port", type=int, default=7981)
    args = parser.parse_args()

    data_dir = Path(tempfile.mkdtemp(prefix="kotori-smoke-"))
    settings = Settings(api_key=None, data_dir=data_dir)
    options = launch_options(settings, allowed_paths=[str(data_dir)])
    options.update(server_name="127.0.0.1", server_port=args.port, prevent_thread_lock=True)

    demo = build_demo(settings)
    demo.launch(**options)

    base = f"http://127.0.0.1:{args.port}"
    wait_for(f"{base}/gradio_api/info")
    client = Client(base, verbose=False)
    print(f"serving on {base} · stories kept in {data_dir}")

    try:
        demo_out = client.predict(api_name="/hear_demo")
        stage = pick(demo_out, 'class="sheet-wrap"')
        deck = pick(demo_out, 'class="deck"')
        room = pick(demo_out, "room-signal")
        print(f"hear_demo        outputs={len(demo_out)}")
        print(f"  room signal    {room.strip()}")
        print(f"  play button    {'deck__play' in deck}")
        print(f"  words          {stage.count('tp-word')}")
        print(f"  status         {pick(demo_out, 'ast-status')[:120]}")

        history = client.predict(api_name="/refresh_history")
        print(f"refresh_history  cards={cards(history[2])}")
        print(f"  masthead       {'1 story kept' in history[3]}")
        print(f"  shelf status   {'1 story on the shelf' in history[4]}")

        story_id = first_story_id(data_dir)
        print(f"story id         {story_id}")

        opened = client.predict(story_id, api_name="/open_selected")
        print(f"open_selected    room={'playground' in pick(opened, 'room-signal')}")
        print(f"  from history   {'from the history' in pick(opened, 'sheet-wrap')}")

        spoken = client.predict(story_id, api_name="/record_voice")
        print(f"record_voice     play={'deck__play' in pick(spoken, 'class="deck"')}")

        deleted = client.predict(story_id, api_name="/delete_selected")
        print(f"delete_selected  empty={'nothing here yet' in deleted[2]}")

        print(f"surprise_me      {bool(client.predict(api_name='/surprise_me'))}")
    finally:
        client.close()
        demo.close()

    print("ok")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    raise SystemExit(main())
