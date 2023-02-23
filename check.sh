#!/bin/sh
set -eu

if [ -d venv ]; then
  # shellcheck disable=SC1091
  if ! . venv/bin/activate; then
    echo "Activating venv failed"
    echo "You have a venv directory, but it isn't a valid Python virtual environment"
    echo 'Either run "rm -r venv" or run "python -m venv venv"'
    exit 1
  fi
fi

pip_install="python3 -m pip install -U --disable-pip-version-check --require-virtualenv --quiet"
${pip_install} "pip>=23.0" wheel; exit_code="$?"
if [ "${exit_code}" -ne 0 ] && [ "${exit_code}" -ne 3 ]; then
  echo "Installing pip>=23.0 and wheel failed"
  exit 1
fi
${pip_install} -r requirements-dev.txt; exit_code="$?"
if [ "${exit_code}" -ne 0 ] && [ "${exit_code}" -ne 3 ]; then
  echo "Installing requirements in requirements-dev.txt failed"
  exit 1
fi

FAILED=0

echo isort:
python3 -m isort . || FAILED=$(( 2 | FAILED ))

echo Black:
if ! python3 -m black --check --diff --color .; then
  echo 'Run "python3 -m black ." to reformat'
  FAILED=$(( 4 | FAILED ))
fi

echo type checks:
./check_types.sh || FAILED=$(( 8 | FAILED ))

echo Flake8:
python3 -m flake8 --show-source || FAILED=$(( 16 | FAILED ))

echo Pylint:
python3 -m pylint . || FAILED=$(( 32 | FAILED ))

echo Bandit:
python3 -m bandit -q -c pyproject.toml -r typed_stream examples || FAILED=$(( 64 | FAILED ))

echo Tests:
python3 -m test || FAILED=$(( 128 | FAILED ))

exit "${FAILED}"
