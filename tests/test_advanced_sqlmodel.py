from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from formaxapi import FieldConfig, RouteField, RouteBase, route, route_factory, Chain
from pydantic import BaseModel, field_validator
from sqlmodel import Field, Session, SQLModel, create_engine
from typing import Optional, ClassVar


# --- Configs ---

class Add(FieldConfig):
    required = True

class Edit(FieldConfig):
    default = None

class Output(FieldConfig):
    pass

class Get(FieldConfig):
    default = None


# --- Nested model ---

class Address(BaseModel):
    street: str
    city: str

    @field_validator("city", mode="before")
    @classmethod
    def uppercase_city(cls, v):
        return v.upper() if isinstance(v, str) else v


# --- ORM + Route model ---

class UserRoute(RouteBase, SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    name: str = RouteField(
        add=Add(apply_func=lambda v: v.strip() if isinstance(v, str) else v),
        edit=Edit(),
        output=Output(),
    )
    email: str = RouteField(add=Add(), edit=Edit(), output=Output())
    age: int = RouteField(add=Add(default=0), edit=Edit(default=None), output=Output(), ge=20)

    # classvar field — not in DB, available for schema generation
    token: ClassVar[str|None] = RouteField(default=None, get=Get(), add=Add())

    @classmethod
    @route(path="/users", method="GET", description="List all users")
    async def get_users(cls, request: Request):
        with Session(engine) as session:
            users = session.exec(select(UserRoute)).scalars().all()
            result = []
            for u in users:
                result.append({"id": u.id, "name": u.name, "email": u.email})
            return result

    @classmethod
    @route(path="/users", method="POST", status_code=201, description="Create user")
    async def create_user(cls, request: Request, data: UserRoute.schema("add")):
        user = cls.from_schema(data)
        with Session(engine) as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            return {"id": user.id, "name": user.name, "email": user.email}

    @classmethod
    @route(path="/users/{user_id}", method="GET", description="Get user by ID")
    async def get_user(cls, request: Request, user_id: int):
        with Session(engine) as session:
            user = session.get(UserRoute, user_id)
            if not user:
                return {"error": "not found"}
            return {"id": user.id, "name": user.name, "email": user.email, "age": user.age}

    @classmethod
    @route(path="/users/{user_id}", method="PUT", description="Update user")
    async def update_user(cls, request: Request, user_id: int, data: UserRoute.schema("edit")):
        with Session(engine) as session:
            user = session.get(UserRoute, user_id)
            if not user:
                return {"error": "not found"}
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(user, key, value)
            session.add(user)
            session.commit()
            session.refresh(user)
            return {"id": user.id, "name": user.name, "email": user.email}

    @classmethod
    @route(path="/users/{user_id}", method="DELETE", description="Delete user")
    async def delete_user(cls, request: Request, user_id: int):
        with Session(engine) as session:
            user = session.get(UserRoute, user_id)
            if not user:
                return {"error": "not found"}
            session.delete(user)
            session.commit()
            return {"deleted": True}

    @classmethod
    @route(path="/users/search", method="POST", description="Search users with nested model")
    async def search_users(cls, request: Request, data: Address):
        return {"query": f"Searching in {data.city}"}


# --- z`` model (different route) ---

class ProductRoute(RouteBase, SQLModel, table=True):
    __tablename__ = "products"

    id: int | None = Field(default=None, primary_key=True)
    title: str = RouteField(
        add=Add(apply_func=Chain(lambda v: v.strip(), lambda v: v.upper())),
        edit=Edit(),
        output=Output(),
    )
    price: float = RouteField(add=Add(), edit=Edit(), output=Output())

    @classmethod
    @route(path="/products", method="GET")
    async def get_products(cls, request: Request):
        with Session(engine) as session:
            products = session.exec(select(ProductRoute)).scalars().all()
            result = []
            for p in products:
                result.append({"id": p.id, "title": p.title, "price": p.price})
            return result

    @classmethod
    @route(path="/products", method="POST", status_code=201)
    async def create_product(cls, request: Request, data: ProductRoute.schema("add")):
        product = cls.from_schema(data)
        with Session(engine) as session:
            session.add(product)
            session.commit()
            session.refresh(product)
            return {"id": product.id, "title": product.title, "price": product.price}


# --- App setup ---

from sqlalchemy import select

engine = create_engine("sqlite:///test_advanced.db")
SQLModel.metadata.create_all(engine)

app = FastAPI()
app.include_router(route_factory(UserRoute, ProductRoute))

client = TestClient(app)


# # === TESTS ===

# def test_create_user():
#     resp = client.post("/users", json={"name": "  ali  ", "email": "ali@test.com", "age": 25})
#     assert resp.status_code == 201
#     data = resp.json()
#     assert data["name"] == "ali"  # apply_func stripped whitespace
#     assert data["email"] == "ali@test.com"
#     print(f"PASS create_user: {data}")


# def test_create_user_default_age():
#     resp = client.post("/users", json={"name": "sara", "email": "sara@test.com"})
#     assert resp.status_code == 201
#     data = resp.json()
#     print(f"PASS create_user_default_age: {data}")


# def test_get_users():
#     resp = client.get("/users")
#     assert resp.status_code == 200
#     users = resp.json()
#     assert isinstance(users, list)
#     assert len(users) >= 1
#     print(f"PASS get_users: {len(users)} users")


# def test_get_user_by_id():
#     resp = client.post("/users", json={"name": "test", "email": "test@test.com"})
#     user_id = resp.json()["id"]
#     resp = client.get(f"/users/{user_id}")
#     assert resp.status_code == 200
#     assert resp.json()["name"] == "test"
#     print(f"PASS get_user_by_id: {resp.json()}")


# def test_get_user_not_found():
#     resp = client.get("/users/99999")
#     assert resp.status_code == 200
#     assert resp.json()["error"] == "not found"
#     print("PASS get_user_not_found")


# def test_update_user():
#     resp = client.post("/users", json={"name": "update_me", "email": "update@test.com"})
#     user_id = resp.json()["id"]
#     resp = client.put(f"/users/{user_id}", json={"name": "updated"})
#     assert resp.status_code == 200
#     assert resp.json()["name"] == "updated"
#     print(f"PASS update_user: {resp.json()}")


# def test_delete_user():
#     resp = client.post("/users", json={"name": "delete_me", "email": "del@test.com"})
#     user_id = resp.json()["id"]
#     resp = client.delete(f"/users/{user_id}")
#     assert resp.status_code == 200
#     assert resp.json()["deleted"] is True
#     resp = client.get(f"/users/{user_id}")
#     assert resp.json()["error"] == "not found"
#     print("PASS delete_user")


# def test_validator_propagates():
#     resp = client.post("/users", json={"name": " validator_test ", "email": "v@test.com"})
#     assert resp.status_code == 201
#     assert resp.json()["name"] == "validator_test"
#     print("PASS validator_propagates")


# def test_product_create_with_chain():
#     resp = client.post("/products", json={"title": "  hello world  ", "price": 99.99})
#     assert resp.status_code == 201
#     assert resp.json()["title"] == "HELLO WORLD"
#     print(f"PASS product_chain: {resp.json()}")


# def test_product_get():
#     client.post("/products", json={"title": "test product", "price": 10.0})
#     resp = client.get("/products")
#     assert resp.status_code == 200
#     data = resp.json()
#     assert isinstance(data, list)
#     assert len(data) >= 1
#     print(f"PASS product_get: {len(data)} products")


# def test_nested_model():
#     resp = client.post("/users/search", json={"street": "123 Main", "city": "tehran"})
#     assert resp.status_code == 200
#     assert resp.json()["query"] == "Searching in TEHRAN"
#     print("PASS nested_model")


# def test_schema_generation():
#     add_schema = UserRoute.schema("add")
#     assert "name" in add_schema.model_fields
#     assert "email" in add_schema.model_fields
#     assert "token" not in add_schema.model_fields  # classvar + exclude

#     output_schema = UserRoute.schema("output")
#     assert "name" in output_schema.model_fields
#     assert "token" not in output_schema.model_fields

#     print("PASS schema_generation")


# def test_classvar_not_in_db():
#     # token is classvar=True, should not be in SQLModel's model_fields
#     assert "token" not in UserRoute.model_fields
#     assert "token" in UserRoute._fields  # but IS in framework's _fields for schema gen

#     # Verify schema still works with classvar fields
#     get_schema = UserRoute.schema("get")
#     assert "token" in get_schema.model_fields

#     add_schema = UserRoute.schema("add")
#     assert "token" not in add_schema.model_fields  # excluded by Add(exclude=True)

#     print("PASS classvar_not_in_db")


# # === RUN ALL ===

# if __name__ == "__main__":
#     import os
#     db_path = "test_advanced.db"
#     if os.path.exists(db_path):
#         try:
#             engine.dispose()
#             os.remove(db_path)
#         except PermissionError:
#             pass
#         engine = create_engine(f"sqlite:///{db_path}")
#         SQLModel.metadata.create_all(engine)

#     tests = [
#         test_create_user,
#         test_create_user_default_age,
#         test_get_users,
#         test_get_user_by_id,
#         test_get_user_not_found,
#         test_update_user,
#         test_delete_user,
#         test_validator_propagates,
#         test_product_create_with_chain,
#         test_product_get,
#         test_nested_model,
#         test_schema_generation,
#         test_classvar_not_in_db,
#     ]

#     passed = 0
#     failed = 0
#     for test in tests:
#         try:
#             test()
#             passed += 1
#         except Exception as e:
#             print(f"FAIL {test.__name__}: {e}")
#             failed += 1

#     print(f"\n{'='*40}")
#     print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
