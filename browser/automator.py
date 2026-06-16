import asyncio
import re


class BrowserAutomator:
    def __init__(self):
        self._browser = None
        self._page = None

    async def _ensure(self):
        if self._browser is None:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=False,
                args=["--start-maximized"]
            )
            ctx = await self._browser.new_context(no_viewport=True)
            self._page = await ctx.new_page()
        return self._page

    async def navigate(self, url):
        page = await self._ensure()
        if not url.startswith("http"):
            url = "https://" + url
        await page.goto(url, wait_until="domcontentloaded")
        return f"Navegou para {url}"

    async def extract_text(self):
        page = await self._ensure()
        text = await page.inner_text("body")
        return text[:5000]

    async def extract_html(self):
        page = await self._ensure()
        html = await page.content()
        return html[:10000]

    async def search_and_extract(self, query):
        page = await self._ensure()
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await asyncio.sleep(1)
        results = await page.evaluate("""
            () => {
                const items = document.querySelectorAll('div.g');
                return Array.from(items).slice(0, 5).map(item => ({
                    title: item.querySelector('h3')?.innerText || '',
                    link: item.querySelector('a')?.href || '',
                    snippet: item.querySelector('.VwiC3b')?.innerText || ''
                }));
            }
        """)
        return "\n".join(
            f"{r['title']}: {r['snippet']} ({r['link']})"
            for r in results if r['title']
        )

    async def fill_form(self, selector, value):
        page = await self._ensure()
        await page.fill(selector, value)
        return f"Preenchido {selector} com {value[:50]}"

    async def click(self, selector):
        page = await self._ensure()
        await page.click(selector)
        return f"Clicou em {selector}"

    async def screenshot(self, path=None):
        page = await self._ensure()
        if path is None:
            import tempfile, os
            path = os.path.join(tempfile.gettempdir(), "jarvis_browser.png")
        await page.screenshot(path=path, full_page=True)
        return path

    async def close(self):
        if self._browser:
            await self._browser.close()
            await self._pw.stop()
            self._browser = None
            self._page = None

    def sync_navigate(self, url):
        return asyncio.run(self.navigate(url))

    def sync_extract_text(self):
        return asyncio.run(self.extract_text())

    def sync_search_and_extract(self, query):
        return asyncio.run(self.search_and_extract(query))

    def sync_fill_form(self, selector, value):
        return asyncio.run(self.fill_form(selector, value))

    def sync_click(self, selector):
        return asyncio.run(self.click(selector))

    def sync_screenshot(self, path=None):
        return asyncio.run(self.screenshot(path))
