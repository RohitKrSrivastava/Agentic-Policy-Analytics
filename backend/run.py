import os
import sys

import uvicorn

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    reload = os.environ.get("DEBUG", "false").lower() == "true"
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=reload)
