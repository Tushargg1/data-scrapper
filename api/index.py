import sys
import os

# Add root directory to sys.path so api.py and other modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from api import app
except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()

    @app.get("/{full_path:path}")
    def fallback_error(full_path: str = ""):
        return JSONResponse(
            status_code=500,
            content={"error": "Vercel Serverless Initialization Error", "details": str(e)}
        )
