lint_python:  # And markdown format
	-shopt -s globstar && pyupgrade --py37-plus **/*.py
	bandit --recursive --skip B101,B311 .
	black -l 79 .
	codespell --ignore-words-list="hass" custom_components README.md
	-autoflake8 -i -r --expand-star-imports custom_components
	flake8 . --count --ignore W503 \
                 --max-complexity=20 --max-line-length=79 \
                 --show-source --statistics
	mypy --ignore-missing-imports --install-types --non-interactive .
	# safety check
	mdformat --wrap 75 README.md --number

# No tests, just for reference:
test:
	pytest .
	pytest --doctest-modules .

install_requirements:
	pip install --upgrade pip wheel
	pip install --upgrade bandit black codespell flake8 flake8-2020 flake8-bugbear \
                  flake8-comprehensions isort mypy pytest pyupgrade safety \
	          autoflake8 mdformat mdformat-toc

upgrade_unsafe:
	A="$$(safety check --bare)" ; [ "$$A" == "" ] || pip install --upgrade $$A

setup_precommit:
	pip install --upgrade pip pre-commit tox
	pre-commit install
