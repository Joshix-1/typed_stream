FAILED=""

echo mypy:
python3 -m mypy || FAILED="${FAILED}mypy "

# echo stricter mypy:
# python3 -m mypy --disallow-any-expr -p typed_stream || FAILED="${FAILED}mypy "

echo pytype:
python3 -m pytype || FAILED="${FAILED}pytype "

# echo pyright:
# python3 -m pyright || FAILED="${FAILED}pyright "

# echo pyre:
# python3 -m pyre || FAILED="${FAILED}pyre "

if [ -n "${FAILED}" ]; then
  echo "${FAILED}"
  exit 1
fi
