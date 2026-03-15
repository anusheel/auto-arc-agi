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
}

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
    <div className="space-y-3 outline-none" ref={containerRef} tabIndex={0} onKeyDown={handleKey}>
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
              <button
                className="text-[11px] text-[#86868b] hover:text-[#1d1d1f] transition-colors"
                onClick={() => setManualIndex(0)}
              >
                &#x23EE;
              </button>
              <button
                className="text-[11px] text-[#86868b] hover:text-[#1d1d1f] transition-colors"
                onClick={stepBack}
              >
                &#x23F4;
              </button>
              <button
                className="text-[11px] text-[#86868b] hover:text-[#1d1d1f] transition-colors"
                onClick={() => setPlaying(!playing)}
              >
                {playing ? "\u23F8" : "\u23F5"}
              </button>
              <button
                className="text-[11px] text-[#86868b] hover:text-[#1d1d1f] transition-colors"
                onClick={stepForward}
              >
                &#x23F5;
              </button>
              <button
                className="text-[11px] text-[#86868b] hover:text-[#1d1d1f] transition-colors"
                onClick={() => setManualIndex(null)}
              >
                &#x23ED;
              </button>
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

function StatePill({ state }: { state: string }) {
  if (state === "WIN") return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-green-600 bg-green-50 px-2.5 py-0.5 rounded-full">
      <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
      Complete
    </span>
  );
  if (state === "GAME_OVER") return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-red-600 bg-red-50 px-2.5 py-0.5 rounded-full">
      <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
      Game Over
    </span>
  );
  if (state === "DONE") return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-[#6e6e73] bg-[#f5f5f7] px-2.5 py-0.5 rounded-full">
      <span className="w-1.5 h-1.5 rounded-full bg-[#86868b]" />
      Done
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-[#1d1d1f] bg-[#f5f5f7] px-2.5 py-0.5 rounded-full">
      <span className="w-1.5 h-1.5 rounded-full bg-[#0071e3] animate-pulse" />
      Running
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

export default function Dashboard() {
  const [statuses, setStatuses] = useState<Status[]>([]);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("/api/status");
        const data = await res.json();
        setStatuses(data);
      } catch {
        // ignore
      }
    };
    poll();
    const interval = setInterval(poll, 1500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  const running = statuses.filter((s) => s.state !== "WIN" && s.state !== "GAME_OVER").length;

  return (
    <main className="min-h-screen bg-white">
      <div className="max-w-[1120px] mx-auto px-6 py-12">
        <header className="mb-12 flex items-start justify-between">
          <div>
            <h1 className="text-[28px] font-semibold tracking-tight text-[#1d1d1f]">
              ARC-AGI
            </h1>
            <p className="text-[15px] text-[#86868b] mt-1">
              {statuses.length === 0
                ? "No active experiments"
                : `${statuses.length} experiment${statuses.length !== 1 ? "s" : ""}${running > 0 ? ` \u00b7 ${running} running` : ""}`
              }
            </p>
          </div>
          <span className="text-[15px] font-mono text-[#86868b] mt-1">
            {statuses.reduce((sum, s) => sum + (s.frames?.length || 0), 0)} actions
          </span>
        </header>

        {statuses.length === 0 ? (
          <div className="text-center py-32">
            <p className="text-[17px] text-[#86868b]">
              Waiting for experiments...
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
            {statuses
              .sort((a, b) => b.updated_at - a.updated_at)
              .map((s) => (
                <div
                  key={s.guid}
                  className="group rounded-2xl bg-[#fbfbfd] border border-[#e8e8ed] p-5 transition-all hover:shadow-md hover:border-[#d2d2d7] flex flex-col"
                >
                  <FramePlayer frames={s.frames || []} />

                  <div className="mt-4 flex flex-col flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[13px] font-mono text-[#1d1d1f]">
                        {s.game_id}
                        <span className="text-[11px] text-[#86868b] ml-1.5">{s.guid.slice(0, 8)}</span>
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
                    </div>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </main>
  );
}
