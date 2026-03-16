#!/usr/bin/env python3
"""ARC-AGI-3 API client and exploration library. Zero external dependencies.

CLI: play.py games | scorecard-open | scorecard-close <id> | scorecard-get <id>
API: start(game_id) → (card_id, obs) opens fresh scorecard + new game at level 1
     reset(game_id, card_id, guid) → retries current level (double-reset for full restart)
"""

import os, sys, json, time, getpass
from pathlib import Path
from urllib.request import Request, urlopen, HTTPCookieProcessor, build_opener
from urllib.error import HTTPError
from http.cookiejar import Cookie, CookieJar

BASE = "https://three.arcprize.org"
KEY = os.environ.get("ARC_API_KEY", "")
REPORT_URL = os.environ.get("REPORT_URL")
PLAYER_KEY = os.environ.get("PLAYER_KEY", getpass.getuser())
COOKIE_FILE = Path(__file__).parent / ".arc_session.json"
ACTION_MAP = {"U": "ACTION1", "D": "ACTION2", "L": "ACTION3", "R": "ACTION4",
              "S": "ACTION5", "X": "ACTION6"}

# Session with cookie persistence
_cookie_jar = CookieJar()
_opener = build_opener(HTTPCookieProcessor(_cookie_jar))

# Restore cookies from previous invocations
if COOKIE_FILE.exists():
    try:
        for c in json.loads(COOKIE_FILE.read_text()):
            cookie = Cookie(
                version=0, name=c["name"], value=c["value"],
                port=None, port_specified=False,
                domain=c.get("domain", ""), domain_specified=bool(c.get("domain")),
                domain_initial_dot=c.get("domain", "").startswith("."),
                path=c.get("path", "/"), path_specified=True,
                secure=c.get("secure", False), expires=None,
                discard=True, comment=None, comment_url=None,
                rest={}, rfc2109=False,
            )
            _cookie_jar.set_cookie(cookie)
    except Exception:
        pass


def _save_cookies():
    try:
        cookie_list = [{"name": c.name, "value": c.value,
                        "domain": c.domain, "path": c.path,
                        "secure": c.secure}
                       for c in _cookie_jar]
        tmp = COOKIE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(cookie_list))
        tmp.rename(COOKIE_FILE)
    except Exception:
        pass


def _http(method, url, body=None, headers=None, timeout=60):
    """Make an HTTP request using stdlib. Returns (status, data_dict)."""
    headers = headers or {}
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, headers=headers, method=method)
    try:
        resp = _opener.open(req, timeout=timeout)
        return resp.status, json.loads(resp.read().decode())
    except HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode()) if e.fp else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return e.code, {}


# ── Reflection enforcement ────────────────────────────────────────────

REFLECT_EVERY = 10  # game actions between mandatory reflections
RETHINK_EVERY = 50  # game actions between full approach review
_REFLECT_LOG = Path(__file__).parent / ".reflect_count"
_RETHINK_LOG = Path(__file__).parent / ".rethink_count"


def _read_counter(path):
    try:
        return int(path.read_text().strip()) if path.exists() else 0
    except Exception:
        return 0


def _should_reflect():
    """Check if rethink or reflect is due. Returns 'rethink', 'reflect', or False."""
    if _read_counter(_RETHINK_LOG) >= RETHINK_EVERY:
        return "rethink"
    if _read_counter(_REFLECT_LOG) >= REFLECT_EVERY:
        return "reflect"
    return False


# ── Core API ─────────────────────────────────────────────────────────


def api(method, path, body=None):
    """Call ARC API with retry on rate limit."""
    # Enforce reflection before game commands
    signal = _should_reflect() if "/cmd/" in path else False
    if signal:
        if signal == "rethink":
            _RETHINK_LOG.write_text("0")
            raise Exception("RETHINK: Write to memory/, then re-read program.md and edit if your workflow has improved. See program.md.")
        _REFLECT_LOG.write_text("0")
        raise Exception("REFLECT: Write to memory/ before continuing. See program.md.")
    if "/cmd/" in path:
        time.sleep(0.1)
    headers = {"X-API-Key": KEY, "Content-Type": "application/json"}
    for attempt in range(3):
        status, data = _http(method, f"{BASE}{path}", body=body if method != "GET" else None, headers=headers)
        if status == 429:
            time.sleep(0.1 * (attempt + 1))
            continue
        if status >= 400:
            raise Exception(f"HTTP {status}: {data}")
        _save_cookies()
        # Increment action counters after successful game command
        if "/cmd/" in path:
            try:
                _REFLECT_LOG.write_text(str(_read_counter(_REFLECT_LOG) + 1))
                _RETHINK_LOG.write_text(str(_read_counter(_RETHINK_LOG) + 1))
            except Exception:
                pass
        # Warn on guid mismatch (stale session routing to wrong game)
        if "/cmd/" in path and body and "guid" in body:
            resp_guid = data.get("guid")
            if resp_guid and resp_guid != body.get("guid"):
                print(f"WARNING: guid mismatch! sent={body['guid'][:8]}… got={resp_guid[:8]}…",
                      file=sys.stderr)
        _status.update(body, data)
        return data
    raise Exception(f"HTTP {status}: {data}")


