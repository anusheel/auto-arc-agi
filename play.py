#!/usr/bin/env python3
"""ARC-AGI-3 API client and exploration library.

CLI: play.py games | scorecard-open | scorecard-close <id> | scorecard-get <id>
API: start(game_id) → (card_id, obs) opens fresh scorecard + new game at level 1
     reset(game_id, card_id, guid) → retries current level (double-reset for full restart)
"""

import os, sys, json, time
from pathlib import Path
import httpx

BASE = "https://three.arcprize.org"
KEY = os.environ["ARC_API_KEY"]
COOKIE_FILE = Path(__file__).parent / ".arc_session.json"
SESSION = httpx.Client(timeout=60)
ACTION_MAP = {"U": "ACTION1", "D": "ACTION2", "L": "ACTION3", "R": "ACTION4",
              "S": "ACTION5", "X": "ACTION6"}

# Restore cookies from previous invocations
if COOKIE_FILE.exists():
    try:
        for name, value in json.loads(COOKIE_FILE.read_text()).items():
            if value and value != "_remove_":
                SESSION.cookies.set(name, value)
    except Exception:
        pass


# ── Core API ─────────────────────────────────────────────────────────

def api(method, path, body=None):
    """Call ARC API with retry on rate limit."""
    if "/cmd/" in path:
        time.sleep(0.1)
    headers = {"X-API-Key": KEY, "Content-Type": "application/json"}
    for attempt in range(3):
        r = (SESSION.get if method == "GET" else SESSION.post)(
            f"{BASE}{path}", headers=headers, **({"json": body or {}} if method != "GET" else {}))
        if r.status_code == 429:
            time.sleep(0.1 * (attempt + 1))
            continue
        r.raise_for_status()
        data = r.json()
        # Persist cookies for cross-invocation state
        try:
            COOKIE_FILE.write_text(json.dumps({n: v for n, v in SESSION.cookies.items()}))
        except Exception:
            pass
        _status.update(body, data)
        return data
    r.raise_for_status()


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


def result(msg):
    """Set final learning for this experiment. Shows on dashboard."""
    print(msg)
    _status.result_msg = msg


# ── Custom helpers (add your own below) ───────────────────────────────


def can_place(grid, r, c, w=5, h=5):
    """Check if a 5x5 unit can occupy rows r..r+h-1, cols c..c+w-1 (all cells are 0, 1, or 3)."""
    for dr in range(h):
        for dc in range(w):
            rr, cc = r + dr, c + dc
            if rr >= len(grid) or cc >= len(grid[0]):
                return False
            v = grid[rr][cc]
            if v not in (0, 1, 3):  # corridor, 0-marker, or 1-marker
                return False
    return True


def find_path(grid, start_r, start_c, target_r, target_c, step=5, avoid=None):
    """BFS to find shortest path (sequence of UDLR) from start to target on 5-cell grid.
    The unit is 5 wide × 5 tall (block 2 + nines 3). Start/target are top-left of block.
    avoid: set of (r,c) positions to skip (e.g. marker position to prevent premature trigger)."""
    from collections import deque
    avoid = avoid or set()
    dirs = {'U': (-step, 0), 'D': (step, 0), 'L': (0, -step), 'R': (0, step)}
    q = deque([(start_r, start_c, '')])
    visited = {(start_r, start_c)}
    while q:
        r, c, path = q.popleft()
        if r == target_r and c == target_c:
            return path
        for name, (dr, dc) in dirs.items():
            nr, nc = r + dr, c + dc
            if (nr, nc) not in visited and (nr, nc) not in avoid and can_place(grid, nr, nc):
                visited.add((nr, nc))
                q.append((nr, nc, path + name))
    return None  # no path found


def reachable(grid, start_r, start_c, step=5):
    """Find all positions reachable from start on the 5-cell grid."""
    from collections import deque
    dirs = [(-step, 0), (step, 0), (0, -step), (0, step)]
    q = deque([(start_r, start_c)])
    visited = {(start_r, start_c)}
    while q:
        r, c = q.popleft()
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if (nr, nc) not in visited and can_place(grid, nr, nc):
                visited.add((nr, nc))
                q.append((nr, nc))
    return sorted(visited)


def block_pos(obs):
    """Get block (r, c) from obs, ignoring answer box 12s."""
    grid = frame_to_grid(obs)
    cells = [(r, c) for r, c in find_objects(grid, 12) if r < 53]
    return (cells[0][0], cells[0][1]) if cells else None


