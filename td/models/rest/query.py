from datetime import date, datetime
from enum import Enum
from typing import List

from pydantic import Field, SerializeAsAny, ValidationInfo, field_validator

from td.enums.enums import (
    ContractType,
    ExpirationMonth,
    FrequencyType,
    Markets,
    MoversChange,
    MoversDirection,
    MoversIndex,
    OptionRange,
    OptionType,
    PeriodType,
    Projections,
    StrategyType,
)
from td.models.base_api_model import BaseApiModel
from td.utils.helpers import convert_to_unix_time_ms

# TODO
# Authentication - Delay for now
# User Info and Preferences - Delay for now
# Saved Orders - Might not do since Schwab integration is removing functionality
# Watchlist - Might not do since Schwab integration is removing functionality


class BaseQueryModel(BaseApiModel):
    pass


# Instruments


class InstrumentsQuery(BaseQueryModel):
    symbol: str
    projection: str | Projections

    @field_validator("projection")
    @classmethod
    def validate_projection(cls, projection):
        return cls.validate_str_enum(projection, Projections)


# Market Hours


class MarketHoursQuery(BaseQueryModel):
    markets: str | SerializeAsAny[List[str | Markets]]
    date_time: str | datetime | date | None = Field(alias="date", default=None)

    @field_validator("markets")
    @classmethod
    def validate_markets(cls, markets):
        all_markets = Markets.all_values()
        if isinstance(markets, list):
            for market in markets:
                if isinstance(market, str) and market not in all_markets:
                    raise ValueError(f"Invalid market: {market}")
                if isinstance(market, Markets):
                    market = market.value
            return ",".join(markets)
        elif isinstance(markets, str):
            markets_list = markets.split(",")
            for market in markets_list:
                if market not in all_markets:
                    raise ValueError(f"Invalid market: {market}")
            return markets
        else:
            raise ValueError(
                "Invalid data type for markets. Must be string or List of strings/Markets enum."
            )

    @field_validator("date_time")
    @classmethod
    def format_date_fields(cls, value):
        return cls.validate_iso_date_field(value)


# Movers


class MoversQuery(BaseQueryModel):
    index: str | MoversIndex
    direction: str | MoversDirection
    change: str | MoversChange

    @field_validator("index")
    @classmethod
    def validate_movers_index(cls, index):
        return cls.validate_str_enum(index, MoversIndex)

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, direction):
        return cls.validate_str_enum(direction, MoversDirection)

    @field_validator("change")
    @classmethod
    def validate_change(cls, change):
        return cls.validate_str_enum(change, MoversChange)


# Option Chains


class OptionChainQuery(BaseQueryModel):
    symbol: str
    contract_type: str | ContractType = ContractType.ALL
    strike_count: int | None = None
    include_quotes: bool = False
    strategy: str | StrategyType = StrategyType.SINGLE
    interval: int | None = None
    strike: float | None = None
    option_range: str | OptionRange = Field(alias="range", default=OptionRange.ALL)
    from_date: str | datetime | date | None = None
    to_date: str | datetime | date | None = None
    volatility: int | None = None
    underlying_price: float | None = None
    interest_rate: float | None = None
    days_to_expiration: int | None = None
    expiration_month: str | ExpirationMonth = ExpirationMonth.ALL
    option_type: str | OptionType = OptionType.ALL

    @field_validator("from_date", "to_date")
    @classmethod
    def format_date_fields(cls, value):
        return cls.validate_iso_date_field(value)

    @field_validator(
        "volatility", "underlying_price", "interest_rate", "days_to_expiration"
    )
    @classmethod
    def validate_strategy_fields(cls, value, info: ValidationInfo):
        strategy = info.data.get("strategy")
        if isinstance(strategy, Enum):
            strategy = strategy.value
        if strategy == "SINGLE" and value is not None:
            raise ValueError(f"{value} cannot be set with strategy type SINGLE.")
        return value

    @field_validator("contract_type")
    @classmethod
    def validate_contract_type(cls, contract_type):
        return cls.validate_str_enum(contract_type, ContractType)

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, strategy):
        return cls.validate_str_enum(strategy, StrategyType)

    @field_validator("option_range")
    @classmethod
    def validate_option_range(cls, option_range):
        return cls.validate_str_enum(option_range, OptionRange)

    @field_validator("expiration_month")
    @classmethod
    def validate_expiration_month(cls, expiration_month):
        return cls.validate_str_enum(expiration_month, ExpirationMonth)

    @field_validator("option_type")
    @classmethod
    def validate_option_type(cls, option_type):
        return cls.validate_str_enum(option_type, OptionType)


