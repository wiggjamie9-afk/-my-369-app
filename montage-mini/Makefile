.PHONY: demo test clean

# Render a zero-key demo video into demos/
demo:
	python3 montage.py --out demos "Make a 45-second animated explainer about why the sky is blue"
	@echo "Open the printed final.html path in your browser."

# Run the offline self-tests (no deps, no network)
test:
	python3 test_pipeline.py

clean:
	rm -rf projects demos **/__pycache__ __pycache__
