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

    @classmethod
    def model_construct(cls, _fields_set=None, **values):
        instance = cls.__new__(cls)
        for k, v in values.items():
            setattr(instance, k, v)
        return instance

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, dict):
            return cls(**obj)
        if isinstance(obj, (list, tuple)):
            return cls(*obj)
        return cls(obj)

    @classmethod
    def construct(cls, _fields_set=None, **values):
        return cls.model_construct(_fields_set=_fields_set, **values)

    @classmethod
    def parse_obj(cls, obj):
        return cls.model_validate(obj)


    def model_dump(self, *args, **kwargs):
        return self.__dict__

    def dict(self, *args, **kwargs):
        return self.__dict__

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.__dict__}>"

class RootModel(BaseModel):
    """Simple stub for pydantic.RootModel used in generated code.
    Supports subscript syntax like ``RootModel[MyModel]``.
    """
    def __init__(self, root=None, **data):
        if root is not None:
            self.root = root
        elif data:
            self.root = data
        else:
            self.root = None

    @classmethod
    def __class_getitem__(cls, item):
        return cls

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, cls):
            return obj
        instance = cls(root=obj)
        return instance

