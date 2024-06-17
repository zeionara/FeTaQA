from docx.text.paragraph import Paragraph


def is_bold(paragraph: Paragraph):
    if paragraph is None or paragraph.soup is None:
        return False

    style = paragraph.soup.find('w:rstyle')

    return style is not None and style.get('w:val') == 'a3'


def is_h1(paragraph: Paragraph):
    if paragraph is None or paragraph.soup is None:
        return False

    style = paragraph.soup.find('w:pstyle')

    return style is not None and style.get('w:val') == '1'
