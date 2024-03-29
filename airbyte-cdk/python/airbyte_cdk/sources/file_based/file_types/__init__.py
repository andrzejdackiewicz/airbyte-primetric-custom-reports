from typing import Any, Mapping, Type

from airbyte_cdk.sources.file_based.config.avro_format import AvroFormat
from airbyte_cdk.sources.file_based.config.csv_format import CsvFormat
from airbyte_cdk.sources.file_based.config.jsonl_format import JsonlFormat
from airbyte_cdk.sources.file_based.config.parquet_format import ParquetFormat

from .avro_parser import AvroParser
from .csv_parser import CsvParser
from .file_type_parser import FileTypeParser
from .jsonl_parser import JsonlParser
from .parquet_parser import ParquetParser

default_parsers: Mapping[Type[Any], FileTypeParser] = {
    AvroFormat: AvroParser(),
    CsvFormat: CsvParser(),
    JsonlFormat: JsonlParser(),
    ParquetFormat: ParquetParser(),
}

__all__ = ["AvroParser", "CsvParser", "JsonlParser", "ParquetParser", "default_parsers"]
