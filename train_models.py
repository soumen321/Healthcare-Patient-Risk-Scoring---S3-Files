"""
Train risk scoring models for 10 patient cohorts
Each cohort reads data from S3 and trains independently
"""

import pickle
import json
import time
import boto3
import pandas as pd
import numpy as np
from botocore.exceptions import ClientError
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from config import AWS_REGION, S3_BUCKET, S3_PREFIX, COHORTS, PATIENTS_PER_COHORT
from logger import setup_logger
from utils.storage import get_model_path

logger = setup_logger(__name__)


def generate_patient_data(cohort_id, n_patients, seed=42):
    """Generate synthetic patient data for a cohort"""
    np.random.seed(seed + cohort_id)
    
    data = {
        'age': np.random.randint(18, 85, n_patients),
        'bmi': np.random.normal(25, 5, n_patients),
        'glucose': np.random.normal(100, 20, n_patients),
        'blood_pressure': np.random.normal(120, 15, n_patients),
        'cholesterol': np.random.normal(200, 40, n_patients),
        'bmi_squared': np.random.randint(18, 85, n_patients) ** 2
    }
    
    # Risk label (target): higher for older patients with worse metrics
    # risk = (
    #     (data['age'] > 60) * 1 +
    #     (data['bmi'] > 30) * 1 +
    #     (data['glucose'] > 120) * 1 +
    #     (data['cholesterol'] > 240) * 1
    # ) > 2
    
    risk = (
        (data['age'] > 50) * 1 +
        (data['bmi'] > 28) * 1 +
        (data['glucose'] > 110) * 1 +
        (data['cholesterol'] > 220) * 1
    ) > 1
    
    data['risk'] = risk.astype(int)
    
    return pd.DataFrame(data)


def train_cohort_model(cohort_id):
    """Train a risk scoring model for one patient cohort"""
    
    try:
        logger.info(f"[COHORT-{cohort_id}] Generating training data...")
        
        # Generate synthetic data (simulates reading from S3)
        df_train = generate_patient_data(cohort_id, PATIENTS_PER_COHORT)
        logger.info(f"   [OK] Generated {len(df_train)} training samples")
        
        # Prepare features and target
        X = df_train[['age', 'bmi', 'glucose', 'blood_pressure', 'cholesterol']]
        y = df_train['risk']
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train model
        logger.info(f"[COHORT-{cohort_id}] Training GradientBoosting model...")
        model = GradientBoostingClassifier(n_estimators=50, random_state=42)
        model.fit(X_scaled, y)
        
        # Calculate accuracy
        accuracy = model.score(X_scaled, y)
        logger.info(f"   [OK] Model trained! Accuracy: {accuracy:.4f}")
        
        # Save model locally
        #model_file = f"cohort_{cohort_id}_model.pkl"
        model_file = get_model_path(cohort_id)
        with open(model_file, "wb") as f:
            pickle.dump({'model': model, 'scaler': scaler}, f)
        logger.info(f"   [OK] Model saved locally")
        
        # Upload to S3
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        s3_model_path = f"{S3_PREFIX}/models/cohort-{cohort_id:02d}/model.pkl"
        s3_client.upload_file(model_file, S3_BUCKET, s3_model_path)
        logger.info(f"   [OK] Uploaded to S3: s3://{S3_BUCKET}/{s3_model_path}")
        
        return True
        
    except ClientError as e:
        logger.error(f"[ERROR] AWS error in cohort {cohort_id}: {str(e)}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"[ERROR] Error in cohort {cohort_id}: {str(e)}", exc_info=True)
        return False


def main():
    """Train models for all 10 cohorts"""
    
    logger.info("=" * 70)
    logger.info("[HEALTHCARE] Starting Risk Scoring Model Training")
    logger.info("=" * 70)
    logger.info(f"[CONFIG] Cohorts: {COHORTS}")
    logger.info(f"[CONFIG] Patients per cohort: {PATIENTS_PER_COHORT}")
    logger.info(f"[CONFIG] S3 Bucket: {S3_BUCKET}")
    
    start_time = time.time()
    
    # Train models for all cohorts
    successful = 0
    for cohort_id in range(1, COHORTS + 1):
        logger.info(f"\n[COHORT-{cohort_id:02d}] ===== Training Cohort {cohort_id}/{COHORTS} =====")
        if train_cohort_model(cohort_id):
            successful += 1
    
    elapsed_time = time.time() - start_time
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info(f"[SUMMARY] Training complete!")
    logger.info(f"[SUMMARY] Successful: {successful}/{COHORTS}")
    logger.info(f"[SUMMARY] Time elapsed: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    logger.info(f"[SUMMARY] Avg time per cohort: {elapsed_time/COHORTS:.2f} seconds")
    logger.info("=" * 70)
    
    return successful == COHORTS


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
