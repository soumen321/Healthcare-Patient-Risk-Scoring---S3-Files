import boto3
import pickle
import io
from config import AWS_REGION, S3_BUCKET, S3_PREFIX

s3_client = boto3.client("s3", region_name=AWS_REGION)

# Optional cache (recommended)
model_cache = {}

def load_model_from_s3(cohort_id: int):
    if cohort_id in model_cache:
        return model_cache[cohort_id]

    s3_model_path = f"{S3_PREFIX}/models/cohort-{cohort_id:02d}/model.pkl"

    obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_model_path)
    model_data = pickle.load(io.BytesIO(obj['Body'].read()))

    model_cache[cohort_id] = (model_data['model'], model_data['scaler'])

    return model_cache[cohort_id]