# Price History


class PriceHistoryQuery(BaseQueryModel):
    api_key: str | None = None
    symbol: str
    period_type: str | PeriodType = PeriodType.DAY
    period: int | None = None
    frequency_type: str | FrequencyType | None = None
    frequency: int | None = None
    start_date: int | datetime | date | None = None
    end_date: int | datetime | date | None = None
    need_extended_hours_data: bool = True

    @field_validator("period_type")
    @classmethod
    def validate_period_type(cls, period_type):
        return cls.validate_str_enum(period_type, PeriodType)

    @field_validator("frequency_type")
    @classmethod
    def validate_frequency_type_str(cls, frequency_type):
        return cls.validate_str_enum(frequency_type, FrequencyType)

    @field_validator("period")
    @classmethod
    def validate_period(cls, period, info: ValidationInfo):
        valid_periods_by_period_type = {
            PeriodType.DAY: [1, 2, 3, 4, 5, 10],
            PeriodType.MONTH: [1, 2, 3, 6],
            PeriodType.YEAR: [1, 2, 3, 5, 10, 15, 20],
            PeriodType.YEAR_TO_DATE: [1],
        }
        period_type = info.data.get("period_type")
        if isinstance(period_type, Enum):
            period_type = period_type.value
        if (
            period
            not in valid_periods_by_period_type[PeriodType.value_mapping()[period_type]]
        ):
            raise ValueError(f"Invalid period for period type {period_type}")
        return period

    @field_validator("frequency_type")
    @classmethod
    def validate_frequency_type(cls, frequency_type, info: ValidationInfo):
        valid_frequency_types_by_period_type = {
            PeriodType.DAY: [FrequencyType.MINUTE],
            PeriodType.MONTH: [FrequencyType.DAILY, FrequencyType.WEEKLY],
            PeriodType.YEAR: [
                FrequencyType.DAILY,
                FrequencyType.WEEKLY,
                FrequencyType.MONTHLY,
            ],
            PeriodType.YEAR_TO_DATE: [FrequencyType.DAILY, FrequencyType.WEEKLY],
        }
        period_type = info.data.get("period_type")
        if isinstance(period_type, Enum):
            period_type = period_type.value
        if isinstance(frequency_type, str):
            frequency_type = FrequencyType.value_mapping()[frequency_type]

        if (
            frequency_type
            not in valid_frequency_types_by_period_type[
                PeriodType.value_mapping()[period_type]
            ]
        ):
            raise ValueError(f"Invalid frequency type for period type {period_type}")
        return frequency_type

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, frequency, info: ValidationInfo):
        valid_frequencies_by_frequency_type = {
            FrequencyType.MINUTE: [1, 5, 10, 15, 30],
            FrequencyType.DAILY: [1],
            FrequencyType.WEEKLY: [1],
            FrequencyType.MONTHLY: [1],
        }
        frequency_type = info.data.get("frequency_type", FrequencyType.MINUTE)
        if isinstance(frequency_type, Enum):
            print(frequency_type)
            frequency_type = frequency_type.value
            print(frequency_type)
        if (
            frequency
            not in valid_frequencies_by_frequency_type[
                FrequencyType.value_mapping()[frequency_type]
            ]
        ):
            raise ValueError(f"Invalid frequency for frequency type {frequency_type}")
        return frequency

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_dates_period(cls, value, info: ValidationInfo):
        if (
            "start_date" in info.data
            and "end_date" in info.data
            and "period" in info.data
        ):
            raise ValueError("Cannot have period with start and end date.")
        return value

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_dates(cls, value):
        return convert_to_unix_time_ms(value)


# Transaction History

# User Info and Preferences

# Watchlist
