"""
Development server script with Windows multiprocessing fix

Also loads environment variables from a local .env file so you can set
secrets like GROQ_API_KEY without exporting them manually.
"""
import multiprocessing
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

if __name__ == "__main__":
    # Load variables from .env in the project root (same dir as this file)
    env_path = Path(__file__).with_name(".env")
    load_dotenv(dotenv_path=env_path)

    # Required for Windows multiprocessing support
    multiprocessing.freeze_support()
    
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["backend", "models"]
    )
