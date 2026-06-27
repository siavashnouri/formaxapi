from __future__ import annotations
from fastapi import FastAPI, Request
from formaxapi import (
    FieldConfig, RouteField, RouteBase, SelfDerivedModel,
    route, route_factory,Chain
)
from pydantic import field_validator, Field
from typing import Annotated
from pydantic import BaseModel
from beanie import Document
from contextlib import asynccontextmanager
from pymongo import AsyncMongoClient
from beanie import init_beanie
from typing import ClassVar
from beanie import PydanticObjectId

class Add(FieldConfig):
    pass

class Edit(FieldConfig):
    pass

class Filter(FieldConfig):
    pass

class Output(FieldConfig):
    pass

class BulkAdd(FieldConfig):
    pass

class BulkEdit(FieldConfig):
    pass

class Get(FieldConfig):
    pass

def apply_f(v):
    return v



def apply_f2(v):
    return v 


class UserRoute(RouteBase, Document):
    name: str = RouteField(add=Add(apply_func=lambda v: v.strip() if isinstance(v, str) else v), edit=Edit(), filter=Filter(), output=Output())
    email: str = RouteField(add=Add(), edit=Edit(), output=Output())


    items: list = RouteField(
        bulk_add=BulkAdd(default=SelfDerivedModel(schema='add', exclude_fields=['email'])),
        bulk_edit=BulkEdit(default=SelfDerivedModel(schema='edit')),
    )

    @classmethod
    @route(path="/users", method="GET")
    async def get_users(cls, request: Request):
        return {"users": []}
    @classmethod
    @route(path="/users", method="POST", status_code=201)
    async def create_user(cls, request: Request, data: UserRoute.schema("add")):
        return {"id": "123", "name": data.name}
    @classmethod
    @route(path="/users/{user_id}", method="PUT")
    async def update_user(cls, request: Request, user_id: str, data: UserRoute.schema("edit")):
        return {"id": user_id}
    @classmethod
    @route(path="/users/{user_id}", method="DELETE")
    async def delete_user(cls, request: Request, user_id: str):
        return {"deleted": True}
    @classmethod
    @route(path="/users/bulk", method="POST", status_code=201)
    async def bulk_create(cls, request: Request, data: UserRoute.schema("bulk_add")):
        return {"count": len(data.items)}
    @classmethod
    @route(path="/users/bulk", method="PUT")
    async def bulk_update(cls, request: Request, data: UserRoute.schema("bulk_edit")):
        return {"count": len(data.items)}


class Data(BaseModel):
    username: str
    password: str


    @field_validator("username", mode="before")
    def validate_username(v):
        return v+" nouri"

class ProductRoute(RouteBase,Document):
    _prefix="test"
    _tags=["product"]
    title: str = RouteField(add=Add(apply_func=Chain(apply_f2, apply_f), before=False), edit=Edit(), output=Output(), min_length=3, max_length= 5)
    price: float = RouteField(add=Add(), edit=Edit(), gt=10, lt=50)

    id_: ClassVar[PydanticObjectId | None] = RouteField(output=Output(), alias="_id")
    doc_id: ClassVar[str | None] = RouteField(default = None, get=Get(), add=Add())
    data: Data = RouteField(add=Add(), edit=Edit(), output=Output())
    @classmethod
    @route(path="/products/get", method="post", tags=["producst"])
    async def get_products(cls, request: Request, data: ProductRoute.schema("get")):
        document = await cls.get(data.doc_id,projection_model=ProductRoute.schema("output"))

        return document

    @classmethod
    @route(path="/products", method="POST", status_code=201)
    async def create_product(cls, request: Request, data: ProductRoute.schema("add")):
        print(data)
        document = cls.model_validate(data, from_attributes=True)
        print(document)
        await document.save()
        return {"id": "123", "title": data.title}


    class Settings:
        name = "products"

    @field_validator("title", mode="before")
    def validate_title(v):
        return v


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient("mongodb://admin:admin@localhost:27017")
    await init_beanie(database=client["test"], document_models=[UserRoute, ProductRoute])
    yield
    client.close()

app = FastAPI(lifespan=lifespan)

app.include_router(route_factory(UserRoute, ProductRoute))