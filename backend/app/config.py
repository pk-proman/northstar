import os
from decimal import Decimal

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./northstar.db")
APP_ENV = os.getenv("APP_ENV", "development")
TRADING_MODE = os.getenv("TRADING_MODE", "PAPER").upper()
LIVE_EXECUTION_ENABLED = os.getenv("LIVE_EXECUTION_ENABLED", "false").lower() == "true"

INITIAL_CAPITAL_INR = Decimal(os.getenv("INITIAL_CAPITAL_INR", "750000"))
MAX_CAPITAL_INR = Decimal(os.getenv("MAX_CAPITAL_INR", "1000000"))
MAX_DAILY_LOSS_INR = Decimal(os.getenv("MAX_DAILY_LOSS_INR", "7500"))
MAX_RISK_PER_TRADE_PCT = Decimal(os.getenv("MAX_RISK_PER_TRADE_PCT", "0.5"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
CASH_RESERVE_PCT = Decimal(os.getenv("CASH_RESERVE_PCT", "20"))
PAPER_FEE_RATE = Decimal(os.getenv("PAPER_FEE_RATE", "0.0004"))
PAPER_SLIPPAGE_BPS = Decimal(os.getenv("PAPER_SLIPPAGE_BPS", "5"))
