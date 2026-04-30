#!/usr/bin/env node

/**
 * 图片生成辅助脚本
 *
 * 用法：
 *   node generate-image.mjs --prompt "描述文字" --output ./out/cover.jpg --width 1792 --height 1024 --seed 42
 *   node generate-image.mjs --prompt "描述文字" --output ./out/s1.jpg --provider openai
 *
 * 支持：
 *   - Pollinations.ai（默认，免费无 Key）
 *   - OpenAI DALL-E 3（需 OPENAI_API_KEY）
 *   - 自动重试（最多 3 次）
 *   - 文件验证（大小 + 格式检查）
 *   - 兼容 Node.js 14+
 */

const { writeFileSync, mkdirSync, existsSync } = require("fs");
const { dirname } = require("path");
const https = require("https");
const http = require("http");

// ── 参数解析 ──────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    prompt: "",
    output: "",
    width: 1024,
    height: 1024,
    seed: 42,
    provider: "pollinations",
    retries: 3,
    timeout: 60,
    model: "flux",
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--prompt": opts.prompt = args[++i]; break;
      case "--output": opts.output = args[++i]; break;
      case "--width": opts.width = parseInt(args[++i], 10); break;
      case "--height": opts.height = parseInt(args[++i], 10); break;
      case "--seed": opts.seed = parseInt(args[++i], 10); break;
      case "--provider": opts.provider = args[++i]; break;
      case "--retries": opts.retries = parseInt(args[++i], 10); break;
      case "--timeout": opts.timeout = parseInt(args[++i], 10); break;
      case "--model": opts.model = args[++i]; break;
    }
  }

  if (!opts.prompt || !opts.output) {
    console.error("❌ 缺少必要参数 --prompt 或 --output");
    process.exit(1);
  }

  return opts;
}

// ── HTTP 请求（兼容 Node 14）────────────────────

function httpGet(url, timeoutSec) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith("https") ? https : http;
    const req = client.get(url, { timeout: timeoutSec * 1000 }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) });
      });
    });

    req.on("timeout", () => { req.destroy(); reject(new Error("请求超时")); });
    req.on("error", reject);
  });
}

function httpPost(url, body, headers, timeoutSec) {
  return new Promise((resolve, reject) => {
    const urlObj = new (require("url").URL)(url);
    const client = urlObj.protocol === "https:" ? https : http;
    const opts = {
      hostname: urlObj.hostname,
      port: urlObj.port || (urlObj.protocol === "https:" ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      method: "POST",
      headers: { ...headers, "Content-Length": Buffer.byteLength(body) },
      timeout: timeoutSec * 1000,
    };

    const req = client.request(opts, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) });
      });
    });

    req.on("timeout", () => { req.destroy(); reject(new Error("请求超时")); });
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

// ── 文件验证 ──────────────────────────────────────

function isValidImage(buffer) {
  if (buffer.length < 10240) return false; // < 10KB
  // JPEG: FF D8
  if (buffer[0] === 0xff && buffer[1] === 0xd8) return true;
  // PNG: 89 50 4E 47
  if (buffer[0] === 0x89 && buffer[1] === 0x50) return true;
  // WebP: 52 49 46 46
  if (buffer[0] === 0x52 && buffer[1] === 0x49) return true;
  return false;
}

// ── Pollinations.ai 生成 ──────────────────────────

async function generatePollinations(opts) {
  const encoded = encodeURIComponent(opts.prompt);
  const url = `https://image.pollinations.ai/prompt/${encoded}?width=${opts.width}&height=${opts.height}&nologo=true&seed=${opts.seed}&model=${opts.model}`;

  for (let attempt = 1; attempt <= opts.retries; attempt++) {
    try {
      const res = await httpGet(url, opts.timeout);

      if (res.status !== 200) {
        console.warn(`⚠️  HTTP ${res.status}，重试 ${attempt}/${opts.retries}`);
        continue;
      }

      if (!isValidImage(res.body)) {
        console.warn(`⚠️  响应不是有效图片 (${res.body.length} bytes)，重试 ${attempt}/${opts.retries}`);
        continue;
      }

      ensureDir(opts.output);
      writeFileSync(opts.output, res.body);
      console.log(`✅ 图片已保存: ${opts.output} (${(res.body.length / 1024).toFixed(0)}KB)`);
      return true;
    } catch (err) {
      console.warn(`⚠️  ${err.message}，重试 ${attempt}/${opts.retries}`);
    }
  }

  console.error(`❌ 生成失败（已重试 ${opts.retries} 次）: ${opts.output}`);
  return false;
}

// ── OpenAI DALL-E 3 生成 ─────────────────────────

async function generateOpenAI(opts) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.error("❌ 缺少 OPENAI_API_KEY 环境变量");
    return false;
  }

  const validSizes = ["1024x1024", "1792x1024", "1024x1792"];
  const size = validSizes.includes(`${opts.width}x${opts.height}`)
    ? `${opts.width}x${opts.height}`
    : "1024x1024";

  for (let attempt = 1; attempt <= opts.retries; attempt++) {
    try {
      const body = JSON.stringify({
        model: "dall-e-3",
        prompt: opts.prompt,
        n: 1,
        size,
        quality: "standard",
      });

      const res = await httpPost(
        "https://api.openai.com/v1/images/generations",
        body,
        { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
        opts.timeout
      );

      const data = JSON.parse(res.body.toString());

      if (res.status !== 200 || !data.data?.[0]?.url) {
        console.warn(`⚠️  API 错误: ${data.error?.message || "未知"}, 重试 ${attempt}/${opts.retries}`);
        continue;
      }

      // 下载图片
      const imgRes = await httpGet(data.data[0].url, opts.timeout);
      ensureDir(opts.output);
      writeFileSync(opts.output, imgRes.body);
      console.log(`✅ 图片已保存: ${opts.output} (${(imgRes.body.length / 1024).toFixed(0)}KB)`);
      return true;
    } catch (err) {
      console.warn(`⚠️  ${err.message}，重试 ${attempt}/${opts.retries}`);
    }
  }

  console.error(`❌ 生成失败（已重试 ${opts.retries} 次）: ${opts.output}`);
  return false;
}

// ── 工具函数 ──────────────────────────────────────

function ensureDir(filePath) {
  const dir = dirname(filePath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

// ── 主入口 ────────────────────────────────────────

async function main() {
  const opts = parseArgs();
  console.log(`🎨 生成图片 [${opts.provider}]: "${opts.prompt.slice(0, 60)}..."`);

  const success =
    opts.provider === "openai"
      ? await generateOpenAI(opts)
      : await generatePollinations(opts);

  process.exit(success ? 0 : 1);
}

main();
