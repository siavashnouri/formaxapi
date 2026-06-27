"""RouteMetaclass - Collects fields and discovers schema types."""

from __future__ import annotations
import sys
import typing
from typing import get_type_hints, ClassVar, get_origin, get_args
from .route_field import RouteField, FieldInfo

try:
    from sqlmodel.main import SQLModelMetaclass as _BaseMetaclass
except ImportError:
    from pydantic._internal._model_construction import ModelMetaclass as _BaseMetaclass


def _resolve_annotations(cls: type) -> dict[str, type]:
    try:
        module = sys.modules.get(cls.__module__)
        if not module:
            return {}
        return get_type_hints(cls, localns=vars(module))
    except Exception:
        return getattr(cls, '__annotations__', {})


def _has_pydantic_base(bases: tuple) -> bool:
    for base in bases:
        if getattr(base, '__pydantic_complete__', False):
            return True
        if getattr(base, '__pydantic_validator__', None) is not None:
            return True
    return False


def _is_classvar(annotation) -> bool:
    origin = get_origin(annotation)
    if origin is ClassVar:
        return True
    if isinstance(annotation, str):
        return 'ClassVar' in annotation
    return False


def _unwrap_classvar(annotation):
    if _is_classvar(annotation):
        args = get_args(annotation)
        if args:
            return args[0]
        return str
    return annotation


class RouteMetaclass(_BaseMetaclass):
    def __new__(mcs, cls_name, bases, namespace, **kwargs):
        if _has_pydantic_base(bases):
            cls = super().__new__(mcs, cls_name, bases, namespace, **kwargs)
        else:
            cls = type.__new__(mcs, cls_name, bases, namespace)

        fields = {}
        for base in bases:
            bf = getattr(base, '_fields', None)
            if bf:
                fields.update(bf)

        resolved = _resolve_annotations(cls)

        # Collect RouteField entries
        for attr_name, annotation in resolved.items():
            attr_value = namespace.get(attr_name)
            if isinstance(attr_value, RouteField):
                # Unwrap ClassVar[str] -> str for the schema
                field_type = _unwrap_classvar(annotation) if _is_classvar(annotation) else annotation
                fields[attr_name] = attr_value.to_field_info(attr_name, field_type)

        # Collect ClassVar fields (not RouteField, but user wants them in schemas)
        for attr_name, annotation in resolved.items():
            if attr_name in fields:
                continue
            if _is_classvar(annotation) and attr_name in namespace:
                inner_type = _unwrap_classvar(annotation)
                field_info = FieldInfo(
                    name=attr_name,
                    annotation=inner_type,
                    default=namespace.get(attr_name, None),
                    configs={},
                )
                fields[attr_name] = field_info

        cls._fields = fields
        schema_types = set()
        for info in fields.values():
            schema_types.update(info.configs.keys())
        cls._schema_types = schema_types

        return cls
