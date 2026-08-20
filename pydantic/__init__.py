"""Very small stub of pydantic used for config validation.
Provides BaseModel that accepts any fields and does nothing.
ValidationError is just an Exception subclass.
"""

class ValidationError(Exception):
    pass

# Minimal stand‑ins for pydantic's Field, ConfigDict and field_validator
def Field(default=None, **kwargs):
    return default

class ConfigDict(dict):
    pass

def field_validator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

class BaseModel:
    def __init__(self, **data):
        for k, v in data.items():
            setattr(self, k, v)
    def dict(self):
        return self.__dict__
    def __repr__(self):
        return f"<BaseModel {self.__dict__}>"

class RootModel(BaseModel):
    """Simple stub for pydantic.RootModel used in generated code.
    Supports subscript syntax like ``RootModel[MyModel]``.
    """
    def __class_getitem__(cls, item):
        return cls
    pass
