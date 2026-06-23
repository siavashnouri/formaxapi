<p align="center">
  <img src="fastschema.png" alt="fastschema" width="400">
</p>

# fastschema

Class-based routing with dynamic Pydantic model generation for FastAPI.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

## Why fastschema?

Traditional FastAPI development scatters code across Pydantic models, route handlers, and router configuration. **fastschema** consolidates everything into a single class:

- **Routes inside the class** — defined with `@route` decorator
- **Typed input** — `UserRoute.schema("add")` auto-validates request body
- **Auto-discovered schemas** — no manual registration
- **SelfDerivedModel** — derive schemas from own fields for bulk operations
- **One-liner router** — `route_factory()` returns a FastAPI `APIRouter`
- **Works with any ORM** — Pydantic, Beanie, SQLAlchemy/SQLModel

```bash
pip install fastschema
```

---

## 30-Second Demo

```python
from __future__ import annotations
from fastapi import FastAPI, Request
from fastschema import FieldConfig, RouteField, RouteBase, route, route_factory

app = FastAPI()

class Add(FieldConfig):
    required = True

class Edit(FieldConfig):
    default = None

class UserRoute(RouteBase):
    name: str = RouteField(add=Add(), edit=Edit(), min_length=1, max_length=100)
    email: str = RouteField(add=Add(), edit=Edit())

    @classmethod
    @route(path="/users", method="POST", status_code=201)
    async def create_user(cls, request: Request, data: UserRoute.schema("add")):
        return {"id": "1", "name": data.name}

    @classmethod
    @route(path="/users", method="GET")
    async def get_users(cls, request: Request):
        return {"users": []}

app.include_router(route_factory(UserRoute))
```

