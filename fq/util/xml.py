from docx.text.paragraph import Paragraph


def is_bold(paragraph: Paragraph):
    style = paragraph.find('w:rstyle')

    return style is not None and style.get('w:val') == 'a3'
