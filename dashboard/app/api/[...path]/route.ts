import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { readFile } from "fs/promises";
import path from "path";
import { readDB, writeDB, appendFrame, readFrames, lookupPlayer } from "@/lib/db";
import { getInstructions } from "@/lib/instructions";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ path: string[] }> };
const json = NextResponse.json;

// ── GET routes ──────────────────────────────────────────────────────

export async function GET(req: Request, ctx: Ctx) {
  const route = (await ctx.params).path.join("/");

  if (route === "active") {
    try {
      const db = await readDB();
      const active = Object.values(db.games);
      const results = await Promise.all(
        active.map(async (g) => ({ ...g, frames: await readFrames(g.guid) }))
      );
      return json(results);
    } catch { return json([]); }
  }

  if (route === "leaderboard") {
    try {
      const db = await readDB();
      const stats: Record<string, { player: string; games_played: number; levels_completed: number; wins: number; total_frames: number }> = {};
      for (const g of Object.values(db.games)) {
        const s = stats[g.player] ??= { player: g.player, games_played: 0, levels_completed: 0, wins: 0, total_frames: 0 };
        s.games_played++;
        s.levels_completed += g.levels_completed;
        if (g.state === "WIN") s.wins++;
        s.total_frames += g.frame_count;
      }
      return json(Object.values(stats).sort((a, b) => b.levels_completed - a.levels_completed || b.wins - a.wins));
    } catch { return json([]); }
  }

  if (route === "strategies") {
    try {
      const db = await readDB();
      const gameId = new URL(req.url).searchParams.get("game_id");
      const list = gameId ? db.strategies.filter((s) => s.game_id === gameId) : db.strategies;
      return json(list.sort((a, b) => b.submitted_at - a.submitted_at));
    } catch { return json([]); }
  }

  if (route === "instructions") {
    const h = await headers();
    const baseUrl = `${h.get("x-forwarded-proto") || "http"}://${h.get("host") || "localhost:3000"}`;
    return new NextResponse(getInstructions(baseUrl), { headers: { "Content-Type": "text/plain" } });
  }

  if (route.startsWith("static/")) {
    const filename = path.basename(route.replace("static/", ""));
    if (!filename || filename.startsWith(".")) return json({ error: "Invalid filename" }, { status: 400 });
    try {
      const content = await readFile(path.join(process.cwd(), "..", filename), "utf-8");
      return new NextResponse(content, {
        headers: { "Content-Type": "text/plain", "Content-Disposition": `attachment; filename="${filename}"` },
      });
    } catch { return json({ error: `${filename} not found` }, { status: 404 }); }
  }

  return json({ error: "Not found" }, { status: 404 });
}

// ── POST routes ─────────────────────────────────────────────────────

export async function POST(req: Request, ctx: Ctx) {
  const route = (await ctx.params).path.join("/");

  if (route === "register") {
    try {
      const { nickname } = await req.json();
      if (!nickname || typeof nickname !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$/.test(nickname))
        return json({ error: "Invalid nickname" }, { status: 400 });
      const db = await readDB();
      if (Object.values(db.players).some((p) => p.nickname.toLowerCase() === nickname.toLowerCase()))
        return json({ error: "Nickname already taken" }, { status: 409 });
      const api_key = crypto.randomUUID();
      db.players[api_key] = { nickname, registered_at: Date.now() / 1000 };
      await writeDB(db);
      return json({ api_key, nickname });
    } catch { return json({ error: "Internal error" }, { status: 500 }); }
  }

  if (route === "report") {
    try {
      const body = await req.json();
      const { api_key, game_id, guid, state, levels_completed, frame, experiment, title } = body;
      if (!api_key || !guid) return json({ error: "Missing api_key or guid" }, { status: 400 });
      const db = await readDB();
      const player = lookupPlayer(db, api_key) || api_key; // accept raw username as fallback
      const existing = db.games[guid];
      db.games[guid] = {
        player, player_key: api_key, guid,
        game_id: game_id || existing?.game_id || "",
        state: state || existing?.state || "PLAYING",
        levels_completed: levels_completed ?? existing?.levels_completed ?? 0,
        experiment: experiment || existing?.experiment || "",
        title: title || existing?.title || "",
        frame_count: (existing?.frame_count || 0) + (frame ? 1 : 0),
        updated_at: Date.now() / 1000,
      };
      await writeDB(db);
      if (frame) await appendFrame(guid, frame);
      return json({ ok: true });
    } catch { return json({ error: "Internal error" }, { status: 500 }); }
  }

  if (route === "strategies") {
    try {
      const { api_key, game_id, content } = await req.json();
      if (!api_key || !game_id || !content) return json({ error: "Missing required fields" }, { status: 400 });
      const db = await readDB();
      const player = lookupPlayer(db, api_key) || api_key;
      db.strategies.push({ player, game_id, content, submitted_at: Date.now() / 1000 });
      await writeDB(db);
      return json({ ok: true });
    } catch { return json({ error: "Internal error" }, { status: 500 }); }
  }

  return json({ error: "Not found" }, { status: 404 });
}
