from pydantic import BaseModel

class PatientData(BaseModel):
    cohort_id: int
    age: int
    bmi: float
    glucose: float
    blood_pressure: float
    cholesterol: float


class PredictionResponse(BaseModel):
    cohort_id: int
    prediction: int
    risk_score: float
    risk_level: str