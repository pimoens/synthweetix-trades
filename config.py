from apscheduler.triggers.interval import IntervalTrigger
from enum import Enum
import logging
import os


__author__ = 'Pieter Moens'
__email__ = "pieter@pietermoens.be"


class BaseConfig:
    TWITTER_CONSUMER_KEY = os.getenv('TWITTER_CONSUMER_KEY', default='')
    TWITTER_CONSUMER_SECRET = os.getenv('TWITTER_CONSUMER_SECRET', default='')
    TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN', default='')
    TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET', default='')

    ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', default='')

    TRADE_VALUE_THRESHOLD = int(os.getenv('TRADE_VALUE_THRESHOLD', default=250000))
    EYE_CATCHER_THRESHOLD = int(os.getenv('EYECATCHER_VALUE_THRESHOLD', default=1000000))


class DevelopmentConfig(BaseConfig):
    LOG_LEVEL = logging.INFO

    TRIGGER = IntervalTrigger(minutes=5)


class ProductionConfig(BaseConfig):
    LOG_LEVEL = logging.WARNING

    TRIGGER = IntervalTrigger(minutes=5)


class CronJobConfig(ProductionConfig):
    LOG_LEVEL = logging.WARNING

    TRIGGER = None


class ConfigType(Enum):
    DEVELOPMENT = 'development'
    PRODUCTION = 'production'

    @classmethod
    def reverse_lookup(cls, value):
        """Reverse lookup."""
        for _, member in cls.__members__.items():
            if member.value == value:
                return member
        raise LookupError


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance


@singleton
class ConfigFactory:
    _configs = {
        ConfigType.DEVELOPMENT: DevelopmentConfig,
        ConfigType.PRODUCTION: ProductionConfig
    }
    current = None

    def get(self, type_: ConfigType):
        cls = self._configs[type_]
        self.current = cls()
        return self.current
