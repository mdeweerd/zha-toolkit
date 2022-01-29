lint_python:
	 -shopt -s globstar && pyupgrade --py36-plus **/*.py
	 bandit --recursive --skip B101,B311 .
	 black -l 79 .
	 codespell --ignore-words-list="hass" custom_components
	 flake8 . --count --ignore F841,C901,W503,B006 \
                  --max-complexity=1 --max-line-length=79 \
                  --show-source --statistics
	 mypy --ignore-missing-imports --install-types --non-interactive . 
	 safety check

# No tests, just for reference:
test:
	 pytest .
	 pytest --doctest-modules .

install_requirements:
	pip install --upgrade pip wheel
	pip install bandit black codespell flake8 flake8-2020 flake8-bugbear \
                  flake8-comprehensions isort mypy pytest pyupgrade safety
