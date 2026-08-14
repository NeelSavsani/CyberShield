import unittest

from app.services.url_safety import (
    UnsafeTargetError,
    ensure_safe_analysis_target,
)


class URLSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def assertBlocked(self, url):
        with self.assertRaises(UnsafeTargetError):
            await ensure_safe_analysis_target(url)

    async def test_public_url_is_allowed(self):
        result = await ensure_safe_analysis_target("https://example.com")
        self.assertTrue(result)

    async def test_localhost_is_blocked(self):
        await self.assertBlocked("http://localhost:8000")

    async def test_private_ip_is_blocked(self):
        await self.assertBlocked("http://192.168.1.10")

    async def test_local_domain_is_blocked(self):
        await self.assertBlocked("http://printer.local")

    async def test_embedded_credentials_are_blocked(self):
        await self.assertBlocked("https://admin:password@example.com")

    async def test_invalid_port_is_blocked(self):
        await self.assertBlocked("https://example.com:99999")