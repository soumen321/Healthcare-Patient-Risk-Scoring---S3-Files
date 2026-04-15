from fastapi import FastAPI
from api.routes import predict

app = FastAPI(title="Healthcare Risk Scoring API")

# Register routes
app.include_router(predict.router)