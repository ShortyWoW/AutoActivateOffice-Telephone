import pyperclip
from src.logging_setup import logger
from src.config import DIGITS_ONLY_RE

def copy_to_clipboard(text: str, label: str = "Text"):
    """
    Copies the given text to the system clipboard.
    """
    try:
        pyperclip.copy(text)
        logger.info(f"Copied {label} to clipboard.")
        return True
    except Exception as e:
        logger.error(f"Failed to copy {label} to clipboard: {e}")
        return False

def get_from_clipboard() -> str:
    """
    Reads text from the system clipboard.
    """
    try:
        return pyperclip.paste()
    except Exception as e:
        logger.error(f"Failed to paste from clipboard: {e}")
        return ""

def copy_iid_groups(groups: list):
    """
    Formats the 9 groups of 7 digits with spaces and copies to clipboard.
    """
    clean_groups = [str(g).strip() for g in groups if g]
    formatted = " ".join(clean_groups)
    return copy_to_clipboard(formatted, "Installation ID")

def copy_cid_groups(groups: list):
    """
    Formats the 8 groups of 6 digits with spaces and copies to clipboard.
    """
    clean_groups = [str(g).strip() for g in groups if g]
    formatted = " ".join(clean_groups)
    return copy_to_clipboard(formatted, "Confirmation ID")

def parse_clipboard_digits() -> str:
    """
    Pulls clipboard content, extracts only numerical digits, and returns them as a single string.
    """
    content = get_from_clipboard()
    digits = "".join(DIGITS_ONLY_RE.findall(content))
    if digits:
        logger.info(f"Parsed {len(digits)} digits from clipboard.")
    return digits
