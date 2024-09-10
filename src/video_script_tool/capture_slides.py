from PIL import Image
import time
import io
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

from ipydex import IPS

pjoin = os.path.join


class SlideCaptureManager:
    def __init__(self, args):
        self.project_dir = args.project_dir
        self.url = args.url
        self.suffix = args.suffix
        self.first_slide_number = args.first_slide_number
        self.image_dir = f"images{self.suffix}"
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
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "reveal"))
        )

        # Enter fullscreen mode
        driver.find_element(By.CLASS_NAME, "reveal").click()
        time.sleep(1)  # Wait for transition

        slide_count = self.first_slide_number
        fragment_count = 1
        last_slide_flag = False
        image_count = 0

        last_slide_number = "1"

        old_progress_width = -100.0

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
            fragments = driver.find_elements(By.CLASS_NAME, "fragment")
            visible_fragments = [f for f in fragments if "visible" in f.get_attribute("class")]

            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.RIGHT)
            time.sleep(0.8)  # Wait for transition
            new_slide_number = driver.find_elements(By.CLASS_NAME, "slide-number")[0].text

            progress_element = driver.find_elements(By.CLASS_NAME, "progress")[0]
            progress_span = progress_element.find_element(By.TAG_NAME, "span")
            progress_width_str = progress_span.value_of_css_property("width")
            assert progress_width_str.endswith("px")
            progress_width = float(progress_width_str[:-2])

            width_diff = progress_width - old_progress_width
            print(f"{old_progress_width=} → {progress_width=} → {width_diff=}")

            if new_slide_number == last_slide_number:
                # More fragments to reveal
                fragment_count += 1
            else:
                fragment_count = 1
                slide_count += 1

            last_slide_number = new_slide_number

            # Check if we've reached the end of the presentation
            # There are 2 different situations:
            # - last slide has no sub-slide
            # - last slide has a sub-slide

            if "enabled" in driver.find_element(By.CLASS_NAME, "navigate-down").get_attribute("class"):
                has_subslide = True
            else:
                has_subslide = False

            if "enabled" in driver.find_element(By.CLASS_NAME, "navigate-right").get_attribute("class"):
                has_next_slide = True
            else:
                has_next_slide = False

            if not has_subslide:
                if not has_next_slide:
                    # break the loop after saving the last screenshot
                    last_slide_flag = True
                else:
                    # there is a ">" symbol → at least one slide/fragment will follow
                    pass
            else:
                # there is a subslide → we cannot use `has_next_slide` as indicator because it is
                # missing on the last slide of a presentation if it has a subslide
                # we use progress width instead
                # note the progress bar luckily behaves differently if the the last slide has a subslide
                if old_progress_width:
                    width_diff = progress_width - old_progress_width
                    print(f"{width_diff}")
                    if width_diff == 0:
                        # we've reached the end of the presentation
                        break

            # IPS(fragment_count>1)
            old_progress_width = progress_width

        driver.quit()


def main(args):
    scm = SlideCaptureManager(args)
    scm.capture_slides()
