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


# ── Core API ─────────────────────────────────────────────────────────

COUNTER_FILE = Path(__file__).parent / ".claude" / "arc_action_count"
STRATEGIC_COUNTER_FILE = Path(__file__).parent / ".claude" / "arc_strategic_count"


def api(method, path, body=None):
    """Call ARC API with retry on rate limit."""
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
        # Increment both action counters after successful game command
        if "/cmd/" in path:
            for cf in (COUNTER_FILE, STRATEGIC_COUNTER_FILE):
                try:
                    count = int(cf.read_text().strip()) if cf.exists() else 0
                    tmp = cf.with_suffix(".tmp")
                    tmp.write_text(str(count + 1))
                    tmp.rename(cf)
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



# ── Game-specific helpers (add per-game helpers below) ─────────────────


def speedrun_ls20(game_id, through_level=4):
    """Speed-run ls20 levels 1-4 using proven paths. Returns (card_id, guid, obs) at the target level."""
    card_id, obs = start(game_id)
    guid = obs["guid"]
    # L1 (14 moves)
    obs = seq(game_id, guid, "LLLLUUUURRRUUU", card_id)
    if through_level <= 1:
        return card_id, guid, obs
    # L2 (~41 moves)
    g = frame_to_grid(obs); pos = find_objects(g, 12)[0]
    m2 = {(46,51),(47,50),(47,51),(47,52),(48,51)}
    p1, pos1 = bfs_path(g, pos, lambda r,c: all(r<=mr<r+5 and c<=mc<c+5 for mr,mc in m2))
    for dr, dc, m in [(-5,0,"U"),(0,-5,"L"),(0,5,"R"),(5,0,"D")]:
        esc = (pos1[0]+dr, pos1[1]+dc)
        if not any(esc[0]<=mr<esc[0]+5 and esc[1]<=mc<esc[1]+5 for mr,mc in m2):
            p2, _ = bfs_path(g, esc, lambda r,c: 39<=r<=44 and 13<=c<=19, avoid=m2)
            if p2:
                obs = seq(game_id, guid, p1 + "UDUD" + m + p2, card_id)
                break
    if through_level <= 2:
        return card_id, guid, obs
    # L3 (60 moves)
    obs = act("D", game_id, guid, card_id)
    obs = seq(game_id, guid, "UUUUUUUURRRRDDDDDDDD" + "UUUUUUUUR" + "LDDDDRRRRRUUUL" + "UDUD" + "U" + "RDDDDDDL" + "RDDD", card_id)
    if through_level <= 3:
        return card_id, guid, obs
    # L4 (~46 moves)
    obs = act("U", game_id, guid, card_id)
    g = frame_to_grid(obs); pos = find_objects(g, 12)[0]
    mk4 = {(31,25),(32,26),(32,27),(33,26)}
    cl4 = {(31,35),(31,36),(31,37),(32,35),(32,36),(32,37),(33,35),(33,36),(33,37)}
    pm, dm = bfs_path(g, pos, lambda r,c: all(r<=mr<r+5 and c<=mc<c+5 for mr,mc in mk4))
    pc, dc = bfs_path(g, dm, lambda r,c: any(r<=sr<r+5 and c<=sc<c+5 for sr,sc in cl4))
    pb, _ = bfs_path(g, dc, lambda r,c: 3<=r<=9 and 7<=c<=14, avoid=cl4)
    obs = seq(game_id, guid, pm + pc + "UDUD" + pb + "L", card_id)
    return card_id, guid, obs


def get_movable(g):
    """Find movable block position (excludes fixed block at cluster and BL box)."""
    c12 = [(r,c) for r,c in find_objects(g, 12)
           if not (55<=r<=60 and 3<=c<=8) and not (27<=r<=33 and 29<=c<=35)]
    return c12[0] if c12 else None


def bfs_path(grid, start, goal_fn, avoid=None):
    """BFS pathfinder for 5x5 block on live grid.
    start: (row, col) top-left of block.
    goal_fn: callable(row, col) -> bool for target positions.
    avoid: set of (row, col) cells the block must not cover.
    Returns (move_string, final_pos) or (None, None)."""
    from collections import deque
    rows, cols = len(grid), len(grid[0])
    avoid = avoid or set()
    WALL = 4

    def can_place(r, c):
        for dr in range(5):
            for dc in range(5):
                rr, cc = r + dr, c + dc
                if rr < 0 or rr >= rows or cc < 0 or cc >= cols:
                    return False
                if grid[rr][cc] == WALL:
                    return False
        if avoid:
            for dr in range(5):
                for dc in range(5):
                    if (r + dr, c + dc) in avoid:
                        return False
        return True

    q = deque([(start, "")])
    visited = {start}
    while q:
        (r, c), path = q.popleft()
        if goal_fn(r, c):
            return path, (r, c)
        for dr, dc, m in [(-5, 0, "U"), (5, 0, "D"), (0, -5, "L"), (0, 5, "R")]:
            nr, nc = r + dr, c + dc
            if (nr, nc) not in visited and can_place(nr, nc):
                visited.add((nr, nc))
                q.append(((nr, nc), path + m))
    return None, None


def box_pattern(g, box="bl"):
    """Extract pattern from a box as compact string. non-5→'X', 5→'.'
    box='bl' for bottom-left (rows 55-60, cols 3-8), 'top' for top (rows 10-14, cols 34-38)."""
    if box == "bl":
        return ["".join("X" if g[y][c] != 5 else "." for c in range(3, 9)) for y in range(55, 61)]
    elif box == "top":
        return ["".join("X" if g[y][c] != 5 else "." for c in range(34, 39)) for y in range(10, 15)]


def box3x3(g, box="bl"):
    """BL 6x6 pattern as 3x3 (2x2 blocks). Returns list of 3 strings.
    Treats any non-5 value as filled (handles both 9 and 12/c patterns)."""
    rows = [g[y][3:9] for y in range(55, 61)]
    result = []
    for br in range(3):
        row = []
        for bc in range(3):
            row.append("X" if rows[br * 2][bc * 2] != 5 else ".")
        result.append("".join(row))
    return result


def snap(obs, label=""):
    """Quick snapshot: block pos, BL 3x3, state, b-count."""
    g = frame_to_grid(obs)
    c12 = find_objects(g, 12)
    pos = c12[0] if c12 else None
    bl = box3x3(g)
    b = sum(1 for r in g for v in r if v == 11)
    markers = find_objects(g, 1)
    state = obs.get("state", "?")
    lvl = obs.get("levels_completed", 0)
    print(f"{label} pos={pos} bl={'|'.join(bl)} b={b} st={state} lv={lvl} m={markers}")
    return g


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


def submit_strategy(game_id, content):
    """Submit learnings to central server."""
    if not REPORT_URL or not PLAYER_KEY:
        print("Set REPORT_URL and PLAYER_KEY to submit strategies")
        return
    try:
        payload = json.dumps({"api_key": PLAYER_KEY, "game_id": game_id, "content": content}).encode()
        req = Request(f"{REPORT_URL}/api/strategies", data=payload,
                      headers={"Content-Type": "application/json"}, method="POST")
        resp = urlopen(req, timeout=10)
        if resp.status < 400:
            print("Strategy submitted!")
        else:
            print(f"Failed to submit strategy: HTTP {resp.status}")
    except Exception as e:
        print(f"Failed to submit strategy: {e}")


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
