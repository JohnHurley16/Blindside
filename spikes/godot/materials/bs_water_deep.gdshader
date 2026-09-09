// Deep standing water: opaque, so that screen-space reflection can run on it.
shader_type spatial;
render_mode depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;
#define BS_WATER_OPAQUE
#include "res://bs_water_core.gdshaderinc"
