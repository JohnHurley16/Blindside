"""Copy the flat renders in _render/ into cave/<concept>/NN_name.png.

The table below is the board's order: one concept per inventory id (B1..B17), shots in
the order clear -> in-situ -> variants. Run with any Python 3:

    python sort_into_concepts.py            # copy what exists, report what is missing
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_render")

# concept slug -> ordered shot names (the number is the position in this list)
BOARD = {
    "cave-shaft": [
        "b1_01_clear_cutaway", "b1_02_clear_aven_only", "b1_03_insitu_pool",
        "b1_04_insitu_leaving", "b1_05_insitu_lookup",
    ],
    "cave-width": [
        "b2_01_clear_section_crawl", "b2_01_clear_section_narrow", "b2_01_clear_section_passage",
        "b2_01_clear_section_hall", "b2_02_clear_scout_crawl", "b2_03_clear_hauler_crawl",
        "b2_04_insitu_crawl_lamp", "b2_05_insitu_hall_lamp",
    ],
    "cave-chamber": ["b3_01_clear_cutaway", "b3_02_insitu_one_lamp", "b3_03_insitu_beacon_far"],
    "cave-waterline": [
        "b4_01_clear_section", "b4_02_clear_grazing", "b4_03_insitu_pool_returns",
        "b4_04_insitu_wet_streak", "b4_05_insitu_dry_same",
    ],
    "cave-underwater": [
        "b5_01a_clear_above", "b5_01b_clear_below", "b5_04_clear_light_death",
        "b5_02_insitu_swimmer_lamp", "b5_03_insitu_from_above",
    ],
    "cave-silt": [
        "b6_01a_insitu_stopped", "b6_01b_insitu_walking", "b6_01c_insitu_blinded",
        "b6_02_insitu_plume_behind",
    ],
    "cave-rock": [
        "b7_01_clear_swatches", "b7_02_clear_three_values", "b7_03_insitu_absorbent",
        "b7_04_insitu_reflective",
    ],
    "cave-magnetic": ["b8_01a_insitu_noisy", "b8_01b_insitu_deposit"],
    "cave-unstable": [
        "b9_01_clear_sets", "b9_04_clear_fracture_set", "b9_02_insitu_failed_set",
        "b9_03_insitu_fracture_set",
    ],
    "cave-thermal": ["b10_01_clear_band", "b10_02_insitu_lamp_up", "b10_03_insitu_condensation"],
    "cave-depth": [
        "b11_01a_clear_shallow", "b11_01b_clear_middle", "b11_01c_clear_deep",
        "b11_02a_insitu_shallow", "b11_02b_insitu_middle", "b11_02c_insitu_deep",
    ],
    "works-drive": [
        "b12_01_clear_down_drive", "b12_02_clear_section_endon", "b12_03_insitu_drive_lamp",
        "b12_04_insitu_machine_height",
    ],
    "works-rails": [
        "b13_01_clear_railhead", "b13_04_clear_gauge_topdown", "b13_02_insitu_rails_long",
        "b13_03_insitu_machine_height",
    ],
    "works-bus": ["b14_01_clear_conductor", "b14_02_clear_insulator", "b14_03_insitu_row"],
    "works-plates": [
        "b15_01_clear_plate_macro", "b15_02_clear_shallow_deep", "b15_03_insitu_plate_1m",
        "b15_04_insitu_lamp_off_it",
    ],
    "works-machine-ground": [
        "b16_01_clear_pump_chamber", "b16_02_insitu_one_lamp", "b16_03_insitu_winch_glow",
    ],
    "works-junction": ["b17_01_clear_crosscut", "b17_02_insitu_crosscut"],
}


def target_name(shot, idx):
    # strip the 'bN_MM[x]_' prefix; keep the descriptive tail
    parts = shot.split("_", 2)
    tail = parts[2] if len(parts) > 2 else shot
    return f"{idx:02d}_{tail}.png"


def main():
    missing, copied = [], 0
    for concept, shots in BOARD.items():
        dst_dir = os.path.join(HERE, concept)
        os.makedirs(dst_dir, exist_ok=True)
        for i, shot in enumerate(shots, 1):
            src = os.path.join(SRC, shot + ".png")
            dst = os.path.join(dst_dir, target_name(shot, i))
            if not os.path.exists(src):
                missing.append(shot)
                continue
            if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                shutil.copyfile(src, dst)
                copied += 1
    print(f"copied {copied}; missing {len(missing)}: {' '.join(missing)}")
    if "--table" in sys.argv:
        for concept, shots in BOARD.items():
            print(concept)
            for i, shot in enumerate(shots, 1):
                print("   ", target_name(shot, i), "<-", shot)


if __name__ == "__main__":
    main()
