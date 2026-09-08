import sys
import os
import importlib.util

# Root directory path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    api_py_path = os.path.join(root_dir, "api.py")
    spec = importlib.util.spec_from_file_location("root_api_server", api_py_path)
    main_api = importlib.util.module_from_spec(spec)
    sys.modules["root_api_server"] = main_api
    spec.loader.exec_module(main_api)
    app = main_api.app
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

