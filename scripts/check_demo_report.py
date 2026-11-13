"""Browser smoke check; optional Playwright is used only by this QA script."""

from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from qf.demo import run_demo


def main() -> None:
    destination = Path("reports/browser-check").resolve()
    run_demo(destination)
    screenshot_dir = destination / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(offline=True)
        page = context.new_page()
        requests = []
        errors = []
        page.on("request", lambda request: requests.append(request.url))
        page.on("pageerror", lambda error: errors.append(str(error)))
        for width in (1280, 390, 320):
            page.set_viewport_size({"width": width, "height": 900})
            page.goto((destination / "report.html").as_uri())
            expect(page.get_by_role("heading", level=1)).to_be_visible()
            expect(page.locator("svg")).to_be_visible()
            dimensions = page.evaluate("({width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth})")
            assert dimensions["scroll"] <= dimensions["width"], f"Horizontal overflow at {width}px: {dimensions}"
            details = page.locator("details").nth(1)
            expect(details).to_have_attribute("open", "")
            details.locator("summary").click()
            for _ in range(2):
                details.locator("summary").click()
                expect(details.locator("tbody tr")).to_have_count(60)
                expect(details.locator("tbody tr").first).to_be_visible()
                details.locator("summary").click()
                expect(details).not_to_have_attribute("open", "")
            # Pointer selection, repeated selection, browser Back/Forward and
            # keyboard selection all use native fragments, without scripts.
            point = page.locator('svg a[href="#day-25"]')
            point.click()
            selected = page.locator("#day-25")
            expect(selected).to_be_visible()
            expect(selected.locator("tbody tr")).to_have_count(4)
            selected.get_by_role("link", name="返回图表").click()
            expect(selected).not_to_be_visible()
            page.go_back()
            expect(selected).to_be_visible()
            page.go_forward()
            expect(selected).not_to_be_visible()
            point.focus()
            page.keyboard.press("Enter")
            expect(selected).to_be_visible()
            selected.get_by_role("link", name="选择其他日期").click()
            details.locator("summary").click()
            details.locator('a[href="#day-59"]').click()
            expect(page.locator("#day-59")).to_be_visible()
            expect(selected).not_to_be_visible()
            page.reload()
            expect(page.locator("#day-59")).to_be_visible()
            page.screenshot(path=str(screenshot_dir / f"selected-holdings-{width}.png"), full_page=True)
            page.locator("#day-59").get_by_role("link", name="返回图表").click()
            page.screenshot(path=str(screenshot_dir / f"report-{width}.png"), full_page=True)
            page.get_by_role("link", name="独立图表 SVG").click()
            expect(page).to_have_url((destination / "equity.svg").as_uri())
            expect(page.locator("svg")).to_be_visible()
            expect(page.locator("svg a")).to_have_count(0)
            page.go_back()
            expect(page.get_by_role("heading", level=1)).to_be_visible()
            print(f"PASS {width}px: offline report, no overflow, 60 rows, repeat open/close, SVG link and back")
        assert not errors, errors
        remote = [url for url in requests if not url.startswith("file:")]
        assert not remote, f"Unexpected external requests: {remote}"
        browser.close()
    print(f"Browser smoke check passed; screenshots: {screenshot_dir}")


if __name__ == "__main__":
    main()
