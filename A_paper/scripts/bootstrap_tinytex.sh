#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${ROOT_DIR}/.TinyTeX"
INSTALL_SCRIPT="${ROOT_DIR}/.tinytex-install.sh"

if [[ ! -d "${INSTALL_DIR}" ]]; then
  export TINYTEX_DIR="${INSTALL_DIR}"
  mkdir -p "${INSTALL_DIR}"
  curl -fsSL https://yihui.org/tinytex/install-bin-unix.sh -o "${INSTALL_SCRIPT}"
  bash "${INSTALL_SCRIPT}"
  rm -f "${INSTALL_SCRIPT}"
fi

if compgen -G "${INSTALL_DIR}/bin/*" > /dev/null; then
  TEXBIN_DIR="$(echo "${INSTALL_DIR}"/bin/*)"
elif compgen -G "${INSTALL_DIR}/.TinyTeX/bin/*" > /dev/null; then
  TEXBIN_DIR="$(echo "${INSTALL_DIR}"/.TinyTeX/bin/*)"
else
  echo "Could not locate TinyTeX binaries under ${INSTALL_DIR}" >&2
  exit 1
fi

"${TEXBIN_DIR}/tlmgr" option repository https://mirror.ctan.org/systems/texlive/tlnet
"${TEXBIN_DIR}/tlmgr" install latexmk xetex ctex collection-langchinese
