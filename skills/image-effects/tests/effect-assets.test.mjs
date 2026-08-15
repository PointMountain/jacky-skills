import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { parseEffect } from '../scripts/effect-library.mjs';

const SKILL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EFFECT_CARD_PATH = path.join(
  SKILL_ROOT,
  'references/effects/healing-anime-scribble-v3.md',
);
const PREVIEW_PATH = path.join(
  SKILL_ROOT,
  'assets/previews/healing-anime-scribble-v3.jpg',
);
const PREVIEW_SHA256 = '70a3c534832532faed62cb80816df56002382cb661b51d2077d7eab429760daf';

const EXPECTED_EFFECT = {
  ref: 'healing-anime-scribble-v3@1.0.0',
  id: 'healing-anime-scribble-v3',
  version: '1.0.0',
  title: {
    en: 'Healing Anime Scribble',
    zh: '治愈系潦草淡彩',
  },
  summary: {
    en: 'Redraw one portrait as an airy anime construction sketch with dense searching lines, sparse pale color, and quiet warm paper.',
    zh: '将一张人物照片重绘为留白通透的动漫结构草图，以密集探索线条、稀薄淡彩和暖白纸张为核心。',
  },
  category: 'portrait',
  executionKind: 'host-image-generation',
  input: { mode: 'image', min: 1, max: 1, formats: ['jpeg', 'png'] },
  outputCount: 1,
  preview: 'assets/previews/healing-anime-scribble-v3.jpg',
  sourceRepository: 'ConardLi/garden-skills',
  sourceRevision: 'aaf9a82f5efd73e87cc0998edc398e75bfc35901',
  sources: [
    {
      path: 'skills/gpt-image-2/references/avatars-and-profile/style-transfer-selfie.md',
      sha256: '67021faabdbd9e5d5db6851eb2e5bc6a650a76ef399a4f0949fdae0f93989461',
    },
  ],
  sourceLicense: {
    spdx: 'MIT',
    url: 'https://github.com/ConardLi/garden-skills/blob/aaf9a82f5efd73e87cc0998edc398e75bfc35901/LICENSE',
  },
  adaptationNotice:
    'Preserves the one-photo anime construction sketch behavior and adds fixed v3 ratios, host-neutral delivery, privacy gates, and one targeted retry.',
  previewProvenance: {
    origin:
      'Text-only image generation of a fictional young adult with glasses, not based on a real person.',
    author: 'wangjs-jacky',
    licenseSpdx: 'CC-BY-4.0',
    sha256: PREVIEW_SHA256,
  },
};

const EXPECTED_SECTIONS = [
  '适用场景',
  '输入契约',
  '视觉编译规则',
  '硬性禁止项',
  '质量检查',
  '交付要求',
];

async function loadImageTools() {
  return import('../scripts/image-metadata.mjs');
}

async function loadSharp() {
  return (await import('sharp')).default;
}

function jpegSegment(marker, payload) {
  const body = Buffer.from(payload);
  const segment = Buffer.alloc(4 + body.length);
  segment[0] = 0xff;
  segment[1] = marker;
  segment.writeUInt16BE(body.length + 2, 2);
  body.copy(segment, 4);
  return segment;
}

function injectJpegSegment(buffer, marker, payload) {
  assert.equal(buffer.readUInt16BE(0), 0xffd8);
  return Buffer.concat([buffer.subarray(0, 2), jpegSegment(marker, payload), buffer.subarray(2)]);
}

const CRC32_TABLE = Array.from({ length: 256 }, (_, value) => {
  let crc = value;
  for (let bit = 0; bit < 8; bit += 1) {
    crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
  }
  return crc >>> 0;
});

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc = CRC32_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type, payload) {
  const typeBuffer = Buffer.from(type, 'ascii');
  const data = Buffer.from(payload);
  const chunk = Buffer.alloc(12 + data.length);
  chunk.writeUInt32BE(data.length, 0);
  typeBuffer.copy(chunk, 4);
  data.copy(chunk, 8);
  chunk.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 8 + data.length);
  return chunk;
}

