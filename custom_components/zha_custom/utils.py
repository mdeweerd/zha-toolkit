import logging

LOGGER = logging.getLogger(__name__)


# Convert string to int if possible or return original string
#  (Returning the original string is usefull for named attributes)
def str2int(s):
    if not type(s) == str:
        return s
    elif s.lower() == "false":
        return 0
    elif s.lower() == "true":
        return 1
    elif s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    elif s.startswith("0") and s.isnumeric():
        return int(s, 8)
    elif s.startswith("b") and s[1:].isnumeric():
        return int(s[1:], 2)
    elif s.isnumeric():
        return int(s)
    else:
        return s

