from PIL import Image
import time
import io
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from ipydex import IPS

pjoin = os.path.join


class SlideCaptureManager:
    def __init__(self, args):
        self.project_dir = args.project_dir
        self.url = args.url
        self.image_dir = pjoin(self.project_dir, "images")
        os.makedirs(self.image_dir, exist_ok=True)

    def capture_slides(self):
        # Set up Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--disable-search-engine-choice-screen")

        production = 1
        if production:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920,1080")
            # chrome_options.add_argument("--window-size=1800,1250")
        else:
            # useful during development
            chrome_options.add_argument("--window-size=1000,600")

        # Initialize the WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(self.url)

        # Wait for the presentation to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "reveal"))
        )

        # Enter fullscreen mode
        driver.find_element(By.CLASS_NAME, "reveal").click()
        time.sleep(1)  # Wait for transition

        slide_count = 1
        fragment_count = 1
        last_slide_flag = False
        image_count = 0

        last_slide_number = "1"

        while True:
            # Capture the current slide
            image_count += 1
            png = driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(png))
            fpath = pjoin(self.image_dir, f"slide_{slide_count:03d}_fragment_{fragment_count:03d}.png")
            img.save(fpath)
            print(f"Screenshot written: {fpath}")
            if last_slide_flag:
                break

            # Check for fragments (does not work reliably)
            # fragments = driver.find_elements(By.CLASS_NAME, "fragment")
            # visible_fragments = [f for f in fragments if "visible" in f.get_attribute("class")]

            driver.find_element(By.TAG_NAME, "body").send_keys(" ")
            new_slide_number = driver.find_elements(By.CLASS_NAME, "slide-number")[0].text

            if new_slide_number == last_slide_number:
                # More fragments to reveal
                fragment_count += 1
            else:
                fragment_count = 1
                slide_count += 1

            last_slide_number = new_slide_number

            # Check if we've reached the end of the presentation
            if "enabled" not in driver.find_element(By.CLASS_NAME, "navigate-right").get_attribute("class"):
                last_slide_flag = True

            time.sleep(0.5)  # Wait for transition

        driver.quit()


def main(args):
    scm = SlideCaptureManager(args)
    scm.capture_slides()
