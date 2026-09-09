// Additive, no depth at all: every disc sums. Order-independent, so no sorting is
// needed and none is done. This is the x-ray register -- the whole believed map is
// visible through itself, which is what a survey wants and what ART 8.3 means by
// "belief is the subject".
shader_type spatial;
render_mode unshaded, shadows_disabled, cull_disabled, fog_disabled,
	depth_draw_never, depth_test_disabled, blend_add, world_vertex_coords;
#include "res://cloud_body.gdshaderinc"
