import csv


class NullObj:
    null = None


class Navigator:
    
    def __init__(self, path, header=True, delimiter=',', raw_output=False, reformat=None, skip=0):
        # open file
        self.fp = open(path, 'r')
        # skip extraneous lines at the beginning of file
        self.skip = skip
        for _ in range(skip):
            self.fp.readline()
        self.delimiter = delimiter
        # initialize pointer arrays
        self.row_ptr = []
        self.field_ptr = {}
        if header:
            # extract csv header
            self.header = list(csv.reader([self.fp.readline()], delimiter=self.delimiter))[0]
        else:
            # file does not have a header
            self.header = None
        # initialize number of rows accessed so far
        self.horizon = 0
        # initialize line and total character length of the file
        self.length = None
        self.char_len = None
        # return raw row output without any formatting
        self.raw_output = raw_output
        # user defined function to reformat row string
        self.reformat = reformat
        # initialize iterator
        self.start_iter = 0

    def close(self):
        self.fp.close()
    
    def __len__(self):
        return self.size()

    def __del__(self):
        # close file on destroy
        self.close()
    
    def chars(self, force=False):
        # get the total number of characters in the file
        if force and self.char_len is None:
            # forcibly compute if stored value is None
            self.char_len = self.fp.seek(0, 2)
        return self.char_len
    
    def size(self, force=False):
        # get the number of lines in the file (less self.skip and the header lines)
        if force and self.length is None:
            # forcibly compute the length of the file if it is not currently known
            if self.horizon == 0:
                # file has not been explored yet, determine size from top of file
                self.fp.seek(0)
                # skip lines
                for _ in range(self.skip):
                    self.fp.readline()
                # skip header
                if self.header:
                    self.fp.readline()
            else:
                # move to last known position and skip line
                self.fp.seek(self.row_ptr[-1])
                self.fp.readline()
            # get pointer to current position
            ptr = self.fp.tell()
            while True:
                # read each remaining line in the file
                line = self.fp.readline()
                if line:
                    # line found, expand horizon and continue
                    self.row_ptr.append(ptr)
                    ptr = self.fp.tell()
                    self.horizon += 1
                else:
                    # no more lines found, report length
                    self.length = self.horizon
                    break
                        
        return self.length

    def set_header(self, header):
        # set the header with a list
        self.header = header

    def register(self, fields):
        # if the file has a header, rows can be grouped such that the values of a field (column) are keys
        assert self.header is not None
        assert not self.raw_output
        if not isinstance(fields, list) and not isinstance(fields, tuple):
            # only a single field was provided, put in a list
            fields = [fields]
        # start from the beginning of the file
        self.fp.seek(0)
        # skip lines
        for _ in range(self.skip):
            self.fp.readline()
        # skip header
        self.fp.readline()
        # get position of first line of data
        ptr = self.fp.tell()
        # initialize mappings, row pointer array, and number of data rows
        field_to_col = {k: self.header.index(k) for k in fields}
        fields_to_vals = {k: {} for k in fields}
        row_ptr = []
        length = 0
        while True:
            line = self.fp.readline()
            if line:
                # if the line is non-empty, store a pointer to the beginning of the line 
                row_ptr.append(ptr)
                if self.reformat is not None:
                    # apply udf to reformat line
                    line = self.reformat(self, line)
                row = list(csv.reader([line], delimiter=self.delimiter))[0]
                # associate row pointer with a key in each field
                for field, col in field_to_col.items():
                    val = row[col]
                    if val not in fields_to_vals[field]:
                        fields_to_vals[field][val] = [ptr]
                    else:
                        fields_to_vals[field][val].append(ptr)
                # update pointer and expand known data row length of file
                ptr = self.fp.tell()
                length += 1
            else:
                # end-of-file
                break
        self.row_ptr = row_ptr
        for field, vals in fields_to_vals.items():
            self.field_ptr[field] = fields_to_vals[field]
        self.length = length
        self.horizon = length
        
    def fields(self):
        # return the registered fields
        return self.field_ptr.keys()
        
    def keys(self, field):
        # return the keys of a given field
        return self.field_ptr[field].keys()
        
    def cols(self):
        # return the header
        return self.header
        
    def get(self, field, key, default=NullObj()):
        # get a row by field and key
        if ((default is None or not isinstance(default, NullObj)) and 
           (key not in self.keys(field))):
            # if the key does not exist for a given field, return the default
            return default
        else:
            # key either exists or default does not exist; return value or error, respectively
            return self.__getitem__((field, key))
        
    def __getitem__(self, index):
        # get a row by index or rows by field and key
        # e.g. data[5] or data['myfield', 'mykey']
        if isinstance(index, tuple):
            assert len(index) == 2
            field = index[0]
            index = index[1]
        else:
            field = None
        
        if field is None:
            # integer index/indices given instead of registered field and key
            if self.length is None:
                # total length of file is not currently known
                if isinstance(index, slice):
                    # return a slice of rows indexed from the file
                    start = 0 if index.start is None else index.start
                    stop = None if index.stop is None else index.stop
                    step = 1 if index.step is None else index.step
                    assert start >= 0
                    rows = []
                    idx = start
                    while True:
                        if stop is None or idx < stop:
                            if idx >= self.horizon:
                                if self.horizon == 0:
                                    self.fp.seek(0)
                                    for _ in range(self.skip):
                                        self.fp.readline()
                                    if self.header:
                                        self.fp.readline()
                                else:
                                    self.fp.seek(self.row_ptr[-1])
                                    self.fp.readline()
                                ptr = self.fp.tell()
                                for i in range(self.horizon, idx+1):
                                    line = self.fp.readline()
                                    if line:
                                        self.row_ptr.append(ptr)
                                        ptr = self.fp.tell()
                                        self.horizon += 1
                                    else:
                                        self.length = self.horizon
                                        stop = self.length
                                        break
                                if self.length is not None:
                                    break
                            self.fp.seek(self.row_ptr[idx])
                            if self.raw_output:
                                row = self.fp.readline()
                            else:
                                line = self.fp.readline()
                                if self.reformat is not None:
                                    line = self.reformat(self, line)
                                row = list(csv.reader([line], delimiter=self.delimiter))[0]
                            rows.append(row)
                            idx += step
                        else:
                            break
                    if self.header and not self.raw_output:
                        rows = [{k: v for k, v in zip(self.header, row)} for row in rows]
                    return rows
                else:
                    if index >= self.horizon:
                        if self.horizon == 0:
                            self.fp.seek(0)
                            for _ in range(self.skip):
                                self.fp.readline()
                            if self.header:
                                self.fp.readline()
                        else:
                            self.fp.seek(self.row_ptr[-1])
                            self.fp.readline()
                        ptr = self.fp.tell()
                        for i in range(self.horizon, index+1):
                            line = self.fp.readline()
                            if line:
                                self.row_ptr.append(ptr)
                                ptr = self.fp.tell()
                                self.horizon += 1
                            else:
                                self.length = self.horizon
                                break
                        if self.length is not None:
                            assert index < self.length
                    self.fp.seek(self.row_ptr[index])
                    if self.raw_output:
                        row = self.fp.readline()
                    else:
                        line = self.fp.readline()
                        if self.reformat is not None:
                            line = self.reformat(self, line)
                        row = list(csv.reader([line], delimiter=self.delimiter))[0]
                    if self.header and not self.raw_output:
                        row = {k: v for k, v in zip(self.header, row)}
                    return row
            else:
                if isinstance(index, slice):
                    start = 0 if index.start is None else index.start
                    stop = self.length if index.stop is None else index.stop
                    step = 1 if index.step is None else index.step
                    assert start >= 0 and stop <= self.length
                    rows = []
                    for idx in range(start, stop, step):
                        self.fp.seek(self.row_ptr[idx])
                        if self.raw_output:
                            row = self.fp.readline()
                        else:
                            line = self.fp.readline()
                            if self.reformat is not None:
                                line = self.reformat(self, line)
                            row = list(csv.reader([line], delimiter=self.delimiter))[0]
                        rows.append(row)
                    if self.header:
                        rows = [{k: v for k, v in zip(self.header, row)} for row in rows]
                    return rows
                else:
                    assert index < self.length
                    self.fp.seek(self.row_ptr[index])
                    if self.raw_output:
                        row = self.fp.readline()
                    else:
                        line = self.fp.readline()
                        if self.reformat is not None:
                            line = self.reformat(self, line)
                        row = list(csv.reader([line], delimiter=self.delimiter))[0]
                    if self.header and not self.raw_output:
                        row = {k: v for k, v in zip(self.header, row)}
                    return row
        else:
            rows = []
            for ptr in self.field_ptr[field][index]:
                self.fp.seek(ptr)
                if self.raw_output:
                    row = self.fp.readline()
                else:
                    line = self.fp.readline()
                    if self.reformat is not None:
                        line = self.reformat(self, line)
                    row = list(csv.reader([line], delimiter=self.delimiter))[0]
                rows.append(row)
            if self.header and not self.raw_output:
                rows = [{k: v for k, v in zip(self.header, row)} for row in rows]
            return rows
        
    def __iter__(self):
        self.start_iter = 0
        return self
    
    def __next__(self):
        if self.start_iter >= self.size(force=True):
            raise StopIteration
        else:
            self.start_iter += 1
            return self.__getitem__(self.start_iter-1)