**Note:** Always use `from __future__ import annotations` at the top of your file.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
  - [FieldConfig](#1-fieldconfig---schema-type-configurations)
  - [RouteField](#2-routefield---declarative-fields)
  - [RouteBase](#3-routebase---base-class)
  - [@route Decorator](#4-route-decorator)
  - [route_factory](#5-route_factory)
- [Examples](#examples)
  - [Raw Pydantic](#raw-pydantic)
  - [Beanie (MongoDB)](#beanie-mongodb)
  - [SQLModel (SQLAlchemy)](#sqlmodel-sqlalchemy)
- [Advanced Features](#advanced-features)
  - [Chain](#chain---compose-functions)
  - [SelfDerivedModel](#selfderivedmodel---bulk-operations)
  - [ClassVar Fields](#classvar-fields)
  - [from_schema()](#from_schema)
  - [Validators](#validators)
  - [Constraint Params](#constraint-params)
- [API Reference](#api-reference)
- [License](#license)

---

## Installation

```bash
pip install fastschema
```

**Optional dependencies:**

```bash
# For Beanie (MongoDB)
pip install beanie motor

# For SQLModel (SQLAlchemy)
pip install sqlmodel aiosqlite
```

---

## Quick Start

### 1. Define Schema Configs

```python
from fastschema import FieldConfig

class Add(FieldConfig):
    required = True

class Edit(FieldConfig):
    default = None

class Output(FieldConfig):
    pass
```

### 2. Define Route Class

```python
from fastschema import RouteField, RouteBase, route

class UserRoute(RouteBase):
    name: str = RouteField(add=Add(), edit=Edit(), output=Output(), min_length=1)
    email: str = RouteField(add=Add(), edit=Edit(), output=Output())

    @classmethod
    @route(path="/users", method="POST", status_code=201)
    async def create_user(cls, request: Request, data: UserRoute.schema("add")):
        # data.name: str (required, min_length=1)
        # data.email: str (required)
        return {"id": "1", "name": data.name}
```

### 3. Register Routes

```python
from fastapi import FastAPI
from fastschema import route_factory

app = FastAPI()
app.include_router(route_factory(UserRoute))
```

---

## Core Concepts

### 1. FieldConfig - Schema Type Configurations

`FieldConfig` defines how a field behaves in different schema contexts:

```python
from fastschema import FieldConfig

class Add(FieldConfig):
    required = True

class Edit(FieldConfig):
    default = None

class Filter(FieldConfig):
    default = None

class Output(FieldConfig):
    pass
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `required` | `bool` | `False` | No default — must be provided |
| `default` | `Any` | `_UNSET` | Default value |
| `default_factory` | `Callable` | `None` | Factory for mutable defaults |
| `alias` | `str` | `None` | Field alias |
| `description` | `str` | `None` | Field description |
| `type_override` | `type` | `None` | Override field type |
| `exclude` | `bool` | `False` | Exclude from this schema |
| `frozen` | `bool` | `False` | Immutable field |
| `apply_func` | `Callable` | `None` | Transform function |
| `before` | `bool` | `True` | Run apply_func before/after validators |
| `metadata` | `dict` | `None` | Extra kwargs for `pydantic.Field` |

---

### 2. RouteField - Declarative Fields

`RouteField` inherits from Pydantic's `FieldInfo`, so it works everywhere:

```python
from fastschema import RouteField, FieldConfig

class Add(FieldConfig):
    required = True

# In RouteBase — schema configs work
class UserRoute(RouteBase):
    title: str = RouteField(
        add=Add(),
        edit=Edit(),
        alias="product_title",
        description="The product title",
        min_length=1,
        max_length=200,
    )

# In BaseModel — Pydantic Field params work
from pydantic import BaseModel

class MyModel(BaseModel):
    title: str = RouteField(alias="x", description="test", min_length=1)
```

**All Pydantic Field params are supported:**

```python
RouteField(
    # Pydantic params
    alias="x",
    validation_alias="title",
    description="Field description",
    exclude=False,
    frozen=False,
    min_length=1,
    max_length=100,
    gt=0,
    ge=0,
    lt=100,
    le=100,
    pattern=r'^[A-Z]+$',
    multiple_of=5,
    json_schema_extra={"example": "hello"},
    # Schema configs
    add=Add(),
    edit=Edit(),
    output=Output(),
)
```

---

### 3. RouteBase - Base Class

`RouteBase` provides schema generation and introspection:

```python
class UserRoute(RouteBase):
    name: str = RouteField(add=Add(), edit=Edit())

# Generate schemas
UserRoute.schema("add")        # => name: str (required)
UserRoute.schema("edit")       # => name: str | None (optional)

# Introspection
UserRoute.schema_types()       # => ["add", "edit"]
UserRoute.schema_fields("add") # => ["name"]
UserRoute.all_fields()         # => {"name": FieldInfo(...)}
UserRoute.field_names()        # => ["name"]
```

---

### 4. @route Decorator

Define endpoints inside the class:

```python
from fastschema import route

class UserRoute(RouteBase):
    @classmethod
    @route(
        path="/users",
        method="POST",
        name="create_user",
        description="Create a new user",
        status_code=201,
        tags=["users"],
    )
    async def create_user(cls, request: Request, data: UserRoute.schema("add")):
        return {"id": "1"}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str` | *required* | URL path |
| `method` | `str` | `"GET"` | HTTP method |
| `name` | `str` | `None` | Route name |
| `description` | `str` | `None` | Route description |
| `status_code` | `int` | `200` | Response status code |
| `tags` | `list[str]` | `None` | OpenAPI tags |

---

### 5. route_factory

Collect all routes into a FastAPI router:

```python
from fastschema import route_factory

router = route_factory(UserRoute, ProductRoute)
app.include_router(router)
```

---

## Examples

### Raw Pydantic

Full example without any ORM:

```python
from __future__ import annotations
from fastapi import FastAPI, Request
from fastschema import FieldConfig, RouteField, RouteBase, route, route_factory
from pydantic import BaseModel, field_validator

app = FastAPI()

# --- Configs ---

class Add(FieldConfig):
    required = True

class Edit(FieldConfig):
    default = None

class Output(FieldConfig):
    pass

# --- Route Class ---

class UserRoute(RouteBase):
    name: str = RouteField(
        add=Add(),
        edit=Edit(),
        output=Output(),
        min_length=1,
        max_length=100,
    )
    email: str = RouteField(add=Add(), edit=Edit(), output=Output())
    age: int = RouteField(add=Add(default=0), edit=Edit(), output=Output(), ge=0)

    @classmethod
    @route(path="/users", method="GET")
    async def get_users(cls, request: Request):
        return {"users": []}

    @classmethod
    @route(path="/users", method="POST", status_code=201)
    async def create_user(cls, request: Request, data: UserRoute.schema("add")):
        return {"id": "1", "name": data.name}

    @classmethod
    @route(path="/users/{user_id}", method="PUT")
    async def update_user(cls, request: Request, user_id: str, data: UserRoute.schema("edit")):
        return {"id": user_id}

    @classmethod
    @route(path="/users/{user_id}", method="DELETE")
    async def delete_user(cls, request: Request, user_id: str):
        return {"deleted": True}

app.include_router(route_factory(UserRoute))
```

---

### Beanie (MongoDB)

Full example with Beanie ODM:

```python
from __future__ import annotations
from fastapi import FastAPI, Request
from fastschema import FieldConfig, RouteField, RouteBase, route, route_factory
from beanie import Document, PydanticObjectId
from contextlib import asynccontextmanager
from pymongo import AsyncMongoClient
from beanie import init_beanie
from typing import ClassVar

app = FastAPI()

# --- Configs ---

class Add(FieldConfig):
    required = True

class Edit(FieldConfig):
    default = None

class Output(FieldConfig):
    pass

class Get(FieldConfig):
    default = None

# --- Document + Route Class ---

class UserRoute(RouteBase, Document):
    name: str = RouteField(add=Add(), edit=Edit(), output=Output(), min_length=1)
    email: str = RouteField(add=Add(), edit=Edit(), output=Output())

    # ClassVar — not in DB, available for schema generation
    token: ClassVar[str | None] = RouteField(get=Get(), add=Add(exclude=True))

    class Settings:
        name = "users"

    @classmethod
    @route(path="/users", method="GET")
    async def get_users(cls, request: Request):
        users = await cls.find_all().to_list()
        return [{"id": str(u.id), "name": u.name} for u in users]

    @classmethod
    @route(path="/users", method="POST", status_code=201)
    async def create_user(cls, request: Request, data: UserRoute.schema("add")):
        user = cls.from_schema(data)
        await user.insert()
        return {"id": str(user.id), "name": user.name}

    @classmethod
    @route(path="/users/{user_id}", method="GET")
    async def get_user(cls, request: Request, user_id: str):
        user = await cls.get(PydanticObjectId(user_id))
        if not user:
            return {"error": "not found"}
        return {"id": str(user.id), "name": user.name}

    @classmethod
    @route(path="/users/{user_id}", method="DELETE")
    async def delete_user(cls, request: Request, user_id: str):
        user = await cls.get(PydanticObjectId(user_id))
        if user:
            await user.delete()
        return {"deleted": True}

# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient("mongodb://localhost:27017")
    await init_beanie(database=client["mydb"], document_models=[UserRoute])
    yield
    client.close()

app = FastAPI(lifespan=lifespan)
app.include_router(route_factory(UserRoute))
```

---

### SQLModel (SQLAlchemy)

Full example with SQLModel:

```python
from __future__ import annotations
from fastapi import FastAPI, Request
from fastschema import FieldConfig, RouteField, RouteBase, route, route_factory
from sqlmodel import SQLModel, Field, Session, create_engine
from typing import ClassVar

# --- Database ---

engine = create_engine("sqlite:///database.db")

# --- Configs ---

class Add(FieldConfig):
    required = True

class Edit(FieldConfig):
    default = None

class Output(FieldConfig):
    pass

# --- Model + Route Class ---

class UserRoute(RouteBase, SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    name: str = RouteField(
        add=Add(),
        edit=Edit(),
        output=Output(),
        min_length=1,
        max_length=100,
    )
    email: str = RouteField(add=Add(), edit=Edit(), output=Output())

    # ClassVar — not in DB, available for schema generation
    token: ClassVar[str | None] = RouteField(
        get=Get(),
        add=Add(exclude=True),
    )

    @classmethod
    @route(path="/users", method="GET")
    async def get_users(cls, request: Request):
        with Session(engine) as session:
            users = session.exec(select(cls)).all()
            return [{"id": u.id, "name": u.name} for u in users]

    @classmethod
    @route(path="/users", method="POST", status_code=201)
    async def create_user(cls, request: Request, data: UserRoute.schema("add")):
        user = cls.from_schema(data)
        with Session(engine) as session:
            session.add(user)
            session.commit()
            session.refresh(user)
        return {"id": user.id, "name": user.name}

    @classmethod
    @route(path="/users/{user_id}", method="GET")
    async def get_user(cls, request: Request, user_id: int):
        with Session(engine) as session:
            user = session.get(cls, user_id)
            if not user:
                return {"error": "not found"}
            return {"id": user.id, "name": user.name}

    @classmethod
    @route(path="/users/{user_id}", method="DELETE")
    async def delete_user(cls, request: Request, user_id: int):
        with Session(engine) as session:
            user = session.get(cls, user_id)
            if user:
                session.delete(user)
                session.commit()
        return {"deleted": True}

# --- Create tables and app ---

SQLModel.metadata.create_all(engine)

app = FastAPI()
app.include_router(route_factory(UserRoute))
```

---

## Advanced Features

### Chain - Compose Functions

Chain multiple functions for `apply_func`:

```python
from fastschema import FieldConfig, RouteField, Chain

def strip(v):
    return v.strip() if isinstance(v, str) else v

def upper(v):
    return v.upper() if isinstance(v, str) else v

def remove_spaces(v):
    return v.replace(" ", "_") if isinstance(v, str) else v

class Add(FieldConfig):
    required = True

class ProductRoute(RouteBase):
    title: str = RouteField(
        add=Add(apply_func=Chain(strip, upper, remove_spaces)),
    )

# "  hello world  " → "hello_world"
```

---

### SelfDerivedModel - Bulk Operations

Derive a field's schema from the route's own fields:

```python
from fastschema import FieldConfig, RouteField, RouteBase, SelfDerivedModel

class Add(FieldConfig):
    required = True

class Output(FieldConfig):
    pass

class BulkAdd(FieldConfig):
    required = True

class BulkEdit(FieldConfig):
    default = None

class UserRoute(RouteBase):
    name: str = RouteField(add=Add(), output=Output())
    email: str = RouteField(add=Add(), output=Output())

    items: list = RouteField(
        bulk_add=BulkAdd(
            default=SelfDerivedModel(schema="add", exclude_fields=["email"])
        ),
    )

# UserRoute.schema("bulk_add") => items: list[name: str]  (email excluded)
```

---

### ClassVar Fields

Use `ClassVar` for fields not in the database but available for schema generation:

```python
from typing import ClassVar

class UserRoute(RouteBase, Document):
    name: str = RouteField(add=Add(), edit=Edit())

    # ClassVar — not in DB, available for schema generation
    token: ClassVar[str | None] = RouteField(get=Get(), add=Add(exclude=True))

# token is NOT in DB columns
# token IS in _fields for schema generation
# token appears in "get" schema, excluded from "add" schema
```

---

### from_schema()

Create Document instances without re-validating nested models:

```python
class UserRoute(RouteBase, Document):
    name: str = RouteField(add=Add())

    @classmethod
    @route(path="/users", method="POST", status_code=201)
    async def create_user(cls, request: Request, data: UserRoute.schema("add")):
        # WRONG — re-validates nested models
        # user = cls(**data.dict())

        # CORRECT — preserves already-validated instances
        user = cls.from_schema(data)
        await user.insert()
        return {"id": str(user.id)}
```

---

### Validators

Validators defined on the route class are propagated to generated models:

```python
from pydantic import BaseModel, field_validator

class Data(BaseModel):
    username: str
    password: str

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, v):
        return v.strip()

class UserRoute(RouteBase, Document):
    data: Data = RouteField(add=Add())

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        return v.strip()

# Both validators run when UserRoute.schema("add") is used
```

---

### Constraint Params

All Pydantic constraint params work in `RouteField`:

```python
class ProductRoute(RouteBase):
    title: str = RouteField(add=Add(), min_length=1, max_length=200)
    price: float = RouteField(add=Add(), gt=0, le=9999.99)
    quantity: int = RouteField(add=Add(), ge=0, multiple_of=1)
    sku: str = RouteField(add=Add(), pattern=r"^[A-Z]{3}-\d{4}$")
    description: str = RouteField(add=Add(), max_length=5000)
```

---

## API Reference

### FieldConfig

```python
class FieldConfig:
    required: bool = False
    default: Any = _UNSET
    default_factory: Callable | None = None
    alias: str | None = None
    description: str | None = None
    type_override: type | None = None
    exclude: bool = False
    frozen: bool = False
    apply_func: Callable | None = None
    before: bool = True
    metadata: dict | None = None
```

### RouteField

```python
class RouteField(PydanticFieldInfo):
    def __init__(
        self,
        default: Any = _UNSET,
        *,
        default_factory: Callable | None = None,
        alias: str | None = None,
        validation_alias: str | None = None,
        serialization_alias: str | None = None,
        description: str | None = None,
        title: str | None = None,
        exclude: bool = False,
        frozen: bool = False,
        deprecated: str | None = None,
        json_schema_extra: dict | None = None,
        validate_default: bool = False,
        repr: bool = True,
        **kwargs: Any,  # Pydantic constraint params + schema configs
    ): ...
```

### RouteBase

```python
class RouteBase(BaseModel, metaclass=RouteMetaclass):
    @classmethod
    def schema(
        cls,
        schema_type: str,
        *,
        name: str | None = None,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
        forbid_extra: bool = True,
        as_literal: bool = False,
    ) -> type[BaseModel]: ...

    @classmethod
    def Schema(cls, schema_type: str) -> type[BaseModel]: ...

    @classmethod
    def schema_fields(cls, schema_type: str) -> list[str]: ...

    @classmethod
    def all_fields(cls) -> dict[str, FieldInfo]: ...

    @classmethod
    def field_names(cls) -> list[str]: ...

    @classmethod
    def schema_types(cls) -> list[str]: ...

    @classmethod
    def from_schema(cls, data) -> Self: ...

    @classmethod
    def field_config_for(cls, field_name: str, schema_type: str) -> FieldConfig | None: ...
```

### SelfDerivedModel

```python
class SelfDerivedModel:
    def __init__(
        self,
        schema: str,
        is_optional: bool = True,
        format: str = "model",
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
    ): ...
```

### route

```python
def route(
    path: str,
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET",
    name: str | None = None,
    description: str | None = None,
    status_code: int = 200,
    tags: list[str] | None = None,
) -> Callable: ...
```

### route_factory

```python
def route_factory(*route_classes: type) -> APIRouter: ...
```

### Chain

```python
class Chain:
    def __init__(self, *funcs: Callable): ...
    def __call__(self, v: Any) -> Any: ...
```

---

## Skills

fastschema includes a `SKILL.md` file for AI code agents (Codex, MiMo, etc.). This file provides agents with specialized knowledge to work effectively with the fastschema package.

**What it covers:**
- Core concepts (FieldConfig, RouteField, RouteBase, @route, route_factory)
- ORM integration patterns (SQLModel, Beanie)
- Advanced features (SelfDerivedModel, Chain, ClassVar, validators)
- Common CRUD and bulk operation patterns

**Usage:** Agents automatically discover and load the skill when working with fastschema-related tasks. The skill file is located at the project root alongside `README.md`.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
