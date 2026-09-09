# ---------------------------------------------------------------------------
# BLINDSIDE -- the lens/sensor CompositorEffect.  TRAILER.md 9.
#
# WHAT GODOT 4.7 ACTUALLY GIVES YOU, established by probing ClassDB rather than
# assumed (the probe is in CINEMA.md):
#
#   on Environment      tonemap (AgX, with its own white and contrast in 4.7),
#                       glow/bloom, SSR, SSAO, SSIL, SDFGI, fog, volumetric fog,
#                       adjustment brightness/contrast/saturation + a LUT
#   on CameraAttributes depth of field (Practical: near/far distance and
#                       transition), exposure, auto-exposure
#   NOT ANYWHERE        motion blur, vignette, chromatic aberration, film grain,
#                       lens distortion. Godot 4.7 has no motion blur of any
#                       kind, per-object or camera, and no velocity pass is
#                       produced unless something asks for motion vectors.
#
# So those five are this file. One compute dispatch at POST_TRANSPARENT plus one
# texture copy, on the HDR colour buffer before tonemapping.
#
# Per-object motion blur was considered and is not built: the cave is static
# geometry and one lamp, so the only thing moving in any cave shot is the camera
# itself, and camera reprojection is exact for 100% of those pixels. The two
# exceptions are the drip and mote particles, which get the camera's velocity
# instead of their own -- a few dozen pixels a frame. See CINEMA.md.
# ---------------------------------------------------------------------------
extends CompositorEffect
class_name CinemaLens

const F_DISTORT: int = 1
const F_CA: int = 2
const F_VIGNETTE: int = 4
const F_GRAIN: int = 8
const F_MBLUR: int = 16
const F_VELDBG: int = 32
const F_BLIT: int = 64

# --- knobs, all set by CinemaGrade -----------------------------------------
var flags: int = 0
# barrel distortion coefficient. Negative is barrel. Sub-percent.
var k_distort: float = 0.0
# lateral chromatic aberration at the frame corner, in pixels
var ca_px: float = 1.6
# how much of the cos^4 law survives the lens design. 1.0 = a pinhole.
var vig_k: float = 0.55
var cos4_corner: float = 1.0
# 180 degree shutter = the shutter is open for half a frame interval
var shutter: float = 0.5
var max_blur_px: float = 40.0
var taps: int = 9
# sensor. full_well is electrons at signal 1.0; read_noise is the floor.
var full_well: float = 9000.0
var read_noise: float = 0.00085
var grain_px: float = 1.6
var seedt: float = 0.0

# In offline capture the rig renders each shot frame many times over to let the
# fog and the shadow atlas settle, so "the previous rendered frame" is the SAME
# pose and the blur would be zero. The rig therefore hands in the previous SHOT
# frame's camera transform explicitly.
var use_external_prev: bool = false
var external_prev: Transform3D = Transform3D.IDENTITY

var rd: RenderingDevice
var shader: RID
var pipeline: RID
var sampler: RID
var ubo: RID
var ubo2: RID
var _prev_live: Transform3D = Transform3D.IDENTITY
var _have_prev: bool = false
var _failed: bool = false

func _init() -> void:
	effect_callback_type = CompositorEffect.EFFECT_CALLBACK_TYPE_POST_TRANSPARENT
	access_resolved_color = true
	access_resolved_depth = true
	needs_motion_vectors = false
	RenderingServer.call_on_render_thread(_init_rd)

func _init_rd() -> void:
	rd = RenderingServer.get_rendering_device()
	if rd == null:
		_failed = true
		return
	var f: RDShaderFile = load("res://lens.glsl")
	if f == null:
		push_error("CINEMA: lens.glsl did not load")
		_failed = true
		return
	var spirv: RDShaderSPIRV = f.get_spirv()
	var err: String = spirv.compile_error_compute
	if err != "":
		push_error("CINEMA SHADER ERROR (lens.glsl compute): " + err)
		_failed = true
		return
	shader = rd.shader_create_from_spirv(spirv)
	pipeline = rd.compute_pipeline_create(shader)
	var ss := RDSamplerState.new()
	ss.min_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	ss.mag_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	ss.repeat_u = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	ss.repeat_v = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	ss.repeat_w = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	sampler = rd.sampler_create(ss)
	ubo = rd.uniform_buffer_create(192)
	ubo2 = rd.uniform_buffer_create(192)

func _notification(what: int) -> void:
	if what == NOTIFICATION_PREDELETE and rd != null:
		for r in [pipeline, shader, sampler, ubo, ubo2]:
			if r.is_valid():
				rd.free_rid(r)

