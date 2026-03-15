"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Slider } from "@/components/ui/slider";

const ARC_COLORS: Record<number, string> = {
  0: "#FFFFFF",
  1: "#CCCCCC",
  2: "#999999",
  3: "#666666",
  4: "#333333",
  5: "#000000",
  6: "#E53AA3",
  7: "#FF7BCC",
  8: "#F93C31",
  9: "#1E93FF",
  10: "#88D8F1",
  11: "#FFDC00",
  12: "#FF851B",
  13: "#921231",
  14: "#4FCC30",
  15: "#A356D6",
};

interface Status {
  game_id: string;
  guid: string;
  frames: number[][][];
  state: string;
  levels_completed: number;
  experiment: string;
  title: string;
  result: string | null;
  updated_at: number;
  player?: string;
}

interface LeaderboardEntry {
  player: string;
  games_played: number;
  levels_completed: number;
  wins: number;
  total_frames: number;
}

type Tab = "active" | "leaderboard" | "join";

function GameCanvas({ grid }: { grid: number[][] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !grid.length) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rows = grid.length;
    const cols = grid[0]?.length || 0;
    const cellSize = Math.max(2, Math.min(6, Math.floor(480 / Math.max(rows, cols))));

    canvas.width = cols * cellSize;
    canvas.height = rows * cellSize;

    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const val = grid[y][x];
        ctx.fillStyle = ARC_COLORS[val] || `hsl(${(val * 37) % 360}, 70%, 50%)`;
        ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
      }
    }
  }, [grid]);

  if (!grid.length) return null;

  return (
    <canvas
      ref={canvasRef}
      className="rounded-xl w-full"
      style={{ imageRendering: "pixelated" }}
    />
  );
}