function injectPngChunk(buffer, type, payload) {
  let offset = 8;
  while (offset + 12 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const chunkType = buffer.toString('ascii', offset + 4, offset + 8);
    if (chunkType === 'IEND') {
      return Buffer.concat([buffer.subarray(0, offset), pngChunk(type, payload), buffer.subarray(offset)]);
    }
    offset += 12 + length;
  }
  throw new Error('Fixture PNG is missing IEND');
}

function corruptPngChunkCrc(buffer, targetType) {
  let offset = 8;
  while (offset + 12 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.toString('ascii', offset + 4, offset + 8);
    if (type === targetType) {
      const corrupted = Buffer.from(buffer);
      corrupted[offset + 8 + length] ^= 0x01;
      return corrupted;
    }
    offset += 12 + length;
  }
  throw new Error(`Fixture PNG is missing ${targetType}`);
}

async function createFixtures(directory) {
  const sharp = await loadSharp();
  const input = {
    create: {
      width: 7,
      height: 5,
      channels: 3,
      background: { r: 214, g: 180, b: 140 },
    },
  };
  const jpegPath = path.join(directory, 'clean.jpg');
  const pngPath = path.join(directory, 'clean.png');

  await sharp(input).jpeg({ quality: 90 }).toFile(jpegPath);
  await sharp(input).png().toFile(pngPath);

  return {
    jpeg: await readFile(jpegPath),
    png: await readFile(pngPath),
  };
}

