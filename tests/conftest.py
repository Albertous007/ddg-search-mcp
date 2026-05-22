import pytest

LITE_HTML_RESULTS = """
<html><body>
<table>
<tr><td><a class="result-link" href="https://example.com/1">Result 1</a></td></tr>
<tr><td class="result-snippet">Snippet for result 1</td></tr>
<tr><td><a class="result-link" href="https://example.com/2">Result 2</a></td></tr>
<tr><td class="result-snippet">Snippet for result 2</td></tr>
</table>
</body></html>
"""

LITE_HTML_EMPTY = "<html><body><p>No results found.</p></body></html>"

LEGACY_HTML = """
<html><body>
<div class="result">
<a class="result__a" href="https://legacy.example.com">Legacy Result</a>
<div class="result__snippet">Legacy snippet</div>
</div>
</body></html>
"""

AD_HTML = """
<html><body>
<div class="result badge--ad">
<a class="result__a" href="https://ad.example.com">Ad Result</a>
<div class="result__snippet">Ad description</div>
</div>
<div class="result">
<a class="result__a" href="https://real.example.com">Real Result</a>
<div class="result__snippet">Real snippet</div>
</div>
</body></html>
"""


@pytest.fixture
def lite_html():
    return LITE_HTML_RESULTS


@pytest.fixture
def empty_html():
    return LITE_HTML_EMPTY


@pytest.fixture
def legacy_html():
    return LEGACY_HTML


@pytest.fixture
def ad_html():
    return AD_HTML
