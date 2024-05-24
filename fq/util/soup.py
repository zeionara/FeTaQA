from .string import is_not_empty


def get_last_non_empty_element(elements: list):
    for element in elements[::-1]:
        if is_not_empty(element.text):
            return element


def get_first_non_empty_element(elements: list):
    for element in elements:
        if is_not_empty(element.text):
            return element
