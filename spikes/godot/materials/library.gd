extends RefCounted

# ---------------------------------------------------------------------------
# BLINDSIDE -- the material library.
#
# One shader family, `bs_surface.gdshader`, plus two water shaders. A material
# is a dictionary of uniform values, nothing else. There is no per-material
# code anywhere in this project, which is the whole point: adopting this
# library is copying three .gdshader files, one .gdshaderinc pair, and this
# table.
#
# Every `alb_*` value is LINEAR reflectance, not sRGB and not a Color. The
# `range` field records the real-world measured range the material is claiming
# to sit inside; `calib.py` reads it back off a screenshot and fails if the
# rendered albedo leaves it. Sources are in NOTES.md section 5.
#
# For a metal (metallic = 1) the albedo channel is not diffuse reflectance at
# all -- it is F0, the specular reflectance at normal incidence. Iron 0.56,
# aluminium 0.91-0.92. Those are the values below, and they are why a metal
# entry looks "too bright" next to a rock entry. It is not a rock.
# ---------------------------------------------------------------------------

const ROWS := [
	"cave rock",
	"underfoot",
	"water and hardstanding",
	"the ancients' register",
	"the players' register",
]


static func _rock_base() -> Dictionary:
	return {
		"alb_lo": Vector3(0.030, 0.026, 0.021),
		"alb_hi": Vector3(0.090, 0.076, 0.060),
		"alb_curve": 1.0,
		"alb_cell": 0.10,
		"rough_lo": 0.66, "rough_hi": 0.95, "rough_micro": 0.12,
		"metallic": 0.0, "spec": 0.5,
		"form_freq": 2.2, "form_amp": 0.014, "form_ridge": 0.25,
		"detail_freq": 16.0, "detail_amp": 0.00528,
		"micro_freq": 130.0, "micro_amp": 0.000396,
		"voro_freq": 7.0, "voro_amp": 0.010, "voro_pebble": 0.0, "voro_warp": 1.1,
		"voro2_freq": 34.0, "voro2_amp": 0.00225, "voro2_pebble": 0.0,
		"bed_freq": 2.2, "bed_amp": 0.006, "bed_value": 0.16,
		"pom_depth": 0.018, "pom_far": 4.5, "pom_steps_near": 14, "pom_steps_far": 5,
		"wet_gain": 1.0, "wet_bias": 0.22, "wet_darken": 0.52, "wet_rough": 0.10,
		"pool_gain": 1.1, "wet_fill": 0.9,
		"stain_amt": 0.35, "stain_col": Vector3(0.045, 0.026, 0.014),
		"stain_freq": 0.50, "stain_sharp": 1.0,
		"macro_var": 0.40, "macro_freq": 0.75,
	}


static func _merge(base: Dictionary, over: Dictionary) -> Dictionary:
	var d := base.duplicate()
	for k in over:
		d[k] = over[k]
	return d


