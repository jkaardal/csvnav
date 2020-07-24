import csv


class Navigator:
    
    def __init__(self, path, header=False, raw_output=False, reformat=None, skip=0, dialect='excel', open_opts=None, 
                 **fmtparams):
        """
        Instantiate a Navigator object. Note that this class assumes that the file it opens is static.

        :param str path: absolute or relative path to the file to be opened.
        :param bool header: when True, indicates the file has a row specifying the header titles after skipping skip 
            (see below) rows. If the file does not contain a header but you would like to define the columns you may
            mimic a header by calling self.set_header() to a list of strings after instantiation. Default is False.
        :param bool raw_output: when True, rows in the file are returned as raw strings without any formatting applied. 
            When False, the raw string is optionally subjected to reformat (see below) and then returned as a csv 
            formatted (using **fmtparams, see below) list of strings. Default is False.
        :param function reformat: if raw_output is False, a reformat function can optionally be provided that takes as 
            arguments self (this instance) and a string corresponding to a row in the file and returns a modified string
            that is then passed into csv.reader. Default is lambda self, line: line.
        :param int skip: number of rows to skip at the beginning of the file to reach either the header row or the first
            row of data. Default is 0.
        :param str dialect: see csv.reader() docs for definition. Default is 'excel'.
        :param dict open_opts: see keyword arguments in the docs for builtin function open(). Note that the keyword
            argument mode is restricted because Navigator is fixed to mode 'r'. Default is {} (uses defaults).
        :param **dict **fmtparams: additional keyword arguments are passed into csv.reader() and the supported fields
            are identical to those defined by the fmtparams argument of csv.reader() in the documentation.
        """
        self.open_opts = {} if open_opts is None else open_opts
        self.fmtparams = fmtparams
        # Open the file.
        self.fp = open(path, 'r', **self.open_opts)
        # Skip extraneous non-header and non-data lines at the beginning of file.
        self.skip = skip
        for _ in range(skip):
            self.fp.readline()
        # Initialize pointer list and dict for registering groups.
        self.row_ptr = []
        self.field_ptr = {}
        if header:
            # Extract the csv header.
            self.header = list(csv.reader([self.fp.readline()], **self.fmtparams))[0]
        else:
            # The file does not have a header.
            self.header = None
        # Initialize the number of explored (accessed) rows so far.
        self.horizon = 0
        # Initialize row length and total character length of the file.
        self.length = None
        self.char_len = None
        # Return raw string row without any formatting.
        self.raw_output = raw_output
        # User defined function to reformat a row string (default passes through).
        self.reformat = lambda self, line: line if reformat is None else reformat
        # Initialize iterator counter.
        self.start_iter = 0

    def close(self):
        """
        Close the file, if it is open.
        """
        self.fp.close()
    
    def __len__(self):
        """
        Get the number of rows of data in the file. Note that if the end of the file has not been accessed, this
        function will return None. In this case, you can get the length of the file by calling self.size(force=True).
        See the method self.size() for more information.

        :returns int|None: the number of rows of data or None if the end of the file has not been reached.
        """
        return self.size()

    def __del__(self):
        """
        Close the file when Navigator instance is garbage collected.
        """
        self.close()
    
    def chars(self, force=False):
        """
        Get the total number of characters in the file.

        :param bool force: when True, forcibly computes the number of characters in the file even if the end of the file
            has not been reached. When False and the end of the file has not been reached, the function will return
            None. Default is False.
        :returns int|None: the number of characters in the file or None if the end of the file has not been reached.
        """
        if force and self.char_len is None:
            # Forcibly compute if stored value is None.
            self.char_len = self.fp.seek(0, 2)
        return self.char_len
    
    def size(self, force=False):
        """
        Get the size number of rows of data in the file.

        :param bool force: when True, forcibly computes the number of rows of data in the file even if the end of the
            file has not been reached. When False and the end of the file has not been reached, this function will
            return None. Warning - to count the number of rows when force=True, this function needs to iterate through 
            all the rows in the file which could take long for very large files. Default is False.
        :returns int|None: the number of rows of data in the file or None if the end of the file has not been reached.
        """
        # Get the number of rows in the file (less self.skip and the header lines).
        if force and self.length is None:
            # Forcibly compute the length of the file if it is not currently known.
            if self.horizon == 0:
                # File has not been explored yet, determine size from top of file.
                self.fp.seek(0)
                # Skip lines.
                for _ in range(self.skip):
                    self.fp.readline()
                # Skip header.
                if self.header:
                    self.fp.readline()
            else:
                # Move to last known position and skip line.
                self.fp.seek(self.row_ptr[-1])
                self.fp.readline()
            # Get pointer to current position.
            ptr = self.fp.tell()
            while True:
                # Read each remaining row in the file.
                line = self.fp.readline()
                if line:
                    # Row found, expand horizon and continue.
                    self.row_ptr.append(ptr)
                    ptr = self.fp.tell()
                    self.horizon += 1
                else:
                    # No more rows found, report length.
                    self.length = self.horizon
                    break
                        
        return self.length

    def set_header(self, header):
        """
        Set the file's header (does not modify the file).

        :param list<immutable> header: the header can technically be composed of any immutable objects but is typically
            composed of strings. The number of elements in the list should be equal to the number of columns in the
            file. 
        """
        self.header = header

    def register(self, fields):
        """
        Group rows by the values in a column. See the README.md file for an example. Note that this is also memory
        efficient in the sense that it only stores pointers and does not store the grouped data in memory. This method
        only performs the initial mapping of the pointers and does not return rows. To return results, see self.get()
        or self.__getitem__(). Note that this function cannot be used when header=False or raw_output=True.

        TODO: add the option to perform conjuctions/disjunctions?

        :param immutable|list<immutable> fields: either an immutable (typically a string) or a list of immutables that
            correspond to column names defined in self.header whose values we would like to group by. Note that each
            field is grouped independently (no conjunctions/disjunctions).
        """
        # If the file has a header, rows can be grouped such that the values of a field (column) are keys.
        assert self.header is not None
        assert not self.raw_output
        if not isinstance(fields, list):
            # Only a single field was provided, put in a list.
            fields = [fields]
        # Start from the beginning of the file.
        self.fp.seek(0)
        # Skip lines.
        for _ in range(self.skip):
            self.fp.readline()
        # Skip header.
        self.fp.readline()
        # Get position of first line of data.
        ptr = self.fp.tell()
        # Initialize mappings, row pointer array, and number of data rows.
        field_to_col = {k: self.header.index(k) for k in fields}
        fields_to_vals = {k: {} for k in fields}
        row_ptr = []
        length = 0
        while True:
            line = self.fp.readline()
            if line:
                # If the line is non-empty, store a pointer to the beginning of the line.
                row_ptr.append(ptr)
                # Apply udf to reformat line.
                line = self.reformat(self, line)
                row = list(csv.reader([line], **self.fmtparams))[0]
                # Associate row pointer with a key in each field.
                for field, col in field_to_col.items():
                    val = row[col]
                    if val not in fields_to_vals[field]:
                        fields_to_vals[field][val] = [ptr]
                    else:
                        fields_to_vals[field][val].append(ptr)
                # Update pointer and expand known data row length of file.
                ptr = self.fp.tell()
                length += 1
            else:
                # End-of-file.
                break
        self.row_ptr = row_ptr
        for field, vals in fields_to_vals.items():
            self.field_ptr[field] = fields_to_vals[field]
        self.length = length
        self.horizon = length
        
    def fields(self):
        """
        Gets a dict_keys object corresponding the fields (columns) that have been grouped by the self.register() method.

        :returns dict_keys: fields (columns) that have been registered.
        """
        return self.field_ptr.keys()
        
    def keys(self, field):
        """
        Gets a dict_keys object corresponding to the unique values of the field (column) that has been used to key a
        grouping by the self.register() method.

        :returns dict_keys: keys of a registered field (column).
        """
        return self.field_ptr[field].keys()
        
    def cols(self):
        """
        Get the header that defines the columns of the file.

        :returns list<immutable>: the header of the file.
        """
        return self.header
        
    def get(self, field, key, default=None):
        """
        Get a row by field (column) and key provided a key has been registered by self.register() method.

        :param immutable field: typically a string that matches an element of the header.
        :param str key: one of the unique values in the field (column) of the file defined by field that is used as a
            key in the grouping by the self.register() method.
        :param any default: value to return if key does not exist. Default is None.
        :returns list<dict>|any: either returns the matching rows or a default value.
        """
        if key not in self.keys(field):
            # If the key does not exist for a given field, return the default.
            return default
        else:
            # Key exists, return the value.
            return self.__getitem__((field, key))

    def items(self, field):
        """
        Get a generator over key/value pairs for a given registered field by the self.register() method.

        :param immutable field: typically a string that matches an element of the header.
        :yields (str, any): returns a generator that iterates over a tuple of key/value pairs.
        """
        for key, ptr in self.field_ptr[field].items():
            yield key, self.__getitem__((field, key))
        
    def __getitem__(self, index):
        """
        Get row(s) from the file by index/indices or field and key. May use brackets to access this method.
        E.g. data[5] will get the 6th row of data from the file while data['myfield', 'mykey'] will get all rows where
        the column 'myfield' has value 'mykey' provided the 'myfield' column has been registered by the method
        self.register('myfield').

        TODO: accept negative indices?

        :param int|slice|tuple<immutable,str> index: this variable may take on three forms such that it may be used to
            access rows by either index or by field (column) and key (see self.register() method). The three forms are:
                int - get a single row by index.
                slice - return one or more rows by index via a slicing operation. Only supports non-negative integers
                    at least for now.
                tuple<immutable,str> - a two element tuple where the first element is the field (column) and the second
                    element is the key which returns all rows that match the field and key. Must be registered first
                    by method self.register().
        :returns str|dict|list<any>|list<dict|list|str>: the five different return types depend on the following 
            conditions:
                str - when raw_output=True and index is an int, then the row is returned as a string.
                dict - when the Navigator instance has a header defined and index is an int, then a dictionary of column
                    names to values in the indexed row is returned.
                list<any> - when the Navigator instance does NOT have a header defined and index is an int, then a list 
                    of values is returned for the indexed row is returned.
                list<dict> - when the Navigator instance has a header defined and index is either a slice or a tuple, 
                    then a list is returned where each element corresponds to a row formatted as a dictionary.
                list<list> - when the Navigator instance does NOT have a header defined and index is a slice or a tuple,
                    then a list is returned where each element is a list that corresponds to a row formatted as a list.
                list<str> - when raw_output=True and index is a slice, then a list is returned where each element
                    corresponds to a row formatted as a string.
        """
        if isinstance(index, tuple):
            assert len(index) == 2
            field = index[0]
            index = index[1]
        else:
            field = None
        
        if field is None:
            # Integer index/indices given instead of registered field and key.
            if self.length is None:
                # Total length of file is not currently known.
                if isinstance(index, slice):
                    # Received a slice so get a result list of corresponding rows.
                    start = 0 if index.start is None else index.start
                    stop = None if index.stop is None else index.stop
                    step = 1 if index.step is None else index.step
                    assert start >= 0
                    rows = []
                    idx = start
                    while True:
                        if stop is None or idx < stop:
                            # We have not reached the end of the slice yet.
                            if idx >= self.horizon:
                                # The current row index is beyond what has been explored.
                                if self.horizon == 0:
                                    # We have not explored anything yet, start from the beginning and skip non-data.
                                    self.fp.seek(0)
                                    for _ in range(self.skip):
                                        self.fp.readline()
                                    if self.header:
                                        self.fp.readline()
                                else:
                                    # Go to the last known row pointer and advance the pointer by one row.
                                    self.fp.seek(self.row_ptr[-1])
                                    self.fp.readline()
                                # Get the current pointer to the first unexplored row.
                                ptr = self.fp.tell()
                                # Iterate through unexplored rows until we reach the requested row.
                                for i in range(self.horizon, idx+1):
                                    line = self.fp.readline()
                                    if line:
                                        # An unexplored line has been found, store the pointer to this newly explored
                                        # row, set the pointer to the next unexplored row, and advance the horizon.
                                        self.row_ptr.append(ptr)
                                        ptr = self.fp.tell()
                                        self.horizon += 1
                                    else:
                                        # The end of the file has been reached. Set the row length of the file.
                                        self.length = self.horizon
                                        stop = self.length
                                        break
                                if self.length is not None:
                                    # No lines left to add to the result list, break out of while loop.
                                    break
                            # Now that we have the pointer for the current index, move to the pointer.
                            self.fp.seek(self.row_ptr[idx])
                            if self.raw_output:
                                # Get the row as a string.
                                row = self.fp.readline()
                            else:
                                # Get the row, optionally reformat, and read as csv.
                                line = self.fp.readline()
                                line = self.reformat(self, line)
                                row = list(csv.reader([line], **self.fmtparams))[0]
                            # Append the row to the result list and move on to the next index in the slice.
                            if self.header and not self.raw_output:
                                # Add the row as a dictionary to the results list.
                                rows.append({k: v for k, v in zip(self.header, row)})
                            else:
                                # Add the row as a string or list to the results list.
                                rows.append(row)
                            idx += step
                        else:
                            # We are at the end of the slice, break out.
                            break
                    return rows
                else:
                    # An integer index was received, get a single row.
                    if index >= self.horizon:
                        # The row index is beyond what has been explored.
                        if self.horizon == 0:
                            # We have not explored anything yet, start from the beginning and skip non-data.
                            self.fp.seek(0)
                            for _ in range(self.skip):
                                self.fp.readline()
                            if self.header:
                                self.fp.readline()
                        else:
                            # Go to the last known row pointer and advance the pointer by one row.
                            self.fp.seek(self.row_ptr[-1])
                            self.fp.readline()
                        # Get the current pointer to the first unexplored row.
                        ptr = self.fp.tell()
                        # Iterate through the unexplored rows until we reach the requested row.
                        for i in range(self.horizon, index+1):
                            line = self.fp.readline()
                            if line:
                                # An unexplored line has been found, store the pointer to this newly explored row, set
                                # the pointer to the next unexplored row, and advance the horizon.
                                self.row_ptr.append(ptr)
                                ptr = self.fp.tell()
                                self.horizon += 1
                            else:
                                # The end of the file has been reached. Set the row length of the file.
                                self.length = self.horizon
                                break
                        if self.length is not None:
                            # Throw an error if index is too large.
                            assert index < self.length
                    # Now that we have the pointer for the requested row, move to the pointer.
                    self.fp.seek(self.row_ptr[index])
                    if self.raw_output:
                        # Get the row as a string.
                        row = self.fp.readline()
                    else:
                        # Get the row, optionally reformat, and read as csv.
                        line = self.fp.readline()
                        line = self.reformat(self, line)
                        row = list(csv.reader([line], **self.fmtparams))[0]
                    if self.header and not self.raw_output:
                        # Convert the row into a dictionary.
                        row = {k: v for k, v in zip(self.header, row)}
                    return row
            else:
                # The total row length of the file is already known.
                if isinstance(index, slice):
                    # Received a slice so get a result list of corresponding rows.
                    start = 0 if index.start is None else index.start
                    stop = self.length if index.stop is None else index.stop
                    step = 1 if index.step is None else index.step
                    assert start >= 0 and stop <= self.length
                    rows = []
                    # Since all rows must have been explored to know the length of the file, we can simply iterate over
                    # the slice.
                    for idx in range(start, stop, step):
                        # Move to the pointer of the current row index.
                        self.fp.seek(self.row_ptr[idx])
                        if self.raw_output:
                            # Get the row as a string.
                            row = self.fp.readline()
                        else:
                            # Get the row, optionally reformat, and read as csv.
                            line = self.fp.readline()
                            line = self.reformat(self, line)
                            row = list(csv.reader([line], **self.fmtparams))[0]
                        if self.header and not self.raw_output:
                            # Add the row as a dictionary to the results list.
                            rows.append({k: v for k, v in zip(self.header, row)})
                        else:
                            # Add the row as a string or list to the results list.
                            rows.append(row)
                    return rows
                else:
                    # An integer index was received, get a single row.
                    assert index < self.length
                    # Move to the pointer of the row index.
                    self.fp.seek(self.row_ptr[index])
                    if self.raw_output:
                        # Get the row as a string.
                        row = self.fp.readline()
                    else:
                        # Get the row, optionally reformat, and read as csv.
                        line = self.fp.readline()
                        line = self.reformat(self, line)
                        row = list(csv.reader([line], **self.fmtparams))[0]
                    if self.header and not self.raw_output:
                        # Convert the row into a dictionary.
                        row = {k: v for k, v in zip(self.header, row)}
                    return row
        else:
            # Received a field (column) and key (where index=key) as input, get all rows where the value of the field
            # column matches the key. Note that there is no need to deal with unexplored rows like in the above case
            # because it is necessary to explore all rows when registering in the first place.
            # TODO: make it possible to run this without the extra self.register() step.
            rows = []
            # Iterate through the pointers of all matching rows.
            for ptr in self.field_ptr[field][index]:
                # Move to the pointer.
                self.fp.seek(ptr)
                if self.raw_output:
                    # Get the row as a string.
                    row = self.fp.readline()
                else:
                    # Get the row, optionally reformat, and read as csv.
                    line = self.fp.readline()
                    line = self.reformat(self, line)
                    row = list(csv.reader([line], **self.fmtparams))[0]
                if self.header and not self.raw_output:
                    # Add the row as a dictionary to the results list.
                    rows.append({k: v for k, v in zip(self.header, row)})
                else:
                    # Add the row as a string or list to the results list.
                    rows.append(row)
            return rows
        
    def __iter__(self):
        """
        Initialize an iterator over the rows of data in the file.

        :returns Navigator self: returns this instance.
        """
        self.start_iter = 0
        return self
    
    def __next__(self):
        """
        Get the next row of data in the file.

        :returns str|dict|list<any>: a row with types defined in the __getitem__ return documentation.
        """
        if self.start_iter >= self.size(force=True):
            raise StopIteration
        else:
            self.start_iter += 1
            return self.__getitem__(self.start_iter - 1)
