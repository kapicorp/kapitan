all: clean package

.PHONY: test
test:
	@echo ----- Running python tests -----
	python3 -m unittest discover
	@echo ----- Testing build of docker image -----
	docker build . --no-cache -t kapitan
	@echo ----- Testing run of docker image -----
	docker run -ti --rm kapitan --help
	docker run -ti --rm kapitan lint
	@echo ----- Testing build of docker ci image -----
	docker build . --no-cache -t kapitan-ci -f Dockerfile.ci
	@echo ----- Testing run of docker ci image -----
	docker run -ti --rm kapitan-ci kapitan --help
	docker run -ti --rm kapitan-ci kapitan lint

.PHONY: test_coverage
test_coverage:
	@echo ----- Testing code coverage -----
	coverage run --source=kapitan --omit="*reclass*" -m unittest discover
	coverage report --fail-under=60 -m

.PHONY: release
release:
ifeq ($(version),)
	@echo Please pass version to release e.g. make release version=0.16.5
else
	scripts/inc_version.sh $(version)
endif

.PHONY: package
package:
	python3 setup.py sdist bdist_wheel

.PHONY: clean
clean:
	rm -rf dist/ build/ kapitan.egg-info/

.PHONY: codestyle
codestyle:
	which flake8 || echo "Install flake8 with pip3 install --user flake8"
	# ignores line length and reclass related errors
	flake8 --ignore E501 . --exclude=reclass
	@echo
