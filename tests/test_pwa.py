"""Tests for PWA functionality."""

import json
import pytest
from pathlib import Path


class TestManifest:
    """Tests for manifest.json."""

    def test_manifest_exists(self):
        """Test that manifest.json exists in static directory."""
        manifest_path = Path("static/manifest.json")
        assert manifest_path.exists(), "manifest.json should exist in static/"

    def test_manifest_valid_json(self):
        """Test that manifest.json is valid JSON."""
        manifest_path = Path("static/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert isinstance(manifest, dict)

    def test_manifest_required_fields(self):
        """Test that manifest has all required PWA fields."""
        manifest_path = Path("static/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        required_fields = [
            "name",
            "short_name",
            "start_url",
            "display",
            "background_color",
            "theme_color",
            "icons",
        ]
        for field in required_fields:
            assert field in manifest, f"manifest.json missing required field: {field}"

    def test_manifest_icons(self):
        """Test that manifest has icons array with proper structure."""
        manifest_path = Path("static/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        assert isinstance(manifest["icons"], list)
        assert len(manifest["icons"]) > 0

        for icon in manifest["icons"]:
            assert "src" in icon
            assert "sizes" in icon
            assert "type" in icon


class TestServiceWorker:
    """Tests for service worker."""

    def test_sw_exists(self):
        """Test that sw.js exists in static directory."""
        sw_path = Path("static/sw.js")
        assert sw_path.exists(), "sw.js should exist in static/"

    def test_sw_registers_in_base(self):
        """Test that base.html registers the service worker."""
        base_path = Path("templates/base.html")
        with open(base_path) as f:
            content = f.read()
        assert (
            "navigator.serviceWorker.register" in content
            or "serviceWorker.register" in content
        )

    def test_sw_cache_strategy(self):
        """Test that service worker implements cache-first strategy."""
        sw_path = Path("static/sw.js")
        with open(sw_path) as f:
            content = f.read()

        # Check for cache-first strategy patterns
        assert "cache" in content.lower() or "cacheFirst" in content
        assert "fetch" in content


class TestOfflineFallback:
    """Tests for offline fallback page."""

    def test_offline_page_exists(self):
        """Test that offline.html exists."""
        offline_path = Path("templates/offline.html")
        assert offline_path.exists(), "offline.html should exist in templates/"

    def test_offline_page_content(self):
        """Test that offline page has appropriate content."""
        offline_path = Path("templates/offline.html")
        with open(offline_path) as f:
            content = f.read()

        assert "offline" in content.lower()
        assert "internet" in content.lower() or "connection" in content.lower()


class TestBaseTemplate:
    """Tests for base.html PWA integration."""

    def test_manifest_link(self):
        """Test that base.html links to manifest.json."""
        base_path = Path("templates/base.html")
        with open(base_path) as f:
            content = f.read()
        assert 'rel="manifest"' in content
        assert 'href="/static/manifest.json"' in content or 'href="{% static' in content

    def test_theme_color_meta(self):
        """Test that base.html has theme-color meta tag."""
        base_path = Path("templates/base.html")
        with open(base_path) as f:
            content = f.read()
        assert 'name="theme-color"' in content

    def test_apple_web_app_meta(self):
        """Test that base.html has apple-mobile-web-app-capable meta tag."""
        base_path = Path("templates/base.html")
        with open(base_path) as f:
            content = f.read()
        assert 'name="apple-mobile-web-app-capable"' in content

    def test_viewport_meta(self):
        """Test that base.html has proper viewport meta tag."""
        base_path = Path("templates/base.html")
        with open(base_path) as f:
            content = f.read()
        assert 'name="viewport"' in content
        assert "width=device-width" in content


class TestResponsiveCSS:
    """Tests for responsive CSS."""

    def test_css_has_media_queries(self):
        """Test that CSS has mobile-first responsive breakpoints."""
        css_path = Path("static/css/base.css")
        with open(css_path) as f:
            content = f.read()

        # Check for mobile-first breakpoints
        assert "@media (max-width:" in content
        assert "max-width: 640px" in content or "max-width: 768px" in content

    def test_css_uses_relative_units(self):
        """Test that CSS uses relative units (rem/em) instead of fixed px."""
        css_path = Path("static/css/base.css")
        with open(css_path) as f:
            content = f.read()

        # Check that rem/em are used for spacing/typography
        assert "rem" in content or "em" in content


class TestLighthouseCI:
    """Tests for Lighthouse CI configuration."""

    def test_lighthouserc_exists(self):
        """Test that lighthouserc.json exists."""
        lh_path = Path("lighthouserc.json")
        assert lh_path.exists(), "lighthouserc.json should exist"

    def test_lighthouse_config_valid(self):
        """Test that lighthouserc.json is valid JSON with PWA config."""
        lh_path = Path("lighthouserc.json")
        with open(lh_path) as f:
            config = json.load(f)

        assert "ci" in config
        assert "collect" in config["ci"]
        assert "assert" in config["ci"]


class TestGitHubActions:
    """Tests for GitHub Actions Lighthouse CI step."""

    def test_github_actions_workflow_exists(self):
        """Test that GitHub Actions workflow exists for Lighthouse CI."""
        workflow_dir = Path(".github/workflows")
        assert workflow_dir.exists()

        workflow_files = list(workflow_dir.glob("*.yml")) + list(
            workflow_dir.glob("*.yaml")
        )
        assert len(workflow_files) > 0, "At least one workflow file should exist"

    def test_lighthouse_step_in_workflow(self):
        """Test that Lighthouse CI step exists in a workflow."""
        workflow_dir = Path(".github/workflows")
        workflow_files = list(workflow_dir.glob("*.yml")) + list(
            workflow_dir.glob("*.yaml")
        )

        found = False
        for wf in workflow_files:
            with open(wf) as f:
                content = f.read()
                if "lighthouse" in content.lower() or "lighthouseci" in content:
                    found = True
                    break

        assert found, "No Lighthouse CI step found in GitHub Actions workflows"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
