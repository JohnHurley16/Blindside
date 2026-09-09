// The other half of the blending question: alpha over, writing depth. Discs occlude
// each other, so a bank of returns reads as an opaque surface and the far wall stops
// shining through the near one -- at the cost of order artefacts where discs are
// coplanar, and of hiding the map behind itself.
shader_type spatial;
render_mode unshaded, shadows_disabled, cull_disabled, fog_disabled,
	depth_draw_opaque, blend_mix, world_vertex_coords;
#include "res://cloud_body.gdshaderinc"
