import { readFile } from "fs/promises";
import path from "path";

const ROOT = path.join(process.cwd(), "..");

async function read(filePath: string): Promise<string> {
  return readFile(path.join(ROOT, filePath), "utf-8");
}

export async function getSetupScript(baseUrl: string): Promise<string> {
  const [playPy, programMd, settings, blockActions, checkReflection, resetCounter, preCompact, gridAnalyzer, experimentRunner] = await Promise.all([
    read("play.py"),
    read("program.md"),
    read(".claude/settings.json"),
    read(".claude/hooks/block-actions.sh"),
    read(".claude/hooks/check-reflection.sh"),
    read(".claude/hooks/reset-counter.sh"),
    read(".claude/hooks/pre-compact.sh"),
    read(".claude/agents/grid-analyzer.md"),
    read(".claude/agents/experiment-runner.md"),
  ]);

  return `#!/bin/sh
set -e

echo "Setting up ARC-AGI swarm player..."

# Create directory structure
mkdir -p .claude/hooks .claude/agents

# Download play.py
cat > play.py << 'PLAY_PY_EOF'
${playPy}
PLAY_PY_EOF

# Download program.md
cat > program.md << 'PROGRAM_MD_EOF'
${programMd}
PROGRAM_MD_EOF

# Create initial memory.md
if [ ! -f memory.md ]; then
cat > memory.md << 'MEMORY_MD_EOF'
# ARC-AGI-3 Game Strategy

## Current Model

(none yet)

## Falsified

(none yet)

## Next Test

(none yet)

## Game State

(none yet)

## Last Reflection

(none yet)
MEMORY_MD_EOF
fi

# Claude Code settings
cat > .claude/settings.json << 'SETTINGS_EOF'
${settings}
SETTINGS_EOF

# Hooks
cat > .claude/hooks/block-actions.sh << 'HOOK_EOF'
${blockActions}
HOOK_EOF
chmod +x .claude/hooks/block-actions.sh

cat > .claude/hooks/check-reflection.sh << 'HOOK_EOF'
${checkReflection}
HOOK_EOF
chmod +x .claude/hooks/check-reflection.sh

cat > .claude/hooks/reset-counter.sh << 'HOOK_EOF'
${resetCounter}
HOOK_EOF
chmod +x .claude/hooks/reset-counter.sh

cat > .claude/hooks/pre-compact.sh << 'HOOK_EOF'
${preCompact}
HOOK_EOF
chmod +x .claude/hooks/pre-compact.sh

# Initialize counters
echo 0 > .claude/arc_action_count
echo 0 > .claude/arc_strategic_count

# Sub-agents
cat > .claude/agents/grid-analyzer.md << 'AGENT_EOF'
${gridAnalyzer}
AGENT_EOF

cat > .claude/agents/experiment-runner.md << 'AGENT_EOF'
${experimentRunner}
AGENT_EOF

# Create .env if it doesn't exist
if [ ! -f .env ]; then
  echo ""
  echo "Create your .env file with:"
  echo ""
  echo "  ARC_API_KEY=your-key-from-arcprize.org"
  echo "  REPORT_URL=${baseUrl}"
  echo ""
  echo "Get your ARC API key from https://three.arcprize.org"
else
  echo "Existing .env found, not overwriting."
fi

echo ""
echo "Setup complete! Run: claude"
echo "Then tell Claude: read program.md and start playing"
`;
}
