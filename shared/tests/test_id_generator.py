"""Tests for ID generation utilities."""

import re

from shared.utils.id_generator import generate_api_key_value, generate_id


class TestGenerateId:
    """Tests for UUID generation."""

    def test_returns_string(self):
        result = generate_id()
        assert isinstance(result, str)

    def test_uuid_format(self):
        result = generate_id()
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, result)

    def test_unique_ids(self):
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100


class TestGenerateApiKeyValue:
    """Tests for API key generation."""

    def test_returns_string(self):
        result = generate_api_key_value()
        assert isinstance(result, str)

    def test_correct_length(self):
        result = generate_api_key_value()
        assert len(result) == 64

    def test_hex_characters_only(self):
        result = generate_api_key_value()
        assert re.match(r"^[0-9a-f]{64}$", result)

    def test_unique_keys(self):
        keys = {generate_api_key_value() for _ in range(100)}
        assert len(keys) == 100
