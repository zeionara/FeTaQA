from docx.text.paragraph import Paragraph


def is_bold(paragraph: Paragraph):
    return 'rStyle' in paragraph._element.xml
