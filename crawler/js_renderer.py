import asyncio
from playwright.async_api import async_playwright

class JSRenderer:
    def __init__(self, pool_size: int = 2):
        self.pool_size = pool_size
        self._pw = None
        self._browser = None
        self._pages: asyncio.Queue = asyncio.Queue()

    async def start(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        for _ in range(self.pool_size):
            page = await self._browser.new_page()
            await self._pages.put(page)

    async def stop(self):
        while not self._pages.empty():
            p = await self._pages.get()
            try:
                await p.close()
            except:
                pass
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def render(self, url: str) -> str:
        page = await self._pages.get()
        try:
            await page.goto(url, wait_until="networkidle", timeout=20000)
            return await page.content()
        finally:
            await self._pages.put(page)
