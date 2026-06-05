import re
import time
from src.logging_setup import logger
from src.config import ACTIVATION_URL, CID_GROUPS, CID_DIGITS_PER_GROUP

# Lazy load selenium imports to optimize application startup time
webdriver = None
By = None
EdgeOptions = None
ChromeOptions = None

def _init_selenium():
    global webdriver, By, EdgeOptions, ChromeOptions
    if webdriver is None:
        logger.info("Lazy-loading Selenium dependencies...")
        from selenium import webdriver as _webdriver
        from selenium.webdriver.common.by import By as _By
        from selenium.webdriver.edge.options import Options as _EdgeOptions
        from selenium.webdriver.chrome.options import Options as _ChromeOptions
        import selenium.webdriver.edge.service
        import selenium.webdriver.edge.webdriver
        import selenium.webdriver.chrome.service
        import selenium.webdriver.chrome.webdriver
        webdriver = _webdriver
        By = _By
        EdgeOptions = _EdgeOptions
        ChromeOptions = _ChromeOptions


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
        _init_selenium()
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
            start_char = i * 7 + 1
            end_char = (i + 1) * 7
            element = self.find_element_by_selectors([
                (By.ID, f"otc_{i}"),
                (By.ID, f"txtIID_{i}"),
                (By.ID, f"txtIid_{i}"),
                (By.NAME, f"otc_{i}"),
                (By.CSS_SELECTOR, f"input[id*='otc_{i}']"),
                (By.CSS_SELECTOR, f"input[name*='otc_{i}']"),
                (By.CSS_SELECTOR, f"input[aria-label*='group {i+1}']"),
                (By.CSS_SELECTOR, f"input[aria-label*='Group {i+1}']"),
                (By.CSS_SELECTOR, f"input[aria-label*='character {start_char}-{end_char}']"),
                (By.CSS_SELECTOR, f"input[aria-label*='character {start_char}']")
            ])
            if element and element not in inputs:
                inputs.append(element)
                
        # If we found 9 inputs, clear and fill them
        if len(inputs) == 9:
            for idx, inp in enumerate(inputs):
                val = iid_groups[idx]
                inp.clear()
                inp.send_keys(val)
            logger.info("Successfully filled 9 Installation ID groups in the current frame context.")
            self._click_next_button()
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
            self._click_next_button()
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
            self._click_next_button()
            return True

        return False

    def fill_installation_id(self, iid_groups: list) -> bool:
        """
        Finds input elements on the Microsoft self-service activation portal
        and enters the 9 groups of 7 digits. Scans iframes if main context fails.
        """
        _init_selenium()
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
        _init_selenium()
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

    def _click_next_button(self) -> bool:
        """
        Attempts to find and click the 'Next' or 'Submit' button in the current frame context.
        """
        try:
            btn = self.find_element_by_selectors([
                (By.ID, "next-button"),
                (By.ID, "submit-button"),
                (By.ID, "nextBtn"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Next')]"),
                (By.XPATH, "//button[contains(text(), 'Submit')]"),
                (By.XPATH, "//button[contains(text(), 'next')]"),
                (By.XPATH, "//button[contains(text(), 'submit')]"),
                (By.XPATH, "//a[contains(text(), 'Next')]")
            ])
            if btn:
                btn.click()
                logger.info("Clicked 'Next/Submit' button automatically.")
                return True
        except Exception as e:
            logger.debug(f"Could not click next button: {e}")
        return False

    def _do_answer_question(self) -> bool:
        """
        Inner helper to detect questionnaire elements and auto-select standard answer.
        """
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if "how many" in body_text or "installed on" in body_text or "number of devices" in body_text or "how many computers" in body_text:
                logger.info("Questionnaire page text detected.")
                
                # Check for radio buttons
                radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                if radios:
                    # Look for value "0" or "1"
                    for r in radios:
                        val = r.get_attribute("value") or ""
                        if val == "0" or val == "1":
                            r.click()
                            logger.info(f"Selected radio button automatically with value '{val}'.")
                            self._click_next_button()
                            return True
                            
                    # Fallback: check labels text
                    labels = self.driver.find_elements(By.TAG_NAME, "label")
                    for lbl in labels:
                        lbl_text = lbl.text.lower().strip()
                        if lbl_text == "0" or lbl_text == "1" or "only one" in lbl_text or "not installed on other" in lbl_text:
                            lbl.click()
                            logger.info(f"Clicked radio label: '{lbl.text}'.")
                            self._click_next_button()
                            return True
                            
                # Check for selects
                selects = self.driver.find_elements(By.TAG_NAME, "select")
                for sel in selects:
                    options = sel.find_elements(By.TAG_NAME, "option")
                    for opt in options:
                        val = opt.get_attribute("value") or ""
                        txt = opt.text.lower().strip()
                        if val == "0" or val == "1" or txt == "0" or txt == "1":
                            opt.click()
                            logger.info(f"Selected dropdown option: '{opt.text}'.")
                            self._click_next_button()
                            return True
        except Exception as e:
            logger.debug(f"Error in _do_answer_question: {e}")
        return False

    def _attempt_auto_answer_question(self) -> bool:
        """
        Finds and answers the questionnaire page, scanning inside iframes if needed.
        """
        if self._do_answer_question():
            return True
            
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                for idx, iframe in enumerate(iframes):
                    try:
                        self.driver.switch_to.frame(iframe)
                        if self._do_answer_question():
                            return True
                    except Exception as e:
                        pass
                    finally:
                        self.driver.switch_to.default_content()
        except Exception as e:
            logger.debug(f"Error scanning iframes for questionnaire: {e}")
        return False

    def start_monitor_pipeline(self, iid_groups: list, on_cid_scraped_callback) -> None:
        """
        Polls the browser in a background loop. Detects when login is complete,
        auto-fills the IID, auto-answers the 'number of computers' question,
        and auto-scrapes the CID once it appears.
        """
        _init_selenium()
        logger.info("Background activation pipeline monitor started.")
        
        iid_filled = False
        question_answered = False
        
        while self.is_alive():
            time.sleep(1.5)  # Moderate sleep interval to avoid thrashing CPU
            
            # 1. Skip check if still on login/auth pages
            try:
                current_url = self.driver.current_url.lower()
                if "login.microsoft" in current_url or "login.live" in current_url or "oauth" in current_url:
                    continue
            except Exception:
                continue
                
            # 2. Auto-Fill IID
            if not iid_filled:
                try:
                    current_iid = iid_groups() if callable(iid_groups) else iid_groups
                    if current_iid and len("".join(current_iid)) == 63:
                        if self.fill_installation_id(current_iid):
                            iid_filled = True
                            logger.info("Auto-fill IID step executed successfully. Monitoring next steps...")
                            time.sleep(2.0)
                            continue
                except Exception as e:
                    logger.debug(f"Error checking/filling IID: {e}")
                    
            # 3. Auto-Answer Questionnaire
            if iid_filled and not question_answered:
                try:
                    if self._attempt_auto_answer_question():
                        question_answered = True
                        logger.info("Auto-answered self-service questionnaire step. Monitoring for CID...")
                        time.sleep(2.0)
                        continue
                except Exception as e:
                    logger.debug(f"Error checking/answering questionnaire: {e}")
                    
            # 4. Auto-Scrape CID
            if iid_filled:
                try:
                    cid_groups = self.scrape_confirmation_id()
                    if cid_groups and len(cid_groups) == 8:
                        logger.info(f"Auto-scraped Confirmation ID successfully: {cid_groups}")
                        on_cid_scraped_callback(cid_groups)
                        break
                except Exception as e:
                    logger.debug(f"Error polling for CID: {e}")
                    
        logger.info("Background activation pipeline monitor finished.")

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
