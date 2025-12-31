.PHONY: compile clean fetch test all

# Default target
all: compile

# Compile the nginx-dump-and-write target using omegaconf backend
compile:
	poetry run kapitan compile -t nginx-dump-and-write --inventory-backend=omegaconf --fetch

# Clean compiled output
clean:
	rm -rf compiled charts

# Run the omegaconf tests
test:
	cd ../.. && poetry run pytest tests/test_omegaconf.py -v

# Run only the compile test
test-compile:
	cd ../.. && poetry run pytest tests/test_omegaconf.py::CompileTestOmegaConf -v

# Show compiled files
list:
	@find compiled -type f -name "*.yml" 2>/dev/null || echo "No compiled files found. Run 'make compile' first."
