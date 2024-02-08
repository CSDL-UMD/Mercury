#!/bin/bash
set -euo pipefail


if [[ ${#} != 1 ]];
then
    >&2 echo "Error: wrong number of arguments: ${*}"
    >&2 echo "Usage: ${0} CONF"
    >&2 echo "  CONF - path to config .INI file"
    exit 1
fi

# TODO do not hardcode these; use parameters instead
USER=ubuntu
HOST=mercury
CONF=${1}
SYSTEMDCONF=mercuryproj/samples/mercuryproj.service

sshrun() {
    ssh "${USER}@${HOST}" "${@}"
}

# Activate virtual environment for build, if present.
# XXX (need to adapt it in case of conda)
source .venv/bin/activate

pip="python3 -m pip"
ensurepip="python3 -m ensurepip"
build="python3 -m build"

# Ensure pip is installed
if ! ${pip} >/dev/null 2>&1;
then
    ${ensurepip} >/dev/null 2>&1;
fi

# Ensure build is installed
if ! ${build} --help >/dev/null 2>&1;
then
    ${pip} install build
fi

# Delete build and dist folder
rm -rf build/ dist/

# Create wheel
${build} --wheel

# Upload it on host
WHEELFILE=$(find dist -type f)
rsync -aP "$WHEELFILE" "${USER}@${HOST}:"

# Check there is a user config dir on host; if not, create it
if [[ -e "${CONF}" ]];
then

    sshrun 'if ! [[ -d .config/mercuryproj ]]; then mkdir -p .config/mercuryproj; fi'
fi

# Upload config file on host
rsync -aP "${CONF}" "${USER}@${HOST}:.config/mercuryproj/config.ini"

# Create virtual environment on host; activate it; ensure pip; install the wheel
sshrun python3 -m venv .venv
sshrun .venv/bin/python -m ensurepip
sshrun .venv/bin/python -m pip install --force-reinstall "${WHEELFILE/dist\//}"

# Start systemd service
rsync -aP "${SYSTEMDCONF}" "${USER}@${HOST}:"
sshrun sudo cp mercuryproj.service /etc/systemd/system
sshrun sudo systemctl daemon-reload
sshrun sudo systemctl stop mercuryproj
sshrun sudo systemctl start mercuryproj
sshrun sudo systemctl enable mercuryproj

# Test that service is running
sshrun sudo systemctl is-active mercuryproj && echo "Deployment successful." || echo "Deployment failed!"

# Run health check
resp=$(curl -s https://mercuryproj.umd.edu/health/check)
echo "Health check: ${resp}"
