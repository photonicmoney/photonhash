#!/usr/bin/env node
// MIT. CPU-only OpenSSL check of the public C20 fixture, not matrix evaluation.
import assert from 'node:assert/strict';
import {createCipheriv, createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';

if (process.argv.length > 3) throw Error('Usage: node tools/check-lf3-c20-vector.mjs [vector.json]');
const file = process.argv[2] ?? new URL('../research/launch/lf3-k8-c20-experiment-1-vector.json', import.meta.url);
const vector = JSON.parse(readFileSync(file, 'utf8'));
function hex(value, size) {
  assert.equal(typeof value, 'string');
  assert.match(value, /^(?:[0-9a-f]{2})*$/);
  const bytes = Buffer.from(value, 'hex');
  if (size !== undefined) assert.equal(bytes.length, size);
  return bytes;
}
const shake = bytes => createHash('shake256', {outputLength:32}).update(bytes).digest();
function stream(key, nonce, length) {
  // Raw OpenSSL IV: 64-bit counter + 64-bit nonce. For this bounded stream,
  // these bytes give the exact RFC state words: counter 1, 96-bit nonce,
  // no carry out of the low 32-bit counter over blocks 1..32.
  const iv = Buffer.alloc(16);
  iv.writeUInt32LE(1);
  nonce.copy(iv, 4);
  const cipher = createCipheriv('chacha20', key, iv);
  return Buffer.concat([cipher.update(Buffer.alloc(length)), cipher.final()]);
}
const rfcKey = Buffer.from(Array.from({length:32}, (_, i) => i));
assert.equal(stream(rfcKey, hex('000000090000004a00000000',12),64).toString('hex'),
  '10f1e7e4d13b5915500fdd1fa32071c4c7d1f4c733c068030422aa9ac3d46c4e' +
  'd2826446079faa0914c2d705d98b02a2b5129cd1de164eb9cbd083e8a2503c4e');
assert.equal(vector.profile, 'LF3-K8-C20-experiment.1');
assert.equal(hex(vector.parent_hex,32).toString('hex'), '00'.repeat(32));
assert.match(vector.nonce_decimal, /^(0|[1-9][0-9]*)$/);
const nonce = BigInt(vector.nonce_decimal);
assert(nonce <= 0xffffffffffffffffn);
const nonceBytes = Buffer.alloc(8);
nonceBytes.writeBigUInt64LE(nonce);
const h = shake(Buffer.concat([
  Buffer.from('LASER/PhotonHash/LF3-K8-C20-experiment.1/vector'),
  hex(vector.header_hex), nonceBytes,
]));
assert.deepEqual(hex(vector.h_in,32), h);
const packed = stream(h,Buffer.alloc(12),2048);
const x = Buffer.alloc(4096);
for (let t = 0; t < packed.length; t++) {
  x[2*t] = ((packed[t] & 15) - 8) & 255;
  x[2*t+1] = ((packed[t] >> 4) - 8) & 255;
}
assert.deepEqual(hex(vector.signed_x_digest,32), shake(x));
const frozen = readFileSync(new URL('../docs/v0.4-shadow-vectors.txt',import.meta.url),'utf8');
const commitment = /^case\[0\]\.bank_commitment=([0-9a-f]{64})$/m.exec(frozen);
assert(commitment);
assert.equal(vector.bank_commitment, commitment[1]);
const digest = shake(Buffer.concat([
  Buffer.from('LASER/PhotonHash/LF3-K8-C20-experiment.1/final'),h,hex(vector.folded,2048),
]));
assert.deepEqual(hex(vector.digest,32),digest);
console.log(JSON.stringify({passed:true,profile:vector.profile,rfc8439Primitive:true,
  binding:true,expansion:true,finalHash:true,fullMatrixRecomputed:false,
  performanceMeasured:false}));
