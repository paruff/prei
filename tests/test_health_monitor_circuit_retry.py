"""Unit tests for DataSourceHealthMonitor circuit breaker and retry logic."""

import pytest

from core.integrations.health_monitor import (
    DataSourceHealthMonitor,
    retry_with_backoff,
)


pytestmark = pytest.mark.django_db(transaction=True)


# Helper function for retry tests (fails first 2 calls, succeeds on 3rd)
_failing_twice_then_succeeding_calls = 0


def _failing_twice_then_succeeding():
    """Function that fails twice, succeeds on third attempt."""
    global _failing_twice_then_succeeding_calls
    _failing_twice_then_succeeding_calls += 1
    if _failing_twice_then_succeeding_calls <= 2:
        raise ValueError("test error")
    return "success"


def _reset_retry_counter():
    _failing_twice_then_succeeding_calls = 0


@pytest.fixture
def monitor() -> DataSourceHealthMonitor:
    return DataSourceHealthMonitor()


class TestDataSourceHealthMonitor:
    def test_check_circuit_open(self, monitor):
        """Circuit opens after 3+ consecutive errors."""
        from core.models import DataSourceHealth

        _ = DataSourceHealth.objects.create(source_name="test", consecutive_errors=3)
        assert monitor.check_circuit("test") is True

    def test_check_circuit_closed(self, monitor):
        """Circuit closed when errors below threshold."""
        from core.models import DataSourceHealth

        _ = DataSourceHealth.objects.create(source_name="test", consecutive_errors=2)
        assert monitor.check_circuit("test") is False

    def test_record_success_resets_counter(self, monitor):
        """Successful run resets consecutive_errors to 0."""
        from core.models import DataSourceHealth

        health = DataSourceHealth.objects.create(
            source_name="test", consecutive_errors=3, status="error"
        )
        monitor.record_success("test", record_count=10)
        health.refresh_from_db()
        assert health.consecutive_errors == 0
        assert health.status == "ok"
        assert health.record_count == 10

    def test_record_failure_increments_counter(self, monitor):
        """Failed run increments consecutive_errors."""
        from core.models import DataSourceHealth

        health = DataSourceHealth.objects.create(
            source_name="test", consecutive_errors=0
        )
        monitor.record_failure("test", Exception("test error"))
        health.refresh_from_db()
        assert health.consecutive_errors == 1
        assert health.status == "error"
        assert "test error" in health.error_message


class TestRetryWithBackoff:
    @retry_with_backoff(max_retries=2, base_delay=0.01)
    def _retry_test_func(self):
        return _failing_twice_then_succeeding()

    def test_retry_eventually_succeeds(self):
        """Function succeeds after retries."""
        _reset_retry_counter()
        result = self._retry_test_func()
        assert result == "success"

    @retry_with_backoff(max_retries=0)
    def always_fails(self):
        raise ValueError("test error")

    def test_retry_exhaustion_raises(self):
        """Exception raised after max retries exhausted."""
        with pytest.raises(ValueError, match="test error"):
            self.always_fails()

    @retry_with_backoff(max_retries=1, base_delay=0.01)
    def succeeds_on_first_try(self):
        return "success"

    def test_no_retry_when_succeeds_first(self):
        """Function returns immediately on first success."""
        result = self.succeeds_on_first_try()
        assert result == "success"
