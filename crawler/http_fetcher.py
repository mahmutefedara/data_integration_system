import asyncio
from typing import Optional, Tuple

import aiohttp


class DomainLimiter:
    def __init__(self, per_domain: int):
        self.per_domain = per_domain
        self._locks: dict[str, asyncio.Semaphore] = {}

    def sem(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._locks:
            self._locks[domain] = asyncio.Semaphore(self.per_domain)
        return self._locks[domain]


class HttpFetcher:
    def __init__(
        self,
        timeout_s: int = 20,
        per_domain: int = 2,
        user_agent: str = "aime_crawler/1.0",
    ):
        self._timeout = aiohttp.ClientTimeout(total=timeout_s)
        self._session: Optional[aiohttp.ClientSession] = None
        self._ua = user_agent
        self._limiter = DomainLimiter(per_domain)

    async def open(self):
        if self._session is None or self._session.closed:
            headers = {"User-Agent": self._ua}
            self._session = aiohttp.ClientSession(timeout=self._timeout, headers=headers)

    async def close(self):
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def fetch(self, url: str, domain: Optional[str] = None) -> Tuple[Optional[bytes], str]:
        """
        Returns (data_bytes, content_type). data_bytes None if failed.
        If domain is provided, limits concurrency per-domain.
        """
        await self.open()
        assert self._session is not None

        sem = self._limiter.sem(domain or "_")
        async with sem:
            try:
                async with self._session.get(url, allow_redirects=True) as resp:
                    ctype = resp.headers.get("Content-Type", "") or ""
                    data = await resp.read()
                    return data, ctype
            except Exception:
                return None, ""
