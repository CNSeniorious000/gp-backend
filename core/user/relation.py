from random import randrange
from .impl import *

router = APIRouter(tags=["relation"])


class RelationItem(SQLModel, table=True):
    __tablename__ = "relations"
    id: int | None = Field(default=None, primary_key=True)
    from_user_id: str = Field(foreign_key="users.id")
    to_user_id: str = Field(foreign_key="users.id")
    relation: str


class RelativePut(BaseModel):
    from_user_id: str | None = Field("openid of mine", description="添加谁的亲戚，不填则为自己")
    to_user_id: str = Field("openid of somebody", description="添加谁")
    relation: str = Field("父/母", description="什么关系")


@router.put("/relative", response_model=RelationItem)
async def add_relative(data: RelativePut, bearer: Bearer = Depends()):
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


@router.get("/relative")
async def get_relatives(id: str | None, bearer: Bearer = Depends()):
    from_user_id = bearer.id if id is None else ensure(id)
    user = bearer.user
    with Session(engine) as session:
        return [
            {
                "from_user_id": from_user_id,
                "to_user_id": item.to_user_id,
                "relation": item.relation,
                "permitted": user.id in User(item.to_user_id).permissions
            }
            for item in session.exec(select(RelationItem).where(RelationItem.from_user_id == from_user_id))
        ]


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
