# ---------------------------------------------------------------------------
# BLINDSIDE -- a scanning range sensor.
#
# A spinning head carrying a fixed vertical array of emitters. Each emitter
# sits at a FIXED elevation, so as the head turns each one traces a ring: that
# is where the ring structure in the output comes from. It is not drawn on, it
# is what the device is.
#
# Everything here is the SENSOR, not the belief. It reads the true world (it
# is the only thing in this spike allowed to) and it hands back measurements
# in the sensor's own frame: range, bearing, elevation, intensity, ring index
# and the instant the shot was taken. Nothing downstream sees a world
# coordinate. That is CLAUDE.md's one invariant, kept by construction rather
# than by discipline: `scan()` returns local vectors and a time, and the
# believed pose is applied by the caller.
# ---------------------------------------------------------------------------
class_name LidarScan
extends RefCounted

# --- the model ------------------------------------------------------------
var rings: int = 32
var el_min_deg: float = -30.0
var el_max_deg: float = 12.0
var az_steps: int = 1024          # shots per revolution per emitter
var spin_hz: float = 10.0
var range_min: float = 0.55
var range_max: float = 40.0
var range_sigma: float = 0.020    # 20 mm, one sigma
var ref_range: float = 12.0       # range at which a rock returns reliably
var det_floor: float = 0.55       # SNR below this and the shot is a dropout
var inten_gain: float = 1.05
var beam_div_mrad: float = 3.0    # full-angle beam divergence
var sensor_h: float = 0.90        # head height above the machine's footprint
var seed_v: int = 7

# --- output (parallel arrays; one entry per return) -----------------------
var out_local: PackedVector3Array      # measurement in the SENSOR frame, metres
var out_t: PackedFloat32Array          # absolute time of the shot
var out_int: PackedFloat32Array        # 0..1 normalised reflectivity, clipped
var out_pack: PackedFloat32Array       # ring + 64 * surface class
var out_org: PackedVector3Array        # true sensor origin, for stats only
var out_hit: PackedVector3Array        # true hit, for stats only

# --- stats ----------------------------------------------------------------
var n_shots: int = 0
var n_hits: int = 0
var n_dropped: int = 0
var scan_usec: int = 0


func reset() -> void:
	out_local = PackedVector3Array()
	out_t = PackedFloat32Array()
	out_int = PackedFloat32Array()
	out_pack = PackedFloat32Array()
	out_org = PackedVector3Array()
	out_hit = PackedVector3Array()
	n_shots = 0
	n_hits = 0
	n_dropped = 0
	scan_usec = 0


func shots_per_rev() -> int:
	return rings * az_steps


func shots_per_second() -> float:
	return float(shots_per_rev()) * spin_hz


# Per-emitter calibration. Real units ship a table of these and the rings on a
# flat floor are visibly unevenly spaced because of it. Deterministic.
func _ring_el(k: int) -> float:
	var span: float = el_max_deg - el_min_deg
	var base: float = el_min_deg + span * float(k) / float(maxi(1, rings - 1))
	var b: float = (_h01(0x51ed, k, 0) - 0.5) * 0.16      # +/- 0.08 deg
	return deg_to_rad(base + b)


func _ring_range_bias(k: int) -> float:
	return (_h01(0x9d21, k, 0) - 0.5) * 0.030             # +/- 15 mm


func _h01(purpose: int, a: int, b: int) -> float:
	var x: int = seed_v & 0xFFFFFFFF
	x = (x ^ ((purpose * 0x9E3779B1) & 0xFFFFFFFF)) & 0xFFFFFFFF
	x = (x ^ ((a * 0x85EBCA77) & 0xFFFFFFFF)) & 0xFFFFFFFF
	x = (x ^ ((b * 0xC2B2AE3D) & 0xFFFFFFFF)) & 0xFFFFFFFF
	x = (x ^ (x >> 15)) & 0xFFFFFFFF
	x = (x * 0x2545F491) & 0xFFFFFFFF
	x = (x ^ (x >> 13)) & 0xFFFFFFFF
	x = (x * 0x27D4EB2F) & 0xFFFFFFFF
	x = (x ^ (x >> 16)) & 0xFFFFFFFF
	return float(x) / 4294967296.0


