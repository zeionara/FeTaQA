from docx.text.paragraph import Paragraph


def is_bold(paragraph: Paragraph):
    style = paragraph.find('w:rstyle')

    return style is not None and style.get('w:val') == 'a3'

def is_h1(paragraph: Paragraph):
    style = paragraph.find('w:pstyle')

    return style is not None and style.get('w:val') == '1'
