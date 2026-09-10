# Valley landform generator for the Unreal look spike.
# Emits 16-bit height PNGs and 8-bit mask PNGs that Unreal displaces a Nanite grid with.
# Numbers come from docs/THE-ICE.md 7.2. Everything else is stated in NOTES.md.
import numpy as np, json, os, math, time
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gen")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- noise
def _hash2(ix, iy, seed):
    h = (ix.astype(np.int64) * np.int64(374761393) + iy.astype(np.int64) * np.int64(668265263)
         + np.int64(seed) * np.int64(1442695040888963407))
    h = (h ^ (h >> 13)) * np.int64(1274126177)
    return h ^ (h >> 16)

def _grad(ix, iy, seed, dx, dy):
    h = _hash2(ix, iy, seed) & 7
    a = (h.astype(np.float32)) * (np.float32(2.0 * math.pi / 8.0))
    return np.cos(a) * dx + np.sin(a) * dy

def perlin(x, y, seed=0):
    x = x.astype(np.float32); y = y.astype(np.float32)
    ix = np.floor(x); iy = np.floor(y)
    fx = x - ix; fy = y - iy
    i0 = ix.astype(np.int64); j0 = iy.astype(np.int64)
    u = fx*fx*fx*(fx*(fx*6-15)+10); v = fy*fy*fy*(fy*(fy*6-15)+10)
    n00 = _grad(i0,   j0,   seed, fx,   fy)
    n10 = _grad(i0+1, j0,   seed, fx-1, fy)
    n01 = _grad(i0,   j0+1, seed, fx,   fy-1)
    n11 = _grad(i0+1, j0+1, seed, fx-1, fy-1)
    return ((n00*(1-u)+n10*u)*(1-v) + (n01*(1-u)+n11*u)*v).astype(np.float32)

def fbm(x, y, seed, octaves=8, lac=2.03, gain=0.5, freq=1.0):
    """Plain fBm. lac deliberately not exactly 2 so octaves never re-align."""
    s = np.zeros_like(x, dtype=np.float32); a = np.float32(1.0); f = np.float32(freq); norm = 0.0
    for o in range(octaves):
        s += a * perlin(x*f, y*f, seed + o*911)
        norm += a; a *= gain; f *= lac
    return s / norm

def ridged(x, y, seed, octaves=7, lac=2.07, gain=0.52, freq=1.0):
    """Ridged multifractal, weighted by the previous octave: aretes and buttresses,
    scale-invariant rather than the three fixed bands the Godot pass had."""
    s = np.zeros_like(x, dtype=np.float32); a = np.float32(1.0); f = np.float32(freq)
    w = np.ones_like(x, dtype=np.float32); norm = 0.0
    for o in range(octaves):
        n = perlin(x*f, y*f, seed + o*1777)
        n = 1.0 - np.abs(n) * 2.0
        n = np.clip(n, -1.0, 1.0); n = n*n
        s += a * n * w
        w = np.clip(n * 1.6, 0.0, 1.0)     # feedback: detail only rides on ridges
        norm += a; a *= gain; f *= lac
    return (s / norm).astype(np.float32)

def warp(x, y, seed, amp, freq):
    """Domain warp. The single fix for 'the ridge noise repeated at one period'."""
    wx = fbm(x, y, seed + 31, octaves=4, freq=freq)
    wy = fbm(x, y, seed + 97, octaves=4, freq=freq)
    return x + wx * amp, y + wy * amp

# ---------------------------------------------------------------- landform
FLOOR_HALF   = 600.0     # 1.2 km trough, THE-ICE 7.2
WALL_RUN     = 1040.0    # horizontal run of the 1800 m wall -> ~60 deg mean
WALL_H       = 1800.0
PEAK_RUN     = 2600.0
PEAK_H       = 1400.0    # above the ridge -> 3200 m peaks

def centreline(x):
    """The valley bends. A straight extrusion is the other half of 'reads as procedural'."""
    return 300.0*np.sin(x/2350.0) + 130.0*np.sin(x/830.0 + 1.3) + 55.0*np.sin(x/410.0 + 2.7)

