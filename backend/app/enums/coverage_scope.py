from enum import Enum


class CoverageScope(str, Enum):
    LOCAL = "LOCAL"
    REGIONAL = "REGIONAL"
    NATIONAL = "NATIONAL"
    INTERNATIONAL = "INTERNATIONAL"
    GLOBAL = "GLOBAL"
