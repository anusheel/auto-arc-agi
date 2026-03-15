import { readFile, writeFile, mkdir, appendFile } from "fs/promises";
import path from "path";

const DATA_DIR = path.join(process.cwd(), "data");
const DB_PATH = path.join(DATA_DIR, "db.json");
const FRAMES_DIR = path.join(DATA_DIR, "frames");

interface Player {
  nickname: string;
  registered_at: number;
}

interface Game {
  player: string;
  player_key: string;
  game_id: string;
  guid: string;
  state: string;
  levels_completed: number;
  experiment: string;
  title: string;
  frame_count: number;
  updated_at: number;
}

interface Strategy {
  player: string;
  game_id: string;
  content: string;
  submitted_at: number;
}

export interface DB {
  players: Record<string, Player>;
  games: Record<string, Game>;
  strategies: Strategy[];
}

export async function readDB(): Promise<DB> {
  try {
    const raw = await readFile(DB_PATH, "utf-8");
    return JSON.parse(raw);
  } catch {
    return { players: {}, games: {}, strategies: [] };
  }
}

export async function writeDB(db: DB): Promise<void> {
  await mkdir(DATA_DIR, { recursive: true });
  await writeFile(DB_PATH, JSON.stringify(db, null, 2));
}

export async function appendFrame(guid: string, frame: number[][]): Promise<void> {
  await mkdir(FRAMES_DIR, { recursive: true });
  await appendFile(path.join(FRAMES_DIR, `${guid}.frames.jsonl`), JSON.stringify(frame) + "\n");
}

export async function readFrames(guid: string): Promise<number[][][]> {
  try {
    const raw = await readFile(path.join(FRAMES_DIR, `${guid}.frames.jsonl`), "utf-8");
    return raw.trimEnd().split("\n").map((line) => JSON.parse(line));
  } catch {
    return [];
  }
}

export function lookupPlayer(db: DB, apiKey: string): string | null {
  return db.players[apiKey]?.nickname ?? null;
}
