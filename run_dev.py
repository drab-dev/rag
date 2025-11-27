"""
Development server script with Windows multiprocessing fix
"""
import multiprocessing
import uvicorn

if __name__ == "__main__":
    # Required for Windows multiprocessing support
    multiprocessing.freeze_support()
    
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["backend", "models"]
    )