def navigate(game_id, guid, target_r, target_c, grid=None, avoid=None, max_moves=30):
    """Navigate block to target position using BFS, self-correcting after each move.
    Returns final obs or None if unreachable."""
    obs = None
    for step in range(max_moves):
        if grid is None:
            obs = act('U', game_id, guid)  # dummy move to get state
            grid = frame_to_grid(obs)
        pos = block_pos_from_grid(grid)
        if pos == (target_r, target_c):
            return obs
        path = find_path(grid, pos[0], pos[1], target_r, target_c, avoid=avoid)
        if not path:
            print(f"navigate: no path from {pos} to ({target_r},{target_c})")
            return obs
        # Execute just the first move of the path
        obs = act(path[0], game_id, guid)
        grid = frame_to_grid(obs)
        if obs.get("state") in ("WIN", "GAME_OVER"):
            return obs
    return obs


def block_pos_from_grid(grid):
    """Get block top-left (r, c) from grid, ignoring answer box 12s."""
    cells = [(r, c) for r, c in find_objects(grid, 12) if r < 53]
    return (cells[0][0], cells[0][1]) if cells else None


def maze_map(grid, step=5):
    """Show the corridor maze on a coarse grid. Each cell = step×step area."""
    legend = {12: 'B', 9: '9', 0: '.', 1: 'M', 11: 'b', 8: '8'}
    header = '    ' + ''.join(f'{c:3d}' for c in range(0, len(grid[0]), step))
    lines = [header]
    for r in range(0, len(grid), step):
        row_str = f'R{r:02d} '
        for c in range(0, len(grid[0]), step):
            vals = set()
            for dr in range(step):
                for dc in range(step):
                    if r+dr < len(grid) and c+dc < len(grid[0]):
                        vals.add(grid[r+dr][c+dc])
            # Priority: block > markers > nines > resources > corridor > wall
            ch = '#'
            for v, sym in legend.items():
                if v in vals:
                    ch = sym
                    break
            if ch == '#':
                if vals == {4}:
                    ch = '#'
                elif vals == {3}:
                    ch = '_'
                elif 3 in vals and 4 not in vals:
                    ch = '_'
                elif 3 in vals:
                    ch = '/'
            row_str += f'  {ch}'

        lines.append(row_str)
    return '\n'.join(lines)




def level_status(obs):
    """Print a compact summary of current level state."""
    grid = frame_to_grid(obs)
    print(f"State: {obs.get('state')}  Levels: {obs.get('levels_completed')}/{obs.get('win_levels')}")
    # Block position
    c_pos = find_objects(grid, 12)
    if c_pos:
        print(f"Block c(12): rows {min(r for r,c in c_pos)}-{max(r for r,c in c_pos)}, "
              f"cols {min(c for r,c in c_pos)}-{max(c for r,c in c_pos)}")
    # Marker position
    zeros = [(r, c) for r, c in find_objects(grid, 0) if 5 <= r <= 54 and 5 <= c <= 54]
    ones = find_objects(grid, 1)
    marker_cells = zeros + ones
    # Filter to workspace markers (not box borders)
    if marker_cells:
        print(f"Marker 0s: {zeros}  1s: {ones}")
    # Resources
    b_count = len([(r, c) for r, c in find_objects(grid, 11) if r >= 60])
    print(f"Resources: {b_count} b-cells ({b_count // 2} moves left)")


# ── Dashboard status tracking (do not edit) ──────────────────────────

STATUS_DIR = Path(__file__).parent / "status"


class _Status:
    """Writes experiment state to status/<guid>.json for the dashboard."""

    def __init__(self):
        self.guid = self.game_id = self.state = self.result_msg = None
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
            if guid != self.guid:
                self._finalize()
            self.guid, self.game_id = guid, (body or {}).get("game_id")
            self.state = data.get("state")
            self.levels = data.get("levels_completed", 0)
            frames = data.get("frame", [[]])
            frame = frames[-1] if frames else []
            self._append_frame(frame)
            self._write_meta()
        except Exception:
            pass

    def _append_frame(self, frame):
        STATUS_DIR.mkdir(exist_ok=True)
        with open(STATUS_DIR / f"{self.guid}.frames.jsonl", "a") as f:
            f.write(json.dumps(frame) + "\n")

    def _write_meta(self):
        STATUS_DIR.mkdir(exist_ok=True)
        (STATUS_DIR / f"{self.guid}.json").write_text(json.dumps({
            "game_id": self.game_id, "guid": self.guid,
            "state": self.state, "levels_completed": self.levels,
            "experiment": self.experiment, "title": self.title,
            "result": self.result_msg, "updated_at": time.time(),
        }))

    def _finalize(self):
        try:
            if not self.guid:
                return
            path = STATUS_DIR / f"{self.guid}.json"
            if not path.exists():
                return
            s = json.loads(path.read_text())
            if s.get("state") not in ("WIN", "GAME_OVER"):
                s["state"] = "DONE"
            s["result"] = self.result_msg
            s["updated_at"] = time.time()
            path.write_text(json.dumps(s))
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