def base_height(X, Y, seed=7):
    yc = centreline(X)
    d = np.abs(Y - yc)

    # trough half-width breathes along the valley so the two walls are never parallel
    hw = FLOOR_HALF * (1.0 + 0.22*np.sin(X/1900.0 + 0.7) + 0.10*np.sin(X/620.0))

    t = np.clip((d - hw) / WALL_RUN, 0.0, 1.0)
    ss = t*t*(3.0 - 2.0*t)
    wall = WALL_H * np.power(ss, 0.82)

    u = np.clip((d - hw - WALL_RUN) / PEAK_RUN, 0.0, 1.0)
    back = PEAK_H * (1.0 - (1.0-u)**1.9)

    h = wall + back

    # ---- floor: rising up-valley toward the glacier terminus
    floor_mask = np.clip(1.0 - (d/hw)**2, 0.0, 1.0)
    h = h + floor_mask * (X * 0.011)

    # ---- head wall: close the valley up-valley so the tile edge is never in frame
    hx = np.clip((X - 2100.0)/900.0, 0.0, 1.0)
    h = h + (hx*hx*(3-2*hx)) * (1500.0 + 500.0*fbm(X/900.0, Y/900.0, seed+404, octaves=4))

    # ---- relief mask keyed to DISTANCE FROM THE FLOOR, not to height.
    # Keying it to height was the Godot failure: the lower wall, which is the part you
    # actually see from the floor, got almost no detail. VALLEY.md 8.2.
    rr = np.clip((d - hw*0.86)/(hw*0.55), 0.0, 1.0)
    relief = rr*rr*(3.0-2.0*rr)

    # anisotropic: ranges are elongated, not a field of lumps
    wx, wy = warp(X/2400.0, Y/1350.0, seed+11, amp=0.62, freq=0.55)
    massif = fbm(wx, wy, seed+3, octaves=6, freq=1.0)
    h = h + massif * 460.0 * (0.10 + 0.90*relief)

    wx2, wy2 = warp(X/430.0, Y/430.0, seed+23, amp=0.48, freq=0.8)
    ar = ridged(wx2, wy2, seed+5, octaves=8, freq=1.0)
    h = h + (ar - 0.30) * 560.0 * relief

    wx3, wy3 = warp(X/120.0, Y/120.0, seed+41, amp=0.35, freq=1.1)
    h = h + (ridged(wx3, wy3, seed+9, octaves=6, freq=1.0) - 0.32) * 95.0 * relief

    # ---- bedding: real strata, dipping, domain-warped so it is not a corrugation
    bed = np.sin((h*0.040) + (X*0.0016) + fbm(X/700.0, Y/700.0, seed+66, octaves=3)*2.4)
    h = h + bed * 11.0 * relief

    # ---- close the tile on all four sides so its edge is never a cliff in frame
    ed = np.clip((np.maximum(np.abs(X), np.abs(Y)) - 2150.0)/620.0, 0.0, 1.0)
    ed = ed*ed*(3-2*ed)
    h = np.maximum(h, ed * (1650.0 + 700.0*fbm(X/1100.0, Y/1100.0, seed+909, octaves=5)))

    # ---- roches moutonnees and drift on the floor
    h = h + np.clip(fbm(X/210.0, Y/210.0, seed+77, octaves=4)*2.2 - 1.35, 0, 1) * 26.0 * floor_mask
    h = h + floor_mask * fbm(X/85.0, Y/85.0, seed+88, octaves=5) * 3.4
    return h.astype(np.float32)

