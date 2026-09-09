#!/usr/bin/env python3
"""ART-DIRECTION 2.9's exposure contract, computed on LINEARISED luminance.

The mistake 2.9 names -- computing relative luminance on gamma-encoded values --
puts a "5% legible" threshold at linear 0.0039, which is essentially black, and
makes every measurement three times more flattering than it reads. Everything
here undoes the sRGB transfer function first.

    python lum.py shots/*.png
"""
import sys
import glob
import struct
import zlib


def read_png(path):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    pos = 8
    w = h = bitd = ct = None
    idat = b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bitd, ct = struct.unpack(">IIBB", body[:10])
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
        pos += 12 + ln
    assert bitd == 8 and ct in (2, 6), (bitd, ct)
    nch = 3 if ct == 2 else 4
    raw = zlib.decompress(idat)
    stride = w * nch
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        ft = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if ft == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 255
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                b = prev[i]
                c = prev[i - nch] if i >= nch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, nch, out


_LIN = [((v / 255.0) / 12.92) if (v / 255.0) <= 0.04045
        else (((v / 255.0) + 0.055) / 1.055) ** 2.4 for v in range(256)]


def stats(path):
    w, h, nch, px = read_png(path)
    n = w * h
    # sample every 3rd pixel in each direction: 1/9 of 2M pixels is still
    # 230k samples, which is far more than enough for a percentile
    lum = []
    for y in range(0, h, 3):
        row = y * w * nch
        for x in range(0, w, 3):
            i = row + x * nch
            lum.append(0.2126 * _LIN[px[i]] + 0.7152 * _LIN[px[i + 1]]
                       + 0.0722 * _LIN[px[i + 2]])
    lum.sort()
    m = len(lum)

    def frac_above(t):
        lo, hi = 0, m
        while lo < hi:
            mid = (lo + hi) // 2
            if lum[mid] < t:
                lo = mid + 1
            else:
                hi = mid
        return (m - lo) / m * 100.0

    return {
        "path": path, "n": n,
        "blown": frac_above(0.50),
        "mid": frac_above(0.18),
        "legible": frac_above(0.05),
        "black": 100.0 - frac_above(0.02),
        "p50": lum[m // 2], "p90": lum[int(m * 0.90)],
        "p99": lum[int(m * 0.99)], "max": lum[-1],
        "mean": sum(lum) / m,
    }


def main():
    args = sys.argv[1:] or sorted(glob.glob("shots/*.png"))
    paths = []
    for a in args:
        paths.extend(sorted(glob.glob(a)) or [a])
    print("%-42s %6s %6s %6s %6s | %7s %7s %7s" % (
        "shot", ">0.5", ">0.18", ">0.05", "<0.02", "p50", "p90", "max"))
    print("%-42s %6s %6s %6s %6s | %7s %7s %7s" % (
        "ART 2.9 target, lamp frame", "<=3%", "1-25%", "3-20%", ">=70%", "", "", ""))
    print("-" * 100)
    for p in paths:
        try:
            s = stats(p)
        except Exception as e:  # noqa: BLE001
            print("%-42s  ERROR %s" % (p, e))
            continue
        print("%-42s %5.1f%% %5.1f%% %5.1f%% %5.1f%% | %7.4f %7.4f %7.4f" % (
            p.replace("shots/", "").replace("shots\\", ""),
            s["blown"], s["mid"], s["legible"], s["black"],
            s["p50"], s["p90"], s["max"]))


if __name__ == "__main__":
    main()
