FAILED=""

echo mypy:
python3 -m mypy --pretty || FAILED="${FAILED}mypy "

echo pytype:
python3 -m pytype || FAILED="${FAILED}pytype "

if [ -n "${FAILED}" ]; then
  echo ${FAILED}
  exit 1
fi