# ── Game helpers ─────────────────────────────────────────────────────

def start(game_id):
    """Open a fresh scorecard and start a new game instance at level 1.
    Returns (card_id, obs). The obs contains the guid for subsequent calls."""
    card = api("POST", "/api/scorecard/open", {})
    card_id = card.get("card_id") or card.get("id")
    obs = api("POST", "/api/cmd/RESET", {"game_id": game_id, "card_id": card_id})
    time.sleep(2)
    return card_id, obs


def reset(game_id, card_id, guid):
    """Retry current level (smart reset with guid).
    With actions since last level transition → resets current level only.
    Without actions → full game reset. Two consecutive resets guarantee full reset."""
    return api("POST", "/api/cmd/RESET", {"game_id": game_id, "card_id": card_id, "guid": guid})


def act(action_cmd, game_id, guid, card_id=None, x=None, y=None):
    """Single action (U/D/L/R/S/X or ACTION1-6). Returns obs dict."""
    if action_cmd in ACTION_MAP:
        action_cmd = ACTION_MAP[action_cmd]
    body = {"game_id": game_id, "guid": guid}
    if card_id:
        body["card_id"] = card_id
    if x is not None and y is not None:
        body["x"], body["y"] = int(x), int(y)
    return api("POST", f"/api/cmd/{action_cmd}", body)


def seq(game_id, guid, moves, card_id=None):
    """Execute a move string (e.g. 'UUULLDR'). Returns final obs only."""
    obs = None
    for m in moves.upper():
        cmd = ACTION_MAP.get(m)
        if not cmd:
            continue
        body = {"game_id": game_id, "guid": guid}
        if card_id:
            body["card_id"] = card_id
        obs = api("POST", f"/api/cmd/{cmd}", body)
        if obs.get("guid"):
            guid = obs["guid"]
        if obs.get("state") in ("WIN", "GAME_OVER"):
            break
    if obs:
        save_grid(obs)
    return obs


def frame_to_grid(obs):
    """Extract the last frame from obs as a 2D list."""
    frames = obs.get("frame", [[]])
    return frames[-1] if frames else []


def find_objects(grid, val):
    """Find all (row, col) with given value."""
    return [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v == val]


def find_blob(grid, val, min_size=3):
    """Bounding box of largest region of val. Returns (r0, c0, r1, c1) or None."""
    pts = find_objects(grid, val)
    if len(pts) < min_size:
        return None
    return (min(r for r, c in pts), min(c for r, c in pts),
            max(r for r, c in pts), max(c for r, c in pts))


def diff_frames(grid_a, grid_b):
    """Dict of {(row, col): (old, new)} for changed cells."""
    return {(r, c): (grid_a[r][c], grid_b[r][c])
            for r in range(min(len(grid_a), len(grid_b)))
            for c in range(min(len(grid_a[r]), len(grid_b[r])))
            if grid_a[r][c] != grid_b[r][c]}


def grid_summary(grid):
    """Value counts as sorted dict."""
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return dict(sorted(counts.items()))


def render(frame_data):
    """Compact text render of frame. Skips empty rows."""
    lines = []
    for fi, frame in enumerate(frame_data):
        if len(frame_data) > 1:
            lines.append(f"--- Frame {fi} ---")
        for y, row in enumerate(frame):
            if any(v != 0 for v in row):
                lines.append(f"{y:02d}|{''.join('.' if v == 0 else hex(v)[2:] for v in row)}")
    return "\n".join(lines) or "(empty)"


# ── Observe/diff workflow ────────────────────────────────────────────

_GRID_FILE = Path(__file__).parent / ".prev_grid.json"


