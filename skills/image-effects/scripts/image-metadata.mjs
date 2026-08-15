import sharp from 'sharp';

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const FORBIDDEN_PNG_CHUNKS = new Set(['eXIf', 'tEXt', 'zTXt', 'iTXt']);
const MAX_INPUT_PIXELS = 20_000_000;
const CRC32_TABLE = Uint32Array.from({ length: 256 }, (_, value) => {
  let crc = value;
  for (let bit = 0; bit < 8; bit += 1) {
    crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
  }
  return crc >>> 0;
});

function normalizeFormat(format) {
  if (typeof format !== 'string') throw new TypeError('Image format must be jpeg or png');
  const normalized = format.toLowerCase();
  if (normalized !== 'jpeg' && normalized !== 'png') {
    throw new Error(`Unsupported image format: ${format}`);
  }
  return normalized;
}

function assertBuffer(buffer) {
  if (!Buffer.isBuffer(buffer) || buffer.length === 0) {
    throw new TypeError('Image input must be a non-empty Buffer');
  }
}

function assertMatchingSignature(buffer, format) {
  const matches =
    format === 'jpeg'
      ? buffer.length >= 2 && buffer[0] === 0xff && buffer[1] === 0xd8
      : buffer.length >= PNG_SIGNATURE.length &&
        buffer.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE);
  if (!matches) throw new Error(`Image bytes do not match declared ${format} format`);
}

function jpegSegments(buffer) {
  const segments = [];
  let offset = 2;
  let inScan = false;
  let sawScan = false;

  while (offset < buffer.length) {
    if (buffer[offset] !== 0xff) {
      if (inScan) {
        offset += 1;
        continue;
      }
      throw new Error('Invalid JPEG structure: expected marker');
    }

    while (offset < buffer.length && buffer[offset] === 0xff) offset += 1;
    if (offset >= buffer.length) throw new Error('Invalid JPEG structure: truncated marker');

    const marker = buffer[offset];
    offset += 1;

    if (marker === 0x00) {
      if (!inScan) throw new Error('Invalid JPEG structure: stuffed byte outside scan');
      continue;
    }
    if (marker >= 0xd0 && marker <= 0xd7) {
      if (!inScan) throw new Error('Invalid JPEG structure: restart marker outside scan');
      continue;
    }
    if (marker === 0xd9) {
      if (!sawScan) throw new Error('Invalid JPEG structure: EOI before SOS');
      if (offset !== buffer.length) {
        throw new Error('Invalid JPEG structure: trailing bytes after EOI');
      }
      return segments;
    }
    if (marker === 0xd8) throw new Error('Invalid JPEG structure: duplicate SOI marker');
    if (marker === 0x01) continue;

    inScan = false;
    if (offset + 2 > buffer.length) throw new Error('Invalid JPEG structure: truncated length');

    const length = buffer.readUInt16BE(offset);
    if (length < 2 || offset + length > buffer.length) {
      throw new Error('Invalid JPEG structure: invalid segment length');
    }

    const payload = buffer.subarray(offset + 2, offset + length);
    segments.push({ marker, payload });
    offset += length;
    if (marker === 0xda) {
      sawScan = true;
      inScan = true;
    }
  }

  throw new Error('Invalid JPEG structure: missing end marker');
}

function hasPrefix(payload, prefix) {
  return payload.length >= prefix.length && payload.subarray(0, prefix.length).equals(prefix);
}

function assertValidJfif(payload) {
  if (!hasPrefix(payload, Buffer.from('JFIF\0', 'binary')) || payload.length < 14) {
    throw new Error('JPEG APP0 must contain a structurally valid JFIF segment');
  }
  const units = payload[7];
  const width = payload[12];
  const height = payload[13];
  const expectedLength = 14 + 3 * width * height;
  if (
    payload[5] !== 1 ||
    payload[6] > 2 ||
    units > 2 ||
    payload.readUInt16BE(8) === 0 ||
    payload.readUInt16BE(10) === 0 ||
    payload.length !== expectedLength
  ) {
    throw new Error('JPEG APP0 contains an invalid JFIF structure');
  }
}

function assertValidJfxx(payload) {
  if (!hasPrefix(payload, Buffer.from('JFXX\0', 'binary')) || payload.length < 6) {
    throw new Error('JPEG APP0 must contain a structurally valid JFXX segment');
  }

  const extensionCode = payload[5];
  if (extensionCode === 0x10) {
    if (
      payload.length < 10 ||
      payload.readUInt16BE(6) !== 0xffd8 ||
      payload.readUInt16BE(payload.length - 2) !== 0xffd9
    ) {
      throw new Error('JPEG APP0 contains an invalid JFXX JPEG thumbnail');
    }
    return;
  }

  if ((extensionCode === 0x11 || extensionCode === 0x13) && payload.length >= 8) {
    const width = payload[6];
    const height = payload[7];
    const expectedLength =
      extensionCode === 0x11 ? 8 + 768 + width * height : 8 + 3 * width * height;
    if (payload.length === expectedLength) return;
  }
  throw new Error('JPEG APP0 contains an invalid JFXX structure');
}

