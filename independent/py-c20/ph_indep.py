"""Independent PhotonHash LF2-K8 / LF3-K8-C20 evaluator, written from the public specs only.
ChaCha20 is implemented here from RFC 8439 (no OpenSSL). Matrix products use float32 BLAS,
which is exact here: every product and every partial sum is an integer with |v| <= 262144 < 2^24."""
import hashlib, json, struct, sys, time
import numpy as np

N, K = 4096, 8
shake = lambda b, n: hashlib.shake_256(b).digest(n)

def nibbles(packed):  # low nibble first, u - 8
    a = np.frombuffer(packed, dtype=np.uint8)
    out = np.empty(a.size * 2, dtype=np.int8)
    out[0::2] = (a & 15).astype(np.int8) - 8
    out[1::2] = (a >> 4).astype(np.int8) - 8
    return out

def bank(parent):
    mats, sums = [], []
    for j in range(K):
        pj = parent if j == 0 else shake(b"LASER/PhotonHash/launch-LF2/matrix" + parent + struct.pack("<I", j), 32)
        seed = shake(b"LASER/PhotonHash/v1/matrix" + pj, 64)
        packed = shake(seed, N * N // 2)
        sums.append(shake(packed, 32).hex())
        mats.append(nibbles(packed).reshape(N, N).astype(np.float32))
    return mats, sums

def rotl(v, c): return ((v << c) & 0xffffffff) | (v >> (32 - c))
def qr(s, a, b, c, d):
    s[a] = (s[a] + s[b]) & 0xffffffff; s[d] = rotl(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & 0xffffffff; s[b] = rotl(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & 0xffffffff; s[d] = rotl(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & 0xffffffff; s[b] = rotl(s[b] ^ s[c], 7)
def chacha_block(key, counter, nonce12):
    init = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574] + list(struct.unpack("<8I", key)) \
        + [counter] + list(struct.unpack("<3I", nonce12))
    s = init[:]
    for _ in range(10):
        qr(s, 0, 4, 8, 12); qr(s, 1, 5, 9, 13); qr(s, 2, 6, 10, 14); qr(s, 3, 7, 11, 15)
        qr(s, 0, 5, 10, 15); qr(s, 1, 6, 11, 12); qr(s, 2, 7, 8, 13); qr(s, 3, 4, 9, 14)
    return struct.pack("<16I", *[(x + y) & 0xffffffff for x, y in zip(s, init)])

# RFC 8439 section 2.3.2 block test vector
assert chacha_block(bytes(range(32)), 1, bytes.fromhex("000000090000004a00000000")).hex() == (
    "10f1e7e4d13b5915500fdd1fa32071c4c7d1f4c733c068030422aa9ac3d46c4e"
    "d2826446079faa0914c2d705d98b02a2b5129cd1de164eb9cbd083e8a2503c4e")

def vector(profile, header, nonce):
    if profile == "LF2":
        h = shake(b"LASER/PhotonHash/v1/vector" + header + struct.pack("<Q", nonce), 32)
        return h, nibbles(shake(h, 2048))
    h = shake(b"LASER/PhotonHash/LF3-K8-C20-experiment.1/vector" + header + struct.pack("<Q", nonce), 32)
    s = b"".join(chacha_block(h, c, bytes(12)) for c in range(1, 33))
    return h, nibbles(s)

def evaluate(profile, mats, header, nonce, keep=False):
    h, x = vector(profile, header, nonce)
    xf = x.astype(np.float32)
    z = np.zeros(N, dtype=np.uint8); qs = []
    for M in mats:
        y = (M @ xf).astype(np.int64)
        assert np.abs(y).max() <= 262144
        q = (((y + 262144) & 0xffffffff) >> 9 & 15).astype(np.uint8)
        if keep: qs.append(q)
        z ^= q
    F = (z[0::2] | (z[1::2] << 4)).astype(np.uint8).tobytes()
    tag = b"LASER/PhotonHash/launch-LF2/final" if profile == "LF2" else b"LASER/PhotonHash/LF3-K8-C20-experiment.1/final"
    D = shake(tag + h + F, 32)
    return h, x, F, D, qs

if __name__ == "__main__":
    repo = sys.argv[1]
    out = {}
    # 1) LF2 frozen vector case[0], parent e3d7..., header80, nonce 0
    vec = dict(l.split("=", 1) for l in open(f"{repo}/docs/launch-profile-lf2-vectors.txt").read().split("\n") if "=" in l)
    t = time.time(); mats, sums = bank(bytes.fromhex(vec["parent"]))
    out["lf2_bank_seconds"] = round(time.time() - t, 2)
    out["lf2_matrix_checksums_match"] = all(sums[j] == vec[f"matrix[{j}].checksum"] for j in range(K))
    for c in (0, 1):
        t = time.time()
        h, x, F, D, _ = evaluate("LF2", mats, bytes.fromhex(vec[vec[f"case[{c}].header"]]), int(vec[f"case[{c}].nonce"]))
        out[f"lf2_case{c}"] = {"h": h.hex() == vec[f"case[{c}].h_in"], "folded": F.hex() == vec[f"case[{c}].folded"],
                               "digest": D.hex() == vec[f"case[{c}].digest"], "seconds": round(time.time() - t, 2)}
    del mats
    # 2) C20 fixture, zero parent
    fx = json.load(open(f"{repo}/research/launch/lf3-k8-c20-experiment-1-vector.json"))
    mats, sums = bank(bytes.fromhex(fx["parent_hex"]))
    t = time.time()
    h, x, F, D, qs = evaluate("C20", mats, bytes.fromhex(fx["header_hex"]), int(fx["nonce_decimal"]), keep=True)
    out["c20_fixture"] = {"h": h.hex() == fx["h_in"], "signed_x_digest": shake(x.astype(np.uint8).tobytes(), 32).hex() == fx["signed_x_digest"],
                          "folded_full_matrix_recompute": F.hex() == fx["folded"], "digest": D.hex() == fx["digest"],
                          "seconds": round(time.time() - t, 2)}
    # 3) Output statistics: per-pass nibble entropy and folded nibble entropy over a few nonces
    def ent(v):
        p = np.bincount(v, minlength=16) / v.size; p = p[p > 0]; return float(-(p * np.log2(p)).sum())
    hdr = bytes.fromhex(fx["header_hex"]); pass_e, fold_e, allq, allz = [], [], [], []
    for n in range(16):
        _, _, F, _, qs = evaluate("C20", mats, hdr, n, keep=True)
        allq.append(np.concatenate(qs)); fb = np.frombuffer(F, np.uint8); allz.append(np.concatenate([fb & 15, fb >> 4]))
    out["c20_stats_16_nonces"] = {"per_pass_nibble_entropy_bits": round(ent(np.concatenate(allq)), 4),
                                  "folded_nibble_entropy_bits": round(ent(np.concatenate(allz)), 4),
                                  "per_pass_nibble_histogram": np.bincount(np.concatenate(allq), minlength=16).tolist()}
    print(json.dumps(out, indent=1))