func _mkset(src: RID, dep: RID, dst: RID, buf: RID) -> RID:
	var u0 := RDUniform.new()
	u0.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	u0.binding = 0
	u0.add_id(sampler); u0.add_id(src)
	var u1 := RDUniform.new()
	u1.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	u1.binding = 1
	u1.add_id(sampler); u1.add_id(dep)
	var u2 := RDUniform.new()
	u2.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
	u2.binding = 2
	u2.add_id(dst)
	var u3 := RDUniform.new()
	u3.uniform_type = RenderingDevice.UNIFORM_TYPE_UNIFORM_BUFFER
	u3.binding = 3
	u3.add_id(buf)
	return UniformSetCacheRD.get_cache(shader, 0, [u0, u1, u2, u3])

func _uset(src: RID, dep: RID, dst: RID) -> RID:
	return _mkset(src, dep, dst, ubo)

func _uset2(src: RID, dep: RID, dst: RID) -> RID:
	return _mkset(src, dep, dst, ubo2)

static func _pack_proj(b: PackedFloat32Array, o: int, p: Projection) -> void:
	var cols := [p.x, p.y, p.z, p.w]
	for c in range(4):
		var v: Vector4 = cols[c]
		b[o + c * 4 + 0] = v.x
		b[o + c * 4 + 1] = v.y
		b[o + c * 4 + 2] = v.z
		b[o + c * 4 + 3] = v.w

func _render_callback(cb_type: int, render_data: RenderData) -> void:
	if _failed or rd == null or flags == 0:
		return
	if cb_type != CompositorEffect.EFFECT_CALLBACK_TYPE_POST_TRANSPARENT:
		return
	var buffers: RenderSceneBuffersRD = render_data.get_render_scene_buffers()
	var scene: RenderSceneData = render_data.get_render_scene_data()
	if buffers == null or scene == null:
		return
	var size: Vector2i = buffers.get_internal_size()
	if size.x == 0 or size.y == 0:
		return

	# a scratch target the same shape as the colour buffer. create_texture is a
	# no-op after the first frame; it is keyed on context+name.
	buffers.create_texture("cinema", "tmp", RenderingDevice.DATA_FORMAT_R16G16B16A16_SFLOAT,
		RenderingDevice.TEXTURE_USAGE_STORAGE_BIT | RenderingDevice.TEXTURE_USAGE_SAMPLING_BIT
		| RenderingDevice.TEXTURE_USAGE_CAN_COPY_FROM_BIT,
		RenderingDevice.TEXTURE_SAMPLES_1, size, 1, 1, true, false)

	var cam: Transform3D = scene.get_cam_transform()
	var prev: Transform3D = external_prev if use_external_prev else _prev_live
	if not use_external_prev and not _have_prev:
		prev = cam
	var views: int = buffers.get_view_count()
	for v in range(views):
		var proj: Projection = scene.get_view_projection(v)
		var vp: Projection = proj * Projection(cam.affine_inverse())
		var pvp: Projection = proj * Projection(prev.affine_inverse())
		var inv_vp: Projection = vp.inverse()

		var b := PackedFloat32Array()
		b.resize(48)
		_pack_proj(b, 0, inv_vp)
		_pack_proj(b, 16, pvp)
		b[32] = float(size.x); b[33] = float(size.y)
		b[34] = 0.5 / float(size.x); b[35] = 0.5 / float(size.y)
		b[36] = k_distort
		b[37] = ca_px
		b[38] = vig_k
		b[39] = cos4_corner
		b[40] = shutter
		b[41] = max_blur_px
		b[42] = full_well
		b[43] = read_noise
		b[44] = grain_px
		b[45] = seedt
		var bytes: PackedByteArray = b.to_byte_array()
		bytes.encode_s32(184, taps)
		bytes.encode_s32(188, flags)
		rd.buffer_update(ubo, 0, 192, bytes)

		var col: RID = buffers.get_color_layer(v)
		var dep: RID = buffers.get_depth_layer(v)
		var tmp: RID = buffers.get_texture_slice("cinema", "tmp", v, 0, 1, 1)

		var gx: int = (size.x + 7) / 8
		var gy: int = (size.y + 7) / 8
		# pass 1: the lens and the sensor, colour -> scratch
		var cl: int = rd.compute_list_begin()
		rd.compute_list_bind_compute_pipeline(cl, pipeline)
		rd.compute_list_bind_uniform_set(cl, _uset(col, dep, tmp), 0)
		rd.compute_list_dispatch(cl, gx, gy, 1)
		rd.compute_list_end()
		# pass 2: scratch -> colour, 1:1
		bytes.encode_s32(188, F_BLIT)
		rd.buffer_update(ubo2, 0, 192, bytes)
		var cl2: int = rd.compute_list_begin()
		rd.compute_list_bind_compute_pipeline(cl2, pipeline)
		rd.compute_list_bind_uniform_set(cl2, _uset2(tmp, dep, col), 0)
		rd.compute_list_dispatch(cl2, gx, gy, 1)
		rd.compute_list_end()
	_prev_live = cam
	_have_prev = true