# ---------------------------------------------------------------- hydraulic erosion
def hydraulic(h, ds, n_drops=420000, batch=42000, steps=70, seed=1,
              inertia=0.045, cap=5.2, erode_k=0.42, dep_k=0.16, evap=0.016,
              grav=10.0, radius=2, min_slope=0.0016):
    N0, N1 = h.shape
    H = h.copy()
    flow = np.zeros_like(H)
    rng = np.random.default_rng(seed)

    off = []; wts = []
    for oy in range(-radius, radius+1):
        for ox in range(-radius, radius+1):
            r = math.hypot(ox, oy)
            if r <= radius:
                off.append((ox, oy)); wts.append(1.0 - r/(radius+1e-6))
    wts = np.array(wts, dtype=np.float32); wts /= wts.sum()
    off = np.array(off, dtype=np.int64)

    def grad_at(px, py):
        x0 = np.clip(px.astype(np.int64), 0, N1-2); y0 = np.clip(py.astype(np.int64), 0, N0-2)
        fx = px - x0; fy = py - y0
        h00 = H[y0, x0]; h10 = H[y0, x0+1]; h01 = H[y0+1, x0]; h11 = H[y0+1, x0+1]
        gx = ((h10-h00)*(1-fy) + (h11-h01)*fy) / ds
        gy = ((h01-h00)*(1-fx) + (h11-h10)*fx) / ds
        hh = (h00*(1-fx)+h10*fx)*(1-fy) + (h01*(1-fx)+h11*fx)*fy
        return gx, gy, hh, x0, y0, fx, fy

    done = 0
    while done < n_drops:
        m = min(batch, n_drops-done); done += m
        px = rng.uniform(1, N1-2, m).astype(np.float32)
        py = rng.uniform(1, N0-2, m).astype(np.float32)
        dx = np.zeros(m, np.float32); dy = np.zeros(m, np.float32)
        vel = np.zeros(m, np.float32) + 1.0
        water = np.ones(m, np.float32)
        sed = np.zeros(m, np.float32)
        alive = np.ones(m, bool)

        for s in range(steps):
            gx, gy, hh, x0, y0, fx, fy = grad_at(px, py)
            dx = dx*inertia - gx*(1-inertia)
            dy = dy*inertia - gy*(1-inertia)
            L = np.sqrt(dx*dx+dy*dy) + 1e-9
            dx = dx/L; dy = dy/L
            npx = px + dx; npy = py + dy
            oob = (npx < 1) | (npx > N1-2) | (npy < 1) | (npy > N0-2)
            alive = alive & (~oob)
            if not alive.any(): break
            npx = np.clip(npx, 1, N1-2); npy = np.clip(npy, 1, N0-2)
            _, _, nh, _, _, _, _ = grad_at(npx, npy)
            dh = nh - hh

            capy = np.clip(np.maximum(-dh, min_slope) * vel * water * cap, 0.0, 24.0)
            uphill = dh > 0.0
            over = sed > capy
            drop = np.where(uphill, np.minimum(dh, sed),
                            np.where(over, (sed - capy)*dep_k, 0.0))
            take = np.where((~uphill) & (~over),
                            np.minimum((capy - sed)*erode_k, -dh), 0.0)
            drop = np.clip(np.where(alive, drop, 0.0), 0.0, 24.0)
            take = np.clip(np.where(alive, take, 0.0), 0.0, 4.0)
            sed = np.clip(sed + take - drop, 0.0, 48.0)

            for (ii, jj, wf) in ((x0, y0, (1-fx)*(1-fy)), (x0+1, y0, fx*(1-fy)),
                                 (x0, y0+1, (1-fx)*fy),   (x0+1, y0+1, fx*fy)):
                np.add.at(H, (jj, ii), drop*wf)
            for k in range(len(off)):
                np.add.at(H, (np.clip(y0+off[k][1],0,N0-1), np.clip(x0+off[k][0],0,N1-1)), -take*wts[k])
            np.add.at(flow, (y0, x0), np.where(alive, water, 0.0))

            vel = np.clip(np.sqrt(np.maximum(vel*vel + dh*(-grav), 0.02)), 0.0, 12.0)
            water = water * (1.0-evap)
            px, py = npx, npy
    return np.nan_to_num(H, nan=0.0, posinf=0.0, neginf=0.0), flow

