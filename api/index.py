import sys
import os
import importlib.util

# Ensure root directory is first in path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# Remove any accidentally cached "api" package references so import resolves to api.py
for k in list(sys.modules.keys()):
    if k == "api" or k.startswith("api."):
        del sys.modules[k]

try:
    # Explicitly load the root api.py by file path
    spec = importlib.util.spec_from_file_location("api_main", os.path.join(root_dir, "api.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    app = mod.app
    application = app   # Vercel looks for "application" too
    handler = app       # Vercel looks for "handler" too
except Exception as _e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()
    application = app
    handler = app
    _err_msg = str(_e)

    @app.get("/{full_path:path}")
    def startup_error(full_path: str = ""):
        return JSONResponse(
            status_code=500,
            content={"error": "Server startup failed", "details": _err_msg}
        )
