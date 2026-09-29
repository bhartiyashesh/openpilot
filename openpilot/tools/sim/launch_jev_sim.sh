#!/usr/bin/env bash
# Like launch_openpilot.sh, but runs manager.main() directly (the forkpty relay in
# manager.py dies on macOS) and keeps Experimental Mode + DEC on for the Jev switcher.
export PASSIVE="0" NOBOARD="1" SIMULATION="1" SKIP_FW_QUERY="1" FINGERPRINT="HONDA_CIVIC_2022"
export BLOCK="${BLOCK},camerad,loggerd,encoderd,micd,logmessaged,manage_athenad,manage_sunnylinkd"
export JEV_DIR="${JEV_DIR:-$HOME/.jev-sim}"
cd "$(dirname "$0")/../../system/manager" || exit 1
# activate the repo venv when the caller has not
if ! python3 -c "import openpilot" 2>/dev/null; then
  source "$(pwd)/../../../.venv/bin/activate" || exit 1
fi
python3 -c "
from openpilot.selfdrive.test.helpers import set_params_enabled
from openpilot.common.params import Params
set_params_enabled()
p = Params()
for k in ('ExperimentalMode', 'ExperimentalModeConfirmed', 'DynamicExperimentalControl',
          'AlphaLongitudinalEnabled'):  # sim panda claims BOSCH_LONG; without op long, pcmCruise never engages
    p.put_bool(k, True)
"
exec python3 -X faulthandler -c "from openpilot.system.manager import manager; manager.main()"
