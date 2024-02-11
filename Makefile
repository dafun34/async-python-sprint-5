format:
	isort .
	black .

check:
	flake8 .
