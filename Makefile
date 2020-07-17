all: clean package

.PHONY: test
test:
	@echo ----- Running python tests -----
	python3 -m unittest discover

.PHONY: test_docker
# for local testing, CI/CD uses docker github action for testing/pushing images
test_docker:
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
	coverage report --fail-under=65 -m

.PHONY: test_formatting
test_formatting:
	@echo ----- Testing code formatting -----
	black --check .
	@echo

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
	rm -rf dist/ build/ kapitan.egg-info/ bindist/

.PHONY: format_codestyle
format_codestyle:
	which black || echo "Install black with pip3 install --user black"
	# ignores line length and reclass
	black .
	@echo

.PHONY: build_binary
build_binary:
	scripts/build-binary.sh

.PHONY: test_binary
test_binary:
	python3 -m unittest tests.test_binary

.PHONY: build_helm_binding
build_helm_binding:
	bash kapitan/inputs/helm/build.sh

.PHONY: build_helm_fetch_binding
build_helm_fetch_binding:
	bash kapitan/dependency_manager/helm/build.sh
