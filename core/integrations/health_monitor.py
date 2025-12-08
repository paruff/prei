"""Data source health monitoring and alerting."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict

import requests
from django.core.cache import cache
from django.utils import timezone

from core.models import ForeclosureProperty

logger = logging.getLogger(__name__)


class DataSourceHealthMonitor:
    """
    Monitor health and performance of data source integrations.

    Tracks API health, data quality, uptime, and costs.
    """

    HEALTH_CHECK_INTERVAL = 300  # 5 minutes in seconds

    def __init__(self):
        """Initialize health monitor."""
        self.sources = ["attom", "hud"]

    async def check_all_sources(self) -> Dict[str, Any]:
        """
        Check health of all data sources.

        Returns:
            Dictionary with health status for each source
        """
        health_status = {}

        for source in self.sources:
            try:
                status = await self._check_source_health(source)
                health_status[source] = status

                # Store in cache for dashboard
                cache.set(
                    f"health:{source}",
                    status,
                    self.HEALTH_CHECK_INTERVAL,
                )

                # Alert if unhealthy
                if not status.get("healthy", False):
                    await self._send_alert(source, status)

            except Exception as e:
                logger.error(f"Error checking health for {source}: {str(e)}")
                health_status[source] = {
                    "healthy": False,
                    "error": str(e),
                    "lastCheck": datetime.now().isoformat(),
                }

        return health_status

    async def _check_source_health(self, source: str) -> Dict[str, Any]:
        """
        Check individual source health.

        Args:
            source: Source name (attom, hud)

        Returns:
            Health status dictionary
        """
        if source == "attom":
            return await self._check_attom_health()
        elif source == "hud":
            return await self._check_hud_health()
        else:
            return {"healthy": False, "error": f"Unknown source: {source}"}

    async def _check_attom_health(self) -> Dict[str, Any]:
        """
        Check ATTOM API health.

        Returns:
            Health status dictionary
        """
        start_time = datetime.now()

        api_key = os.getenv("ATTOM_API_KEY", "")
        if not api_key:
            return {
                "healthy": False,
                "error": "API key not configured",
                "lastCheck": start_time.isoformat(),
            }

        try:
            # Make a lightweight test request
            response = requests.get(
                "https://api.attomdata.com/propertyapi/v1.0.0/property/detail",
                headers={"apikey": api_key, "Accept": "application/json"},
                params={"address": "123 Main St", "address2": "Miami, FL"},
                timeout=10,
            )

            response_time = (datetime.now() - start_time).total_seconds()

            # Check rate limit headers
            rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
            rate_limit_reset = response.headers.get("X-RateLimit-Reset")

            healthy = response.status_code in [200, 404]  # 404 is ok for test address

            return {
                "healthy": healthy,
                "responseTime": response_time,
                "statusCode": response.status_code,
                "lastCheck": datetime.now().isoformat(),
                "rateLimitRemaining": rate_limit_remaining,
                "rateLimitReset": rate_limit_reset,
            }

        except requests.exceptions.Timeout:
            return {
                "healthy": False,
                "error": "Request timeout",
                "lastCheck": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "lastCheck": datetime.now().isoformat(),
            }

    async def _check_hud_health(self) -> Dict[str, Any]:
        """
        Check HUD website health.

        Returns:
            Health status dictionary
        """
        start_time = datetime.now()

        try:
            # Check if HUD website is accessible
            response = requests.get(
                "https://www.hudhomestore.gov",
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )

            response_time = (datetime.now() - start_time).total_seconds()

            healthy = response.status_code == 200

            return {
                "healthy": healthy,
                "responseTime": response_time,
                "statusCode": response.status_code,
                "lastCheck": datetime.now().isoformat(),
            }

        except requests.exceptions.Timeout:
            return {
                "healthy": False,
                "error": "Request timeout",
                "lastCheck": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "lastCheck": datetime.now().isoformat(),
            }

    def calculate_data_quality_score(
        self, source: str, days: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate data quality score for a source.

        Args:
            source: Source name (ATTOM, HUD)
            days: Number of days to analyze

        Returns:
            Dictionary with quality score and metrics
        """
        since_date = timezone.now() - timedelta(days=days)

        # Get recent properties from source
        recent_props = ForeclosureProperty.objects.filter(
            data_source=source.upper(),
            created_at__gte=since_date,
        )

        total_count = recent_props.count()

        if total_count == 0:
            return {
                "source": source,
                "score": 0.0,
                "totalProperties": 0,
                "period": f"{days} days",
            }

        # Calculate completeness scores
        completeness_scores = []

        required_fields = [
            "street",
            "city",
            "state",
            "zip_code",
            "foreclosure_status",
            "property_type",
        ]

        important_fields = [
            "bedrooms",
            "bathrooms",
            "square_footage",
            "opening_bid",
            "estimated_value",
        ]

        for prop in recent_props:
            # Count required fields
            required_present = sum(
                1 for field in required_fields if getattr(prop, field, None)
            )

            # Count important fields
            important_present = sum(
                1 for field in important_fields if getattr(prop, field, None)
            )

            # Calculate completeness: required fields are weighted 70%, important 30%
            required_completeness = (required_present / len(required_fields)) * 70
            important_completeness = (important_present / len(important_fields)) * 30

            completeness = required_completeness + important_completeness
            completeness_scores.append(completeness)

        avg_completeness = sum(completeness_scores) / len(completeness_scores)

        return {
            "source": source,
            "score": round(avg_completeness, 2),
            "totalProperties": total_count,
            "period": f"{days} days",
            "avgRequiredFields": round(
                sum(
                    sum(1 for field in required_fields if getattr(prop, field, None))
                    for prop in recent_props
                )
                / total_count,
                2,
            ),
            "avgImportantFields": round(
                sum(
                    sum(1 for field in important_fields if getattr(prop, field, None))
                    for prop in recent_props
                )
                / total_count,
                2,
            ),
        }

    def calculate_uptime_percentage(
        self, source: str, hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calculate uptime percentage for a source.

        Args:
            source: Source name
            hours: Number of hours to analyze

        Returns:
            Dictionary with uptime metrics
        """
        # Get health check results from cache
        checks = []
        now = datetime.now()

        # Sample health checks every 5 minutes for the specified hours
        for i in range(0, hours * 12):  # 12 five-minute intervals per hour
            check_time = now - timedelta(minutes=i * 5)
            cache_key = f"health:{source}:{check_time.strftime('%Y%m%d%H%M')}"
            check_result = cache.get(cache_key)

            if check_result:
                checks.append(check_result)

        if not checks:
            return {
                "source": source,
                "uptimePercentage": 0.0,
                "totalChecks": 0,
                "successfulChecks": 0,
                "period": f"{hours} hours",
            }

        successful_checks = sum(1 for check in checks if check.get("healthy", False))
        uptime_percentage = (successful_checks / len(checks)) * 100

        return {
            "source": source,
            "uptimePercentage": round(uptime_percentage, 2),
            "totalChecks": len(checks),
            "successfulChecks": successful_checks,
            "period": f"{hours} hours",
        }

    def get_cost_tracking(
        self, source: str = "attom", days: int = 30
    ) -> Dict[str, Any]:
        """
        Get cost tracking information for ATTOM API.

        Args:
            source: Source name (currently only ATTOM has costs)
            days: Number of days to retrieve

        Returns:
            Dictionary with cost tracking data
        """
        if source.lower() != "attom":
            return {
                "source": source,
                "error": "Cost tracking only available for ATTOM",
            }

        stats: Dict[str, Any] = {
            "source": "ATTOM",
            "days": [],
            "totalCalls": 0,
            "totalCost": Decimal("0"),
            "period": f"{days} days",
        }

        today = datetime.now().date()
        monthly_budget = Decimal(os.getenv("ATTOM_MONTHLY_BUDGET", "1000.00"))

        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.isoformat()

            call_count_key = f"attom_calls_{date_str}"
            cost_key = f"attom_cost_{date_str}"

            calls = cache.get(call_count_key, 0)
            cost = cache.get(cost_key, Decimal("0"))

            stats["days"].append(
                {"date": date_str, "calls": calls, "cost": float(cost)}
            )
            stats["totalCalls"] += calls
            stats["totalCost"] += cost

        stats["totalCost"] = float(stats["totalCost"])
        stats["monthlyBudget"] = float(monthly_budget)
        stats["budgetUsedPercentage"] = round(
            (stats["totalCost"] / float(monthly_budget)) * 100, 2
        )

        # Check if approaching budget thresholds
        if stats["budgetUsedPercentage"] >= 100:
            stats["alert"] = "CRITICAL: Monthly budget exceeded"
        elif stats["budgetUsedPercentage"] >= 90:
            stats["alert"] = "WARNING: Approaching monthly budget (90%)"
        elif stats["budgetUsedPercentage"] >= 80:
            stats["alert"] = "NOTICE: 80% of monthly budget used"

        return stats

    async def _send_alert(self, source: str, status: Dict[str, Any]) -> None:
        """
        Send alert for unhealthy data source.

        TODO: Implement production alerting mechanisms
        Current implementation only logs alerts. For production deployment:
        1. Email alerts via Django email backend
        2. Slack notifications via webhook
        3. PagerDuty integration for critical alerts
        4. SMS alerts for budget overruns

        Example production implementation:
        ```python
        from django.core.mail import send_mail

        send_mail(
            subject=f"Alert: {source} data source unhealthy",
            message=error_msg,
            from_email=settings.ALERT_FROM_EMAIL,
            recipient_list=settings.ALERT_RECIPIENTS,
        )
        ```

        Args:
            source: Source name
            status: Health status dictionary
        """
        error_msg = status.get("error", "Unknown error")
        logger.error(f"ALERT: Data source {source} is unhealthy - {error_msg}")

        # Production: Send email/Slack/PagerDuty alerts here

    def get_health_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive health dashboard data.

        Returns:
            Dictionary with all health metrics
        """
        dashboard_data: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "sources": {},
        }

        for source in self.sources:
            # Get cached health status
            health_status = cache.get(f"health:{source}", {"healthy": None})

            # Get data quality
            quality = self.calculate_data_quality_score(source)

            # Get uptime
            uptime_24h = self.calculate_uptime_percentage(source, hours=24)
            uptime_7d = self.calculate_uptime_percentage(source, hours=24 * 7)

            source_data = {
                "health": health_status,
                "dataQuality": quality,
                "uptime": {"24hours": uptime_24h, "7days": uptime_7d},
            }

            # Add cost tracking for ATTOM
            if source == "attom":
                cost_tracking = self.get_cost_tracking(source)
                source_data["costs"] = cost_tracking

            dashboard_data["sources"][source] = source_data

        return dashboard_data
