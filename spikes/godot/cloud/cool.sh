#!/bin/sh
# Wait for the GPU to go idle, and report where it is thermally.
#
# THIS MACHINE THROTTLES HARD. Measured mid-session: an RTX 3080 Laptop at 87 C
# runs its SM clock at 780 MHz against a 2100 MHz maximum -- a 2.7x throttle --
# and it does not fall back below about 75 C in any reasonable time even at 0%
# utilisation, because the fan curve does not spin up for an idle GPU. Two runs
# of the same build therefore differ by more than any change in this directory
# does.
#
# So this script does NOT try to wait for cold: that would take ten minutes a
# row. It waits for idle, waits a short fixed settle, and PRINTS the thermal
# state so every row of a table can be read against the conditions it was taken
# in. The ablation controls for drift by interleaving a baseline row between
# every variant instead (see ablate.sh).
SETTLE=${1:-20}
for i in $(seq 1 60); do
  u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | tr -d ' ')
  [ -z "$u" ] && { echo "  [no nvidia-smi]"; exit 0; }
  [ "$u" -lt 12 ] && break
  sleep 2
done
sleep "$SETTLE"
nvidia-smi --query-gpu=temperature.gpu,clocks.sm,utilization.gpu --format=csv,noheader,nounits |
  awk -F, '{printf "  [gpu %s C, %s MHz, %s%%]\n", $1, $2, $3}'
