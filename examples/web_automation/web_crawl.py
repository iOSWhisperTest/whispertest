import json
from time import sleep
from urllib.parse import urlparse
from datetime import datetime

import pymobiledevice3
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.web_protocol.driver import WebDriver
from pymobiledevice3.services.webinspector import SAFARI, WebinspectorService

# insert path. Can be removed if whisper_test is installed
import sys
from os.path import dirname, abspath, join
sys.path.insert(0, abspath(join(dirname(dirname(__file__)), '..')))

from whisper_test.device import WhisperTestDevice
from whisper_test.common import logger


WAIT_DURATION_AFTER_VC = 3

RELIABLE_DOMAINS = abspath(join(dirname(__file__), 'reliable_domains.txt'))
UNRELIABLE_DOMAINS = abspath(join(dirname(__file__), 'unreliable_domains.txt'))


def scrape_privacy_report(dev: WhisperTestDevice, test_hostname: str, timestamp: str) -> None:
    """Scrape Safari Privacy Report."""
    dev.tts.say("View Privacy Report")
    sleep(2)
    dev.take_screenshot(f'lockdown/{test_hostname}_privacy_report_{timestamp}.png')
    privacy_report = dev.a11y.get_ax_list_items(timeout=20, max_items=-1)
    dev.tts.say("Back done")
    sleep(2)
    return privacy_report


def scrape_webpage_details(dev: WhisperTestDevice, driver: WebDriver, target_url: str) -> None:
    """Load and scrape a given page."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    page_data = dict()
    logger.info("Loading %s", target_url)
    test_hostname = urlparse(target_url).hostname
    t0 = datetime.now()
    try:
        driver.get(target_url)
    except (pymobiledevice3.exceptions.WirError,
            pymobiledevice3.exceptions.ConnectionFailedError) as wderr:
        logger.error("Error loading %s: %s", target_url, wderr)
        return
    page_data['load_time'] = (datetime.now() - t0).total_seconds() * 1000
    logger.info("⏱️  Page load time: %.2f ms", page_data['load_time'])
    page_data['test_url'] = target_url
    page_data['final_url'] = driver.current_url
    page_data['title'] = driver.title
    page_data['page_source'] = driver.page_source
    page_data['inner_text'] = driver.execute_script('return document?.body.innerText;')
    page_data['error'] = ""
    if "Safari can’t open the page because the server can’t" in page_data['inner_text']:
        logger.error("ERROR: Page not found %s", target_url)
        return
    driver.get_screenshot_as_file(f'lockdown/{test_hostname}_homepage_{timestamp}.png')
    result = dev.tts.say("View page menu")
    if not result:
        logger.error("ERROR: Cannot open the page menu %s", target_url)
        return
    sleep(WAIT_DURATION_AFTER_VC)
    dev.take_screenshot(f'lockdown/{test_hostname}_page_menu_{timestamp}.png')

    page_data['page_menu'] = dev.a11y.get_ax_list_items(timeout=5, max_items=10)
    # logger.debug("page_menu", page_data['page_menu'])

    if any("No Trackers Contact" in menu_item for menu_item in page_data['page_menu']):
        logger.info("No trackers found %s", target_url)
        page_data['privacy_report'] = []
    else:
        page_data['privacy_report'] = scrape_privacy_report(dev, test_hostname, timestamp)
        # logger.debug("Privacy report %s %s", target_url, page_data['privacy_report'])
        sleep(WAIT_DURATION_AFTER_VC)
        dev.tts.say("View page menu")

    if any("Connection Security Details" in menu_item for menu_item in page_data['page_menu']):
        result = dev.tts.say("Tap, connection security details")
        sleep(WAIT_DURATION_AFTER_VC)
        if not result:
            logger.error("Cannot open the certificate details %s", target_url)
            return
        dev.take_screenshot(f'lockdown/{test_hostname}_certificate_details_{timestamp}.png')
        page_data['cert_details'] = dev.a11y.get_ax_list_items(timeout=5, max_items=-1)
    else:
        page_data['cert_details'] = []
        logger.info("No certificate details found (http?) %s", target_url)

    with open(f'lockdown/{test_hostname}_{timestamp}.json', 'w', encoding='utf-8') as f:
        json.dump(page_data, f, ensure_ascii=False, indent=2)


def crawl_urls(dev: WhisperTestDevice, urls: list[str]) -> None:
    """Crawl a list of URLs and scrape data."""
    inspector = WebinspectorService(lockdown=create_using_usbmux())
    inspector.connect()
    safari = inspector.open_app(SAFARI)
    inspector.flush_input(1)
    session = inspector.automation_session(safari)
    session.page_load_timeout = 10000
    session.implicit_wait_timeout = 10000

    for url in urls:
        driver = WebDriver(session)
        driver.start_session()
        try:
            scrape_webpage_details(dev, driver, url)
        except Exception as wderr:
            print(f"Error loading {url}: {wderr}")
            continue

    inspector.close()
    inspector.loop.close()


N_URLS_TO_CRAWL = 100


def main():
    """Initialize the device an run the web crawl."""
    dev = WhisperTestDevice(connect_to_device=True)

    reliable_domains = []
    unreliable_domains = []

    for line in open(RELIABLE_DOMAINS, encoding='utf-8'):
        reliable_domains.append("https://" + line.strip())

    for line in open(UNRELIABLE_DOMAINS, encoding='utf-8'):
        unreliable_domains.append("https://" + line.strip())

    crawl_urls(dev, reliable_domains[:N_URLS_TO_CRAWL])
    crawl_urls(dev, unreliable_domains[:N_URLS_TO_CRAWL])

if __name__ == "__main__":
    main()
