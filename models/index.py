import os
import importlib.util
import sys
from pathlib import Path
from config.database import engine, SessionLocal, Base

# Dictionary to store dynamically loaded models
models = {}

# Function to dynamically load models from the `api` directory
def scan_models(directory: Path):
    for item in directory.rglob("*.model.py"):  # Recursively find all `.model.py` files
        module_name = item.stem
        module_path = str(item)

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, "__tablename__"):  # Check if it is a SQLAlchemy model
                models[attr.__tablename__] = attr

# Scan the `api` directory for models
scan_models(Path(__file__).parent.parent / "api")

# Create tables in the database
def init_db():
    # Since models are loaded dynamically, simply create all tables
    Base.metadata.create_all(bind=engine)

# Exporting components
__all__ = ["engine", "SessionLocal", "Base", "models"]
