from .core import BotCore
from .owner import OwnerMixin
from .settings import SettingsMixin
from .moderation import ModerationMixin
from .handlers import HandlersMixin

class Bot(BotCore, OwnerMixin, SettingsMixin, ModerationMixin, HandlersMixin):
    pass
