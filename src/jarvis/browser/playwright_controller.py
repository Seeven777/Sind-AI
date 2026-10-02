from __future__ import annotations

from dataclasses import dataclass


class BrowserUnavailable(RuntimeError):
    pass


@dataclass(slots=True)
class BrowserSnapshot:
    url:str
    title:str
    text:str


class PlaywrightBrowserController:
    """Structured browser controller.

    Playwright is intentionally optional. Import failure degrades only browser
    capabilities and never blocks Jarvis startup.
    """

    def __init__(self,headless=False):
        self.headless=headless
        self._pw=None
        self._browser=None
        self._page=None

    def available(self):
        try:
            import playwright.async_api  # noqa:F401
            return True
        except Exception:
            return False

    def health(self):
        return {
            'status':'healthy' if self.available() else 'unavailable',
            'backend':'playwright',
            'headless':self.headless,
        }

    async def start(self):
        if self._page is not None:
            return
        if not self.available():
            raise BrowserUnavailable(
                'Playwright não está instalado. Use Setup-Jarvis-Extras.cmd.'
            )
        from playwright.async_api import async_playwright
        self._pw=await async_playwright().start()
        self._browser=await self._pw.chromium.launch(headless=self.headless)
        context=await self._browser.new_context()
        self._page=await context.new_page()

    async def open(self,url):
        await self.start()
        response=await self._page.goto(url,wait_until='domcontentloaded',timeout=30000)
        return {
            'url':self._page.url,
            'title':await self._page.title(),
            'status':response.status if response else None,
        }

    async def snapshot(self,max_chars=20000):
        await self.start()
        return {
            'url':self._page.url,
            'title':await self._page.title(),
            'text':(await self._page.locator('body').inner_text())[:max_chars],
        }

    async def click(self,selector):
        await self.start()
        await self._page.locator(selector).first.click(timeout=15000)
        return await self.snapshot(5000)

    async def fill(self,selector,text):
        await self.start()
        await self._page.locator(selector).first.fill(text,timeout=15000)
        return {
            'url':self._page.url,
            'selector':selector,
            'filled_chars':len(text),
        }

    async def screenshot(self,path):
        await self.start()
        await self._page.screenshot(path=str(path),full_page=False)
        return {'path':str(path),'url':self._page.url}

    async def close(self):
        if self._browser is not None:
            await self._browser.close()
        if self._pw is not None:
            await self._pw.stop()
        self._pw=self._browser=self._page=None
