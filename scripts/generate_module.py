import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Templates for Model, Schema, Service, Controller, and Routes
MODEL_TEMPLATE = """from sqlalchemy import Column, Integer, String
from config.database import Base

class {class_name}(Base):
    __tablename__ = '{table_name}'
    id = Column(Integer, primary_key=True, index=True)
    {fields}
"""

SCHEMA_TEMPLATE = """from pydantic import BaseModel

class {class_name}Base(BaseModel):
    {fields}

class {class_name}Create({class_name}Base):
    pass

class {class_name}Response({class_name}Base):
    id: int

    class Config:
        orm_mode = True
"""

SERVICE_TEMPLATE = """from sqlalchemy.orm import Session
from api.{module_name}.user_model import {class_name}
from api.{module_name}.user_schema import {class_name}Create

def create_{module_name}(db: Session, {module_name}_data: {class_name}Create):
    db_{module_name} = {class_name}(**{module_name}_data.dict())
    db.add(db_{module_name})
    db.commit()
    db.refresh(db_{module_name})
    return db_{module_name}

def get_{module_name}s(db: Session):
    return db.query({class_name}).all()
"""

CONTROLLER_TEMPLATE = """from fastapi import Depends
from sqlalchemy.orm import Session
from config.database import get_db
from api.{module_name}.user_service import create_{module_name}, get_{module_name}s
from api.{module_name}.user_schema import {class_name}Create, {class_name}Response

def create_{module_name}_controller({module_name}_data: {class_name}Create, db: Session = Depends(get_db)):
    return create_{module_name}(db, {module_name}_data)

def get_{module_name}s_controller(db: Session = Depends(get_db)):
    return get_{module_name}s(db)
"""

ROUTE_TEMPLATE = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from api.{module_name}.user_controller import create_{module_name}_controller, get_{module_name}s_controller
from api.{module_name}.user_schema import {class_name}Create, {class_name}Response

router = APIRouter(prefix="/{module_name}", tags=["{class_name}"])

@router.post("/", response_model={class_name}Response)
def create_{module_name}_route({module_name}_data: {class_name}Create, db: Session = Depends(get_db)):
    return create_{module_name}_controller({module_name}_data, db)

@router.get("/", response_model=list[{class_name}Response])
def get_{module_name}s_route(db: Session = Depends(get_db)):
    return get_{module_name}s_controller(db)
"""

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

def generate_module(module_name, fields):
    class_name = module_name.capitalize()
    table_name = module_name.lower()
    field_definitions = "\n    ".join([f"{name} = Column({dtype}, index=True)" for name, dtype in fields.items()])
    schema_fields = "\n    ".join([f"{name}: {dtype}" for name, dtype in fields.items()])

    # Generate file contents
    model_code = MODEL_TEMPLATE.format(class_name=class_name, table_name=table_name, fields=field_definitions)
    schema_code = SCHEMA_TEMPLATE.format(class_name=class_name, fields=schema_fields)
    service_code = SERVICE_TEMPLATE.format(class_name=class_name, module_name=module_name)
    controller_code = CONTROLLER_TEMPLATE.format(class_name=class_name, module_name=module_name)
    route_code = ROUTE_TEMPLATE.format(class_name=class_name, module_name=module_name)

    # Create module structure inside api/{module_name}/
    create_file(f"api/{module_name}/user_model.py", model_code)
    create_file(f"api/{module_name}/user_schema.py", schema_code)
    create_file(f"api/{module_name}/user_service.py", service_code)
    create_file(f"api/{module_name}/user_controller.py", controller_code)
    create_file(f"api/{module_name}/user_routes.py", route_code)

    print(f"✅ API module '{module_name}' generated successfully!")
    print("Run the following command to create the database migration:")
    print(f"alembic revision --autogenerate -m 'Added {module_name} model' && alembic upgrade head")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_module.py <module_name> <field1:type1> <field2:type2>...")
        sys.exit(1)
    
    module_name = sys.argv[1]
    fields = {arg.split(':')[0]: arg.split(':')[1] for arg in sys.argv[2:]}
    generate_module(module_name, fields)
