"""
Configuration for Healthcare Risk Scoring POC
"""

import os
from dotenv import load_dotenv

load_dotenv()

# AWS S3 Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "healthcare-poc")

if not S3_BUCKET:
    raise ValueError("S3_BUCKET environment variable is required!")

# Healthcare Configuration
COHORTS = 10  # Number of patient cohorts
PATIENTS_PER_COHORT = 100  # Patients per cohort for training
TEST_PATIENTS = 20  # Test patients per cohort

# S3 Paths
S3_DATA_PATH = f"{S3_PREFIX}/data/cohort-{{cohort_id}}"
S3_MODEL_PATH = f"{S3_PREFIX}/models/cohort-{{cohort_id}}/model.pkl"
S3_RESULTS_PATH = f"{S3_PREFIX}/results/scores-cohort-{{cohort_id}}.json"
S3_SUMMARY_PATH = f"{S3_PREFIX}/summary/risk-scores.json"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "logs/healthcare.log"
