from pathlib import Path

import zipfile
import os


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
