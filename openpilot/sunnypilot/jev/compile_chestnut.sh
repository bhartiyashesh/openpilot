#!/usr/bin/env bash
# One-time big-model compile for chestnut on a prebuilt branch (no scons on device).
# Needs the chestnut attached with its link up and big_driving_supercombo.onnx in
# selfdrive/modeld/models/ (765 MB, LFS sha 1791d594...). Takes a while; run from SSH:
#   cd /data/openpilot && ./openpilot/sunnypilot/jev/compile_chestnut.sh
set -e
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
MD="$ROOT/openpilot/selfdrive/modeld"
export PYTHONPATH="$ROOT:$ROOT/tinygrad_repo"
python3 -c "from openpilot.system.hardware.chestnut.flash import link_up; import sys; sys.exit(0 if link_up() else 1)" \
  || { echo "chestnut link is not up (attach it and turn the car on)"; exit 1; }
[ -f "$MD/models/big_driving_supercombo.onnx" ] || { echo "big_driving_supercombo.onnx missing"; exit 1; }
cd "$MD"
DEBUG=1 DEV=USB+AMD:LLVM FRAME_DEV=CPU FLOAT16=1 JIT_BATCH_SIZE=0 GMMU=0 TC_OPT=2 TC_OCCUPANCY_OPT=1 \
python3 compile_modeld.py \
  --model-size 512x256 --camera-resolutions 1344x760 \
  --onnx "$MD/models/big_driving_supercombo.onnx" \
  --output "$MD/models/big_driving_tinygrad.pkl" --frame-skip 4
echo "compiled: $(ls -la "$MD"/models/big_driving_tinygrad.pkl)"
echo "reboot (or ignition cycle) and modeld will pick up the big model when chestnut is linked"
