import os

BASE_DIR = os.getcwd()

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def get_model_path(cohort_id):
    path = f"models/cohort-{cohort_id:02d}"
    ensure_dir(path)
    return f"{path}/model.pkl"

def get_result_path(cohort_id):
    ensure_dir("results")
    return f"results/cohort-{cohort_id:02d}_scores.json"

def get_summary_path():
    ensure_dir("summary")
    return "summary/risk-scores.json"