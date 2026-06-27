"""route decorator and route_factory."""

from __future__ import annotations
from typing import Callable, Literal
from fastapi import APIRouter, status


class _RouteInfo:
    __slots__ = ('path', 'method', 'name', 'description', 'status_code', 'tags')

    def __init__(self, path, method, name, description, status_code, tags):
        self.path = path
        self.method = method
        self.name = name
        self.description = description
        self.status_code = status_code
        self.tags = tags


def route(
    path: str,
    method: Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] = 'GET',
    name: str | None = None,
    description: str | None = None,
    status_code: int = status.HTTP_200_OK,
    tags: list[str] | None = None,
) -> Callable:
    """Decorator to mark a method as a route endpoint."""
    def decorator(func: Callable) -> Callable:
        func._route_info = _RouteInfo(
            path=path, method=method,
            name=name or func.__name__,
            description=description,
            status_code=status_code,
            tags=tags or [],
        )
        return func
    return decorator


def route_factory(*route_classes: type) -> APIRouter:
    """Collect all @route methods from Route classes into a FastAPI APIRouter."""
    router = APIRouter()

    for cls in route_classes:
        cls_prefix = ""
        if cls._prefix:
            cls_prefix=cls._prefix if cls._prefix.startswith("/") else "/" + cls._prefix
        default_tags = [getattr(cls, '_tags', None) or cls.__name__]

        for attr_name in dir(cls):
            attr = getattr(cls, attr_name, None)
            if attr is None:
                continue

            func = getattr(attr, '__func__', attr)
            info = getattr(func, '_route_info', None)
            if info is None:
                continue

            tags = info.tags + default_tags
            path = cls_prefix + info.path if info.path.startswith("/") else cls_prefix + "/" + info.path
            router.add_api_route(
                path=path,
                endpoint=attr,
                methods=[info.method],
                name=info.name,
                description=info.description,
                status_code=info.status_code,
                tags=tags,
            )

    return router
