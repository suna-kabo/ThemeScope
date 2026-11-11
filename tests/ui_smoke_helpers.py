"""Shared native disclosure actions for current UI browser acceptance."""
def open_exports(page):
    if not page.locator('#export-menu').evaluate('e=>e.open'):
        page.locator('#export-menu>summary').click()


def open_filters(page):
    if not page.locator('.secondary-filters').evaluate('e=>e.open'):
        page.locator('.secondary-filters>summary').click()
