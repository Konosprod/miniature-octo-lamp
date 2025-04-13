import binascii
import re

from lxml import html

REGEX_SOURCE = re.compile(r"\(Source.*\)")


def clean_html_string(html_string: str) -> str:
    """Clean HTML string by removing tags and decoding HTML entities.
    Args:
        html_string (str): The HTML string to clean.
    Returns:
        str: The cleaned string.
    """

    if html_string is None:
        return ""

    html_string = html_string.lstrip().rstrip()

    if html_string == "":
        return ""

    # Remove HTML tags
    clean_text = html.fromstring(html_string).text_content()
    # Remove extra spaces
    clean_text = " ".join(clean_text.split())

    # Remove the source information
    clean_text = REGEX_SOURCE.sub("", clean_text)

    return clean_text
