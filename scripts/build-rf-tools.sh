#!/usr/bin/env bash
# Build missing tools in user-owned isolated prefixes, with one low-priority job.
set -euo pipefail
(( EUID != 0 )) || { echo 'Run this build stage as the desktop user.' >&2; exit 1; }
TASK_RF_ROOT="$HOME/.local/share/verdant-rf"
mkdir -p "$TASK_RF_ROOT" "$HOME/.local/bin"
log="$TASK_RF_ROOT/build-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$log") 2>&1
export CMAKE_BUILD_PARALLEL_LEVEL=1
publish_wrapper() {
    local name="$1" target="$2" temporary
    if [[ -e "$HOME/.local/bin/$name" || -L "$HOME/.local/bin/$name" ]]; then
        cp -a -- "$HOME/.local/bin/$name" "$TASK_RF_ROOT/$name.backup-$(date +%s)" || return
    fi
    temporary=$(mktemp "$HOME/.local/bin/.rf-wrapper-XXXXXX") || return
    printf '#!/usr/bin/env bash\nexport PYTHONPATH="%s${PYTHONPATH:+:$PYTHONPATH}"\nexport LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexec "%s" "$@"\n' "${3:-}" "${4:-}" "$target" > "$temporary" || return
    chmod 755 "$temporary" || return
    mv -- "$temporary" "$HOME/.local/bin/$name" || return
}
build_urh() {
    local venv="$TASK_RF_ROOT/urh-2.10.0"
    python3 -m venv --system-site-packages "$venv" || return
    nice -n 10 "$venv/bin/python" -m pip install --no-build-isolation --no-deps 'urh==2.10.0' || return
    "$venv/bin/python" -c 'import urh; import urh.cythonext.signal_functions' || return
    QT_QPA_PLATFORM=offscreen "$venv/bin/urh" --help || return
    publish_wrapper urh "$venv/bin/urh"
}
build_gsm() {
    local commit=7f37c7a067d041ce3e26c1387cad095ab4087793 source prefix build pyver
    source="$TASK_RF_ROOT/gr-gsm-$commit-source"
    prefix="$TASK_RF_ROOT/gr-gsm-$commit"
    build="$TASK_RF_ROOT/gr-gsm-$commit-build"
    if [[ ! -d "$source/.git" ]]; then
        [[ ! -e "$source" ]] || { echo 'Source destination already exists; preserving it.' >&2; return 1; }
        git clone https://github.com/ptrkrysik/gr-gsm.git "$source" || return
    fi
    [[ "$(git -C "$source" remote get-url origin)" == https://github.com/ptrkrysik/gr-gsm.git ]] || return 1
    [[ -z "$(git -C "$source" status --porcelain)" ]] || { echo 'Source was edited; preserving it.' >&2; return 1; }
    git -C "$source" checkout --detach "$commit" || return
    pyver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    nice -n 10 cmake -S "$source" -B "$build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DENABLE_DOXYGEN=OFF -DGR_PYTHON_DIR="$prefix/lib/python$pyver/site-packages" -DPYTHON_EXECUTABLE=/usr/bin/python3 || return
    nice -n 10 cmake --build "$build" --parallel 1 || return
    cmake --install "$build" || return
    export PYTHONPATH="$prefix/lib/python$pyver/site-packages${PYTHONPATH:+:$PYTHONPATH}"
    export LD_LIBRARY_PATH="$prefix/lib:$prefix/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    python3 -c 'import grgsm' || return
    "$prefix/bin/grgsm_decode" --help || return
    for executable in "$prefix"/bin/grgsm_*; do
        [[ -x "$executable" ]] || continue
        publish_wrapper "${executable##*/}" "$executable" "$prefix/lib/python$pyver/site-packages" "$prefix/lib:$prefix/lib/aarch64-linux-gnu" || return
    done
}
failed=0
if ! build_urh; then echo 'URH BUILD FAILED; see visible errors and log.' >&2; failed=1; fi
if ! build_gsm; then echo 'GR-GSM BUILD FAILED; see visible errors and log.' >&2; failed=1; fi
printf 'Build log: %s\n' "$log"
exit "$failed"
