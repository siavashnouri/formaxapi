
from formaxapi import RouteBase, RouteField, FieldConfig, route, route_factory, SelfDerivedModel
from sqlmodel import Field, Session, SQLModel, create_engine
from typing import ClassVar
engine = create_engine("sqlite:///database.db")


class Add(FieldConfig):
    pass
class BulkAdd(FieldConfig):
    pass

class Edit(FieldConfig):
    pass


class Output(FieldConfig):
    pass

class ProductRoute(RouteBase, SQLModel, table=True):
    _prefix="/product"
    _tags=["product"]
    __tablename__ = "products"
    id: int | None = Field(default=None, primary_key=True, exclude=True)
    title: str = RouteField(add=Add(), edit=Edit(), output=Output())
    price: float = RouteField(add=Add(), edit=Edit(), output=Output())
    
    test_field:ClassVar[list] = RouteField(bulk_add = BulkAdd(default=SelfDerivedModel(schema="add", container="list")))
    
    @classmethod
    @route(path="/create", method="post")
    async def create_product(cls, data:ProductRoute.schema("bulk_add")):
        row = cls.from_schema(data)
        print(row)
        with Session(engine) as session:
            session.add(row)
            session.commit()
            return {"id": row.id}



SQLModel.metadata.create_all(engine)
from fastapi import FastAPI
app = FastAPI()
app.include_router(route_factory(ProductRoute))