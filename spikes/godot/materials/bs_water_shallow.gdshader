// Shallow standing water over silt: transparent, refracting.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;
#include "res://bs_water_core.gdshaderinc"
