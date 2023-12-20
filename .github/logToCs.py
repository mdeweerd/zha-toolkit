#!/usr/bin/python3
# pylint: disable=invalid-name
"""
Convert a log to CheckStyle format.

Url: https://github.com/mdeweerd/LogToCheckStyle

The log can then be used for generating annotations in a github action.

Note: this script is very young and "quick and dirty".
      Patterns can be added to "PATTERNS" to match more messages.

# Examples

Assumes that logToCs.py is available as .github/logToCs.py.

## Example 1:


```yaml
      - run: |
          pre-commit run -all-files | tee pre-commit.log
          .github/logToCs.py pre-commit.log pre-commit.xml
      - uses: staabm/annotate-pull-request-from-checkstyle-action@v1
        with:
          files: pre-commit.xml
          notices-as-warnings: true # optional
```

## Example 2:


```yaml
      - run: |
          pre-commit run --all-files | tee pre-commit.log
      - name: Add results to PR
        if: ${{ always() }}
        run: |
          .github/logToCs.py pre-commit.log | cs2pr
```

Author(s):
  - https://github.com/mdeweerd

License: MIT License

"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET  # nosec


def convert_to_checkstyle(messages):
    """
    Convert provided message to CheckStyle format.
    """
    root = ET.Element("checkstyle")
    for message in messages:
        fields = parse_message(message)
        if fields:
            add_error_entry(root, **fields)
    return ET.tostring(root, encoding="utf-8").decode("utf-8")


ANY_REGEX = r".*?"
FILE_REGEX = r"\s*(?P<file_name>\S.*?)\s*?"
LINE_REGEX = r"\s*(?P<line>\d+?)\s*?"
COLUMN_REGEX = r"\s*(?P<column>\d+?)\s*?"
SEVERITY_REGEX = r"\s*(?P<severity>error|warning|notice|style|info)\s*?"
MSG_REGEX = r"\s*(?P<message>.+?)\s*?"
# cpplint confidence index
CONFIDENCE_REGEX = r"\s*\[(?P<confidence>\d+)\]\s*?"


# List of message patterns, add more specific patterns earlier in the list
# Creating patterns by using constants makes them easier to define and read.
PATTERNS = [
    # ESLint (JavaScript Linter), RoboCop
    # path/to/file.js:10:2: Some linting issue
    # path/to/file.rb:10:5: Style/Indentation: Incorrect indentation detected
    # path/to/script.sh:10:1: SC2034: Some shell script issue
    re.compile(f"^{FILE_REGEX}:{LINE_REGEX}:{COLUMN_REGEX}: {MSG_REGEX}$"),
    # Cpplint default output:
    #           '%s:%s:  %s  [%s] [%d]\n'
    #   % (filename, linenum, message, category, confidence)
    re.compile(f"^{FILE_REGEX}:{LINE_REGEX}:{MSG_REGEX}{CONFIDENCE_REGEX}$"),
    # MSVC
    # file.cpp(10): error C1234: Some error message
    re.compile(
        f"^{FILE_REGEX}\\({LINE_REGEX}\\):{SEVERITY_REGEX}{MSG_REGEX}$"
    ),
    # Java compiler
    # File.java:10: error: Some error message
    re.compile(f"^{FILE_REGEX}:{LINE_REGEX}:{SEVERITY_REGEX}:{MSG_REGEX}$"),
    # Python
    # File ".../logToCs.py", line 90 (note: code line follows)
    re.compile(f'^File "{FILE_REGEX}", line {LINE_REGEX}$'),
    # Pylint, others
    # path/to/file.py:10: [C0111] Missing docstring
    # others
    re.compile(f"^{FILE_REGEX}:{LINE_REGEX}: {MSG_REGEX}$"),
    # Shellcheck:
    # In script.sh line 76:
    re.compile(f"^In {FILE_REGEX} line {LINE_REGEX}:({MSG_REGEX})?$"),
]

# Severities available in CodeSniffer report format
SEVERITY_NOTICE = "notice"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"


def parse_message(message):
    """
    Parse message until it matches a pattern.

    Returns the fields in a dict.
    """
    for pattern in PATTERNS:
        fields = pattern.match(message)
        if not fields:
            continue
        result = fields.groupdict()
        if len(result) == 0:
            continue

        if "confidence" in result:
            # Convert confidence level of cpplint
            # to warning, etc.
            confidence = int(result["confidence"])
            del result["confidence"]

            if confidence <= 1:
                severity = SEVERITY_NOTICE
            elif confidence >= 5:
                severity = SEVERITY_ERROR
            else:
                severity = SEVERITY_WARNING
            result["severity"] = severity

        if "severity" not in result:
            result["severity"] = SEVERITY_ERROR
        else:
            result["severity"] = result["severity"].lower()

        if result["severity"] in ["info", "style"]:
            result["severity"] = SEVERITY_NOTICE

        return result

    # Nothing matched
    return None


def add_error_entry(  # pylint: disable=too-many-arguments
    root,
    severity,
    file_name,
    line=None,
    column=None,
    message=None,
    source=None,
):
    """
    Add error information to the CheckStyle output being created.
    """
    file_element = find_or_create_file_element(root, file_name)
    error_element = ET.SubElement(file_element, "error")
    error_element.set("severity", severity)
    if line:
        error_element.set("line", line)
    if column:
        error_element.set("column", column)
    if message:
        error_element.set("message", message)
    if source:
        # To verify if this is a valid attribute
        error_element.set("source", source)


def find_or_create_file_element(root, file_name):
    """
    Find/create file element in XML document tree.
    """
    for file_element in root.findall("file"):
        if file_element.get("name") == file_name:
            return file_element
    file_element = ET.SubElement(root, "file")
    file_element.set("name", file_name)
    return file_element


def main():
    """
    Parse the script arguments and get the conversion done.
    """
    parser = argparse.ArgumentParser(
        description="Convert messages to Checkstyle XML format."
    )
    parser.add_argument(
        "input", help="Input file. Use '-' for stdin.", nargs="?", default="-"
    )
    parser.add_argument(
        "output",
        help="Output file. Use '-' for stdout.",
        nargs="?",
        default="-",
    )
    parser.add_argument(
        "-i",
        "--input-named",
        help="Named input file. Overrides positional input.",
    )
    parser.add_argument(
        "-o",
        "--output-named",
        help="Named output file. Overrides positional output.",
    )

    args = parser.parse_args()

    if args.input == "-" and args.input_named:
        with open(args.input_named, encoding="utf_8") as input_file:
            messages = input_file.readlines()
    elif args.input != "-":
        with open(args.input, encoding="utf_8") as input_file:
            messages = input_file.readlines()
    else:
        messages = sys.stdin.readlines()

    checkstyle_xml = convert_to_checkstyle(messages)

    if args.output == "-" and args.output_named:
        with open(args.output_named, "w", encoding="utf_8") as output_file:
            output_file.write(checkstyle_xml)
    elif args.output != "-":
        with open(args.output, "w", encoding="utf_8") as output_file:
            output_file.write(checkstyle_xml)
    else:
        print(checkstyle_xml)


if __name__ == "__main__":
    main()
