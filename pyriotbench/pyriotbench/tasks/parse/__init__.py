"""Parse tasks - data parsing and transformation.

This module contains parsing benchmark tasks:
- senml_parse: Parse SenML (Sensor Markup Language) JSON format
- xml_parse: Parse XML sensor data
- csv_to_senml: Convert CSV to SenML format
- annotate: Add metadata/labels to data
"""

from pyriotbench.tasks.parse.senml_parse import SenMLParseTask

__all__ = [
    "SenMLParseTask",
]