# ---------------------------------------------------------------------------
# The library. `shader` is one of full / lean / far / water_shallow / water_deep.
# `range` is [min, max] linear luminance the material claims, from NOTES.md 5.
# ---------------------------------------------------------------------------
static func materials() -> Array:
	var out: Array = []

	# ---------------- row 0: cave rock, ART-DIRECTION 3.1 -------------------
	out.append({
		"id": "rock_wet", "label": "wet cave rock", "row": 0, "shader": "lean",
		"range": [0.030, 0.095], "note": "the ART 3.1 rock at wet 0.5",
		"p": _rock_base(),
			"ao_strength": 0.45, "ao_radius": 0.075,
	})
	out.append({
		"id": "rock_fresh", "label": "rock, freshly broken", "row": 0, "shader": "lean",
		"range": [0.045, 0.140], "note": "conchoidal, unstained, no patina",
		"p": _merge(_rock_base(), {
			"ao_strength": 0.4, "ao_radius": 0.045,
			"alb_lo": Vector3(0.055, 0.050, 0.044),
			"alb_hi": Vector3(0.135, 0.126, 0.113),
			"form_ridge": 0.90, "form_freq": 5.0, "form_amp": 0.010,
			"voro_freq": 14.0, "voro_amp": 0.012, "voro_warp": 0.45,
			"voro2_freq": 60.0, "voro2_amp": 0.0015,
			"detail_freq": 40.0, "detail_amp": 0.00384,
			"micro_freq": 300.0, "micro_amp": 0.00018, "rough_micro": 0.06,
			"rough_lo": 0.80, "rough_hi": 0.98,
			"bed_amp": 0.002, "bed_value": 0.06,
			"stain_amt": 0.0, "wet_bias": 0.04, "wet_darken": 0.60,
			"pom_depth": 0.012, "alb_cell": 0.06,
		}),
	})
	out.append({
		"id": "rock_weathered", "label": "rock, long weathered", "row": 0, "shader": "lean",
		"range": [0.020, 0.080], "note": "rounded, joints opened, iron patina",
		"p": _merge(_rock_base(), {
			"ao_strength": 0.5, "ao_radius": 0.11,
			"alb_lo": Vector3(0.022, 0.018, 0.014),
			"alb_hi": Vector3(0.072, 0.060, 0.046),
			"form_ridge": 0.0, "form_freq": 1.5, "form_amp": 0.018,
			"voro_freq": 4.0, "voro_amp": 0.012, "voro_warp": 1.7,
			"voro2_freq": 22.0, "voro2_amp": 0.0033,
			"detail_freq": 9.0, "detail_amp": 0.0072,
			"micro_freq": 110.0, "micro_amp": 0.000504, "rough_micro": 0.14,
			"rough_lo": 0.72, "rough_hi": 0.96,
			"stain_amt": 0.55, "stain_col": Vector3(0.038, 0.020, 0.010),
			"stain_freq": 0.30,
			"wet_bias": 0.20, "pom_depth": 0.022, "alb_cell": 0.14,
		}),
	})
	out.append({
		"id": "rock_stained", "label": "rock, mineral stained", "row": 0, "shader": "lean",
		"range": [0.025, 0.110], "note": "iron ochre. The hue this family is allowed",
		"p": _merge(_rock_base(), {
			"ao_strength": 0.45, "ao_radius": 0.075,
			"alb_lo": Vector3(0.028, 0.023, 0.018),
			"alb_hi": Vector3(0.085, 0.070, 0.055),
			"stain_amt": 0.80, "stain_col": Vector3(0.115, 0.052, 0.018),
			"stain_freq": 0.22, "stain_sharp": 1.4,
			"wet_bias": 0.32, "voro_warp": 1.4,
		}),
	})
	out.append({
		"id": "rock_tidemark", "label": "tide-mark crust", "row": 0, "shader": "lean",
		"range": [0.090, 0.240], "note": "ART 3.5: 0.12 m band, albedo x1.7, matte",
		"p": _merge(_rock_base(), {
			"ao_strength": 0.3, "ao_radius": 0.03,
			"alb_lo": Vector3(0.100, 0.093, 0.082),
			"alb_hi": Vector3(0.220, 0.205, 0.180),
			"rough_lo": 0.90, "rough_hi": 0.99, "rough_micro": 0.06,
			"voro_freq": 30.0, "voro_amp": 0.0035, "voro_pebble": 0.80, "voro_warp": 0.6,
			"voro2_freq": 120.0, "voro2_amp": 0.0009, "voro2_pebble": 1.0,
			"micro_freq": 380.0, "micro_amp": 0.000162,
			"stain_amt": 0.12, "wet_gain": 0.22, "wet_bias": 0.0,
			"bed_amp": 0.0, "bed_value": 0.0, "pom_depth": 0.006,
		}),
	})

	# ---------------- row 1: underfoot --------------------------------------
	out.append({
		"id": "silt_dry", "label": "silt / fines, dry", "row": 1, "shader": "lean",
		"range": [0.070, 0.175], "note": "desiccation cracks, no grains visible",
		"p": {
			"ao_strength": 0.35, "ao_radius": 0.14,
			"macro_var": 0.34, "macro_freq": 0.9,
			"alb_lo": Vector3(0.075, 0.066, 0.052),
			"alb_hi": Vector3(0.165, 0.148, 0.120),
			"alb_curve": 0.85, "alb_cell": 0.05,
			"rough_lo": 0.92, "rough_hi": 0.99, "rough_micro": 0.05,
			"metallic": 0.0, "spec": 0.45,
			"form_freq": 3.0, "form_amp": 0.006, "form_ridge": 0.0,
			"detail_freq": 30.0, "detail_amp": 0.0024,
			"micro_freq": 420.0, "micro_amp": 0.000144,
			"voro_freq": 6.5, "voro_amp": 0.0034, "voro_pebble": 0.0, "voro_warp": 1.5,
			"voro2_freq": 0.0, "voro2_amp": 0.0,
			"bed_freq": 0.0, "bed_amp": 0.0, "bed_value": 0.0,
			"pom_depth": 0.008, "pom_far": 4.0, "pom_steps_near": 10, "pom_steps_far": 4,
			"wet_gain": 1.0, "wet_bias": 0.0, "wet_darken": 0.42, "wet_rough": 0.16,
			"pool_gain": 1.2, "wet_fill": 0.95,
			"stain_amt": 0.10, "stain_col": Vector3(0.055, 0.042, 0.026),
			"stain_freq": 0.7, "stain_sharp": 1.0,
		},
	})
	var silt: Dictionary = out[out.size() - 1]["p"]
	out.append({
		"id": "silt_damp", "label": "silt, damp", "row": 1, "shader": "lean",
		"range": [0.030, 0.090], "note": "the same silt at wet_bias 0.38",
		"p": _merge(silt, {"wet_bias": 0.38, "pool_gain": 1.4}),
	})
	out.append({
		"id": "mud_saturated", "label": "mud, saturated", "row": 1, "shader": "lean",
		"range": [0.010, 0.055], "note": "churned, no grains, holds standing water",
		"p": _merge(silt, {
			"alb_lo": Vector3(0.013, 0.011, 0.009),
			"alb_hi": Vector3(0.068, 0.060, 0.047),
			"macro_var": 0.42, "macro_freq": 1.30,
			"rough_lo": 0.80, "rough_hi": 0.95,
			"form_freq": 2.0, "form_amp": 0.012,
			"detail_freq": 14.0, "detail_amp": 0.0072,
			"micro_freq": 200.0, "micro_amp": 0.000216,
			"voro_amp": 0.0, "voro2_amp": 0.0,
			"pom_depth": 0.020, "pom_steps_near": 12,
			"wet_bias": 0.62, "wet_darken": 0.45, "wet_rough": 0.08, "pool_gain": 1.9,
			"stain_amt": 0.0,
		}),
	})
	out.append({
		"id": "aggregate", "label": "aggregate, 40 mm", "row": 1, "shader": "lean",
		"range": [0.025, 0.125], "note": "THE underfoot case. Half-buried, every stone different",
		"p": {
			"ao_strength": 0.6, "ao_radius": 0.035,
			"macro_var": 0.3, "macro_freq": 1.1,
			"alb_lo": Vector3(0.030, 0.026, 0.021),
			"alb_hi": Vector3(0.115, 0.100, 0.082),
			"alb_curve": 1.0, "alb_cell": 0.34,
			"rough_lo": 0.62, "rough_hi": 0.93, "rough_micro": 0.10,
			"metallic": 0.0, "spec": 0.5,
			"form_freq": 1.6, "form_amp": 0.006, "form_ridge": 0.0,
			"detail_freq": 55.0, "detail_amp": 0.00216,
			"micro_freq": 380.0, "micro_amp": 0.000162,
			"voro_freq": 26.0, "voro_amp": 0.014, "voro_pebble": 1.0, "voro_warp": 0.35,
			"voro2_freq": 78.0, "voro2_amp": 0.0016, "voro2_pebble": 0.45,
			"bed_freq": 0.0, "bed_amp": 0.0, "bed_value": 0.0,
			"pom_depth": 0.030, "pom_far": 4.2, "pom_steps_near": 16, "pom_steps_far": 6,
			"wet_gain": 1.0, "wet_bias": 0.15, "wet_darken": 0.50, "wet_rough": 0.10,
			"pool_gain": 1.5, "wet_fill": 0.9,
			"stain_amt": 0.18, "stain_col": Vector3(0.040, 0.024, 0.012),
			"stain_freq": 0.45, "stain_sharp": 1.0,
		},
	})
	var agg: Dictionary = out[out.size() - 1]["p"]
	out.append({
		"id": "ballast", "label": "rail ballast, 60 mm", "row": 1, "shader": "lean",
		"range": [0.025, 0.130], "note": "0.6 m gauge (ART 3.3). Deepest parallax in the library",
		"p": _merge(agg, {
			"alb_lo": Vector3(0.028, 0.025, 0.021),
			"alb_hi": Vector3(0.120, 0.108, 0.090),
			"alb_cell": 0.38,
			"form_ridge": 0.60,
			"voro_freq": 16.0, "voro_amp": 0.026, "voro_warp": 0.25,
			"voro2_freq": 48.0, "voro2_amp": 0.0026, "voro2_pebble": 0.45,
			"rough_lo": 0.66, "rough_hi": 0.95,
			"pom_depth": 0.055, "pom_far": 4.6, "pom_steps_near": 17, "pom_steps_far": 7,
			"ao_strength": 0.65, "ao_radius": 0.055,
			"wet_bias": 0.10,
		}),
	})

	# ---------------- row 2: water and hardstanding -------------------------
	out.append({
		"id": "water_shallow", "label": "water, shallow over silt", "row": 2,
		"shader": "water_shallow", "range": [0.0, 0.06],
		"note": "transparent, refracting, absorbing. IOR 1.333, F0 0.0203",
		"p": {
			"absorb": Vector3(0.85, 0.30, 0.18),
			"murk_col": Vector3(0.030, 0.026, 0.020),
			"murk": 0.55, "ripple_amp": 0.0055, "ripple_freq": 7.0,
			"ripple_speed": 0.09, "drip_rings": 0.90, "max_depth": 0.45,
			"refract_k": 0.045,
		},
	})
	out.append({
		"id": "water_deep", "label": "water, deep", "row": 2,
		"shader": "water_deep", "range": [0.0, 0.03],
		"note": "opaque, so screen-space reflection can run on it",
		"p": {
			"absorb": Vector3(0.85, 0.30, 0.18),
			"murk_col": Vector3(0.026, 0.023, 0.019),
			"murk": 0.55, "ripple_amp": 0.0032, "ripple_freq": 4.5,
			"ripple_speed": 0.06, "drip_rings": 0.55, "max_depth": 3.0,
		},
	})
	out.append({
		"id": "concrete_weathered", "label": "concrete, weathered", "row": 2, "shader": "lean",
		"range": [0.180, 0.350], "note": "the checklist band, 0.25-0.35 at mid field",
		"p": {
			"ao_strength": 0.35, "ao_radius": 0.09,
			"macro_var": 0.26, "macro_freq": 0.5,
			"alb_lo": Vector3(0.185, 0.183, 0.175),
			"alb_hi": Vector3(0.345, 0.340, 0.325),
			"alb_curve": 1.0, "alb_cell": 0.045,
			"rough_lo": 0.72, "rough_hi": 0.96, "rough_micro": 0.10,
			"metallic": 0.0, "spec": 0.5,
			"form_freq": 1.1, "form_amp": 0.004, "form_ridge": 0.0,
			"detail_freq": 22.0, "detail_amp": 0.00288,
			"micro_freq": 320.0, "micro_amp": 0.00018,
			"voro_freq": 1.05, "voro_amp": 0.0070, "voro_pebble": 0.0, "voro_warp": 0.9,
			"voro2_freq": 40.0, "voro2_amp": 0.0018, "voro2_pebble": 1.0,
			"bed_freq": 0.0, "bed_amp": 0.0, "bed_value": 0.0,
			"pom_depth": 0.008, "pom_far": 4.0, "pom_steps_near": 9, "pom_steps_far": 4,
			"wet_gain": 0.9, "wet_bias": 0.0, "wet_darken": 0.50, "wet_rough": 0.11,
			"pool_gain": 1.2, "wet_fill": 0.9,
			"stain_amt": 0.30, "stain_col": Vector3(0.075, 0.070, 0.062),
			"stain_freq": 0.42, "stain_sharp": 1.2,
		},
	})
	out.append({
		"id": "hardstanding", "label": "industrial hardstanding", "row": 2, "shader": "lean",
		"range": [0.090, 0.310], "note": "exposed aggregate, oil, tyre polish",
		"p": {
			"ao_strength": 0.45, "ao_radius": 0.045,
			"macro_var": 0.34, "macro_freq": 0.45,
			"alb_lo": Vector3(0.110, 0.107, 0.100),
			"alb_hi": Vector3(0.300, 0.295, 0.280),
			"alb_curve": 1.1, "alb_cell": 0.22,
			"rough_lo": 0.55, "rough_hi": 0.94, "rough_micro": 0.10,
			"metallic": 0.0, "spec": 0.5,
			"form_freq": 0.9, "form_amp": 0.005, "form_ridge": 0.0,
			"detail_freq": 26.0, "detail_amp": 0.0024,
			"micro_freq": 300.0, "micro_amp": 0.00018,
			"voro_freq": 20.0, "voro_amp": 0.0055, "voro_pebble": 0.85, "voro_warp": 0.5,
			"voro2_freq": 70.0, "voro2_amp": 0.0018, "voro2_pebble": 1.0,
			"bed_freq": 0.0, "bed_amp": 0.0, "bed_value": 0.0,
			"pom_depth": 0.010, "pom_far": 5.0, "pom_steps_near": 10, "pom_steps_far": 4,
			"wet_gain": 1.0, "wet_bias": 0.0, "wet_darken": 0.48, "wet_rough": 0.09,
			"pool_gain": 1.4, "wet_fill": 0.9,
			"stain_amt": 0.45, "stain_col": Vector3(0.014, 0.013, 0.012),
			"stain_freq": 0.60, "stain_sharp": 1.5,
		},
	})

	# ---------------- row 3: the ancients' register -------------------------
	var iron_base := {
		"alb_lo": Vector3(0.300, 0.295, 0.290),
		"alb_hi": Vector3(0.560, 0.565, 0.570),      # F0 of iron
		"alb_curve": 1.0, "alb_cell": 0.0,
		"rough_lo": 0.34, "rough_hi": 0.80, "rough_micro": 0.12,
		"metallic": 1.0, "spec": 0.5,
		"macro_var": 0.16, "macro_freq": 1.1,
		"form_freq": 4.0, "form_amp": 0.0018, "form_ridge": 0.0,
		"detail_freq": 34.0, "detail_amp": 0.00192,
		"micro_freq": 600.0, "micro_amp": 0.000126,
		"voro_freq": 0.0, "voro_amp": 0.0, "voro2_freq": 0.0, "voro2_amp": 0.0,
		"bed_freq": 0.0, "bed_amp": 0.0, "bed_value": 0.0,
		"pom_depth": 0.0, "pom_far": 3.0, "pom_steps_near": 6, "pom_steps_far": 3,
		"wet_gain": 0.9, "wet_bias": 0.10, "wet_darken": 0.86, "wet_rough": 0.06,
		"pool_gain": 1.5, "wet_fill": 0.95,
		"stain_amt": 0.0, "edge_wear": 0.18,
		"rust_col": Vector3(0.098, 0.041, 0.018),
		"rust_col_old": Vector3(0.046, 0.025, 0.015),
	}
	out.append({
		"id": "iron_painted", "label": "cast iron, painted", "row": 3, "shader": "full",
		"range": [0.020, 0.560], "note": "works green over iron; paint chips to bare and rust",
		"p": _merge(iron_base, {
			"paint_amt": 0.95, "paint_col": Vector3(0.026, 0.038, 0.032),
			"paint_rough": 0.44, "chip_amt": 0.28,
			"rust_amt": 0.30, "rust_freq": 2.3,
		}),
	})
	out.append({
		"id": "iron_bare", "label": "cast iron, bare", "row": 3, "shader": "full",
		"range": [0.140, 0.570], "note": "sand-cast skin, metallic 1 except in the oxide",
		"p": _merge(iron_base, {"rust_amt": 0.16, "rust_freq": 2.1}),
	})
	out.append({
		"id": "steel_rusted", "label": "steel, lightly rusted", "row": 3, "shader": "full",
		"range": [0.040, 0.570], "note": "rolled plate; the metallic transition band",
		"p": _merge(iron_base, {
			"rough_lo": 0.30, "rough_hi": 0.55,
			"form_freq": 6.0, "form_amp": 0.0010,
			"detail_freq": 40.0, "detail_amp": 0.0012,
			"rust_amt": 0.40, "rust_freq": 2.6, "edge_wear": 0.30,
		}),
	})
	out.append({
		"id": "iron_rotten", "label": "iron, rotten", "row": 3, "shader": "full",
		"range": [0.015, 0.210], "note": "laminating scale; metallic has gone to 0 almost everywhere",
		"p": _merge(iron_base, {
			"ao_strength": 0.35, "ao_radius": 0.04,
			"rough_lo": 0.72, "rough_hi": 0.97,
			"form_freq": 6.0, "form_amp": 0.004, "form_ridge": 0.50,
			"voro_freq": 18.0, "voro_amp": 0.0035, "voro_pebble": 0.20, "voro_warp": 0.8,
			"detail_freq": 45.0, "detail_amp": 0.00216,
			"rust_amt": 0.80, "rust_freq": 3.2, "macro_var": 0.34, "macro_freq": 2.2,
			"rust_col_old": Vector3(0.045, 0.023, 0.014),
			"pom_depth": 0.006, "pom_steps_near": 7,
			"wet_bias": 0.25, "edge_wear": 0.0,
		}),
	})
	out.append({
		"id": "timber_wet", "label": "timber, wet", "row": 3, "shader": "full",
		"range": [0.015, 0.080], "note": "pit prop, sawn, soaked; grain along X",
		"p": {
			"macro_var": 0.3, "macro_freq": 1.6,
			"alb_lo": Vector3(0.013, 0.009, 0.005),
			"alb_hi": Vector3(0.098, 0.068, 0.039),
			"alb_curve": 1.0, "alb_cell": 0.0,
			"rough_lo": 0.55, "rough_hi": 0.90, "rough_micro": 0.12,
			"metallic": 0.0, "spec": 0.5,
			"form_freq": 2.4, "form_amp": 0.0035, "form_ridge": 0.20,
			"detail_freq": 18.0, "detail_amp": 0.0024,
			"micro_freq": 260.0, "micro_amp": 0.000216,
			"voro_freq": 0.0, "voro_amp": 0.0, "voro2_freq": 0.0, "voro2_amp": 0.0,
			"bed_freq": 0.0, "bed_amp": 0.0, "bed_value": 0.0,
			"grain_freq": 34.0, "grain_amp": 0.0022, "grain_stretch": 0.045,
			"grain_axis": Vector3(1, 0, 0), "grain_value": 0.46,
			"pom_depth": 0.006, "pom_far": 3.5, "pom_steps_near": 8, "pom_steps_far": 4,
			"wet_gain": 1.0, "wet_bias": 0.45, "wet_darken": 0.55, "wet_rough": 0.11,
			"pool_gain": 1.2, "wet_fill": 0.9,
			"stain_amt": 0.20, "stain_col": Vector3(0.030, 0.016, 0.008),
			"stain_freq": 0.8, "stain_sharp": 1.0,
		},
	})
	var tw: Dictionary = out[out.size() - 1]["p"]
	out.append({
		"id": "timber_rotten", "label": "timber, rotten", "row": 3, "shader": "full",
		"range": [0.018, 0.090], "note": "cubical rot, fibres standing proud, greyed",
		"p": _merge(tw, {
			"ao_strength": 0.35, "ao_radius": 0.06,
			"alb_lo": Vector3(0.022, 0.021, 0.019),
			"alb_hi": Vector3(0.085, 0.081, 0.074),
			"grain_freq": 26.0, "grain_amp": 0.0042, "grain_value": 0.52,
			"form_freq": 3.5, "form_amp": 0.0065, "form_ridge": 0.55,
			"voro_freq": 9.0, "voro_amp": 0.0035, "voro_pebble": 0.0, "voro_warp": 0.6,
			"rough_lo": 0.85, "rough_hi": 0.99,
			"pom_depth": 0.012, "pom_steps_near": 10,
			"wet_bias": 0.35, "stain_amt": 0.10,
		}),
	})

	# ---------------- row 4: the players' register --------------------------
	out.append({
		"id": "alu_machined", "label": "aluminium, machined", "row": 4, "shader": "full",
		"range": [0.850, 0.930], "note": "F0 0.91-0.92. Turned lay, edges polished by handling",
		"p": {
			"macro_var": 0.06, "macro_freq": 4.0,
			"alb_lo": Vector3(0.860, 0.870, 0.880),
			"alb_hi": Vector3(0.920, 0.925, 0.930),
			"alb_curve": 1.0, "alb_cell": 0.0,
			"rough_lo": 0.16, "rough_hi": 0.30, "rough_micro": 0.06,
			"metallic": 1.0, "spec": 0.5,
			"form_freq": 8.0, "form_amp": 0.0004, "form_ridge": 0.0,
			"detail_freq": 90.0, "detail_amp": 0.000288,
			"micro_freq": 1400.0, "micro_amp": 3.6e-05,
			"voro_freq": 0.0, "voro_amp": 0.0, "voro2_freq": 0.0, "voro2_amp": 0.0,
			"bed_freq": 0.0, "bed_amp": 0.0, "bed_value": 0.0,
			"lay_amt": 0.17, "lay_freq": 1600.0, "lay_axis": Vector3(0, 0, 1),
			"edge_wear": 0.50,
			"pom_depth": 0.0,
			"wet_gain": 0.7, "wet_bias": 0.0, "wet_darken": 0.95, "wet_rough": 0.05,
			"pool_gain": 1.7, "wet_fill": 0.95, "stain_amt": 0.0,
		},
	})
	var alu: Dictionary = out[out.size() - 1]["p"]
	out.append({
		"id": "alu_anodised", "label": "aluminium, anodised", "row": 4, "shader": "full",
		"range": [0.190, 0.350], "note": "hard anodise, dark grey; wears bright at the edges",
		"p": _merge(alu, {
			"alb_lo": Vector3(0.200, 0.205, 0.215),
			"alb_hi": Vector3(0.320, 0.330, 0.345),
			"rough_lo": 0.34, "rough_hi": 0.50,
			"lay_amt": 0.05, "micro_freq": 900.0, "micro_amp": 5.4e-05,
			"edge_wear": 0.60,
		}),
	})
	out.append({
		"id": "composite", "label": "composite, woven", "row": 4, "shader": "full",
		"range": [0.012, 0.038], "note": "2x2 twill under clear epoxy, F0 0.043",
		"p": {
			"macro_var": 0.08, "macro_freq": 3.0,
			"alb_lo": Vector3(0.014, 0.014, 0.015),
			"alb_hi": Vector3(0.034, 0.034, 0.036),
			"alb_curve": 1.0, "alb_cell": 0.0,
			"rough_lo": 0.18, "rough_hi": 0.34, "rough_micro": 0.05,
			"metallic": 0.0, "spec": 0.55,
			"form_freq": 6.0, "form_amp": 0.0003, "form_ridge": 0.0,
			"detail_freq": 60.0, "detail_amp": 0.00024,
			"micro_freq": 1200.0, "micro_amp": 3.6e-05,
			"voro_freq": 0.0, "voro_amp": 0.0, "voro2_freq": 0.0, "voro2_amp": 0.0,
			"bed_freq": 0.0, "bed_amp": 0.0, "bed_value": 0.0,
			"weave_amt": 0.00022, "weave_freq": 260.0,
			"edge_wear": 0.20, "pom_depth": 0.0,
			"wet_gain": 0.6, "wet_bias": 0.0, "wet_darken": 0.94, "wet_rough": 0.04,
			"pool_gain": 1.8, "wet_fill": 0.95, "stain_amt": 0.0,
		},
	})
	out.append({
		"id": "polymer", "label": "polymer, moulded", "row": 4, "shader": "full",
		"range": [0.014, 0.034], "note": "spark-eroded mould texture, F0 0.04",
		"p": {
			"macro_var": 0.07, "macro_freq": 3.5,
			"alb_lo": Vector3(0.016, 0.016, 0.017),
			"alb_hi": Vector3(0.030, 0.030, 0.032),
			"alb_curve": 1.0, "alb_cell": 0.0,
			"rough_lo": 0.36, "rough_hi": 0.52, "rough_micro": 0.07,
			"metallic": 0.0, "spec": 0.5,
			"form_freq": 12.0, "form_amp": 0.0003, "form_ridge": 0.0,
			"detail_freq": 120.0, "detail_amp": 0.000192,
			"micro_freq": 700.0, "micro_amp": 7.2e-05,
			"voro_freq": 0.0, "voro_amp": 0.0, "voro2_freq": 0.0, "voro2_amp": 0.0,
			"bed_freq": 0.0, "bed_amp": 0.0, "bed_value": 0.0,
			"edge_wear": 0.25, "pom_depth": 0.0,
			"wet_gain": 0.6, "wet_bias": 0.0, "wet_darken": 0.92, "wet_rough": 0.05,
			"pool_gain": 1.7, "wet_fill": 0.95, "stain_amt": 0.0,
		},
	})
	var poly: Dictionary = out[out.size() - 1]["p"]
	out.append({
		"id": "powdercoat", "label": "powder-coated", "row": 4, "shader": "full",
		"range": [0.110, 0.240], "note": "orange peel at 45 cycles/m is the whole tell",
		"p": _merge(poly, {
			"alb_lo": Vector3(0.135, 0.120, 0.090),
			"alb_hi": Vector3(0.225, 0.200, 0.150),
			"rough_lo": 0.38, "rough_hi": 0.56,
			"form_freq": 45.0, "form_amp": 0.00035,
			"micro_freq": 800.0, "micro_amp": 5.4e-05,
			"edge_wear": 0.30,
		}),
	})
	out.append({
		"id": "rubber", "label": "rubber", "row": 4, "shader": "full",
		"range": [0.010, 0.030], "note": "moulded knurl; the darkest thing in the library",
		"p": _merge(poly, {
			"alb_lo": Vector3(0.012, 0.012, 0.013),
			"alb_hi": Vector3(0.026, 0.026, 0.028),
			"rough_lo": 0.68, "rough_hi": 0.93, "rough_micro": 0.15,
			"macro_var": 0.16, "macro_freq": 6.0,
			"form_freq": 18.0, "form_amp": 0.0008,
			"micro_freq": 480.0, "micro_amp": 0.000216,
			"voro_freq": 55.0, "voro_amp": 0.0009, "voro_pebble": 0.60, "voro_warp": 0.3,
			"edge_wear": 0.0,
			"wet_gain": 0.8, "wet_darken": 0.88, "wet_rough": 0.12,
		}),
	})
	out.append({
		"id": "label", "label": "printed label", "row": 4, "shader": "full",
		"range": [0.015, 0.760], "note": "the one UV in the family. Print is 0.02 on 0.72",
		"p": _merge(poly, {
			"print_amt": 1.0,
			"print_bg": Vector3(0.660, 0.655, 0.630),
			"print_fg": Vector3(0.018, 0.018, 0.019),
			"rough_lo": 0.30, "rough_hi": 0.44,
		}),
	})

	return out


