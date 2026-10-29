from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict

class CapitalCreate(BaseModel):
    transaction_type: Literal["DEPOSIT", "WITHDRAWAL"]
    amount: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=2)
    reference: str = Field(min_length=3, max_length=100)
    note: str | None = Field(default=None, max_length=500)

class RiskSettingsUpdate(BaseModel):
    max_capital: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    max_daily_loss: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    max_risk_per_trade_pct: Decimal = Field(gt=0, le=2, max_digits=8, decimal_places=4)
    max_open_positions: int = Field(ge=1, le=50)
    cash_reserve_pct: Decimal = Field(ge=0, le=80, max_digits=8, decimal_places=4)
    halted: bool = False

class PaperOrderCreate(BaseModel):
    instrument: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    exchange: Literal["NSE", "BSE"] = "NSE"
    side: Literal["BUY", "SELL"]
    quantity: int = Field(gt=0, le=100000)
    entry_price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    stop_loss: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    target_price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    strategy_name: str = Field(default="Manual paper", max_length=100)

    @model_validator(mode="after")
    def valid_price_levels(self):
        if self.side == "BUY" and not self.stop_loss < self.entry_price < self.target_price:
            raise ValueError("BUY requires stop_loss < entry_price < target_price")
        if self.side == "SELL" and not self.target_price < self.entry_price < self.stop_loss:
            raise ValueError("SELL requires target_price < entry_price < stop_loss")
        return self

class QuoteCreate(BaseModel):
    instrument: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    exchange: Literal["NSE", "BSE"] = "NSE"
    price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    source: str = Field(default="manual_paper_feed", max_length=40)
    observed_at: datetime | None = None
    is_synthetic: bool = True

class ManualExit(BaseModel):
    exit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    reason: Literal["MANUAL", "STOP_LOSS", "TARGET", "TIME_EXIT", "KILL_SWITCH"] = "MANUAL"

class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_order_ref: str
    instrument: str
    exchange: str
    side: str
    quantity: int
    requested_price: Decimal
    entry_fill_price: Decimal
    mark_price: Decimal
    stop_loss: Decimal
    target_price: Decimal
    status: str
    gross_pnl: Decimal
    fees: Decimal
    net_pnl: Decimal
    exit_fill_price: Decimal | None
    exit_reason: str | None
    strategy_name: str
    created_at: datetime
    closed_at: datetime | None
