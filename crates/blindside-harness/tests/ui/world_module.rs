// BLD-32: the `world` module is private; opening it from another crate must not compile.
fn main() {
    let _w: Option<blindside_sim::world::World> = None;
}
