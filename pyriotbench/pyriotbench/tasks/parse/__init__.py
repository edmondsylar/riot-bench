"""Parse tasks - data parsing and transformation.

This module contains parsing benchmark tasks:
- senml_parse: Parse SenML (Sensor Markup Language) JSON format
- csv_to_senml_parse: Convert CSV to SenML format
- xml_parse: Parse XML sensor data (TODO)
- annotate: Add metadata/labels to data (TODO)
"""

from pyriotbench.tasks.parse.senml_parse import SenMLParseTask
from pyriotbench.tasks.parse.csv_to_senml_parse import CsvToSenMLParse

__all__ = [
    "SenMLParseTask",
    "CsvToSenMLParse",
]
