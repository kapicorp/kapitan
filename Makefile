all: clean package

.PHONY: test
test:
	python3 -m unittest discover

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
