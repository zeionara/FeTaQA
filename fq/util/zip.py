from pathlib import Path
from lxml import etree

import zipfile
import os


ooXMLns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def truncate_name(name, suffix, max_length=100):
    # return name + suffix if len(name) + len(suffix) <= max_length else name[:max_length - len(suffix)] + suffix

    components = name.split(' ', maxsplit = 2)

    return ' '.join(components[:2]) + suffix


def unpack(source: str, destination: str):
    if not os.path.isdir(destination):
        os.makedirs(destination)

    with zipfile.ZipFile(source, 'r') as zip_ref:
        for info in zip_ref.infolist():
            if info.is_dir():
                continue

            original_name = info.filename.encode('cp437').decode('utf-8')

            path = Path(original_name)
            truncated_name = truncate_name(path.stem, path.suffix)

            # truncated_name = truncate_name(original_name)

            # if info.is_dir():
            #     directory = os.path.join(destination, truncated_name)

            #     if not os.path.isdir(directory):
            #         os.makedirs(directory)

            #     break

            # directory = os.path.join(destination, os.path.dirname(truncated_name))
            # if directory:
            #     os.makedirs(directory, exist_ok=True)

            print(f'Unpacking file {original_name}')

            with zip_ref.open(info) as inner_file:
                with open(os.path.join(destination, truncated_name), 'wb') as outer_file:
                    outer_file.write(inner_file.read())


def get_document_comments(docxFileName):
    comments_dict = {}
    comments_of_dict = {}
    docx_zip = zipfile.ZipFile(docxFileName)
    comments_xml = docx_zip.read('word/comments.xml')
    comments_of_xml = docx_zip.read('word/document.xml')
    et_comments = etree.XML(comments_xml)
    et_comments_of = etree.XML(comments_of_xml)
    comments = et_comments.xpath('//w:comment', namespaces=ooXMLns)
    comments_of = et_comments_of.xpath('//w:commentRangeStart', namespaces=ooXMLns)

    for c in comments:
        comment = c.xpath('string(.)', namespaces=ooXMLns)
        comment_id = c.xpath('@w:id', namespaces=ooXMLns)[0]
        comments_dict[comment_id] = comment

    comments = []

    for c in comments_of:
        comments_of_id = c.xpath('@w:id', namespaces=ooXMLns)[0]

        parts = et_comments_of.xpath(
            "//w:r[preceding-sibling::w:commentRangeStart[@w:id=" + comments_of_id + "] and following-sibling::w:commentRangeEnd[@w:id=" + comments_of_id + "]]",
            # "//w:p[./w:r[preceding-sibling::w:commentRangeStart[@w:id=" + comments_of_id + "]]]",
            # "//w:r[preceding-sibling::w:commentRangeStart[@w:id=" + comments_of_id + "]]",
            namespaces=ooXMLns
        )

        if len(parts) < 1:  # if no paragraphs are found, then try looking for tables
            parts = et_comments_of.xpath(
                "//w:tbl[//w:r[preceding-sibling::w:commentRangeStart[@w:id=" + comments_of_id + "]]]",
                namespaces=ooXMLns
            )
        else:
            parts = et_comments_of.xpath(
                "//w:p[./w:r[preceding-sibling::w:commentRangeStart[@w:id=" + comments_of_id + "]]]",
                namespaces=ooXMLns
            )

        comment_of = ''
        # print(comments_of_id, [part.xpath('string(.)', namespaces=ooXMLns) for part in parts])
        for part in parts:
            comment_of += part.xpath('string(.)', namespaces=ooXMLns)
            comments_of_dict[comments_of_id] = comment_of

            comments.append((etree.tostring(part, encoding = str), comments_dict[comments_of_id]))

    return comments
