// Distant variant: no parallax, no voronoi, no bedding. Two normal bands and
// the field. For anything past the parallax range, and for the thousands of
// scattered instances that are never close to the lamp.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_schlick_ggx;
#include "res://bs_surface_core.gdshaderinc"
