"""What a carried lamp actually delivers, in radiometric units, so the wattage
argument stops being a taste argument.

Blender treats a SPOT light as a point source with a cone cutoff: `energy` is the
power the source WOULD radiate over the full sphere, and narrowing the cone does not
concentrate it. So:

    I  = P / (4 pi)                      W/sr
    E  = I * cos(theta) / d^2            W/m^2 on a surface at distance d
    L  = E * rho / pi                    W/(m^2 sr) leaving a lambertian surface

Blender's AgX view transform puts a linear radiance of about 0.18 at mid grey; call
0.01 the floor of legibility (just off black) and 0.6 the point where the AgX shoulder
starts flattening highlights.

Run with any python: no bpy needed.
"""
import math

MID = 0.18
FLOOR = 0.01          # just legible above black
BLOWN = 0.60          # into the AgX shoulder
CELL = 0.6            # metres per cell (derived; see the art doc)


def radiance(power_w, d_m, cos_theta, albedo):
    I = power_w / (4 * math.pi)
    E = I * cos_theta / (d_m ** 2)
    return E * albedo / math.pi


def reach(power_w, cos_theta, albedo, target=FLOOR):
    """Distance at which a surface falls to `target` radiance."""
    I = power_w / (4 * math.pi)
    return math.sqrt(I * cos_theta * albedo / (math.pi * target))


HEAD_Z = 0.50         # surveyor head height, m (ride 0.32 + hull 0.12 + neck 0.10)

print("=" * 78)
print("1. WHAT THE CURRENT 70 W LAMP DELIVERS, AND WHAT IT WOULD TAKE")
print("=" * 78)
print(f"{'lamp W':>8} {'floor@3m':>10} {'wall@1.5m':>10} {'wall@6m':>9} {'floor@8m':>9}")
for P in (70, 200, 400, 600, 1000, 1500, 3000):
    # floor 3 m ahead of a lamp at 0.50 m: grazing incidence
    d = math.hypot(3.0, HEAD_Z)
    f3 = radiance(P, d, HEAD_Z / d, 0.30)
    # side wall 1.5 m away, near-normal
    w15 = radiance(P, 1.6, 0.90, 0.30)
    w6 = radiance(P, 6.0, 0.80, 0.30)
    d8 = math.hypot(8.0, HEAD_Z)
    f8 = radiance(P, d8, HEAD_Z / d8, 0.30)
    print(f"{P:>8} {f3:>10.4f} {w15:>10.4f} {w6:>9.4f} {f8:>9.4f}")
print(f"  (mid grey = {MID}; legible floor = {FLOOR}; AgX shoulder from {BLOWN})")

print()
print("=" * 78)
print("2. HOW FAR A 600 W LAMP REACHES, BY ALBEDO AND GEOMETRY")
print("=" * 78)
print(f"{'albedo':>8} {'wall (normal)':>15} {'wall (25 deg)':>15} {'floor (grazing)':>17}")
for rho in (0.06, 0.10, 0.18, 0.25, 0.30, 0.40, 0.50):
    rw = reach(600, 1.0, rho)
    rw25 = reach(600, 0.90, rho)
    # grazing on the floor: cos = HEAD_Z/d, so d^3 = I*HEAD_Z*rho/(pi*target)
    I = 600 / (4 * math.pi)
    rf = (I * HEAD_Z * rho / (math.pi * FLOOR)) ** (1 / 3)
    print(f"{rho:>8.2f} {rw:>13.1f} m {rw25:>13.1f} m {rf:>15.1f} m")

