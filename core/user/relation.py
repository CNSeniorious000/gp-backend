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


class NewRelationForm(BaseModel):
    to_user_id: str
    relation: str
    permission: bool


@router.put("/relationship")
async def new_relationship(form: NewRelationForm, to_bearer: Bearer = Depends()):
    from_user_id = to_bearer.id
    with Session(engine) as session:
        session.add(RelationItem(from_user_id=from_user_id, to_user_id=form.to_user_id, relation=form.relation))
        session.commit()

    add_permission(from_user_id, to_bearer)


@router.get("/relationship")
async def get_relationship(token: str, bearer: Bearer = Depends(), verbose: bool = True):
    user = bearer.user
    results = []
    with Session(engine) as session:
        for item in session.exec(select(RelationItem).where(RelationItem.from_user_id == user.id)):
            to = User(item.to_user_id)
            results.append(
                {
                    "id": item.to_user_id,
                    "name": to["name"],
                    "avatar": to["avatar"],
                    "relation": item.relation,
                    "favorites": await get_favorites(token),
                    "activities": get_activities(token)
                } if verbose else {
                    "name": to["name"], "avatar": to["avatar"], "relation": item.relation
                }
            )

    return results
