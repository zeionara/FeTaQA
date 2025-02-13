from docx.text.paragraph import Paragraph
from bs4 import BeautifulSoup


# def is_bold(paragraph: Paragraph):
#     if paragraph is None or paragraph.soup is None:
#         return False
#
#     style = paragraph.soup.find('w:rstyle')
#
#     return style is not None and style.get('w:val') == 'a3'


def is_bold(paragraph: BeautifulSoup):
    style = paragraph.find('w:rstyle')

    return style is not None and style.get('w:val') == 'a3'


def is_h1(paragraph: Paragraph):
    if paragraph is None or paragraph.soup is None:
        return False

    style = paragraph.soup.find('w:pstyle')

    return style is not None and style.get('w:val') == '1'


def get_paragraph_style(paragraph: BeautifulSoup):
    style = paragraph.find('w:pstyle')

    return None if style is None else style.get('w:val')
