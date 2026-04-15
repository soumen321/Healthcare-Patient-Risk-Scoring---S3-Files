import numpy as np
from fastapi import APIRouter
from api.schemas.patient import PatientData, PredictionResponse
from api.services.model_loader import load_model_from_s3

router = APIRouter()

@router.post("/predict", response_model=PredictionResponse)
def predict(data: PatientData):
    model, scaler = load_model_from_s3(data.cohort_id)

    X = np.array([[ 
        data.age,
        data.bmi,
        data.glucose,
        data.blood_pressure,
        data.cholesterol
    ]])

    X_scaled = scaler.transform(X)

    prediction = int(model.predict(X_scaled)[0])
    probability = float(model.predict_proba(X_scaled)[0][1])    


    return PredictionResponse(
        cohort_id=data.cohort_id,
        prediction=prediction,
        risk_score=probability,
        risk_level=get_risk_level(probability)
    )
    
def get_risk_level(score: float) -> str:
    if score < 0.3:
        return "LOW"
    elif score < 0.7:
        return "MEDIUM"
    else:
        return "HIGH"    