# One revolution. `p0/yaw0` is the pose at the start of the revolution and
# `p1/yaw1` at the end; the head is spinning while the machine moves, so each
# azimuth column is fired from its own pose. That is why a real cloud taken
# from a moving vehicle is skewed, and it is free to model here.
func sweep(space: PhysicsDirectSpaceState3D, p0: Vector3, yaw0: float,
		   p1: Vector3, yaw1: float, t0: float, rev: int) -> void:
	var t_us: int = Time.get_ticks_usec()
	var q := PhysicsRayQueryParameters3D.new()
	q.collide_with_areas = false
	q.collide_with_bodies = true
	# layer 1 only. LidarGeo also builds a SECOND collision body for the
	# camera rig (layer 2) that omits loose scatter; a laser must never see it
	# or every surface answers twice.
	q.collision_mask = 1
	var dyaw: float = wrapf(yaw1 - yaw0, -PI, PI)
	var period: float = 1.0 / spin_hz
	var el := PackedFloat32Array()
	var rb := PackedFloat32Array()
	el.resize(rings)
	rb.resize(rings)
	for k in range(rings):
		el[k] = _ring_el(k)
		rb[k] = _ring_range_bias(k)

	for a in range(az_steps):
		var u: float = float(a) / float(az_steps)
		var org: Vector3 = p0.lerp(p1, u)
		var yaw: float = yaw0 + dyaw * u
		var t: float = t0 + u * period
		var az: float = yaw + u * TAU
		var ca: float = cos(az)
		var sa: float = sin(az)
		for k in range(rings):
			var e: float = el[k]
			var ce: float = cos(e)
			# machine frame: +X forward, +Y up, -Z... use world-aligned yaw
			var dir := Vector3(ce * ca, sin(e), ce * sa)
			q.from = org
			q.to = org + dir * range_max
			var r: Dictionary = space.intersect_ray(q)
			n_shots += 1
			if r.is_empty():
				continue
			var hit: Vector3 = r["position"]
			var nrm: Vector3 = r["normal"]
			var rng: float = org.distance_to(hit)
			if rng < range_min:
				continue
			var cls: int = 0
			var col: Object = r["collider"]
			if col != null and col.has_meta("surf"):
				cls = int(col.get_meta("surf"))
			var cos_i: float = absf(dir.dot(nrm))
			var alb: float = LidarGeo.SURF_ALBEDO[cls]
			var retro: float = LidarGeo.SURF_RETRO_F[cls]
			# Reflectance is not uniform over a surface: rock is banded, dusty,
			# damp in patches, and a real intensity image of a rock face is
			# visibly mottled at the 50-100 mm scale. Hashed off the HIT point,
			# so two passes over the same wall agree about its brightness --
			# which matters, because if they did not, drift would be masked by
			# noise instead of shown by it.
			if retro < 0.5:
				var qx: int = int(floor(hit.x * 13.0))
				var qy: int = int(floor(hit.y * 13.0))
				var qz: int = int(floor(hit.z * 13.0))
				var mott: float = 0.52 + 0.92 * _h01(0x3f19, qx * 7919 + qy, qz)
				alb *= mott
			# Diffuse returns fall off with the cosine of incidence; a
			# retroreflector does not, until it is nearly edge on.
			var lam: float = pow(maxf(cos_i, 0.0), 0.75)
			var wide: float = smoothstep(0.06, 0.30, cos_i)
			var refl: float = alb * lerp(lam, wide, retro)
			# link budget: the fraction of the pulse that comes back falls as
			# 1/r^2, so a far dark surface simply does not answer.
			var snr: float = refl * (ref_range * ref_range) / maxf(rng * rng, 0.01)
			var p_det: float = clampf(snr / det_floor, 0.0, 1.0)
			if _h01(0x2c17, rev * 4096 + a, k) > p_det:
				n_dropped += 1
				continue
			# range noise, plus the per-emitter bias
			var g: float = (_h01(0x77b3, rev * 4096 + a, k) + _h01(0x77b3, rev * 4096 + a, k + 97)
						  + _h01(0x77b3, rev * 4096 + a, k + 991) - 1.5) * 1.155
			var rn: float = rng + g * range_sigma + rb[k]
			var local := Vector3(ce * cos(u * TAU), sin(e), ce * sin(u * TAU)) * rn
			out_local.push_back(local)
			out_t.push_back(t)
			# receiver noise: an intensity channel is never clean
			var shot_n: float = 1.0 + 0.09 * (_h01(0x6a41, rev * 4096 + a, k) - 0.5) * 2.0
			out_int.push_back(clampf(refl * inten_gain * shot_n, 0.0, 1.0))
			out_pack.push_back(float(k) + 64.0 * float(cls))
			out_org.push_back(org)
			out_hit.push_back(hit)
			n_hits += 1
	scan_usec += Time.get_ticks_usec() - t_us


# The footprint a return could have come from, at this range. A real beam is a
# few milliradians of full angle, so the patch is millimetres near and tens of
# centimetres far -- not the 45 mm constant ART-DIRECTION 8.2 asks for, and
# not the 0.2-0.7 m the toy sim's 2-degree ray spacing implies either.
func footprint_m(rng: float) -> float:
	return rng * beam_div_mrad * 0.001


func describe() -> String:
	return "%d rings %.1f..%.1f deg (step %.3f), %d az/rev (%.3f deg), %.0f Hz, %.0f k shots/s, %.1f-%.0f m" % [
		rings, el_min_deg, el_max_deg,
		(el_max_deg - el_min_deg) / float(maxi(1, rings - 1)),
		az_steps, 360.0 / float(az_steps), spin_hz,
		shots_per_second() / 1000.0, range_min, range_max]