print()
print("=" * 78)
print("3. THE REACH IN CELLS, AGAINST THE SENSOR RANGES THE SIM ALREADY HAS")
print("=" * 78)
I = 600 / (4 * math.pi)
wall = reach(600, 0.90, 0.30)
floor = (I * HEAD_Z * 0.30 / (math.pi * FLOOR)) ** (1 / 3)
print(f"  600 W lamp, rock albedo 0.30")
print(f"    wall legible to  {wall:6.1f} m = {wall / CELL:5.1f} cells")
print(f"    floor legible to {floor:6.1f} m = {floor / CELL:5.1f} cells")
print(f"    LIDAR_RANGE      {18.0 * CELL:6.1f} m = {18.0:5.1f} cells")
print(f"    SONAR_RANGE      {30.0 * CELL:6.1f} m = {30.0:5.1f} cells")
print(f"    BEACON_RANGE     {6.0 * CELL:6.1f} m = {6.0:5.1f} cells")

print()
print("=" * 78)
print("4. DYNAMIC RANGE INSIDE ONE FRAME (600 W, albedo 0.30)")
print("=" * 78)
rows = [("near wall, 1.6 m, near-normal", 1.6, 0.90),
        ("wall at 4 m", 4.0, 0.85),
        ("wall at 8 m", 8.0, 0.80),
        ("floor 2 m ahead, grazing", math.hypot(2.0, HEAD_Z), HEAD_Z / math.hypot(2.0, HEAD_Z)),
        ("floor 5 m ahead, grazing", math.hypot(5.0, HEAD_Z), HEAD_Z / math.hypot(5.0, HEAD_Z)),
        ("floor 12 m ahead, grazing", math.hypot(12.0, HEAD_Z), HEAD_Z / math.hypot(12.0, HEAD_Z)),
        ("wall at 25 m", 25.0, 0.80)]
vals = []
for label, d, c in rows:
    L = radiance(600, d, c, 0.30)
    vals.append(L)
    tag = "BLOWN" if L > BLOWN else ("black" if L < FLOOR else "")
    print(f"  {label:<32} {L:8.4f}  ({L / MID:6.2f} x mid grey) {tag}")
lit = [v for v in vals if v >= FLOOR]
print(f"  ratio brightest:dimmest legible = {max(lit) / min(lit):.0f} : 1")

print()
print("=" * 78)
print("5. THE BOUNCE BUDGET: does the passage light the machine?")
print("=" * 78)
print("  A lit wall patch at radiance L, subtending solid angle W at the agent's flank,")
print("  puts E = L*W on it; the shell (albedo 0.62) then returns E*0.62/pi.")
for wname, Lw in (("wall 1.6 m, 600 W", radiance(600, 1.6, 0.90, 0.30)),
                  ("wall 1.6 m, 70 W", radiance(70, 1.6, 0.90, 0.30)),
                  ("wall 1.6 m, 600 W, albedo 0.10", radiance(600, 1.6, 0.90, 0.10)),
                  ("wall 1.6 m, 600 W, albedo 0.50", radiance(600, 1.6, 0.90, 0.50))):
    for omega, oname in ((0.30, "flank sees 0.30 sr"),):
        E = Lw * omega
        shell = E * 0.62 / math.pi
        chassis = E * 0.055 / math.pi
        print(f"  {wname:<34} shell {shell:7.4f} ({shell / MID:5.2f}x mid) "
              f"| graphite {chassis:7.4f}")

print()
print("=" * 78)
print("6. WHAT THE ASSAYER WOULD HAVE TO EMIT TO BE THE CAVE'S KEY LIGHT")
print("=" * 78)
print("  Target: the machine's own iron reads at mid grey at 3 m, and an agent")
print("  standing at the lethal contour (9 cells = 5.4 m) is legible.")
for P in (200, 500, 700, 1000, 2000):
    at3 = radiance(P, 3.0, 0.85, 0.22)     # its own iron, albedo 0.22
    at54 = radiance(P, 5.4, 0.80, 0.30)    # rock at the lethal contour
    at18 = radiance(P, 18.0, 0.80, 0.30)   # rock 30 cells away
    print(f"  {P:>5} W   iron@3m {at3:7.4f} ({at3 / MID:5.2f}x mid)   "
          f"rock@5.4m {at54:7.4f}   rock@18m {at18:7.4f}")
