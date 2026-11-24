import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL(".", import.meta.url)));
const source = resolve(root, "public");
const output = resolve(root, "dist");
const required = ["API_BASE_URL", "SUPABASE_URL", "SUPABASE_ANON_KEY"];
const missing = required.filter((key) => !process.env[key]);

if (missing.length) {
  throw new Error(`Missing Netlify environment variables: ${missing.join(", ")}`);
}

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(source, output, { recursive: true });
await writeFile(
  resolve(output, "config.js"),
  `window.APP_CONFIG = ${JSON.stringify({
    apiBaseUrl: process.env.API_BASE_URL,
    supabaseUrl: process.env.SUPABASE_URL,
    supabaseAnonKey: process.env.SUPABASE_ANON_KEY
  })};\n`
);