function assertAllowedAppSegment(marker, payload) {
  if (marker === 0xe0) {
    if (hasPrefix(payload, Buffer.from('JFIF\0', 'binary'))) assertValidJfif(payload);
    else if (hasPrefix(payload, Buffer.from('JFXX\0', 'binary'))) assertValidJfxx(payload);
    else throw new Error('JPEG APP0 metadata is not an allowed JFIF or JFXX segment');
    return;
  }

  if (marker === 0xee) {
    if (
      payload.length !== 12 ||
      !hasPrefix(payload, Buffer.from('Adobe', 'ascii')) ||
      payload.readUInt16BE(5) !== 100 ||
      payload[11] > 2
    ) {
      throw new Error('JPEG APP14 metadata is not a structurally valid Adobe segment');
    }
    return;
  }

  throw new Error(`JPEG APP${marker - 0xe0} metadata is not allowed`);
}

function assertMetadataFreeJpeg(buffer) {
  for (const { marker, payload } of jpegSegments(buffer)) {
    if (marker === 0xfe) throw new Error('JPEG comment metadata is not allowed');
    if (marker < 0xe0 || marker > 0xef) continue;
    assertAllowedAppSegment(marker, payload);
  }
}

function pngChunkCrc(buffer, start, end) {
  let crc = 0xffffffff;
  for (let offset = start; offset < end; offset += 1) {
    crc = CRC32_TABLE[(crc ^ buffer[offset]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunkTypes(buffer) {
  const types = [];
  let offset = PNG_SIGNATURE.length;
  let chunkIndex = 0;
  let sawIhdr = false;
  let sawIdat = false;
  let endedIdatRun = false;
  let sawIend = false;

  while (offset < buffer.length) {
    if (offset + 12 > buffer.length) throw new Error('Invalid PNG structure: truncated chunk');
    const length = buffer.readUInt32BE(offset);
    const end = offset + 12 + length;
    if (end > buffer.length) throw new Error('Invalid PNG structure: invalid chunk length');

    const type = buffer.toString('ascii', offset + 4, offset + 8);
    if (!/^[A-Za-z]{4}$/.test(type)) throw new Error('Invalid PNG structure: invalid chunk type');
    if (!/[A-Z]/.test(type[2])) {
      throw new Error(`Invalid PNG structure: reserved bit is set in ${type}`);
    }
    const storedCrc = buffer.readUInt32BE(offset + 8 + length);
    const computedCrc = pngChunkCrc(buffer, offset + 4, offset + 8 + length);
    if (storedCrc !== computedCrc) {
      throw new Error(`Invalid PNG structure: CRC mismatch in ${type}`);
    }

    if (type === 'IHDR') {
      if (chunkIndex !== 0 || sawIhdr || length !== 13) {
        throw new Error('Invalid PNG structure: IHDR must be the unique first 13-byte chunk');
      }
      sawIhdr = true;
    } else if (!sawIhdr) {
      throw new Error('Invalid PNG structure: IHDR must be the first chunk');
    }

    if (type === 'IDAT') {
      if (endedIdatRun) throw new Error('Invalid PNG structure: IDAT chunks must be consecutive');
      sawIdat = true;
    } else if (sawIdat && type !== 'IEND') {
      endedIdatRun = true;
    }

    if (type === 'IEND') {
      if (sawIend || length !== 0 || !sawIdat) {
        throw new Error('Invalid PNG structure: IEND must be unique and empty after IDAT');
      }
      sawIend = true;
    }

    types.push(type);
    offset = end;
    chunkIndex += 1;

    if (type === 'IEND') {
      break;
    }
  }

  if (!sawIhdr || !sawIdat || !sawIend || offset !== buffer.length) {
    throw new Error('Invalid PNG structure: IHDR, IDAT, and final IEND are required');
  }
  return types;
}

function assertMetadataFreePng(buffer) {
  for (const type of pngChunkTypes(buffer)) {
    if (FORBIDDEN_PNG_CHUNKS.has(type)) {
      throw new Error(`PNG ${type} metadata is not allowed`);
    }
  }
}

export async function inspectImage(buffer, format) {
  assertBuffer(buffer);
  const normalizedFormat = normalizeFormat(format);
  assertMatchingSignature(buffer, normalizedFormat);

  const { info } = await sharp(buffer, {
    failOn: 'warning',
    limitInputPixels: MAX_INPUT_PIXELS,
  })
    .raw()
    .toBuffer({ resolveWithObject: true });
  if (
    !Number.isInteger(info.width) ||
    info.width <= 0 ||
    !Number.isInteger(info.height) ||
    info.height <= 0
  ) {
    throw new Error('Decoded image has invalid dimensions');
  }

  return {
    format: normalizedFormat,
    width: info.width,
    height: info.height,
  };
}

export async function assertMetadataFreeImage(buffer, format) {
  const image = await inspectImage(buffer, format);
  if (image.format === 'jpeg') assertMetadataFreeJpeg(buffer);
  else assertMetadataFreePng(buffer);
  return image;
}
