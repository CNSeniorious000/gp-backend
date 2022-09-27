from ..userdata.favorite import get_favorites
from ..userdata.activity import get_activities
from .impl import *

router = APIRouter(tags=["relation"])


class RelationItem(SQLModel, table=True):
    __tablename__ = "relations"
    id: int | None = Field(default=None, primary_key=True)
    from_user_id: str = Field(foreign_key="users.id")
    to_user_id: str = Field(foreign_key="users.id")
    relation: str


class RelationPut(BaseModel):
    from_user_id: str
    to_user_id: str
    relation: str
    permission: bool = False


@router.put("/relative")
async def add_relative(data: RelationPut, bearer: Bearer = Depends()):
    ensure(data.from_user_id), ensure(data.to_user_id)
    assert verify_permitted(bearer.id, data.from_user_id)

    with Session(engine) as session:
        session.add(item := RelationItem(
            from_user_id=data.from_user_id, to_user_id=data.to_user_id, relation=data.relation
        ))
        session.commit()

    return item


@router.get("/relative")
async def get_relatives(id: str | None = None, bearer: Bearer = Depends()):
    from_user_id = id or bearer.id
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
