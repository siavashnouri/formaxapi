"""RouteBase - Base class with schema generation."""

from __future__ import annotations
from typing import ClassVar
from .metaclass import RouteMetaclass
from .route_field import FieldInfo, RouteField
from .field_config import FieldConfig
from .model_factory import ModelFactory
from .self_derived import SelfDerivedModel
from pydantic import BaseModel


class RouteBase(BaseModel,metaclass=RouteMetaclass):
    """Base class. Routes defined inside with @route decorator.

        class UserRoute(RouteBase):
            name: str = RouteField(add=Add(), edit=Edit())

            @route(path="/users", method="POST")
            async def create_user(cls, request, data: UserRoute.schema("add")):
                ...
    """

    _fields: ClassVar[dict[str, FieldInfo]] = {}
    _schema_types: ClassVar[set[str]] = set()
    _tags: ClassVar[list[str]] = []
    _prefix: ClassVar[str] = ""

    @classmethod
    def schema(cls, schema_type: str, *, name: str | None = None,
               include_fields: list[str] | None = None,
               exclude_fields: list[str] | None = None,
               forbid_extra: bool = True, as_literal: bool = False) -> type[BaseModel]:
        """Generate a Pydantic model for the given schema type."""
        if schema_type not in cls._schema_types:
            raise ValueError(
                f"Unknown schema type '{schema_type}'. Available: {sorted(cls._schema_types)}"
            )
        model_name = name or f"{cls.__name__}_{schema_type.title()}"
        return ModelFactory.create(
            fields=cls._fields, schema_type=schema_type,
            model_name=model_name, forbid_extra=forbid_extra,
            include_fields=include_fields, exclude_fields=exclude_fields,
            as_literal=as_literal, route_cls=cls,
        )

    @classmethod
    def schema_fields(cls, schema_type: str) -> list[str]:
        return ModelFactory.field_names(cls._fields, schema_type)

    @classmethod
    def all_fields(cls) -> dict[str, FieldInfo]:
        return dict(cls._fields)

    @classmethod
    def field_names(cls) -> list[str]:
        return list(cls._fields.keys())

    @classmethod
    def schema_types(cls) -> list[str]:
        return sorted(cls._schema_types)

    @classmethod
    def from_schema(cls, data):
        """Create an instance from a schema model without re-validating nested models."""
        return cls.model_validate(data, from_attributes=True)

    @classmethod
    def field_config_for(cls, field_name: str, schema_type: str) -> FieldConfig | None:
        info = cls._fields.get(field_name)
        return info.get_config(schema_type) if info else None
