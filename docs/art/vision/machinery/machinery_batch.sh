#!/usr/bin/env bash
# The machinery vision board: every single render, at 40 spp, to its final path.
# Re-runnable: an existing file is skipped. Then run machinery_sheets.py for the composites.
#
#   bash docs/art/vision/machinery/machinery_batch.sh            # everything
#   bash docs/art/vision/machinery/machinery_batch.sh dormant     # only shots whose name contains "dormant"
#
# --out is ABSOLUTE: Blender resolves relative paths against its own cwd.
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/jackh/documents/programming/Blindside"
OUT="$ROOT/docs/art/vision/machinery"
LOG="$OUT/_batch.log"
FILTER="${1:-}"
Q="--samples 40"

shot () { name="$1"; rel="$2"
  if [ -n "$FILTER" ] && [[ "$name" != *"$FILTER"* ]]; then return; fi
  if [ -f "$OUT/$rel" ]; then echo "skip $rel"; return; fi
  mkdir -p "$(dirname "$OUT/$rel")"
  t0=$(date +%s)
  "$BL" -b -P "$ROOT/docs/art/vision/machinery/machinery_probe.py" -- --shot "$name" --out "$OUT/$rel" $Q > "$OUT/_last.log" 2>&1
  rc=$?
  t1=$(date +%s)
  if grep -q -i traceback "$OUT/_last.log"; then rc=99; grep -i -A8 traceback "$OUT/_last.log" | tail -12; fi
  echo "$name -> $rel rc=$rc $((t1-t0))s" | tee -a "$LOG"
}

# C1 dormant
shot dormant_elevation        assayer-dormant/01_clear_elevation.png
shot dormant_plan             assayer-dormant/02_clear_plan.png
shot dormant_footing          assayer-dormant/03_clear_footing.png
shot dormant_bearing          assayer-dormant/04_clear_bearing_boom.png
shot dormant_tank             assayer-dormant/05_clear_tank_sightglass.png
shot dormant_insitu_lamp      assayer-dormant/06_insitu_lamp.png
shot dormant_insitu_drip      assayer-dormant/07_insitu_drip.png
# C2 winding
shot wind_click6_clear        assayer-winding/01_clear_click6.png
shot wind_click1_clear        assayer-winding/_click1_clear.png
shot wind_click5_clear        assayer-winding/_click5_clear.png
shot wind_click9_clear        assayer-winding/_click9_clear.png
shot wind_click1_insitu       assayer-winding/03_insitu_click1.png
shot wind_click5_insitu       assayer-winding/04_insitu_click5.png
shot wind_click9_insitu       assayer-winding/05_insitu_click9.png
shot wind_insitu_wide         assayer-winding/07_insitu_wide_click8.png
shot wind_next_chamber        assayer-winding/08_insitu_next_chamber.png
# C3 firing
shot fire_strike_clear        assayer-firing/01_clear_strike.png
shot fire_strike_machine_height assayer-firing/02_insitu_strike_machine_height.png
shot fire_decay_2s            assayer-firing/03_insitu_decay_2s_lobe.png
shot fire_strike_wide         assayer-firing/04_insitu_strike_wide.png
# C4 scour
shot scour_topdown            assayer-scour/01_clear_topdown.png
shot scour_oblique            assayer-scour/02_clear_oblique.png
shot scour_insitu_lamp        assayer-scour/03_insitu_lamp_edge.png
# C5 iron
shot iron_three_ages          assayer-iron/_three_ages.png
shot iron_casting_macro       assayer-iron/02_clear_casting_macro.png
shot iron_waterline           assayer-iron/03_clear_waterline.png
shot iron_bearing_shine       assayer-iron/04_insitu_bearing_shine.png
# C6 haulage
shot haulage_side_elevation   sibling-haulage/01_clear_side_elevation.png
shot haulage_threequarter     sibling-haulage/02_clear_threequarter.png
shot haulage_bearing_detail   sibling-haulage/03_clear_bearing_detail.png
shot haulage_round_the_curve  sibling-haulage/04_insitu_round_the_curve.png
shot haulage_riding           sibling-haulage/05_insitu_riding.png
shot rails_return_lamp        sibling-haulage/06_insitu_rails_return.png
# C7 bus
shot bus_dead_clear           sibling-bus-live/_dead.png
shot bus_live_clear           sibling-bus-live/_live.png
shot bus_insulator_detail     sibling-bus-live/04_clear_insulator_detail.png
shot bus_corona_from_bank     sibling-bus-live/05_insitu_corona_from_bank.png
shot bus_beacon_in_sump       sibling-bus-live/06_insitu_beacon_in_sump.png
# C8 download
shot download_pose_clear      download/01_clear_pose_footing.png
shot download_pose_macro      download/02_clear_pose_macro.png
shot download_junction_box_clear download/03_clear_pose_junction_box.png
shot download_insitu_wind     download/04_insitu_pose_during_wind.png
shot download_insitu_anvil_glow download/05_insitu_pose_anvil_glow.png
shot download_step_out        download/06_insitu_step_out.png
# C9 spent
shot spent_working_clear      spent/_working.png
shot spent_spent_clear        spent/_spent.png
shot spent_insitu_lamp        spent/04_insitu_spent_lamp.png
# extras
shot slew_index_plan          assayer-slew/_plan_a.png
shot slew_index_plan_b        assayer-slew/_plan_b.png
shot slew_insitu_blur         assayer-slew/02_insitu_blur.png
shot chamber_rule_cutaway     assayer-chamber/_cutaway.png
echo "BATCH DONE" | tee -a "$LOG"
