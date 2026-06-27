"""ModelFactory - Generates Pydantic models from FieldInfo + schema type."""

from __future__ import annotations
from types import NoneType
from typing import Literal
from pydantic import BaseModel, Field, create_model, ConfigDict
from pydantic import field_validator as pv_field_validator
from pydantic import model_validator as pv_model_validator
from .route_field import FieldInfo
from .self_derived import SelfDerivedModel
from .field_config import _UNSET


class ModelFactory:

    @staticmethod
    def create(fields, schema_type, model_name="GeneratedModel",
               forbid_extra=True, include_fields=None, exclude_fields=None,
               as_literal=False, route_cls=None) -> type[BaseModel]:
        skip = set(exclude_fields or [])
        only = set(include_fields) if include_fields else None

        if as_literal:
            names = [n for n, info in fields.items()
                     if n not in skip and (only is None or n in only)
                     and info.has_config(schema_type)
                     and not info.get_config(schema_type).exclude]
            return Literal[tuple(names)]

        model_fields = {}
        apply_funcs = {}
        for name, info in fields.items():
            if name in skip or (only is not None and name not in only):
                continue
            config = info.get_config(schema_type)
            if config is None or config.exclude:
                continue

            ftype = config.type_override or info.annotation

            if isinstance(ftype, str):
                import typing
                ftype = typing._eval_type(typing.ForwardRef(ftype), globals(), None)

            fdefault = ModelFactory._resolve_default(config, info)

            # Resolve SelfDerivedModel
            if isinstance(fdefault, SelfDerivedModel) and route_cls:
                ftype, fdefault = ModelFactory._resolve_self_derived(fdefault, route_cls)

            if fdefault is not None and fdefault is not ...:
                if NoneType not in (getattr(ftype, '__args__', ()) or ()):
                    ftype = ftype | None

            # Start with RouteField's Pydantic Field kwargs
            fk = dict(info.field_info_kwargs) if info.field_info_kwargs else {}

            # Remove 'default' from kwargs — we pass it as positional arg
            fk.pop('default', None)
            fk.pop('default_factory', None)

            # Config-level overrides take precedence
            if info.alias and 'alias' not in fk:
                fk['alias'] = info.alias
            desc = config.description or info.description
            if desc and 'description' not in fk:
                fk['description'] = desc
            if config.frozen and 'frozen' not in fk:
                fk['frozen'] = True
            if config.metadata:
                fk.update(config.metadata)

            # Pass constraint kwargs (max_length, min_length, gt, etc.) from RouteField
            field_metadata = info.metadata if hasattr(info, 'metadata') and info.metadata else None
            if field_metadata and isinstance(field_metadata, dict):
                fk.update(field_metadata)

            model_fields[name] = (ftype, Field(fdefault, **fk))

            if config.apply_func is not None:
                func = config.apply_func
                if hasattr(func, '__func__'):
                    func = func.__func__
                apply_funcs[name] = (func, 'before' if config.before else 'after')

        validator_base = ModelFactory._create_validator_base(route_cls, fields, schema_type, apply_funcs)
        model_module = route_cls.__module__ if route_cls else __name__

        if validator_base:
            model = create_model(
                model_name,
                __base__=validator_base,
                __config__=ConfigDict(extra='forbid' if forbid_extra else 'ignore'),
                __module__=model_module,
                **model_fields,
            )
        else:
            model = create_model(
                model_name,
                __config__=ConfigDict(extra='forbid' if forbid_extra else 'ignore'),
                __module__=model_module,
                **model_fields,
            )

        try:
            model.model_rebuild(force=True)
        except Exception:
            pass

        return model

    @staticmethod
    def _create_validator_base(route_cls, fields, schema_type, apply_funcs=None):
        """Create a base class with validators from route_cls and apply_func."""
        apply_funcs = apply_funcs or {}
        namespace = {}

        # Collect validators from route_cls
        if route_cls and getattr(route_cls, '__pydantic_complete__', False):
            decorators = getattr(route_cls, '__pydantic_decorators__', None)
            if decorators:
                for name, dec in decorators.field_validators.items():
                    func = getattr(route_cls, name, None)
                    if func is None:
                        continue
                    raw_func = getattr(func, '__func__', func)
                    mode = dec.info.mode or 'before'
                    for field_name in dec.info.fields:
                        validator_name = f'_validator_{field_name}_{mode}'
                        namespace[validator_name] = pv_field_validator(field_name, mode=mode, check_fields=False)(raw_func)

                for name, dec in decorators.model_validators.items():
                    if name == 'fill_back_refs':
                        continue
                    func = getattr(route_cls, name, None)
                    if func is None:
                        continue
                    raw_func = getattr(func, '__func__', func)
                    namespace[f'_model_validator_{name}'] = pv_model_validator(mode=dec.info.mode)(raw_func)

        # Create validators from apply_func
        for field_name, (func, mode) in apply_funcs.items():
            validator_name = f'_apply_func_{field_name}_{mode}'
            def _make_validator(f):
                def validator(cls, v):
                    return f(v)
                return validator
            v = _make_validator(func)
            v.__qualname__ = validator_name
            namespace[validator_name] = pv_field_validator(field_name, mode=mode, check_fields=False)(v)

        if namespace:
            base_name = f'{route_cls.__name__}Validators' if route_cls else 'Validators'
            return type(base_name, (BaseModel,), namespace)
        return None

    @staticmethod
    def _resolve_default(config, info):
        if config.default is not _UNSET:
            return config.default
        if config.default_factory is not None:
            return config.default_factory
        if info.default is not _UNSET:
            return info.default
        if info.default_factory is not None:
            return info.default_factory
        if config.required:
            return ...
        return ...

    @staticmethod
    def _resolve_self_derived(sdm, route_cls):
        derived = route_cls.schema(
            sdm.schema,
            include_fields=sdm.include_fields,
            exclude_fields=sdm.exclude_fields,
        )
        try:
            derived.model_rebuild(force=True)
        except Exception:
            pass
        if sdm.container == "dict":
            field_type = derived
            default = {} if not sdm.is_optional else None
        else:
            field_type = list[derived]
            default = [] if not sdm.is_optional else None
        return field_type, default

    @staticmethod
    def field_names(fields, schema_type, include=None, exclude=None):
        skip = set(exclude or [])
        only = set(include) if include else None
        return [n for n, info in fields.items()
                if n not in skip and (only is None or n in only)
                and info.has_config(schema_type)
                and not info.get_config(schema_type).exclude]
