import sharp from 'sharp';

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const FORBIDDEN_PNG_CHUNKS = new Set(['eXIf', 'tEXt', 'zTXt', 'iTXt']);
const JPEG_METADATA_TEXT = /(?:exif\0\0|xmp|xap\/1\.0|gps|(?:make|model|device|camera|software|artist|copyright)\s*[=:])/i;

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
    if (marker === 0xd9) return segments;
    if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) {
      continue;
    }
    if (offset + 2 > buffer.length) throw new Error('Invalid JPEG structure: truncated length');

    const length = buffer.readUInt16BE(offset);
    if (length < 2 || offset + length > buffer.length) {
      throw new Error('Invalid JPEG structure: invalid segment length');
    }

    const payload = buffer.subarray(offset + 2, offset + length);
    segments.push({ marker, payload });
    offset += length;
    inScan = marker === 0xda;
  }

  throw new Error('Invalid JPEG structure: missing end marker');
}

function assertMetadataFreeJpeg(buffer) {
  for (const { marker, payload } of jpegSegments(buffer)) {
    if (marker === 0xfe) throw new Error('JPEG comment metadata is not allowed');
    if (marker < 0xe0 || marker > 0xef) continue;

    const text = payload.toString('latin1');
    if (JPEG_METADATA_TEXT.test(text)) {
      throw new Error('JPEG EXIF, XMP, GPS, or device metadata is not allowed');
    }
  }
}

function pngChunkTypes(buffer) {
  const types = [];
  let offset = PNG_SIGNATURE.length;
  let sawIend = false;

  while (offset < buffer.length) {
    if (offset + 12 > buffer.length) throw new Error('Invalid PNG structure: truncated chunk');
    const length = buffer.readUInt32BE(offset);
    const end = offset + 12 + length;
    if (end > buffer.length) throw new Error('Invalid PNG structure: invalid chunk length');

    const type = buffer.toString('ascii', offset + 4, offset + 8);
    if (!/^[A-Za-z]{4}$/.test(type)) throw new Error('Invalid PNG structure: invalid chunk type');
    types.push(type);
    offset = end;

    if (type === 'IEND') {
      sawIend = true;
      break;
    }
  }

  if (!sawIend || offset !== buffer.length) {
    throw new Error('Invalid PNG structure: missing final IEND chunk');
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

  const { info } = await sharp(buffer, { failOn: 'error' })
    .raw()
    .toBuffer({ resolveWithObject: true });
  if (!Number.isInteger(info.width) || info.width <= 0 || !Number.isInteger(info.height) || info.height <= 0) {
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
