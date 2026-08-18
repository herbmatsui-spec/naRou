.PHONY: all assets tileset atlas test run clean

# Default target
all: assets

# Asset generation targets
assets: tileset atlas

tileset:
	@echo "Generating tileset atlases..."
	python3 tools/generate_tileset_atlas.py --size 16
	python3 tools/generate_tileset_atlas.py --size 32
	@echo "Tileset generation complete."

atlas:
	@echo "Atlas generation is part of tileset target."

# Run the game
run:
	@echo "Starting game..."
	python3 -m game

# Run tests
test:
	@echo "Running tests..."
	python3 -m pytest tests/ -v

# Clean generated assets
clean:
	@echo "Cleaning generated assets..."
	rm -f assets/tiles/tileset_*.png assets/tiles/tileset_*.json
	@echo "Clean complete."

# Watch for asset changes and regenerate
watch:
	@echo "Starting file watcher for asset regeneration..."
	watchmedo shell-command -p "assets/tiles/**/*.png" -c "make assets" --recursive --wait

# Help target
help:
	@echo "Available targets:"
	@echo "  all     : Generate assets (default)"
	@echo "  assets  : Generate all assets"
	@echo "  tileset : Generate tileset atlases"
	@echo "  run     : Run the game"
	@echo "  test    : Run tests"
	@echo "  clean   : Clean generated assets"
	@echo "  watch   : Watch for asset changes and regenerate"
	@echo "  help    : Show this help"