from pydantic import BaseModel, Field
from typing import Annotated, Optional
class TourStatus(BaseModel):
    shown: bool
    
class LanguageUpdate(BaseModel):
    # Instead of regex=, use pattern=
    language: Annotated[
        str,
        Field(
            ...,
            min_length=2,
            max_length=2,
            pattern='^(en|kn)$'
        )
    ]
    
class LanguageResponse(BaseModel):
    language: Optional[str]  # now allows None