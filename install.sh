#!/bin/sh
set -eu
project_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
install_dir="$project_dir/.install"
workspace=${1:-"$project_dir"}
if [ "$#" -gt 1 ]; then
    echo 'Usage: sh install.sh [workspace-directory]' >&2
    exit 2
fi
mkdir -p "$install_dir"
if command -v uv >/dev/null 2>&1; then
    uv_command=$(command -v uv)
elif [ -x "$install_dir/uv/uv" ]; then
    uv_command="$install_dir/uv/uv"
else
    echo 'Installing uv locally (no sudo required)...'
    installer="$install_dir/uv-installer.sh"
    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --show-error --silent https://astral.sh/uv/install.sh -o "$installer"
    elif command -v wget >/dev/null 2>&1; then
        wget -q https://astral.sh/uv/install.sh -O "$installer"
    else
        echo 'Install curl or wget, then run this script again.' >&2
        exit 1
    fi
    UV_UNMANAGED_INSTALL="$install_dir/uv" sh "$installer"
    uv_command="$install_dir/uv/uv"
fi
export UV_PROJECT_ENVIRONMENT="$install_dir/venv"
"$uv_command" sync --project "$project_dir" --locked --no-dev --python 3.12
python="$UV_PROJECT_ENVIRONMENT/bin/python"
"$python" -m winproladder_mcp.setup check
"$python" -m winproladder_mcp.setup prepare --root "$workspace" --config-dir "$install_dir"
