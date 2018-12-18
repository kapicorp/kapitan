all: clean package

.PHONY: test
test:
	python3 -m unittest discover

.PHONY: release
release:
ifeq ($(version),)
	@echo Please pass version to release e.g. make release version=0.16.5
else
	scripts/make_release.sh $(version)
endif

.PHONY: package
package:
	python3 setup.py sdist bdist_wheel

.PHONY: clean
clean:
	rm -rf dist/ build/ kapitan.egg-info/

.PHONY: pycodestyle
pycodestyle:
	which pycodestyle || echo "Install pycodestyle with pip3 install --user pycodestyle"
	# ignores line length and reclass related errors
	pycodestyle --ignore=E501 . | grep -v "reclass"
	@echo
