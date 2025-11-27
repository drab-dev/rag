# Windows Setup Guide

## Issues Fixed

### 1. NumPy 2.0 Compatibility Issue
**Problem**: ChromaDB 0.4.18 was incompatible with NumPy 2.0+
**Solution**: Upgraded ChromaDB to version 1.3.5 which supports NumPy 2.0+

### 2. Uvicorn Reload Issue on Windows
**Problem**: Running `python -m uvicorn backend.main:app --reload` causes startup failures on Windows due to multiprocessing issues
**Solution**: Created `run_dev.py` with proper Windows multiprocessing support

## How to Run the Server

### Option 1: Using the batch file (Easiest)
```bash
start_server.bat
```

### Option 2: Using the Python script
```bash
python run_dev.py
```

### Option 3: Without reload (for production)
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Notes

- The server will be accessible at: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Dependencies Updated

- `chromadb>=1.3.0` (updated from 0.4.18)
- Added `multiprocessing.freeze_support()` for Windows compatibility