# ---------------------------------------------------------------- thermal / talus
def thermal(h, ds, iters=90, repose_deg=34.0, rate=0.42):
    H = h.copy()
    maxd = math.tan(math.radians(repose_deg)) * ds
    diag = math.tan(math.radians(repose_deg)) * ds * math.sqrt(2.0)
    dirs = [(0,1,maxd),(0,-1,maxd),(1,0,maxd),(-1,0,maxd),
            (1,1,diag),(1,-1,diag),(-1,1,diag),(-1,-1,diag)]
    for _ in range(iters):
        tot = np.zeros_like(H); mx = np.zeros_like(H)
        ds_list = []
        for (ox,oy,md) in dirs:
            d = H - np.roll(np.roll(H, oy, axis=0), ox, axis=1)
            d = np.maximum(d - md, 0.0)
            ds_list.append(d); tot = tot + d; mx = np.maximum(mx, d)
        move = np.minimum(mx*rate, tot)
        safe = np.where(tot > 1e-9, move/np.maximum(tot,1e-9), 0.0)
        H = H - move
        for i in range(len(dirs)):
            ox, oy, md = dirs[i]
            give = ds_list[i]*safe
            H = H + np.roll(np.roll(give, -oy, axis=0), -ox, axis=1)
    return H

# ---------------------------------------------------------------- drive
def distant(X, Y, seed):
    r = np.maximum(np.abs(X), np.abs(Y))
    inner = np.clip((r - 2500.0)/620.0, 0.0, 1.0)
    inner = inner*inner*(3-2*inner)
    wx, wy = warp(X/2600.0, Y/2600.0, seed+301, amp=0.7, freq=0.5)
    big = fbm(wx, wy, seed+303, octaves=6)
    rg = ridged(X/1300.0, Y/1300.0, seed+305, octaves=7)
    h = 1500.0 + big*1500.0 + (rg-0.3)*1500.0
    h = np.maximum(h, 300.0)
    return (h*inner - 900.0*(1.0-inner)).astype(np.float32)

def build(name, extent_m, n, seed=7, do_erode=True, back=False):
    t0 = time.time()
    ax = (np.arange(n, dtype=np.float32)/(n-1) - 0.5) * extent_m
    X, Y = np.meshgrid(ax, ax)
    ds = extent_m/(n-1)
    if back:
        H = distant(X, Y, seed)
        flow = np.zeros_like(H); dep = np.zeros_like(H)
    else:
        H = base_height(X, Y, seed)
        if do_erode:
            H, flow = hydraulic(H, ds, n_drops=int(0.11*n*n), batch=45000, steps=72, seed=seed)
            Ht = thermal(H, ds, iters=90)
            dep = Ht - H
            H = Ht
        else:
            flow = np.zeros_like(H); dep = np.zeros_like(H)
    print("  %s landform %.1fs  h=[%.0f %.0f]" % (name, time.time()-t0, H.min(), H.max()))
    return X, Y, H, flow, dep, ds

def masks(H, flow, dep, ds):
    gy, gx = np.gradient(H, ds)
    slope = np.sqrt(gx*gx+gy*gy)
    nz = 1.0/np.sqrt(1.0+slope*slope)
    lap = (np.roll(H,1,0)+np.roll(H,-1,0)+np.roll(H,1,1)+np.roll(H,-1,1)-4*H)/(ds*ds)
    f = np.log1p(np.maximum(flow, 0.0))
    rng_ = max(float(f.max())-float(f.min()), 1e-6)
    f = (f - f.min())/rng_
    d = np.clip(dep/6.0, 0, 1)
    c = np.clip(lap*450.0+0.5, 0, 1)
    return f.astype(np.float32), d.astype(np.float32), c.astype(np.float32), nz.astype(np.float32)

def save16(path, A, lo, hi):
    a = np.clip((A-lo)/(hi-lo), 0, 1)
    Image.fromarray((a*65535.0+0.5).astype(np.uint16), mode="I;16").save(path)

def hillshade(path, H, ds, az=315.0, alt=28.0):
    gy, gx = np.gradient(H, ds)
    a = math.radians(az); e = math.radians(alt)
    lx, ly, lz = math.cos(e)*math.sin(a), math.cos(e)*math.cos(a), math.sin(e)
    nz = 1.0/np.sqrt(1+gx*gx+gy*gy)
    sh = np.clip((-gx*nz)*lx + (-gy*nz)*ly + nz*lz, 0, 1)
    Image.fromarray((sh*255).astype(np.uint8)).resize((1024,1024)).save(path)

