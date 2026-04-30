PYTHON ?= python
STREAMLIT ?= streamlit

.PHONY: setup pipeline dashboard

setup:
	$(PYTHON) -m pip install -r requirements.txt

pipeline:
	$(PYTHON) load_data.py
	$(PYTHON) analysis.py

dashboard:
	$(STREAMLIT) run dashboard.py --server.address 0.0.0.0 --server.port 8501
