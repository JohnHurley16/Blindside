// BLD-32: `World` is `pub(crate)`; naming it from another crate must not compile.
use blindside_sim::World;

fn main() {
    let _w: Option<World> = None;
}