test('效果卡严格解析全部 frontmatter 并包含固定六节正文', async () => {
  const markdown = await readFile(EFFECT_CARD_PATH, 'utf8');
  const effect = parseEffect(markdown, EFFECT_CARD_PATH);
  const { body, filePath, ...parsed } = effect;

  assert.equal(filePath, EFFECT_CARD_PATH);
  assert.deepEqual(parsed, EXPECTED_EFFECT);
  assert.deepEqual(
    [...body.matchAll(/^## (.+)$/gm)].map((match) => match[1]),
    EXPECTED_SECTIONS,
  );
});

test('真实编码的干净 JPEG 和 PNG 可完整解码并通过元数据检查', async () => {
  const directory = await mkdtemp(path.join(tmpdir(), 'image-effects-media-'));
  try {
    const { inspectImage, assertMetadataFreeImage } = await loadImageTools();
    const fixtures = await createFixtures(directory);

    assert.deepEqual(await inspectImage(fixtures.jpeg, 'jpeg'), {
      format: 'jpeg',
      width: 7,
      height: 5,
    });
    assert.deepEqual(await assertMetadataFreeImage(fixtures.png, 'png'), {
      format: 'png',
      width: 7,
      height: 5,
    });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('JPEG 拒绝 EXIF、XMP、COM、GPS 和设备文本元数据', async (t) => {
  const directory = await mkdtemp(path.join(tmpdir(), 'image-effects-jpeg-metadata-'));
  try {
    const { assertMetadataFreeImage } = await loadImageTools();
    const { jpeg } = await createFixtures(directory);
    const samples = [
      ['EXIF', 0xe1, Buffer.from('Exif\0\0II*\0', 'binary')],
      [
        'XMP',
        0xe1,
        Buffer.from('http://ns.adobe.com/xap/1.0/\0<x:xmpmeta>private</x:xmpmeta>'),
      ],
      ['COM', 0xfe, Buffer.from('private comment')],
      ['GPS', 0xed, Buffer.from('GPSLatitude=31.2304;GPSLongitude=121.4737')],
      ['设备文本', 0xed, Buffer.from('Make=Example;Model=Camera Device')],
    ];

    for (const [name, marker, payload] of samples) {
      await t.test(name, async () => {
        await assert.rejects(
          () => assertMetadataFreeImage(injectJpegSegment(jpeg, marker, payload), 'jpeg'),
          /metadata|EXIF|XMP|comment|GPS|device/i,
        );
      });
    }
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('JPEG 拒绝 EOI 后追加的 COM 段和任意尾随字节', async (t) => {
  const directory = await mkdtemp(path.join(tmpdir(), 'image-effects-jpeg-trailing-'));
  try {
    const { assertMetadataFreeImage } = await loadImageTools();
    const { jpeg } = await createFixtures(directory);
    const samples = [
      ['COM 段', jpegSegment(0xfe, Buffer.from('private trailing comment'))],
      ['任意字节', Buffer.from([0xde, 0xad, 0xbe, 0xef])],
    ];

    for (const [name, suffix] of samples) {
      await t.test(name, async () => {
        await assert.rejects(
          () => assertMetadataFreeImage(Buffer.concat([jpeg, suffix]), 'jpeg'),
          /JPEG structure|trailing|EOI/i,
        );
      });
    }
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('PNG 拒绝 eXIf、tEXt、zTXt 和 iTXt 元数据块', async (t) => {
  const directory = await mkdtemp(path.join(tmpdir(), 'image-effects-png-metadata-'));
  try {
    const { assertMetadataFreeImage } = await loadImageTools();
    const { png } = await createFixtures(directory);
    const samples = [
      ['eXIf', Buffer.from('II*\0Exif')],
      ['tEXt', Buffer.from('Comment\0private')],
      ['zTXt', Buffer.from('Comment\0\0compressed')],
      ['iTXt', Buffer.from('Description\0\0\0\0\0private')],
    ];

    for (const [type, payload] of samples) {
      await t.test(type, async () => {
        await assert.rejects(
          () => assertMetadataFreeImage(injectPngChunk(png, type, payload), 'png'),
          new RegExp(`metadata|${type}`, 'i'),
        );
      });
    }
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('PNG 拒绝 ancillary chunk 和 IEND 的损坏 CRC', async (t) => {
  const directory = await mkdtemp(path.join(tmpdir(), 'image-effects-png-crc-'));
  try {
    const { assertMetadataFreeImage } = await loadImageTools();
    const { png } = await createFixtures(directory);
    const withAncillary = injectPngChunk(
      png,
      'pHYs',
      Buffer.from([0, 0, 0x0e, 0xc4, 0, 0, 0x0e, 0xc4, 1]),
    );
    const samples = [
      ['ancillary pHYs', corruptPngChunkCrc(withAncillary, 'pHYs')],
      ['IEND', corruptPngChunkCrc(png, 'IEND')],
    ];

    for (const [name, sample] of samples) {
      await t.test(name, async () => {
        await assert.rejects(
          () => assertMetadataFreeImage(sample, 'png'),
          /PNG structure|CRC/i,
        );
      });
    }
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('图像检查拒绝未知格式和未完成像素解码的损坏图片', async () => {
  const directory = await mkdtemp(path.join(tmpdir(), 'image-effects-decode-'));
  try {
    const { inspectImage } = await loadImageTools();
    const { jpeg } = await createFixtures(directory);

    await assert.rejects(() => inspectImage(jpeg, 'webp'), /unsupported.*format/i);
    await assert.rejects(() => inspectImage(jpeg.subarray(0, jpeg.length - 24), 'jpeg'));
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('授权预览具有固定 SHA、尺寸且不含被禁止的元数据', async () => {
  const sharp = await loadSharp();
  const { assertMetadataFreeImage } = await loadImageTools();
  const buffer = await readFile(PREVIEW_PATH);

  assert.equal(createHash('sha256').update(buffer).digest('hex'), PREVIEW_SHA256);
  assert.deepEqual(await assertMetadataFreeImage(buffer, 'jpeg'), {
    format: 'jpeg',
    width: 1448,
    height: 1086,
  });
  const { info } = await sharp(buffer, { failOn: 'error' }).raw().toBuffer({ resolveWithObject: true });
  assert.equal(info.width, 1448);
  assert.equal(info.height, 1086);
});
