import { readFile } from "fs/promises";
import path from "path";

const ROOT = path.join(process.cwd(), "..");

async function read(filePath: string): Promise<string> {
  return readFile(path.join(ROOT, filePath), "utf-8");
}

export async function getSetupScript(baseUrl: string): Promise<string> {
  const [playPy, programMd, settings] = await Promise.all([
    read("play.py"),
    read("program.md"),
    read(".claude/settings.json"),
  ]);

  return `#!/bin/sh
set -e

echo "Setting up ARC-AGI swarm player..."

# Create directory structure
mkdir -p .claude memory

# Download play.py
cat > play.py << 'PLAY_PY_EOF'
${playPy}
PLAY_PY_EOF

# Download program.md
cat > program.md << 'PROGRAM_MD_EOF'
${programMd}
PROGRAM_MD_EOF

# Claude Code settings
cat > .claude/settings.json << 'SETTINGS_EOF'
${settings}
SETTINGS_EOF

# Initialize action counter
echo 0 > .action_count

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