def save8rgba(path, r, g, b, a):
    arr = np.stack([(np.clip(x,0,1)*255+0.5).astype(np.uint8) for x in (r,g,b,a)], axis=-1)
    Image.fromarray(arr, mode="RGBA").save(path)

if __name__ == "__main__":
    T = time.time()
    meta = {}

    n = 2049; ext = 6144.0
    X, Y, H, flow, dep, ds = build("main", ext, n, seed=7)
    lo, hi = -80.0, 4700.0
    save16(os.path.join(OUT, "main_h.png"), H, lo, hi)
    f, d, c, nz = masks(H, flow, dep, ds)
    save8rgba(os.path.join(OUT, "main_m.png"), f, d, c, np.clip((H+60)/3460.0,0,1))
    hillshade(os.path.join(OUT, "prev_main.png"), H, ds)
    meta["main"] = dict(extent=ext, n=n, lo=lo, hi=hi, ds=ds)
    np.save(os.path.join(OUT, "main_h.npy"), H)

    n2 = 2049; ext2 = 640.0
    ax = (np.arange(n2, dtype=np.float32)/(n2-1) - 0.5) * ext2
    CX, CY = 900.0, -100.0
    NX, NY = np.meshgrid(ax + CX, ax + CY)
    im = Image.fromarray(H, mode="F")
    bx0 = ((CX-ext2*0.5)/ext + 0.5)*(n-1); bx1 = ((CX+ext2*0.5)/ext + 0.5)*(n-1)
    by0 = ((CY-ext2*0.5)/ext + 0.5)*(n-1); by1 = ((CY+ext2*0.5)/ext + 0.5)*(n-1)
    NH = np.asarray(im.resize((n2, n2), Image.BICUBIC, box=(bx0, by0, bx1, by1)), dtype=np.float32)
    dsn = ext2/(n2-1)
    u = (NX*0.80 + NY*0.60); v = (-NX*0.60 + NY*0.80)
    NH = NH + (fbm(u/26.0, v/9.0, 501, octaves=5)*0.42)
    NH = NH + np.clip(fbm(u/7.0, v/3.2, 503, octaves=4), 0, 1)*0.11
    NH = NH + fbm(NX/2.4, NY/2.4, 505, octaves=3)*0.035
    NHt = thermal(NH, dsn, iters=30, repose_deg=36.0)
    fn, dn, cn, nzn = masks(NHt, np.zeros_like(NHt), NHt-NH, dsn)
    lo2, hi2 = float(NHt.min())-1.0, float(NHt.max())+1.0
    save16(os.path.join(OUT, "near_h.png"), NHt, lo2, hi2)
    save8rgba(os.path.join(OUT, "near_m.png"), fn, dn, cn, np.clip((NHt-lo2)/(hi2-lo2),0,1))
    hillshade(os.path.join(OUT, "prev_near.png"), NHt, dsn)
    meta["near"] = dict(extent=ext2, n=n2, lo=lo2, hi=hi2, ds=dsn, cx=CX, cy=CY)

    n3 = 769; ext3 = 24576.0
    X3, Y3, H3, _, _, ds3 = build("back", ext3, n3, seed=7, back=True)
    lo3, hi3 = -1000.0, 3600.0
    save16(os.path.join(OUT, "back_h.png"), H3, lo3, hi3)
    f3, d3, c3, nz3 = masks(H3, np.zeros_like(H3), np.zeros_like(H3), ds3)
    save8rgba(os.path.join(OUT, "back_m.png"), f3, d3, c3, np.clip((H3-lo3)/(hi3-lo3),0,1))
    hillshade(os.path.join(OUT, "prev_back.png"), H3, ds3)
    meta["back"] = dict(extent=ext3, n=n3, lo=lo3, hi=hi3, ds=ds3)

    json.dump(meta, open(os.path.join(OUT, "valley.json"), "w"), indent=1)
    print("total %.1fs" % (time.time()-T))
