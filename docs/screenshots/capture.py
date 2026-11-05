# Captures the screenshots used in the README and the coursework report.
# Needs the full stack with demo data and the tools profile:
#   docker compose --profile tools up -d
#   docker compose exec backend python -m app.seed --force
#   pip install playwright && playwright install chromium
#   python docs/screenshots/capture.py
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

SITE = "http://localhost:8080"
API_DOCS = "http://localhost:8000/docs"
ADMINER = "http://localhost:8081"
OUT = Path(__file__).parent


def settle(page: Page) -> None:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)


def shot(page: Page, name: str, full: bool = False) -> None:
    settle(page)
    page.screenshot(path=OUT / f"{name}.png", full_page=full)
    print("saved", name)


def login(page: Page, email: str, password: str) -> None:
    page.goto(f"{SITE}/login")
    page.fill("input[type=email]", email)
    page.fill("input[type=password]", password)
    page.click("form button.btn")
    settle(page)


def logout(page: Page) -> None:
    page.get_by_role("button", name="Вийти").click()
    settle(page)


def public_and_booking(page: Page) -> None:
    page.goto(SITE)
    shot(page, "01-home", full=True)
    page.goto(f"{SITE}/doctors")
    shot(page, "02-doctors")

    page.goto(f"{SITE}/register")
    for label, value in [("Прізвище", "Коваль"), ("Ім’я", "Оксана"), ("По батькові", "Ігорівна")]:
        page.get_by_label(label, exact=True).fill(value)
    page.get_by_label("Дата народження").fill("1991-04-12")
    page.fill("input[type=tel]", "067 111 22 44")
    page.get_by_label("E-mail", exact=True).fill(f"oksana{int(time.time())}@clinic.example")
    page.fill("input[type=password]", "secret12")
    shot(page, "03-registration")
    page.get_by_role("button", name="Зареєструватися").click()
    expect(page.get_by_role("heading", name="Мої записи")).to_be_visible()

    page.goto(f"{SITE}/doctors/3")
    settle(page)
    page.locator(".day:not([disabled])").nth(1).click()
    settle(page)
    page.locator(".slot").nth(2).click()
    page.fill("textarea", "Підвищений тиск зранку, запаморочення")
    shot(page, "04-booking-slot", full=True)
    page.get_by_role("button", name="Записатися на цей час").click()
    expect(page.locator(".stamp")).to_have_text("Записано")
    page.wait_for_timeout(700)
    shot(page, "05-booked")
    logout(page)


def patient(page: Page) -> None:
    login(page, "patient@medbook.example", "patient123")
    page.goto(f"{SITE}/my")
    shot(page, "06-my-appointments")
    page.get_by_role("button", name="Перенести").first.click()
    page.wait_for_timeout(300)
    page.locator("dialog .day:not([disabled])").nth(2).click()
    settle(page)
    page.locator("dialog .slot").nth(1).click()
    shot(page, "07-reschedule-dialog")
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Минулі").click()
    shot(page, "08-past-appointments")
    page.goto(f"{SITE}/profile")
    shot(page, "09-profile")
    logout(page)


def doctor(page: Page) -> None:
    login(page, "doctor@medbook.example", "doctor123")
    page.set_viewport_size({"width": 1280, "height": 1100})
    today = page.locator(".schedule-day", has_text="Сьогодні")
    today.scroll_into_view_if_needed()
    page.evaluate("window.scrollBy(0, -90)")
    shot(page, "10-doctor-schedule")
    finish = today.get_by_role("button", name="Завершити").first
    if finish.count():
        finish.click()
        page.fill("dialog textarea", "Тиск 135/85. Рекомендовано контроль тиску двічі на день, повторний огляд через 2 тижні.")
        shot(page, "11-doctor-complete")
        page.keyboard.press("Escape")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(f"{SITE}/doctor/history")
    shot(page, "12-doctor-history")
    logout(page)


def admin(page: Page) -> None:
    login(page, "admin@medbook.example", "admin123")
    page.set_viewport_size({"width": 1280, "height": 1050})
    page.goto(f"{SITE}/admin")
    shot(page, "13-report-appointments")
    page.get_by_role("tab", name="Завантаженість лікарів").click()
    page.get_by_role("button", name="6 місяців").click()
    page.locator(".segmented button", has_text="За лікарями").click()
    shot(page, "14-report-doctor-load")
    page.get_by_role("tab", name="Нові пацієнти").click()
    page.get_by_role("button", name="Рік").click()
    shot(page, "15-report-new-patients")
    page.set_viewport_size({"width": 1280, "height": 900})

    page.goto(f"{SITE}/admin/appointments")
    shot(page, "16-admin-appointments")
    page.get_by_role("button", name="Записати пацієнта").click()
    page.fill("dialog input[placeholder*='Прізвище']", "Мельник")
    settle(page)
    page.locator("dialog .btn--ghost", has_text="Мельник").first.click()
    page.locator("dialog select").select_option(index=2)
    settle(page)
    page.locator("dialog .day:not([disabled])").nth(1).click()
    settle(page)
    page.locator("dialog .slot").nth(4).click()
    shot(page, "17-admin-book-for-patient")
    page.keyboard.press("Escape")

    page.goto(f"{SITE}/admin/doctors")
    shot(page, "18-admin-doctors")
    page.goto(f"{SITE}/admin/doctors/1")
    shot(page, "19-admin-doctor-edit", full=True)
    page.goto(f"{SITE}/admin/patients")
    shot(page, "20-admin-patients")
    page.goto(f"{SITE}/admin/notifications")
    shot(page, "21-admin-notifications")
    page.goto(f"{SITE}/admin/settings")
    shot(page, "22-admin-settings")
    logout(page)


def tools(page: Page) -> None:
    page.goto(API_DOCS)
    page.wait_for_selector(".opblock")
    shot(page, "23-swagger")

    page.goto(ADMINER)
    page.select_option("select[name='auth[driver]']", "pgsql")
    page.fill("input[name='auth[server]']", "db")
    page.fill("input[name='auth[username]']", "medbook")
    page.fill("input[name='auth[password]']", "medbook")
    page.fill("input[name='auth[db]']", "medbook")
    page.click("input[type=submit]")
    settle(page)
    shot(page, "24-db-tables")
    page.goto(f"{ADMINER}/?pgsql=db&username=medbook&db=medbook&ns=public&select=appointments&order%5B0%5D=id&desc%5B0%5D=1")
    shot(page, "25-db-appointments")


def mobile(browser) -> None:
    page = browser.new_page(viewport={"width": 400, "height": 860}, device_scale_factor=2)
    page.goto(SITE)
    shot(page, "26-mobile-home")
    page.goto(f"{SITE}/doctors/3")
    settle(page)
    page.locator(".slot").nth(1).click()
    page.locator(".talon").scroll_into_view_if_needed()
    shot(page, "27-mobile-booking")
    page.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    public_and_booking(page)
    patient(page)
    doctor(page)
    admin(page)
    tools(page)
    mobile(browser)
    browser.close()
