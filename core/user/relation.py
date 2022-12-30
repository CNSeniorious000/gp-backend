from random import randrange
from .impl import *
from sqlmodel import Field as DbField
from pydantic import Field

router = APIRouter(tags=["relation"])


class RelationItem(SQLModel, table=True):
    __tablename__ = "relations"
    id: int | None = DbField(default=None, primary_key=True)
    from_user_id: str = DbField(foreign_key="users.id")
    to_user_id: str = DbField(foreign_key="users.id")
    relation: str

    class Config:
        schema_extra = {"example": {
            "id": 1,
            "from_user_id": "******(openid)",
            "to_user_id": "***(openid)",
            "relation": "父/母"
        }}

    @property
    def permitted(self):
        return self.from_user_id in User(self.to_user_id).permissions


class RelativePost(BaseModel):
    from_user_id: str = Field("openid of myself", description="添加谁的亲戚，不填则为自己")
    to_user_id: str = Field("openid of somebody", description="添加谁")
    relation: str = Field("父/母", description="什么关系")


@router.post("/relative", response_model=RelationItem)
async def add_relative(data: RelativePost, bearer: Bearer = Depends()):
    from_user_id = bearer.id if data.from_user_id is None else ensure(data.from_user_id)
    to_user_id = ensure(data.to_user_id)

    if bearer.id != from_user_id:
        assert verify_permitted(bearer.id, from_user_id)

    with Session(engine) as session:
        session.add(item := RelationItem(
            from_user_id=from_user_id, to_user_id=to_user_id, relation=data.relation
        ))
        session.commit()
        session.refresh(item)

    return item


class RelativeRes(RelativePost):
    id: int = Field(1, title="关系唯一标识", description="人与人可以有多重关系，这个id可用在`PATCH`中修改关系名")
    permitted: bool = Field(example=False, title="是否被允许",
                            description="获取允许需要对方账号`PUT`权限接口`/permission`添加自己")


@router.get("/relative", response_model=list[RelativeRes])
async def get_relatives(id: str | None = None, bearer: Bearer = Depends()):
    from_user_id = bearer.id if id is None else ensure(id)
    bearer.ensure_been_permitted_by(from_user_id)
    with Session(engine) as session:
        return [
            {
                "from_user_id": from_user_id,
                "to_user_id": item.to_user_id,
                "relation": item.relation,
                "permitted": from_user_id in User(item.to_user_id).permissions,
                "id": item.id
            }
            for item in session.exec(select(RelationItem).where(RelationItem.from_user_id == from_user_id))
        ]


class RelativePatch(BaseModel):
    id: int = Field(title="关系id", description="每个关系在`GET`到的时候都会有一个id")
    relation: str


@router.patch("/relative", response_model=RelativeRes)
async def update_relative(data: RelativePatch, bearer: Bearer = Depends()):
    with Session(engine) as session:
        item = session.exec(select(RelationItem).where(RelationItem.id == data.id)).one_or_none()
        if item is None:
            raise HTTPException(404, f"relative {data.id} not found")
        bearer.ensure_been_permitted_by(item.from_user_id)

        item.relation = data.relation
        session.add(item)
        session.commit()
        session.refresh(item)

    return RelativeRes(**item.dict(), permitted=item.permitted)


@router.delete("/relative", response_model=str)
async def delete_relative(id: int, bearer: Bearer = Depends()):
    with Session(engine) as session:
        item = session.exec(select(RelationItem).where(RelationItem.id == id)).one_or_none()
        if item is None:
            raise HTTPException(404, f"relative {id} not found")
        bearer.ensure_been_permitted_by(item.from_user_id)

        session.delete(item)
        session.commit()

    return f"delete {id} successfully"


match_cache = Redis(connection_pool=pool, db=2)


@router.post("/match", response_model=str, response_class=PlainTextResponse)
def generate_sequence(n: int = 4, bearer: Bearer = Depends(), expire: int = 60):
    count = 0
    while (sequence := "".join([str(randrange(10)) for _ in range(n)])) in match_cache:
        count += 1
        if count > 1234:
            raise HTTPException(508, f"time out, maybe run out of all possibilities of {n}-digit combinations")

    match_cache[sequence] = bearer.id
    match_cache.set(sequence, bearer.id, expire)

    return sequence


@router.get("/match", response_model=str, response_class=PlainTextResponse)
def match_sequence(sequence: str):
    try:
        return match_cache[sequence]
    except KeyError:
        raise HTTPException(404, f"key {sequence} not found")
