---
name: formaxapi
description: Use when working with the formaxapi package for class-based routing with dynamic Pydantic model generation in FastAPI. Covers RouteBase, RouteField, FieldConfig, @route decorator, route_factory, SelfDerivedModel, Chain, and ORM integration (SQLModel, Beanie).
---

# formaxapi

Class-based routing with dynamic Pydantic model generation for FastAPI.

## Core Concepts

### FieldConfig
Defines how a field behaves per schema type. Extend to create schema types:

```python
from formaxapi import FieldConfig

class Add(FieldConfig):
    required = True

class Edit(FieldConfig):
    default = None

class Output(FieldConfig):
    pass
```

Key attributes: `required`, `default`, `default_factory`, `alias`, `description`, `type_override`, `exclude`, `frozen`, `apply_func`, `before`, `metadata`.

### RouteField
Inherits from Pydantic's `FieldInfo`. Accepts both Pydantic params and schema configs:

```python
from formaxapi import RouteField

# Schema configs (FieldConfig instances) + Pydantic params
name: str = RouteField(
    add=Add(),
    edit=Edit(),
    alias="user_name",
    min_length=1,
    max_length=100,
)
```

### RouteBase
Base class for route definitions. Provides schema generation and introspection:

```python
from formaxapi import RouteBase, route

class UserRoute(RouteBase):
    name: str = RouteField(add=Add(), edit=Edit())

    @classmethod
    @route(path="/users", method="POST", status_code=201)
    async def create_user(cls, request, data: UserRoute.schema("add")):
        return {"id": "1"}
```

Methods: `schema()`, `schema_fields()`, `all_fields()`, `field_names()`, `schema_types()`, `from_schema()`, `field_config_for()`.

### @route Decorator
Marks methods as endpoints. Params: `path`, `method`, `name`, `description`, `status_code`, `tags`.

### route_factory
Collects all `@route` methods into a FastAPI `APIRouter`:

```python
from formaxapi import route_factory
app.include_router(route_factory(UserRoute, ProductRoute))
```

### SelfDerivedModel
Derive a field's schema from the route's own fields (for bulk operations). Supports `list` and `dict` containers:

```python
from formaxapi import SelfDerivedModel

# list container (default)
items: list = RouteField(
    bulk_add=BulkAdd(default=SelfDerivedModel(schema="add", exclude_fields=["email"]))
)

# dict container
mapping: dict = RouteField(
    bulk_add=BulkAdd(default=SelfDerivedModel(schema="add", container="dict"))
)
```

### Chain
Compose multiple functions for `apply_func`:

```python
from formaxapi import Chain

title: str = RouteField(
    add=Add(apply_func=Chain(strip, upper, remove_spaces))
)
```

## ORM Integration

### SQLModel
```python
from formaxapi import RouteBase, RouteField
from sqlmodel import SQLModel, Field

class UserRoute(RouteBase, SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    name: str = RouteField(add=Add(), edit=Edit())
```

### Beanie
```python
from formaxapi import RouteBase, RouteField
from beanie import Document

class UserRoute(RouteBase, Document):
    name: str = RouteField(add=Add(), edit=Edit())
    class Settings:
        name = "users"
```

## ClassVar Fields
Fields marked `ClassVar` are excluded from DB but available for schema generation:

```python
from typing import ClassVar

token: ClassVar[str | None] = RouteField(get=Get(), add=Add(exclude=True))
```

## Validators
Validators on the route class propagate to generated models:

```python
from pydantic import field_validator

class UserRoute(RouteBase):
    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        return v.strip()
```

## from_schema()
Create instances from schema models without re-validating nested models:

```python
user = cls.from_schema(data)  # CORRECT
# user = cls(**data.dict())   # WRONG - re-validates
```

## Schema Generation
```python
UserRoute.schema("add")        # => Pydantic model with required fields
UserRoute.schema("edit")       # => Pydantic model with optional fields
UserRoute.schema("add", exclude_fields=["email"])
UserRoute.schema("add", include_fields=["name"])
UserRoute.schema("add", as_literal=True)  # => Literal["name"]
```

## Common Patterns

### Basic CRUD
```python
class UserRoute(RouteBase):
    name: str = RouteField(add=Add(), edit=Edit(), output=Output())

    @classmethod
    @route(path="/users", method="GET")
    async def get_users(cls, request): ...

    @classmethod
    @route(path="/users", method="POST", status_code=201)
    async def create_user(cls, request, data: UserRoute.schema("add")): ...

    @classmethod
    @route(path="/users/{user_id}", method="PUT")
    async def update_user(cls, request, user_id: str, data: UserRoute.schema("edit")): ...

    @classmethod
    @route(path="/users/{user_id}", method="DELETE")
    async def delete_user(cls, request, user_id: str): ...
```

### Bulk Operations
```python
class UserRoute(RouteBase):
    name: str = RouteField(add=Add())
    items: list = RouteField(
        bulk_add=BulkAdd(default=SelfDerivedModel(schema="add", exclude_fields=["email"]))
    )

    @classmethod
    @route(path="/users/bulk", method="POST", status_code=201)
    async def bulk_create(cls, request, data: UserRoute.schema("bulk_add")):
        return {"count": len(data.items)}
```

### Nested Models
```python
from pydantic import BaseModel

class Address(BaseModel):
    street: str
    city: str

class UserRoute(RouteBase):
    address: Address = RouteField(add=Add())
```
