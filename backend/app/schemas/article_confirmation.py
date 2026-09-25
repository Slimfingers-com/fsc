from uuid import UUID

from pydantic import BaseModel

from app.enums.confirmation_role import ConfirmationRole


class ArticleConfirmationRoleRead(BaseModel):
    article_id: UUID
    confirmation_role: ConfirmationRole


class ArticleConfirmationRoleUpdate(BaseModel):
    confirmation_role: ConfirmationRole