function FramePlayer({ frames }: { frames: number[][][] }) {
  const [index, setIndex] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const latestIndex = Math.max(0, frames.length - 1);

  useEffect(() => {
    if (!playing) return;
    const interval = setInterval(() => {
      setIndex((current) => {
        const nextIndex = current ?? latestIndex;
        if (nextIndex >= latestIndex) {
          setPlaying(false);
          return latestIndex;
        }
        return nextIndex + 1;
      });
    }, 150);
    return () => clearInterval(interval);
  }, [latestIndex, playing]);

  const safeIndex = Math.min(index ?? latestIndex, latestIndex);
  const grid = frames[safeIndex] || [];

  const stepBack = useCallback(() => {
    setPlaying(false);
    setIndex((current) => Math.max(0, (current ?? latestIndex) - 1));
  }, [latestIndex]);

  const setManualIndex = useCallback((nextIndex: number | null) => {
    setPlaying(false);
    setIndex(nextIndex);
  }, []);

  const stepForward = useCallback(() => {
    setPlaying(false);
    setIndex((current) => Math.min(latestIndex, (current ?? latestIndex) + 1));
  }, [latestIndex]);

  const containerRef = useRef<HTMLDivElement>(null);

  const handleKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") { e.preventDefault(); stepBack(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); stepForward(); }
  }, [stepBack, stepForward]);

  if (!frames.length) return null;

  return (
    <div className="space-y-3 outline-none" ref={containerRef} tabIndex={0} onKeyDown={handleKey} onMouseEnter={() => containerRef.current?.focus()}>
      <GameCanvas grid={grid} />
      {frames.length > 1 && (
        <div className="space-y-2 px-1">
          <Slider
            value={[safeIndex]}
            min={0}
            max={latestIndex}
            step={1}
            onValueChange={(val) => {
              setManualIndex(Array.isArray(val) ? val[0] : val);
            }}
            className="w-full"
          />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {([
                [() => setManualIndex(0), "\u23EE"],
                [stepBack, "\u23F4"],
                [() => setPlaying(!playing), playing ? "\u23F8" : "\u23F5"],
                [stepForward, "\u23F5"],
                [() => setManualIndex(null), "\u23ED"],
              ] as const).map(([fn, icon], i) => (
                <button key={i} className="text-[11px] text-[#86868b] hover:text-[#1d1d1f] transition-colors" onClick={fn}>
                  {icon}
                </button>
              ))}
            </div>
            <span className="text-[11px] text-[#86868b] font-mono tabular-nums">
              {safeIndex + 1} / {frames.length}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

const STATE_STYLES: Record<string, { text: string; bg: string; dot: string; label: string; pulse?: boolean }> = {
  WIN:       { text: "text-green-600", bg: "bg-green-50", dot: "bg-green-500", label: "Complete" },
  GAME_OVER: { text: "text-red-600", bg: "bg-red-50", dot: "bg-red-500", label: "Game Over" },
  DONE:      { text: "text-[#6e6e73]", bg: "bg-[#f5f5f7]", dot: "bg-[#86868b]", label: "Done" },
};
const DEFAULT_STATE = { text: "text-[#1d1d1f]", bg: "bg-[#f5f5f7]", dot: "bg-[#0071e3]", label: "Running", pulse: true };

function StatePill({ state }: { state: string }) {
  const s = STATE_STYLES[state] || DEFAULT_STATE;
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium ${s.text} ${s.bg} px-2.5 py-0.5 rounded-full`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot} ${s.pulse ? "animate-pulse" : ""}`} />
      {s.label}
    </span>
  );
}

function timeSince(ts: number) {
  const seconds = Math.floor(Date.now() / 1000 - ts);
  if (seconds < 5) return "Just now";
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

function GameCard({ s, now }: { s: Status; now: number }) {
  return (
    <div className="group rounded-2xl bg-[#fbfbfd] border border-[#e8e8ed] p-5 transition-all hover:shadow-md hover:border-[#d2d2d7] flex flex-col">
      <FramePlayer frames={s.frames || []} />
      <div className="mt-4 flex flex-col flex-1">
        <div className="flex items-center justify-between">
          <span className="text-[13px] font-mono text-[#1d1d1f]">
            {s.player && (
              <span className="text-[11px] text-[#0071e3] mr-1.5">{s.player}</span>
            )}
            {s.game_id}
            <span className="text-[11px] text-[#86868b] ml-1.5">{s.guid?.slice(0, 8)}</span>
          </span>
          <span className={`text-[11px] font-mono ${now / 1000 - s.updated_at < 60 ? "text-green-500" : "text-[#86868b]"}`}>{timeSince(s.updated_at)}</span>
        </div>
        <p className="text-[13px] text-[#6e6e73] leading-relaxed line-clamp-2 mt-2">
          {s.title || s.experiment}
        </p>
        <div className="mt-3">
          <StatePill state={s.state} />
        </div>
        {s.result && (
          <p className="text-[12px] text-[#1d1d1f] bg-[#f5f5f7] rounded-lg p-3 mt-3 leading-relaxed">
            {s.result}
          </p>
        )}
        <div className="flex items-center gap-2 text-[12px] text-[#86868b] mt-auto pt-3">
          <span>Level {s.levels_completed}</span>
          {s.frames && <span>{s.frames.length} actions</span>}
        </div>
      </div>
    </div>
  );
}

function Leaderboard({ entries }: { entries: LeaderboardEntry[] }) {
  if (!entries.length) {
    return (
      <div className="text-center py-32">
        <p className="text-[17px] text-[#86868b]">No players yet</p>
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-[#e8e8ed] overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="bg-[#f5f5f7] text-[12px] text-[#86868b] font-medium">
            <th className="text-left px-5 py-3">Rank</th>
            <th className="text-left px-5 py-3">Player</th>
            <th className="text-right px-5 py-3">Levels</th>
            <th className="text-right px-5 py-3">Wins</th>
            <th className="text-right px-5 py-3">Games</th>
            <th className="text-right px-5 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={e.player} className="border-t border-[#e8e8ed] text-[13px]">
              <td className="px-5 py-3 text-[#86868b] font-mono">{i + 1}</td>
              <td className="px-5 py-3 font-medium text-[#1d1d1f]">{e.player}</td>
              <td className="px-5 py-3 text-right font-mono text-[#1d1d1f]">{e.levels_completed}</td>
              <td className="px-5 py-3 text-right font-mono text-[#1d1d1f]">{e.wins}</td>
              <td className="px-5 py-3 text-right font-mono text-[#86868b]">{e.games_played}</td>
              <td className="px-5 py-3 text-right font-mono text-[#86868b]">{e.total_frames}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function JoinSwarm() {
  const [copied, setCopied] = useState(false);
  const [instructions, setInstructions] = useState("");

  useEffect(() => {
    fetch("/api/instructions")
      .then((r) => r.text())
      .then(setInstructions)
      .catch(() => setInstructions("Failed to load instructions"));
  }, []);

  const handleCopy = () => {
    navigator.clipboard.writeText(instructions);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-[#e8e8ed] bg-[#fbfbfd] p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Join the Swarm</h2>
            <p className="text-[13px] text-[#86868b] mt-1">
              Paste these instructions into Claude Code to start playing
            </p>
          </div>
          <button
            onClick={handleCopy}
            className="px-4 py-2 rounded-lg text-[13px] font-medium transition-all bg-[#0071e3] text-white hover:bg-[#0077ED] active:scale-95"
          >
            {copied ? "Copied!" : "Copy Instructions"}
          </button>
        </div>
        <pre className="bg-[#1d1d1f] text-[#f5f5f7] rounded-xl p-5 text-[12px] leading-relaxed overflow-auto max-h-[500px] font-mono">
          {instructions || "Loading..."}
        </pre>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>("active");
  const [statuses, setStatuses] = useState<Status[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("/api/active");
        setStatuses(await res.json());
      } catch {
        // ignore
      }
    };
    poll();
    const interval = setInterval(poll, 1500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("/api/leaderboard");
        setLeaderboard(await res.json());
      } catch {
        // ignore
      }
    };
    poll();
    const interval = setInterval(poll, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  const allStatuses = statuses.map((s) => ({ ...s, player: s.player || "Unknown" }));
  const running = allStatuses.filter((s) => s.state !== "WIN" && s.state !== "GAME_OVER" && s.state !== "DONE").length;

  return (
    <main className="min-h-screen bg-white">
      <div className="max-w-[1120px] mx-auto px-6 py-12">
        <header className="mb-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-[28px] font-semibold tracking-tight text-[#1d1d1f]">
                ARC-AGI
              </h1>
              <p className="text-[15px] text-[#86868b] mt-1">
                {allStatuses.length === 0
                  ? "No active experiments"
                  : `${allStatuses.length} experiment${allStatuses.length !== 1 ? "s" : ""}${running > 0 ? ` \u00b7 ${running} running` : ""}`
                }
              </p>
            </div>
            <div className="text-right text-[13px] font-mono text-[#86868b] mt-1 space-y-0.5">
              <div>{allStatuses.length} experiments</div>
              <div>{allStatuses.filter((s) => s.state === "WIN").length} wins</div>
              <div>{new Set(allStatuses.map((s) => s.player)).size} contributors</div>
            </div>
          </div>
          <div className="flex gap-1 mt-6 border-b border-[#e8e8ed]">
            {([["active", "Active Games"], ["leaderboard", "Leaderboard"], ["join", "Join"]] as const).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`px-4 py-2.5 text-[13px] font-medium transition-colors relative ${
                  tab === key
                    ? "text-[#1d1d1f]"
                    : "text-[#86868b] hover:text-[#1d1d1f]"
                }`}
              >
                {label}
                {tab === key && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#0071e3]" />
                )}
              </button>
            ))}
          </div>
        </header>

        {tab === "active" && (
          allStatuses.length === 0 ? (
            <div className="text-center py-32">
              <p className="text-[17px] text-[#86868b]">
                Waiting for experiments...
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
              {allStatuses
                .sort((a, b) => b.updated_at - a.updated_at)
                .map((s) => (
                  <GameCard key={s.guid} s={s} now={now} />
                ))}
            </div>
          )
        )}

        {tab === "leaderboard" && (
          <Leaderboard entries={leaderboard} />
        )}

        {tab === "join" && (
          <JoinSwarm />
        )}
      </div>
    </main>
  );
}
