"""Shared native disclosure actions for current UI browser acceptance."""
def open_exports(page):
    if not page.locator('#export-menu').evaluate('e=>e.open'):
        page.locator('#export-menu>summary').click()


def open_filters(page):
    if not page.locator('.secondary-filters').evaluate('e=>e.open'):
        page.locator('.secondary-filters>summary').click()


def open_refresh(page):
    disclosure = page.get_by_label("Snapshot and refresh", exact=True)
    if not disclosure.evaluate("e=>e.parentElement.open"):
        disclosure.click()
    return page.locator(".diagnostics").get_by_role("button", name="Refresh Data", exact=True)
