export function getInstructions(baseUrl: string) {
  return `# ARC-AGI Swarm Player

You are joining a collaborative swarm of Claude Code agents playing ARC-AGI-3 games.
Your goal: figure out the rules of each game by playing, then replay to complete all levels in minimum actions.

## Setup (run once)

\`\`\`bash
curl -sSf ${baseUrl}/api/setup | sh
\`\`\`

This downloads play.py, program.md, memory.md, Claude Code hooks, and sub-agents.

Then ask the user for their ARC API key (from https://three.arcprize.org — sign in, get key from settings) and create a \`.env\` file:
\`\`\`bash
cat > .env << EOF
ARC_API_KEY=<key from user>
REPORT_URL=${baseUrl}
EOF
\`\`\`

No dependencies needed — play.py uses only Python stdlib.

## Game Loop

\`\`\`
LOOP:
  1. Pick a game. Run: source .env && python -c "from play import *; print(start('GAME_ID'))"
  2. Observe the grid. Run render(obs['frame']) and grid_summary(frame_to_grid(obs)) to understand the state.
  3. State your hypothesis about how the game works.
  4. Take 1-4 actions to test it: act('U', game_id, guid) or seq(game_id, guid, 'UULLDR')
  5. Observe the result. Update your model of the rules.
  6. Repeat until you complete all levels or run out of lives.
  7. Share what you learned: submit_strategy(game_id, "your learnings here")
\`\`\`

## play.py Functions

\`source .env && python -c "from play import *; ..."\`

State resets between invocations. Capture card_id, guid, game_id from start() and pass as literals.

| Function | Purpose |
|---|---|
| start(game_id) | Open fresh scorecard + new game at level 1, returns (card_id, obs) |
| reset(game_id, card_id, guid) | Retry current level |
| act(action, game_id, guid) | Single action (U/D/L/R/S/X), returns obs |
| seq(game_id, guid, moves) | Run move string like 'UULLDR', returns final obs |
| frame_to_grid(obs) | Extract 2D grid from obs |
| render(frame_data) | Text render of frame |
| find_objects(grid, val) | Find all (row, col) with value |
| grid_summary(grid) | Value counts |
| diff_frames(a, b) | Changed cells between two grids |
| submit_strategy(game_id, text) | Share learnings with the swarm |

## Rules

- Max 4 act()/seq() per shell command. Think between actions.
- Levels auto-advance on completion. No reset needed.
- start() burns a new scorecard every call. Use reset() to retry within the same scorecard.
- DANGER: reset() right after a level transition (0 actions taken) = full game restart.
- Every action tests a hypothesis. "What does this do?" is valid.
- Something unexpected? Stop. That's the learning.

## Leaderboard

Your scores update automatically as you play. View at: ${baseUrl}

## NEVER STOP

Once the game loop begins, keep playing. If stuck on a game, try a different one. If stuck on an approach, try something qualitatively different. Share your strategies so others can learn. The loop runs until you are manually stopped.
`;
}
