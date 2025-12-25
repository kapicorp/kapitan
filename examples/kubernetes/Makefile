all: compile status

# Use Docker by default, override with: make compile KAPITAN="poetry run kapitan"
KAPITAN ?= docker run --rm -v $(shell pwd):/src:delegated kapitan
# Optional: specify targets with TARGET=minikube-nginx-helm
TARGET ?=

.PHONY: compile
compile:
	@echo compiling kapitan templates...
ifdef TARGET
	$(KAPITAN) compile -t $(TARGET)
else
	$(KAPITAN) compile
endif

.PHONY: fetch
fetch:
	@echo fetching dependencies...
	$(KAPITAN) compile --fetch

.PHONY: clean
clean:
	rm -rf compiled/*

.PHONY: status
status:
	git status
