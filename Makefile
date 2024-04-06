build:
	env SOURCE_DATE_EPOCH="$(git show -s --format=%ct)" python3 -m build

check:
	./check.sh

test:
	python3 -m tests
	python -m examples.test
