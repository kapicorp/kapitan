all: clean package

.PHONY: test
test:
	@echo ----- Running python tests -----
	python3 -m unittest discover

.PHONY: test_docker
test_docker:
	@echo ----- Testing build of docker image -----
	docker build . --no-cache -t kapitan
	@echo ----- Testing run of docker image -----
	docker run -ti --rm kapitan --help
	docker run -ti --rm kapitan lint

.PHONY: test_coverage
test_coverage:
	@echo ----- Testing code coverage -----
	coverage run --source=kapitan -m unittest discover
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

.PHONY: local_serve_documentation
local_serve_documentation:
	docker build -f Dockerfile.docs --no-cache -t kapitan-docs .
	docker run --rm -v $(PWD):/docs -p 8000:8000 kapitan-docs

.PHONY: mkdocs_gh_deploy
mkdocs_gh_deploy: # to run locally assuming git ssh access
	docker build -f Dockerfile.docs --no-cache -t kapitan-docs .
	docker run --rm -it -v $(PWD):/src -v ~/.ssh:/root/.ssh -w /src kapitan-docs gh-deploy -f ./mkdocs.yml
