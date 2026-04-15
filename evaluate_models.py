"""
Evaluate all trained models and score patients
Each model loads from S3 and runs risk scoring
"""

import io
import pickle
import json
import time
import boto3
import pandas as pd
import numpy as np
from botocore.exceptions import ClientError
from sklearn.preprocessing import StandardScaler
from config import AWS_REGION, S3_BUCKET, S3_PREFIX, COHORTS, TEST_PATIENTS
from utils.storage import get_result_path, get_summary_path
from logger import setup_logger

logger = setup_logger(__name__)


def generate_test_data(cohort_id, n_patients, seed=42):
    """Generate synthetic test data for a cohort"""
    np.random.seed(seed + cohort_id + 1000)
    
    data = {
        'age': np.random.randint(18, 85, n_patients),
        'bmi': np.random.normal(25, 5, n_patients),
        'glucose': np.random.normal(100, 20, n_patients),
        'blood_pressure': np.random.normal(120, 15, n_patients),
        'cholesterol': np.random.normal(200, 40, n_patients),
    }
    
    return pd.DataFrame(data)



def score_cohort_patients(cohort_id):
    """Load model from S3 and score patients for a cohort"""
    try:
        logger.info(f"[COHORT-{cohort_id}] Loading model from S3...")

        s3_client = boto3.client("s3", region_name=AWS_REGION)
        s3_model_path = f"{S3_PREFIX}/models/cohort-{cohort_id:02d}/model.pkl"

        # Download model from S3
        
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_model_path)
        model_data = pickle.load(io.BytesIO(obj['Body'].read()))
        
        # try:
        #     s3_client.download_file(S3_BUCKET, s3_model_path, f"temp_cohort_{cohort_id}.pkl")
        #     logger.info(f"   [OK] Downloaded from S3")
        # except s3_client.exceptions.NoSuchKey:
        #     logger.error(f"[ERROR] Model not found in S3: {s3_model_path}")
        #     return None

        # # Load model and scaler
        # with open(f"temp_cohort_{cohort_id}.pkl", "rb") as f:
        #     model_data = pickle.load(f)
        model = model_data['model']
        scaler = model_data['scaler']
        logger.info(f"   [OK] Model loaded in memory")

        # Generate test data
        logger.info(f"[COHORT-{cohort_id}] Scoring {TEST_PATIENTS} test patients...")
        df_test = generate_test_data(cohort_id, TEST_PATIENTS)

        # Prepare features
        X = df_test[['age', 'bmi', 'glucose', 'blood_pressure', 'cholesterol']]
        X_scaled = scaler.transform(X)

        # Run predictions
        predictions = model.predict(X_scaled)
        probabilities = model.predict_proba(X_scaled)

        # Create results (explicit casting everywhere)
        results = {
            'cohort_id': int(cohort_id),
            'total_patients': int(TEST_PATIENTS),
            'at_risk': int(predictions.sum()),
            'low_risk': int(TEST_PATIENTS - predictions.sum()),
            'avg_risk_score': float(probabilities[:, 1].mean()),
            'high_risk_patients': [
                {
                    'patient_id': int(i),
                    'age': int(df_test.iloc[i]['age']),
                    'risk_score': float(probabilities[i, 1])
                }
                for i in np.argsort(probabilities[:, 1])[-5:]
            ]
        }

        logger.info(f"   [OK] At risk: {results['at_risk']}, Low risk: {results['low_risk']}")
        logger.info(f"   [OK] Avg risk score: {results['avg_risk_score']:.4f}")

        # Save results locally
        #results_file = f"results_cohort_{cohort_id}.json"
        results_file = get_result_path(cohort_id)
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"   [OK] Results saved locally")

        # Upload to S3
        s3_results_path = f"{S3_PREFIX}/results/cohort-{cohort_id:02d}_scores.json"
        s3_client.upload_file(results_file, S3_BUCKET, s3_results_path)
        logger.info(f"   [OK] Uploaded to S3: s3://{S3_BUCKET}/{s3_results_path}")

        return results

    except ClientError as e:
        logger.error(f"[ERROR] AWS error in cohort {cohort_id}: {str(e)}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"[ERROR] Error in cohort {cohort_id}: {str(e)}", exc_info=True)
        return None

def main():
    """Score patients for all 10 cohorts"""
    
    logger.info("=" * 70)
    logger.info("[HEALTHCARE] Starting Risk Scoring Evaluation")
    logger.info("=" * 70)
    logger.info(f"[CONFIG] Cohorts: {COHORTS}")
    logger.info(f"[CONFIG] Test patients per cohort: {TEST_PATIENTS}")
    
    start_time = time.time()
    
    # Score patients for all cohorts
    all_results = []
    successful = 0
    for cohort_id in range(1, COHORTS + 1):
        logger.info(f"\n[COHORT-{cohort_id:02d}] ===== Scoring Cohort {cohort_id}/{COHORTS} =====")
        result = score_cohort_patients(cohort_id)
        if result:
            all_results.append(result)
            successful += 1
    
    elapsed_time = time.time() - start_time
    
    # Generate summary
    if all_results:
        total_at_risk = sum(r['at_risk'] for r in all_results)
        total_low_risk = sum(r['low_risk'] for r in all_results)
        avg_risk = np.mean([r['avg_risk_score'] for r in all_results])
        
        summary = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'total_cohorts': COHORTS,
            'successful_cohorts': successful,
            'total_patients_scored': TEST_PATIENTS * successful,
            'total_at_risk': total_at_risk,
            'total_low_risk': total_low_risk,
            'overall_avg_risk_score': float(avg_risk),
            'cohort_results': all_results
        }
        
        # Save summary to S3
        logger.info("\n[SUMMARY] Uploading results summary...")
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        summary_file = get_summary_path()
        #summary_file = "summary_results.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        s3_summary_path = f"{S3_PREFIX}/summary/risk-scores.json"
        s3_client.upload_file(summary_file, S3_BUCKET, s3_summary_path)
        logger.info(f"   [OK] Summary uploaded to S3: s3://{S3_BUCKET}/{s3_summary_path}")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info(f"[SUMMARY] Evaluation complete!")
    logger.info(f"[SUMMARY] Successful: {successful}/{COHORTS}")
    logger.info(f"[SUMMARY] Time elapsed: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    logger.info(f"[SUMMARY] Avg time per cohort: {elapsed_time/COHORTS:.2f} seconds")
    logger.info(f"[SUMMARY] Total patients scored: {TEST_PATIENTS * successful}")
    logger.info("=" * 70)
    
    return successful == COHORTS


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
