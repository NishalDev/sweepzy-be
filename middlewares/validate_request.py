from fastapi import Request, HTTPException, Depends
from pydantic import BaseModel, ValidationError
from typing import Type

def validate_request(schema: Type[BaseModel]):
    async def middleware(request: Request):
        try:
            body = await request.json()
            schema(**body)  # Validate request body against the schema
        except ValidationError as e:
            error_messages = ", ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            raise HTTPException(status_code=422, detail=f"Validation Error: {error_messages}")
        return body

    return Depends(middleware)
