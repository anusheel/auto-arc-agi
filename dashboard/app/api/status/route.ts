import { NextResponse } from "next/server";
import { readdir, readFile } from "fs/promises";
import path from "path";

const STATUS_DIR = path.join(process.cwd(), "..", "status");

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const files = await readdir(STATUS_DIR);
    const jsonFiles = files.filter((f) => f.endsWith(".json"));
    const statuses = await Promise.all(
      jsonFiles.map(async (f) => {
        const raw = await readFile(path.join(STATUS_DIR, f), "utf-8");
        const meta = JSON.parse(raw);
        const framesPath = path.join(STATUS_DIR, f.replace(".json", ".frames.jsonl"));
        try {
          const framesRaw = await readFile(framesPath, "utf-8");
          meta.frames = framesRaw.trimEnd().split("\n").map((line: string) => JSON.parse(line));
        } catch {
          meta.frames = meta.frames || [];
        }
        return meta;
      })
    );
    return NextResponse.json(statuses);
  } catch {
    return NextResponse.json([]);
  }
}
