import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
import selenium.webdriver.edge.service
import selenium.webdriver.edge.webdriver
import selenium.webdriver.chrome.service
import selenium.webdriver.chrome.webdriver
from src.logging_setup import logger
from src.config import ACTIVATION_URL, CID_GROUPS, CID_DIGITS_PER_GROUP

class BrowserController:
    """
    Manages the Selenium-controlled browser instance to navigate the
    Microsoft telephone activation website, fill IDs, and retrieve results.
    """
    def __init__(self):
        self.driver = None

    def is_alive(self) -> bool:
        """
        Checks if the browser instance is open and responding.
        """
        if self.driver is None:
            return False
        try:
            # If the window is closed or driver is dead, accessing window_handles will throw
            _ = self.driver.window_handles
            return True
        except Exception:
            self.driver = None
            return False

    def launch(self) -> bool:
        """
        Launches Edge browser (preferred on Windows) or Chrome as fallback.
        Opens the activation URL and keeps the browser visible.
        """
        if self.is_alive():
            logger.info("Browser is already running. Bringing focus if possible.")
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
                return True
            except Exception:
                pass

        logger.info("Starting browser automation...")
        
        # Try Microsoft Edge first (native to Windows)
        try:
            logger.info("Attempting to launch Microsoft Edge...")
            options = EdgeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-gpu")
            # Clear user profile data to ensure clean login environment
            options.add_argument("--incognito")  # Chrome uses incognito, Edge uses inprivate
            options.add_argument("-inprivate")
            
            self.driver = webdriver.Edge(options=options)
            logger.info("Successfully launched Microsoft Edge.")
        except Exception as edge_err:
            logger.warning(f"Failed to launch Edge: {edge_err}. Attempting Google Chrome fallback...")
            
            # Try Google Chrome fallback
            try:
                options = ChromeOptions()
                options.add_argument("--start-maximized")
                options.add_argument("--disable-gpu")
                options.add_argument("--incognito")
                
                self.driver = webdriver.Chrome(options=options)
                logger.info("Successfully launched Google Chrome.")
            except Exception as chrome_err:
                logger.error(f"Failed to launch Chrome fallback: {chrome_err}")
                self.driver = None
                return False

        try:
            # Navigate to activation portal redirector
            self.driver.get(ACTIVATION_URL)
            logger.info(f"Navigated to: {ACTIVATION_URL}")
            return True
        except Exception as e:
            logger.error(f"Error navigating to {ACTIVATION_URL}: {e}")
            return False

    def _do_fill_iid(self, iid_groups: list) -> bool:
        """
        Inner helper to perform the form filling logic on the current frame context.
        """
        inputs = []
        
        # Method 1: Try finding by ID patterns: otc_0 to otc_8
        for i in range(9):
            element = self.find_element_by_selectors([
                (By.ID, f"otc_{i}"),
                (By.ID, f"txtIID_{i}"),
                (By.ID, f"txtIid_{i}"),
                (By.NAME, f"otc_{i}"),
                (By.CSS_SELECTOR, f"input[id*='otc_{i}']"),
                (By.CSS_SELECTOR, f"input[name*='otc_{i}']"),
                (By.CSS_SELECTOR, f"input[aria-label*='group {i+1}']"),
                (By.CSS_SELECTOR, f"input[aria-label*='Group {i+1}']"),
                (By.CSS_SELECTOR, f"input[aria-label*='character {i+1}']")
            ])
            if element:
                inputs.append(element)
                
        # If we found 9 inputs, clear and fill them
        if len(inputs) == 9:
            for idx, inp in enumerate(inputs):
                val = iid_groups[idx]
                inp.clear()
                inp.send_keys(val)
            logger.info("Successfully filled 9 Installation ID groups in the current frame context.")
            return True

        # Method 2: If we didn't find all 9 by ID pattern, fall back to finding all text-like inputs
        all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
        filtered_inputs = []
        for inp in all_inputs:
            try:
                if inp.is_displayed() and inp.get_attribute("type") in ["text", "tel", "number"]:
                    name = (inp.get_attribute("name") or "").lower()
                    placeholder = (inp.get_attribute("placeholder") or "").lower()
                    # Filter out search or button inputs
                    if "search" not in name and "search" not in placeholder:
                        filtered_inputs.append(inp)
            except Exception:
                continue
            
        # If there are exactly or at least 9 fields, take the first 9
        if len(filtered_inputs) >= 9:
            for idx in range(9):
                inp = filtered_inputs[idx]
                val = iid_groups[idx]
                inp.clear()
                inp.send_keys(val)
            logger.info("Discovered and filled 9 input fields via general DOM search.")
            return True
            
        # Method 3: Try looking for a single large input box
        single_input = self.find_element_by_selectors([
            (By.ID, "installation_id"),
            (By.ID, "iid"),
            (By.CSS_SELECTOR, "input[name='installation_id']"),
            (By.CSS_SELECTOR, "input[placeholder*='Installation ID']"),
            (By.CSS_SELECTOR, "input[placeholder*='installation ID']"),
            (By.CSS_SELECTOR, "input[placeholder*='IID']")
        ])
        if single_input:
            full_iid = "".join(iid_groups)
            single_input.clear()
            single_input.send_keys(full_iid)
            logger.info("Successfully filled Installation ID into single input field.")
            return True

        return False

    def fill_installation_id(self, iid_groups: list) -> bool:
        """
        Finds input elements on the Microsoft self-service activation portal
        and enters the 9 groups of 7 digits. Scans iframes if main context fails.
        """
        if not self.is_alive():
            logger.error("Cannot fill Installation ID: Browser is not running.")
            return False

        logger.info("Attempting to automatically fill Installation ID...")
        
        # 1. Try default content context
        if self._do_fill_iid(iid_groups):
            return True
            
        # 2. If it fails, scan all visible iframes
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                logger.info(f"Discovered {len(iframes)} iframe(s) on the page. Scanning inside them...")
                
                for idx, iframe in enumerate(iframes):
                    try:
                        self.driver.switch_to.frame(iframe)
                        logger.info(f"Checking iframe #{idx}...")
                        if self._do_fill_iid(iid_groups):
                            # Success, we can return
                            return True
                    except Exception as e:
                        logger.debug(f"Could not read iframe #{idx}: {e}")
                    finally:
                        # Revert back to the parent frame context to continue
                        self.driver.switch_to.default_content()
        except Exception as e:
            logger.error(f"Error while scanning iframes: {e}")
            
        logger.warning("No matching Installation ID inputs found on the page or inside iframes.")
        return False

    def find_element_by_selectors(self, selectors: list):
        """
        Attempts to locate an element using a list of selector tuples (By, Value).
        Returns the first element found, or None.
        """
        for by, val in selectors:
            try:
                elem = self.driver.find_element(by, val)
                if elem and elem.is_displayed():
                    return elem
            except Exception:
                continue
        return None

    def _do_scrape_cid(self) -> list:
        """
        Inner helper to locate the 8 groups of 6 digits in the current frame context.
        """
        try:
            # Method 1: Check page text for 8 groups of 6 digits
            body_text = ""
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
            except Exception:
                body_text = self.driver.page_source
                
            six_digit_blocks = re.findall(r"\b\d{6}\b", body_text)
            if len(six_digit_blocks) == 8:
                logger.info(f"Discovered 8 CID blocks in body text: {six_digit_blocks}")
                return six_digit_blocks
            elif len(six_digit_blocks) > 8:
                logger.info(f"Discovered {len(six_digit_blocks)} six-digit blocks. Taking first 8: {six_digit_blocks[:8]}")
                return six_digit_blocks[:8]
                
            # Method 2: Look in inputs on the page
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            input_values = []
            for inp in inputs:
                try:
                    val = (inp.get_attribute("value") or "").strip()
                    if re.match(r"^\d{6}$", val):
                        input_values.append(val)
                except Exception:
                    continue
                    
            if len(input_values) == 8:
                logger.info(f"Discovered 8 CID blocks from input values: {input_values}")
                return input_values
        except Exception as e:
            logger.debug(f"Error inside _do_scrape_cid: {e}")
            
        return []

    def scrape_confirmation_id(self) -> list:
        """
        Searches the current browser page source and elements to locate
        the 8 groups of 6 digits representing the Confirmation ID.
        Scans iframes if main context fails.
        """
        if not self.is_alive():
            logger.error("Cannot scrape Confirmation ID: Browser is not running.")
            return []

        logger.info("Scraping page for Confirmation ID...")
        
        # 1. Try default content context
        cid = self._do_scrape_cid()
        if cid:
            return cid
            
        # 2. Scan iframes
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                logger.info(f"Discovered {len(iframes)} iframe(s). Scanning for Confirmation ID...")
                for idx, iframe in enumerate(iframes):
                    try:
                        self.driver.switch_to.frame(iframe)
                        cid = self._do_scrape_cid()
                        if cid:
                            return cid
                    except Exception as e:
                        logger.debug(f"Could not read iframe #{idx} for CID: {e}")
                    finally:
                        self.driver.switch_to.default_content()
        except Exception as e:
            logger.error(f"Error while scanning iframes for CID: {e}")
            
        logger.warning("Could not automatically locate exactly 8 blocks of 6 digits on the page or inside iframes.")
        return []

    def close(self):
        """
        Closes the browser session.
        """
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser session closed.")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None
