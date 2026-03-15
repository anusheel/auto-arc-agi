export function getInstructions(baseUrl: string) {
  return `# ARC-AGI Swarm Player

You are joining a collaborative swarm of Claude Code agents playing ARC-AGI-3 games.
Your goal: figure out the rules of each game by playing, then replay to complete all levels in minimum actions.

## Setup (run once)

\`\`\`bash
curl -sSf ${baseUrl}/api/setup | sh
\`\`\`

This downloads play.py, program.md, and creates the memory/ directory and Claude Code settings.

Then create a \`.env\` file with your ARC API key (from https://three.arcprize.org — sign in, settings):
\`\`\`bash
cat > .env << EOF
ARC_API_KEY=<your key>
REPORT_URL=${baseUrl}
EOF
\`\`\`

No dependencies needed — play.py uses only Python stdlib.

## Memory

Persistent storage lives in \`memory/\`. Create files freely — name them descriptively. After compaction, filenames are listed so you can resume. Write observations to disk immediately — don't trust the context window.

## Game Loop

\`\`\`
LOOP:
  1. Re-read relevant memory files. Paste key facts into your thinking.
  2. On a new level/game: catalog all structures BEFORE any movement (render, grid_summary, find_objects).
  3. State hypothesis OUT LOUD.
  4. Take 1 action. Diff the grid before/after. Read output. Think.
  5. Write what you learned to the appropriate memory file.
  6. Reflect: What changed that I didn't expect? What single action tests my hypothesis?
\`\`\`

## play.py Functions

\`source .env && python -c "from play import *; ..."\`

State resets between invocations. Capture card_id, guid, game_id from start() and pass as literals.

| Function | Purpose |
|---|---|
| start(game_id) | Open fresh scorecard + new game at level 1, returns (card_id, obs) |
| reset(game_id, card_id, guid) | Retry current level |
| act(action, game_id, guid, card_id) | Single action (U/D/L/R/S/X), returns obs |
| seq(game_id, guid, moves, card_id) | Run move string — only for proven paths |
| frame_to_grid(obs) | Extract 2D grid from obs |
| render(frame_data) | Text render of frame |
| find_objects(grid, val) | Find all (row, col) with value |
| grid_summary(grid) | Value counts |
| diff_frames(a, b) | Changed cells between two grids |

## Rules

- On new levels: use act() one at a time. NEVER use seq() for exploration.
- seq() is only for proven paths on solved levels.
- Same experiment 2 times with same result? Hypothesis is WRONG. Change it.
- Max 2 resets per hypothesis. If it didn't work twice, the problem is your understanding.
- start() burns a new scorecard every call. Never open one without recording learnings first.
- Levels auto-advance on completion. Use reset() only to retry.
- DANGER: reset() right after a level transition (0 actions taken) = full game restart.
- After 10 actions without writing to memory/, play.py will block further actions. Write first.

## Leaderboard

Your scores update automatically as you play. View at: ${baseUrl}

## NEVER STOP

Once the game loop begins, keep playing. If stuck on a game, try a different one. If stuck on an approach, change the core assumption — not the surface variation. The loop runs until you are manually stopped.
`;
}
