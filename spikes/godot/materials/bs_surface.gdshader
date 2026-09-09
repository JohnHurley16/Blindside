// The full family: every layer compiled in. This is what the testbed uses so
// that one shader can be every material. A shipping project uses the lean
// variants below it for the surfaces that cover the screen.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;
#define BS_F_VORO
#define BS_F_BED
#define BS_F_GRAIN
#define BS_F_METAL
#define BS_F_PRINT
#define BS_F_POM
#include "res://bs_surface_core.gdshaderinc"
