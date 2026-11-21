// R3 entry for the make.fun news-image-20261120 bounty.
//
// The front page itself is entry.png, painted in this repo by render.py
// (Pillow; 39 verified Friday 20 November 2026 stories, 15 code-drawn
// panels, a world map with numbered pins and a legend, a DATE CHECK box).
// This script is the competition deliverable: it checks entry.png against
// the image gate (a whole PNG, at most 1 MiB, at most 1024x1024) and
// writes it to the output directory.
//
// Run:  node main.ts
// Output: $MAKEFUN_OUTPUT_DIR/entry.png (default: /output/entry.png)

import { copyFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = dirname(fileURLToPath(import.meta.url));
const SOURCE = join(REPO, "entry.png");

const BYTE_LIMIT = 1048576; // 1 MiB
const SIDE_LIMIT = 1024;
const MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function die(message: string): never {
  console.error(`entry gate FAILED: ${message}`);
  process.exit(1);
}

// IEEE CRC-32, built lazily on first use. Lets the gate verify the IHDR
// chunk's own checksum, so a corrupted header fails here instead of
// reaching the judge as a broken image.
let crcTable: Uint32Array | null = null;

function crc32(data: Buffer): number {
  if (crcTable === null) {
    crcTable = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) {
        c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      }
      crcTable[n] = c >>> 0;
    }
  }
  let crc = 0xffffffff;
  for (const byte of data) {
    crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

interface PngInfo {
  width: number;
  height: number;
  bytes: number;
  sha256: string;
}

function inspectPng(path: string): PngInfo {
  if (!existsSync(path)) {
    die(`entry.png is missing - run \`python3 render.py\` first`);
  }
  const data = readFileSync(path);
  if (data.length > BYTE_LIMIT) {
    die(`entry.png is ${data.length} bytes, over the 1 MiB limit`);
  }
  if (data.length < 33 || !data.subarray(0, 8).equals(MAGIC)) {
    die("entry.png is not a PNG file (bad magic bytes)");
  }
  if (data.toString("ascii", 12, 16) !== "IHDR") {
    die("entry.png has no IHDR chunk right after the signature");
  }
  // The IHDR CRC covers the chunk type plus its 13 data bytes.
  const storedCrc = data.readUInt32BE(29);
  if (crc32(data.subarray(12, 29)) !== storedCrc) {
    die("entry.png has a bad IHDR checksum - the file is corrupt");
  }
  const width = data.readUInt32BE(16);
  const height = data.readUInt32BE(20);
  if (width === 0 || height === 0) {
    die(`entry.png has a zero dimension (${width}x${height})`);
  }
  if (width > SIDE_LIMIT || height > SIDE_LIMIT) {
    die(`entry.png is ${width}x${height}, over the 1024x1024 limit`);
  }
  const tail = data.subarray(data.length - 12);
  const iend = Buffer.concat([
    Buffer.from([0x00, 0x00, 0x00, 0x00]),
    Buffer.from("IEND", "ascii"),
    Buffer.from([0xae, 0x42, 0x60, 0x82]),
  ]);
  if (!tail.equals(iend)) {
    die("entry.png does not end with a whole IEND chunk - truncated?");
  }
  return {
    width,
    height,
    bytes: data.length,
    sha256: createHash("sha256").update(data).digest("hex"),
  };
}

function main(): void {
  const info = inspectPng(SOURCE);
  const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
  mkdirSync(outDir, { recursive: true });
  const dest = join(outDir, "entry.png");
  copyFileSync(SOURCE, dest);

  // Confirm the copy byte-for-byte, so a partial write can never pass
  // silently as a valid entry.
  const copied = readFileSync(dest);
  const copiedHash = createHash("sha256").update(copied).digest("hex");
  if (copiedHash !== info.sha256) {
    die(`copied file ${dest} does not match entry.png byte-for-byte`);
  }
  console.log(
    `entry.png OK: ${info.width}x${info.height}, ${info.bytes} bytes, ` +
      `sha256 ${info.sha256} -> ${dest}`,
  );
}

main();