# ART-DIRECTION 3.1's four scalars, mapped onto this family's uniforms.
# This is the table the cave spike needs in order to drive the rock per cell.
static func rock_from_scalars(wet: float, fracture: float, bedding: float,
		worked: float) -> Dictionary:
	var p := _rock_base()
	p["wet_bias"] = clampf(wet, 0.0, 1.0)
	p["voro_freq"] = lerpf(3.0, 14.0, clampf((fracture - 3.0) / 11.0, 0.0, 1.0))
	p["voro_amp"] = lerpf(0.004, 0.020, clampf((fracture - 3.0) / 11.0, 0.0, 1.0))
	p["form_ridge"] = clampf((fracture - 3.0) / 11.0, 0.0, 1.0) * 0.8
	var b := clampf((bedding - 0.4) / 3.1, 0.0, 1.0)
	p["bed_freq"] = lerpf(1.7, 4.0, b)          # beds at 0.6 m down to 0.25 m
	p["bed_amp"] = lerpf(0.001, 0.010, b)
	p["bed_value"] = lerpf(0.03, 0.40, b)
	p["stain_amt"] = lerpf(0.55, 0.15, clampf(worked, 0.0, 1.0))
	p["rough_lo"] = lerpf(0.66, 0.52, clampf(worked, 0.0, 1.0))
	p["alb_hi"] = (p["alb_hi"] as Vector3) * lerpf(1.0, 1.35, clampf(worked, 0.0, 1.0))
	return p
