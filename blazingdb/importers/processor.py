"""
Defines the StreamProcessor for mapping the stream of rows from a source into a format which
can be imported into BlazingDB
"""

import logging

from . import base


class StreamProcessor(object):
    """ Processes a stream of data into rows BlazingDB can import """

    def __init__(self, stream, **kwargs):
        self.logger = logging.getLogger(__name__)

        self.last_row = None
        self.stream = stream

        self.encoding = kwargs.get("encoding", base.DEFAULT_FILE_ENCODING)
        self.field_terminator = kwargs.get("field_terminator", base.DEFAULT_FIELD_TERMINATOR)
        self.field_wrapper = kwargs.get("field_wrapper", base.DEFAULT_FIELD_WRAPPER)
        self.line_terminator = kwargs.get("line_terminator", base.DEFAULT_LINE_TERMINATOR)

    def _wrap_field(self, column):
        return self.field_wrapper + column + self.field_wrapper

    def _process_column(self, column):
        if column is None:
            return ""
        elif isinstance(column, str):
            return self._wrap_field(column)

        try:
            return column.strftime("%Y-%m-%d")
        except AttributeError:
            pass

        return str(column)

    def _process_row(self, row):
        """ Processes a row of data into it a string to be loaded into Blazing """
        fields = map(self._process_column, row)
        return self.field_terminator.join(fields) + self.line_terminator

    def _load_row(self):
        if self.stream is None:
            return

        try:
            self.last_row = next(self.stream)
        except StopIteration:
            self.last_row = None
            self.stream = None

    def _build_batch(self, stop_check):
        if self.last_row is None:
            self._load_row()

        batch = []
        while self.last_row is not None:
            if stop_check(self.last_row):
                break

            batch.append(self.last_row)
            self._load_row()

        return batch

    def _read_bytes(self, size):
        """ Reads rows from the stream until the next row would exceed the given size (in bytes) """
        self.logger.debug("Reading %s bytes from the stream", size)

        byte_count = 0
        row_count = 0
        def stop_check(row):
            nonlocal byte_count, row_count

            processed_row = self._process_row(row)
            raw_row = processed_row.encode(self.encoding)

            if byte_count + len(raw_row) > size:
                return True

            byte_count += len(raw_row)
            row_count += 1
            return False

        batch = self._build_batch(stop_check)

        self.logger.debug("Read %s row(s) (%s bytes) from the stream", row_count, byte_count)

        return batch

    def _read_rows(self, count):
        """ Reads the given number of rows from the stream """
        self.logger.debug("Reading %s row(s) from the stream", count)

        row_count = 0
        def stop_check(row):
            nonlocal row_count

            if row_count >= count:
                return True

            row_count += 1
            return False

        batch = self._build_batch(stop_check)

        self.logger.debug("Read %s row(s) from the stream", row_count)

        return batch

    def read_bytes(self, size):
        """ Reads rows from the stream until the next row would exceed the given size (in bytes) """
        return list(map(self._process_row, self._read_bytes(size)))

    def read_rows(self, count):
        """ Reads the given number of rows from the stream """
        return list(map(self._process_row, self._read_rows(count)))