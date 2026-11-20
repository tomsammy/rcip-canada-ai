import os
import uvicorn
from backend.config import HOST, PORT

if __name__ == "__main__":
    use_reload = not (os.environ.get("RENDER") or os.environ.get("NO_RELOAD"))
    print(f"Starting RCIP Canada AI at http://{HOST}:{PORT}")
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=use_reload)
