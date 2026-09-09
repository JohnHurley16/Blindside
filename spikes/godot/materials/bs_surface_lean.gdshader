// Lean variant: rock, granular, aggregate and concrete only. No metal, no
// timber grain, no printed label. Same file, same uniforms, three features
// removed at compile time -- this is the one an environment spike puts on the
// rock shell and on the floor, where it covers the screen.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;
#define BS_F_VORO
#define BS_F_BED
#define BS_F_POM
#include "res://bs_surface_core.gdshaderinc"
