import json


class YAMLError(Exception):
    pass


def safe_load(value):
    return json.loads(value)
