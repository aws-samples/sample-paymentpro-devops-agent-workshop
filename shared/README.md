# Shared Library — Payment Processing Services

Common models, enums, utilities, and constants used by all backend services.

## Installation

```bash
pip install -e .
```

For development dependencies:
```bash
pip install -e ".[dev]"
```

## Usage

```python
from shared.models.transaction import Transaction, PaymentRequest, PaymentResponse
from shared.models.merchant import Merchant, MerchantRegistration, ApiKey
from shared.enums.types import PaymentType, TransactionStatus
from shared.utils.validators import validate_luhn, validate_upi_id
from shared.utils.id_generator import generate_id, generate_api_key_value
from shared.utils.response import error_response, success_response
from shared.constants.config import MAX_AMOUNT, CURRENCY
```

## Modules

- **models/** — Pydantic v2 data models for all entities and DTOs
- **enums/** — Enum types (PaymentType, TransactionStatus, etc.)
- **utils/** — Utility functions (ID generation, validation, datetime, response formatting)
- **constants/** — Shared configuration constants

## Running Tests

```bash
pytest
pytest --cov=shared --cov-report=term-missing
```

## Linting

```bash
ruff check .
ruff format .
mypy shared/
```
