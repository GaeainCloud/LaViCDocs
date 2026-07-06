#!/usr/bin/env bash
set -euo pipefail

# Install local blender_mcp_addon.py into Blender user add-ons directory (macOS).
# Usage:
#   bash scripts/install_blender_mcp_addon.sh
#   bash scripts/install_blender_mcp_addon.sh 4.2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ADDON_SRC="${PROJECT_ROOT}/src/blender_mcp_addon.py"
BLENDER_BASE="${HOME}/Library/Application Support/Blender"

if [[ ! -f "${ADDON_SRC}" ]]; then
  echo "ERROR: Addon source not found: ${ADDON_SRC}" >&2
  exit 1
fi

if [[ ! -d "${BLENDER_BASE}" ]]; then
  echo "ERROR: Blender user directory not found: ${BLENDER_BASE}" >&2
  echo "Install and launch Blender once, then rerun this script." >&2
  exit 2
fi

TARGET_VERSION="${1:-}"

install_to_version() {
  local version_dir="$1"
  local addon_dir="${version_dir}/scripts/addons"
  mkdir -p "${addon_dir}"
  cp "${ADDON_SRC}" "${addon_dir}/blender_mcp_addon.py"
  echo "Installed addon -> ${addon_dir}/blender_mcp_addon.py"
}

if [[ -n "${TARGET_VERSION}" ]]; then
  TARGET_DIR="${BLENDER_BASE}/${TARGET_VERSION}"
  if [[ ! -d "${TARGET_DIR}" ]]; then
    echo "ERROR: Blender version directory does not exist: ${TARGET_DIR}" >&2
    exit 3
  fi
  install_to_version "${TARGET_DIR}"
else
  FOUND=0
  while IFS= read -r -d '' version_dir; do
    FOUND=1
    install_to_version "${version_dir}"
  done < <(find "${BLENDER_BASE}" -mindepth 1 -maxdepth 1 -type d -print0)

  if [[ "${FOUND}" -eq 0 ]]; then
    echo "ERROR: No Blender version directories found under ${BLENDER_BASE}" >&2
    exit 4
  fi
fi

cat <<'EOF'
Next steps in Blender:
1. Edit > Preferences > Add-ons
2. Search "Blender MCP" and enable it
3. Open 3D View > Sidebar > BlenderMCP
4. Set Port to 9876
5. Click "Connect to MCP server"
EOF
