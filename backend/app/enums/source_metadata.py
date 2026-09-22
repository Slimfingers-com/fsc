from enum import StrEnum


class SourceMedium(StrEnum):
    PRINT = "print"
    BROADCAST = "broadcast"
    DIGITAL = "digital"
    AGENCY = "agency"
    PRIMARY_SOURCE = "primary_source"
    ORGANIZATION = "organization"
    OTHER = "other"


class PublicationForm(StrEnum):
    DAILY_NEWSPAPER = "daily_newspaper"
    WEEKLY_NEWSPAPER = "weekly_newspaper"
    SUNDAY_NEWSPAPER = "sunday_newspaper"
    MAGAZINE = "magazine"
    PERIODICAL = "periodical"
    RADIO = "radio"
    TELEVISION = "television"
    DIGITAL_NATIVE = "digital_native"
    NEWS_AGENCY = "news_agency"
    OTHER = "other"


class SourceClassificationDimension(StrEnum):
    EDITORIAL_ORIENTATION = "editorial_orientation"
    RADICALITY = "radicality"
    MEDIA_POSITIONING = "media_positioning"
    LEGAL_STATUS = "legal_status"
    OTHER = "other"


class SourceClassifierType(StrEnum):
    SELF_DESCRIPTION = "self_description"
    MEDIA_DATABASE = "media_database"
    ACADEMIC = "academic"
    PUBLIC_AUTHORITY = "public_authority"
    COURT = "court"
    PUBLISHER = "publisher"
    OTHER = "other"


class SourceMetricKind(StrEnum):
    SOLD_CIRCULATION = "sold_circulation"
    DISTRIBUTED_CIRCULATION = "distributed_circulation"
    PRINT_RUN = "print_run"
    PRINT_READERS = "print_readers"
    DIGITAL_UNIQUE_USERS = "digital_unique_users"
    VISITS = "visits"
    PAGE_IMPRESSIONS = "page_impressions"
    PAID_DIGITAL_SUBSCRIPTIONS = "paid_digital_subscriptions"
    SUBSCRIBERS = "subscribers"
