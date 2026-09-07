"""Ground truth as plain numbers, for the after-the-run reveal and nothing else.

Nothing in here imports `phase2.truth`. It is the shape truth arrives in when the
window is allowed to draw it, which is once, after a run is over, under a banner
that says so. `match/reveal_builder.py` is the only thing that fills one in, and
it is on the far side of the sensor layer.
"""
