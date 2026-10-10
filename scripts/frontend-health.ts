import { mkdtemp, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync, type SpawnSyncOptions } from "node:child_process";

const projectRoot = resolve(import.meta.dirname, "..");
const testDirectory = join(projectRoot, "tests", "frontend");
const testFiles = (await readdir(testDirectory))
  .filter((file) => file.endsWith(".test.ts"))
  .sort()
  .map((file) => join(testDirectory, file));

if (Number(process.versions.node.split(".")[0]) < 22) {
  console.error("Frontend health reporting requires Node.js 22 or newer (Fallow 3.30.0).");
  process.exit(1);
}

const coverageDirectory = await mkdtemp(join(tmpdir(), "motioninocean-v8-coverage-"));

function run(command: string, args: string[], options: SpawnSyncOptions = {}): void {
  const result = spawnSync(command, args, {
    cwd: projectRoot,
    stdio: "inherit",
    ...options,
  });
  if (result.error) throw result.error;
  if (result.status !== 0)
    throw new Error(`${command} exited with status ${result.status ?? "unknown"}`);
}

try {
  run(process.execPath, ["--import", "tsx", "--test", ...testFiles], {
    env: { ...process.env, NODE_V8_COVERAGE: coverageDirectory },
  });
  run("npx", [
    "--yes",
    "fallow@3.30.0",
    "health",
    "--coverage",
    coverageDirectory,
    "--report-only",
    "--format",
    "markdown",
    "--explain",
  ]);
  run("npx", [
    "--yes",
    "fallow@3.30.0",
    "health",
    "--complexity",
    "--max-crap",
    "30",
    "--top",
    "20",
    "--sort",
    "severity",
    "--coverage",
    coverageDirectory,
    "--report-only",
    "--format",
    "markdown",
  ]);
} finally {
  await rm(coverageDirectory, { recursive: true, force: true });
}
