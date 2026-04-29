"""
Firebase Cloud Functions entry point.
Wraps the FastAPI app from main.py using Mangum for AWS Lambda / Google Cloud Functions compatibility.

Deploy: firebase deploy --only functions
"""
from main import app
from mangum import Mangum

handler = Mangum(app, lifespan="off")