def observe(action_cmd, game_id, guid, card_id=None, x=None, y=None):
    """Take one action, diff before/after, print all changes.
    Always use this instead of raw act() during exploration."""
    try:
        prev = json.loads(_GRID_FILE.read_text()) if _GRID_FILE.exists() else None
    except Exception:
        prev = None
    obs = act(action_cmd, game_id, guid, card_id=card_id, x=x, y=y)
    new_guid = obs.get("guid") or guid
    grid = frame_to_grid(obs)
    if prev is not None:
        changes = diff_frames(prev, grid)
        print(f"Action: {action_cmd} | State: {obs.get('state')} | Levels: {obs.get('levels_completed')} | Changes: {len(changes)}")
        for (r, c), (old, new) in sorted(changes.items()):
            print(f"  ({r},{c}): {old} -> {new}")
    else:
        print(f"Action: {action_cmd} | State: {obs.get('state')} | Levels: {obs.get('levels_completed')}")
    print(f"  guid: {new_guid[:12]}...")
    print(f"  grid_summary: {grid_summary(grid)}")
    try:
        _GRID_FILE.write_text(json.dumps(grid))
    except Exception:
        pass
    return obs, new_guid


def save_grid(obs):
    """Save current grid as the diff baseline for observe(). Persists to disk.
    Call after reset()/start()."""
    grid = frame_to_grid(obs)
    try:
        _GRID_FILE.write_text(json.dumps(grid))
    except Exception:
        pass
    return grid


# ── Shape helpers ────────────────────────────────────────────────────

def extract_pattern(grid, r0, c0, r1, c1, bg=None):
    """Extract a sub-grid as a list of lists. bg replaces background values for clarity."""
    return [[bg if bg is not None and grid[r][c] == bg else grid[r][c]
             for c in range(c0, c1 + 1)]
            for r in range(r0, r1 + 1)]


def render_pattern(pattern, label=None):
    """Render a small pattern to text. Uses . for 0/None, hex for others."""
    lines = []
    if label:
        lines.append(label)
    for row in pattern:
        lines.append("".join("." if v in (0, None) else hex(v)[2:] for v in row))
    return "\n".join(lines)


def patterns_match(a, b):
    """True if two patterns have identical non-background shapes.
    Compares only non-zero cells; ignores size differences by aligning top-left."""
    def normalize(p):
        cells = set()
        for r, row in enumerate(p):
            for c, v in enumerate(row):
                if v and v not in (0, None):
                    cells.add((r, c, v))
        if not cells:
            return set()
        min_r = min(r for r, c, v in cells)
        min_c = min(c for r, c, v in cells)
        return {(r - min_r, c - min_c, v) for r, c, v in cells}
    return normalize(a) == normalize(b)


# ── Game-specific helpers (add per-game helpers below) ─────────────────


# ── Status reporting ──────────────────────────────────────────────────

class _Status:
    """Reports experiment state to the central server."""

    def __init__(self):
        self.guid = self.game_id = self.state = None
        self.levels = 0
        self._title = None
        raw = sys.argv[0] if sys.argv[0] else ""
        self.experiment = Path(raw).name if raw and not raw.startswith("-") else "interactive"

    @property
    def title(self):
        if self._title is None:
            try:
                line = Path(sys.argv[0]).resolve().read_text().split("\n", 1)[0]
                self._title = line.lstrip("# ").strip() if line.startswith("#") and not line.startswith("#!") else ""
            except Exception:
                self._title = ""
        return self._title or self.experiment

    def update(self, body, data):
        try:
            guid = data.get("guid")
            if not guid or "frame" not in data:
                return
            self.guid, self.game_id = guid, (body or {}).get("game_id")
            self.state = data.get("state")
            self.levels = data.get("levels_completed", 0)
            frames = data.get("frame", [[]])
            frame = frames[-1] if frames else []
            self._report_remote(frame)
        except Exception:
            pass

    def _report_remote(self, frame):
        if not REPORT_URL or not PLAYER_KEY:
            return
        payload = {
            "api_key": PLAYER_KEY, "game_id": self.game_id,
            "guid": self.guid, "state": self.state,
            "levels_completed": self.levels, "frame": frame,
            "experiment": self.experiment, "title": self.title,
        }
        try:
            data = json.dumps(payload).encode()
            req = Request(f"{REPORT_URL}/api/report", data=data,
                          headers={"Content-Type": "application/json"}, method="POST")
            urlopen(req, timeout=5)
        except Exception:
            pass


_status = _Status()


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "games":
        for g in api("GET", "/api/games"):
            gid = g["game_id"] if isinstance(g, dict) else g
            print(f"{gid}  {g.get('title', '') if isinstance(g, dict) else ''}")
    elif cmd == "scorecard-open":
        print(json.dumps(api("POST", "/api/scorecard/open", {})))
    elif cmd == "scorecard-close":
        print(json.dumps(api("POST", "/api/scorecard/close", {"card_id": sys.argv[2]}), indent=2))
    elif cmd == "scorecard-get":
        print(json.dumps(api("GET", f"/api/scorecard/{sys.argv[2]}"), indent=2))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
