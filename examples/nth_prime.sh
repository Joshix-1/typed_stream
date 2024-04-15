#!/bin/sh
set -e

if [ -z "$1" ]; then
  N="1"
else
  N="$1"
fi

set -u

if [ -f "./nth_prime.sh" ]; then
  DIR="."
elif [ -f "./examples/nth_prime.sh" ]; then
  DIR="./examples"
else
  DIR="$(dirname "$0")"
fi

"${DIR}/print_primes.py" | "${DIR}/head.py" - "${N}" 2> /dev/null | "${DIR}/tail.py" - 1 2> /dev/null
