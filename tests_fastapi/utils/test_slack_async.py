import httpx
import pytest

from src.fastapi_app.utils.slack import send_slack_webhook


@pytest.mark.asyncio
async def test_send_slack_webhook_invalid_url_returns_false():
    ok = await send_slack_webhook("http://example.com", text="hi")
    assert ok is False


@pytest.mark.asyncio
async def test_send_slack_webhook_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == httpx.URL("https://hooks.slack.com/services/T/B/XYZ")
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        ok = await send_slack_webhook(
            "https://hooks.slack.com/services/T/B/XYZ",
            text="hello",
            client=client,
        )
        assert ok is True


@pytest.mark.asyncio
async def test_send_slack_webhook_non_2xx_returns_false():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="bad")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        ok = await send_slack_webhook(
            "https://hooks.slack.com/services/T/B/XYZ",
            text="hello",
            client=client,
        )
        assert ok is False

