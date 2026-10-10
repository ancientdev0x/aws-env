# SAM makefile build (template.yaml: BuildMethod makefile, samconfig: build_in_source = true)
# Packs app.py + the shared engine/ module + pure-Python NetworkX.
build-ApiFunction:
	cp app.py $(ARTIFACTS_DIR)/
	mkdir -p $(ARTIFACTS_DIR)/engine
	cp ../engine/reachability.py $(ARTIFACTS_DIR)/engine/
	uv pip install --quiet --target $(ARTIFACTS_DIR) --python-version 3.12 networkx==3.7
