#!/usr/bin/env node

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";

const XMP_NAMESPACE = Buffer.from("http://ns.adobe.com/xap/1.0/\0", "utf8");

function usage() {
  console.log("Usage: node convert_motion_photo.mjs --input input.mp4 --output output_MP.jpg [--cover-at seconds]");
}

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (key === "-h" || key === "--help") return { help: true };
    if (!["--input", "--output", "--cover-at"].includes(key)) throw new Error(`Unknown option: ${key}`);
    const value = argv[++index];
    if (!value || value.startsWith("--")) throw new Error(`${key} requires a value.`);
    values[key.slice(2)] = value;
  }
  if (!values.input || !values.output) throw new Error("--input and --output are required.");
  const coverAt = values["cover-at"] === undefined ? undefined : Number(values["cover-at"]);
  if (coverAt !== undefined && (!Number.isFinite(coverAt) || coverAt < 0)) throw new Error("--cover-at must be a non-negative number.");
  return { inputPath: path.resolve(values.input), outputPath: path.resolve(values.output), coverAt };
}

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (error) => reject(new Error(`Could not start ${command}: ${error.message}`)));
    child.on("close", (code) => code === 0 ? resolve(stdout) : reject(new Error(`${command} failed: ${stderr.trim() || `exit ${code}`}`)));
  });
}

function buildXmp(videoLength, timestampUs) {
  return `<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?><x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:Camera="http://ns.google.com/photos/1.0/camera/" xmlns:Container="http://ns.google.com/photos/1.0/container/" xmlns:Item="http://ns.google.com/photos/1.0/container/item/" Camera:MotionPhoto="1" Camera:MotionPhotoVersion="1" Camera:MotionPhotoPresentationTimestampUs="${timestampUs}"><Container:Directory><rdf:Seq><rdf:li rdf:parseType="Resource"><Container:Item Item:Mime="image/jpeg" Item:Semantic="Primary" Item:Length="0" Item:Padding="0"/></rdf:li><rdf:li rdf:parseType="Resource"><Container:Item Item:Mime="video/mp4" Item:Semantic="MotionPhoto" Item:Length="${videoLength}"/></rdf:li></rdf:Seq></Container:Directory></rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>`;
}

function compose(jpeg, video, timestampUs) {
  if (jpeg[0] !== 0xff || jpeg[1] !== 0xd8) throw new Error("ffmpeg did not produce a valid JPEG cover.");
  const payload = Buffer.concat([XMP_NAMESPACE, Buffer.from(buildXmp(video.length, timestampUs), "utf8")]);
  if (payload.length + 2 > 0xffff) throw new Error("XMP metadata exceeds JPEG APP1 size limit.");
  const header = Buffer.alloc(4);
  header.writeUInt16BE(0xffe1, 0);
  header.writeUInt16BE(payload.length + 2, 2);
  return Buffer.concat([jpeg.subarray(0, 2), header, payload, jpeg.subarray(2), video]);
}

function validate(output, video, timestampUs) {
  const header = output.subarray(0, Math.min(output.length, 96 * 1024)).toString("utf8");
  const tail = output.subarray(output.length - video.length);
  const sameVideo = createHash("sha256").update(tail).digest("hex") === createHash("sha256").update(video).digest("hex");
  const checks = {
    jpegSoi: output.subarray(0, 2).equals(Buffer.from([0xff, 0xd8])),
    motionPhotoXmp: header.includes('Camera:MotionPhoto="1"'),
    videoDirectory: header.includes('Item:Semantic="MotionPhoto"'),
    declaredVideoLength: header.includes(`Item:Length="${video.length}"`),
    timestamp: header.includes(`Camera:MotionPhotoPresentationTimestampUs="${timestampUs}"`),
    mp4Tail: tail.subarray(4, 8).toString("ascii") === "ftyp",
    exactVideoCopy: sameVideo
  };
  if (!Object.values(checks).every(Boolean)) throw new Error(`Generated file failed validation: ${JSON.stringify(checks)}`);
  return checks;
}

async function main() {
  const parsed = parseArgs(process.argv.slice(2));
  if (parsed.help) return usage();
  const probe = JSON.parse(await run("ffprobe", ["-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", parsed.inputPath]));
  const duration = Number(probe.format?.duration);
  if (!Number.isFinite(duration) || duration <= 0 || !probe.streams?.some((stream) => stream.codec_type === "video")) {
    throw new Error("Input must contain a readable video stream with a positive duration.");
  }
  const coverAt = Math.min(parsed.coverAt ?? duration / 2, duration - 0.001);
  const timestampUs = Math.round(coverAt * 1_000_000);
  const coverPath = path.join(os.tmpdir(), `android-live-photo-${process.pid}-${Date.now()}.jpg`);
  try {
    await run("ffmpeg", ["-y", "-ss", coverAt.toFixed(6), "-i", parsed.inputPath, "-frames:v", "1", "-q:v", "2", "-update", "1", coverPath]);
    const [jpeg, video] = await Promise.all([fs.readFile(coverPath), fs.readFile(parsed.inputPath)]);
    const output = compose(jpeg, video, timestampUs);
    await fs.mkdir(path.dirname(parsed.outputPath), { recursive: true });
    await fs.writeFile(parsed.outputPath, output);
    validate(output, video, timestampUs);
    console.log(`Created: ${parsed.outputPath}`);
    console.log(`Cover: ${coverAt.toFixed(3)}s of ${duration.toFixed(3)}s`);
    console.log("validation: passed");
  } finally {
    await fs.rm(coverPath, { force: true });
  }
}

main().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exitCode = 1;
});
