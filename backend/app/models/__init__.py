# Import all models to register them with SQLAlchemy metadata
from app.models.base import Base, IDMixin, TimestampMixin  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.chunk import Chunk  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.system_config import SystemConfig  # noqa: F401
