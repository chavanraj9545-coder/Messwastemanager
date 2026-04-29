from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from ml import predict_attendance, train_model, calculate_food_requirements
from ml.config import METRICS_PATH
import json
import os

from schemas import PredictionRequest, FuturePredictionRequest
from models import Prediction
from typing import List
from datetime import date, timedelta

router = APIRouter(prefix="/api/prediction", tags=["Prediction"])


@router.post("/predict")
def predict(
    data: PredictionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    org_code = current_user.organization_code if current_user.role in ["mess_manager", "admin"] else None
    result = predict_attendance(data.date, db, data.meal, organization_code=org_code)

    # Persist prediction to the predictions table as the report specifies
    try:
        predicted_val = result.get("predicted_students") if isinstance(result, dict) else None
        if predicted_val is not None:
            existing = db.query(Prediction).filter(
                Prediction.date == data.date,
                Prediction.meal == data.meal,
                Prediction.organization_code == org_code
            ).first()
            if existing:
                existing.predicted_students = int(predicted_val)
                existing.model_version = "v1"
            else:
                pred_record = Prediction(
                    date=data.date,
                    meal=data.meal,
                    predicted_students=int(predicted_val),
                    organization_code=org_code,
                    model_version="v1"
                )
                db.add(pred_record)
            db.commit()
    except Exception as e:
        print(f"Warning: Could not persist prediction: {e}")

    return result


@router.post("/predict-future")
def predict_future(
    data: FuturePredictionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    today = date.today()
    org_code = current_user.organization_code if current_user.role in ["mess_manager", "admin"] else None
    predictions = []
    
    # We predict starting from tomorrow
    for i in range(1, data.days + 1):
        target = today + timedelta(days=i)
        try:
            result = predict_attendance(target, db, data.meal, organization_code=org_code)
            predictions.append(result)
        except Exception as e:
            predictions.append({
                "date": target.isoformat(),
                "meal": data.meal,
                "predicted_students": 350,  # Fallback
                "error": str(e)
            })
    return {"predictions": predictions, "days": data.days, "meal": data.meal}


@router.post("/predict-week")
def predict_week(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Keep for backward compatibility
    return predict_future(FuturePredictionRequest(days=7, meal="lunch"), db, current_user)


@router.post("/train")
def retrain_model(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    org_code = current_user.organization_code if current_user.role in ["mess_manager", "admin"] else None
    metrics = train_model(db, organization_code=org_code)
    return {"message": "Model retrained successfully", "metrics": metrics}


@router.get("/metrics")
def model_metrics(current_user=Depends(get_current_user)):
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, "r") as f:
            metrics = json.load(f)
        data_points = metrics.get("training_samples", 0) + metrics.get("test_samples", 0)
        r2 = metrics.get("r2_score", 0)
        metrics["data_points"] = data_points
        metrics["meets_minimum"] = data_points >= 30
        metrics["is_optimal"] = data_points >= 90
        metrics["has_negative_r2"] = r2 < 0
        metrics["sufficiency_note"] = (
            "Model is performing optimally with sufficient data."
            if data_points >= 90
            else f"Model accuracy is limited. {data_points} records available. Minimum 30 required, optimal beyond 90. Add more attendance records and retrain."
        )
        return metrics
    return {
        "status": "Model not trained yet",
        "data_points": 0,
        "meets_minimum": False,
        "is_optimal": False,
        "has_negative_r2": False,
        "sufficiency_note": "No model trained yet. Add at least 30 attendance records then retrain."
    }


@router.get("/food-requirements/{students}")
def get_food_requirements(
    students: int,
    current_user=Depends(get_current_user)
):
    return calculate_food_requirements(students)


@router.get("/history")
def prediction_history(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    org_code = current_user.organization_code if current_user.role in ["mess_manager", "admin"] else None
    query = db.query(Prediction)
    if org_code:
        query = query.filter(Prediction.organization_code == org_code)
    records = (
        query
        .order_by(Prediction.date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "date": r.date.isoformat(),
            "meal": r.meal,
            "predicted_students": r.predicted_students,
            "actual_students": r.actual_students,
            "confidence": r.confidence,
            "model_version": r.model_version
        }
        for r in records
    ]
