import pytest
from ddg_search_mcp import server


class TestEnvHelpers:
    def test_env_int_valid(self, monkeypatch):
        monkeypatch.setenv("DDG_TEST", "42")
        assert server._env_int("DDG_TEST", "10") == 42

    def test_env_int_invalid(self, monkeypatch):
        monkeypatch.setenv("DDG_TEST", "abc")
        assert server._env_int("DDG_TEST", "10") == 10

    def test_env_int_missing(self):
        assert server._env_int("DDG_NONEXISTENT", "10") == 10

    def test_env_float_valid(self, monkeypatch):
        monkeypatch.setenv("DDG_TEST", "3.5")
        assert server._env_float("DDG_TEST", "1.0") == 3.5

    def test_env_float_invalid(self, monkeypatch):
        monkeypatch.setenv("DDG_TEST", "abc")
        assert server._env_float("DDG_TEST", "1.0") == 1.0

    def test_env_float_missing(self):
        assert server._env_float("DDG_NONEXISTENT", "1.0") == 1.0


class TestRegionValidation:
    def test_wt_wt(self):
        assert server.validate_region("wt-wt") == "wt-wt"

    def test_mx_es(self):
        assert server.validate_region("mx-es") == "mx-es"

    def test_invalid(self):
        assert server.validate_region("invalid") == "wt-wt"

    def test_empty(self):
        assert server.validate_region("") == "wt-wt"

    def test_case_insensitive(self):
        assert server.validate_region("MX-ES") == "mx-es"

    def test_numeric(self):
        assert server.validate_region("1234") == "wt-wt"


class TestExtractRealUrl:
    def test_direct_url(self):
        assert server.extract_real_url("https://example.com") == "https://example.com"

    def test_uddg_redirect(self):
        url = "http://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com"
        assert server.extract_real_url(url) == "https://example.com"

    def test_empty(self):
        assert server.extract_real_url("") is None

    def test_tracker(self):
        assert server.extract_real_url("//duckduckgo.com/y.js?q=123") is None

    def test_protocol_relative(self):
        assert server.extract_real_url("//example.com") == "https://example.com"

    def test_none(self):
        assert server.extract_real_url(None) is None

    def test_no_match(self):
        assert server.extract_real_url("javascript:void(0)") is None


class TestDomain:
    def test_simple(self):
        assert server.domain("https://www.example.com/page") == "example.com"

    def test_no_www(self):
        assert server.domain("https://example.com") == "example.com"

    def test_subdomain(self):
        assert server.domain("https://sub.example.com") == "sub.example.com"

    def test_invalid_url(self):
        assert server.domain("not a url") == ""


class TestShouldSkipFetch:
    def test_skips_youtube(self):
        assert server.should_skip_fetch("https://youtube.com/watch?v=123") is True

    def test_skips_facebook(self):
        assert server.should_skip_fetch("https://facebook.com/somepage") is True

    def test_allows_clean_url(self):
        assert server.should_skip_fetch("https://example.com/article") is False

    def test_skips_jstor(self):
        assert server.should_skip_fetch("https://www.jstor.org/stable/123") is True

    def test_skips_twitter(self):
        assert server.should_skip_fetch("https://x.com/user") is True


class TestTextUtils:
    def test_dedupe_removes_duplicates(self):
        assert server.dedupe_lines("Line one\nLine one\nLine two") == "Line one\nLine two"

    def test_dedupe_preserves_empty(self):
        assert server.dedupe_lines("Line one\n\nLine two") == "Line one\n\nLine two"

    def test_dedupe_single_line(self):
        assert server.dedupe_lines("Only one") == "Only one"

    def test_normalize_extra_spaces(self):
        assert server.normalize("  hello   world  ") == "hello\n\nworld"

    def test_normalize_newlines(self):
        result = server.normalize("a\n\n\nb")
        assert result == "a\n\nb"

    def test_clean_content_removes_boilerplate(self):
        raw = "Real content here\nsubscribe\nMore real content"
        result = server.clean_content(raw)
        assert "subscribe" not in result
        assert "Real content" in result


class TestIsAdElement:
    def test_direct_ad_class(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<div>test</div>", "html.parser")
        div = soup.new_tag("div", **{"class": "result badge--ad"})
        div.string = "Ad"
        assert server.is_ad_element(div) is True

    def test_clean_element(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<div>test</div>", "html.parser")
        div = soup.new_tag("div", **{"class": "result"})
        div.string = "Clean"
        assert server.is_ad_element(div) is False

    def test_ad_parent_class(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<div>test</div>", "html.parser")
        parent = soup.new_tag("div", **{"class": "badge--ad"})
        child = soup.new_tag("div", **{"class": "inner"})
        child.string = "Inner"
        parent.append(child)
        assert server.is_ad_element(child) is True


class TestParseHtml:
    def test_lite_parser(self, lite_html):
        results = server.parse_html(lite_html, 5)
        assert len(results) == 2
        assert results[0]["title"] == "Result 1"
        assert results[0]["url"] == "https://example.com/1"
        assert results[1]["title"] == "Result 2"

    def test_respects_limit(self, lite_html):
        results = server.parse_html(lite_html, 1)
        assert len(results) == 1

    def test_empty_html(self, empty_html):
        results = server.parse_html(empty_html, 5)
        assert len(results) == 0

    def test_fallback_parser(self, legacy_html):
        results = server.parse_html(legacy_html, 5)
        assert len(results) == 1
        assert results[0]["title"] == "Legacy Result"
        assert results[0]["url"] == "https://legacy.example.com"

    def test_filters_ads(self, ad_html):
        results = server.parse_html(ad_html, 5)
        assert len(results) == 1
        assert results[0]["title"] == "Real Result"

    def test_zero_limit(self, lite_html):
        results = server.parse_html(lite_html, 0)
        assert len(results) == 0


class TestFallbackTriggered:
    def test_triggered_on_empty(self, empty_html):
        server._fallback_triggered = False
        server.parse_html(empty_html, 5)
        assert server._fallback_triggered is True

    def test_not_triggered_on_success(self, lite_html):
        server._fallback_triggered = False
        server.parse_html(lite_html, 5)
        assert server._fallback_triggered is False


class TestSearchToolDescription:
    def test_search_is_registered(self):
        assert hasattr(server, "search")
        assert callable(server.search)

    def test_search_docstring(self):
        assert "Search DuckDuckGo" in server.search.__doc__


class TestMainEntrypoint:
    def test_main_is_callable(self):
        assert callable(server.main)

    def test_module_has_main(self):
        from ddg_search_mcp import main
        assert callable(main)
