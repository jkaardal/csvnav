import csv
import threading
from csvnav import Navigator


data_file = './inventory.csv'
thread_id = threading.get_ident()


# Create some data for testing
content = [
    ['time', 'product', 'quantity'],
    [5, 'tire', 4],
    [8, 'sparkplug', 20],
    [2, 'battery', 120],
    [10, 'tire', 2],
    [11, 'tire', 3],
    [30, 'sparkplug', 35],
]


with open(data_file, 'w') as fp:
    writer = csv.writer(fp)
    for row in content:
        writer.writerow(row)


def test___init__():
    # Check that some values are initialized correctly.
    nav = Navigator(data_file)
    assert nav.file_has_header == False
    assert nav.fmtparams['strict'] == True
    assert nav.raw_output == False
    assert nav.header is None
    assert len(nav.fps) == 1 and thread_id in nav.fps
    assert nav.horizon == 0
    assert nav.length is None
    nav.close()


def test__get_or_create_fp():
    # Test that existing file objects are returned rather than creating a new one on the current thread.
    nav = Navigator(data_file)
    assert nav._get_or_create_fp() == nav.fps[thread_id]
    assert len(nav.fps) == 1

    def test_thread():
        this_thread_id = threading.get_ident()
        fp = nav._get_or_create_fp()
        assert len(nav.fps) == 2
        assert fp == nav.fps[this_thread_id]
    
    # Test that a new file pointer is created on a new thread.
    thread = threading.Thread(target=test_thread)
    thread.start()
    thread.join()

    nav.close()


def test__readrow():
    # Test that raw string output works.
    nav = Navigator(data_file, raw_output=True)
    for row in content:
        assert nav._readrow() == ','.join([str(r) for r in row]) + '\n'
    nav.close()

    # Test that list output works.
    nav = Navigator(data_file)
    for row in content:
        assert nav._readrow() == [str(r) for r in row]
    nav.close()

    # Test that dict output works.
    nav = Navigator(data_file, header=True)
    header = content[0]
    for row in content[1:]:
        assert nav._readrow() == {header[i]: str(r) for i, r in enumerate(row)}
    nav.close() 


def test_size():
    # Test the size of the file assuming the file does not have a header.
    nav = Navigator(data_file)
    try:
        len(nav)
        raise Exception('len should be returning an error since the size is unknown!')
    except TypeError:
        pass
    assert nav.size() is None
    assert nav.size(force=True) == len(content)
    assert len(nav) == len(content)
    nav.close()

    # Test the size of the file assuming the file does have a header.
    nav = Navigator(data_file, header=True)
    try:
        len(nav)
        raise Exception('len should be returning an error since the size is unknown!')
    except TypeError:
        pass
    assert nav.size() is None
    assert nav.size(force=True) == len(content) - 1
    assert len(nav) == len(content) - 1
    nav.close()


def test_set_header():
    # Test whether a header can be set and used properly.
    nav = Navigator(data_file, skip=1)
    assert nav.header is None
    nav.set_header(content[0])
    assert nav.header == content[0]
    header = content[0]
    for row in content[1:]:
        assert nav._readrow() == {header[i]: str(r) for i, r in enumerate(row)}
    nav.close() 


def test__handle_scalar():
    # Test in-order scalar row indexing.
    nav = Navigator(data_file)
    for i in range(len(content)):
        assert nav[i] == [str(r) for r in content[i]]
    nav.close()
    
    # Test reverse-order scalar row indexing followed by in-order.
    nav = Navigator(data_file)
    for i in reversed(range(len(content))):
        assert nav[i] == [str(r) for r in content[i]]
    for i in range(len(content)):
        assert nav[i] == [str(r) for r in content[i]]
    nav.close()


def test__handle_slice():
    # Test slicing of entire file.
    nav = Navigator(data_file)
    for i, row in enumerate(nav[:]):
        assert row == [str(r) for r in content[i]]
    # Test intermediate start and end points in the file.
    for i in range(len(content) - 1):
        for j in range(i + 1, len(content)):
            for k, row in enumerate(nav[i:j]):
                assert row == [str(r) for r in content[i + k]]
    # Test skipped rows.
    for i, row in enumerate(nav[::2]):
        assert row == [str(r) for r in content[i * 2]]
    nav.close()


def test_register():
    # Test whether a single column can be registered and that the rows is appropriately grouped.
    nav = Navigator(data_file, header=True)
    nav.register('product')
    assert list(nav.fields) == ['product']
    assert set(nav.keys('product')) == {str(row[content[0].index('product')]) for row in content[1:]}
    header = content[0]
    for k, v in nav.items('product'):
        rows = []
        for row in content[1:]:
            if row[header.index('product')] == k:
                rows.append({header[i]: str(r) for i, r in enumerate(row)})
        assert list(v) == rows
    nav.close()

    # Test whether multiple columns can be registered simultaneously.
    nav = Navigator(data_file, header=True)
    nav.register(['product', 'time'])
    assert list(nav.fields) == ['product', 'time']
    assert set(nav.keys('product')) == {str(row[content[0].index('product')]) for row in content[1:]}
    assert set(nav.keys('time')) == {str(row[content[0].index('time')]) for row in content[1:]}
    nav.close()


def test__handle_field():
    # Test whether a rows from a registered column are correct.
    nav = Navigator(data_file, header=True)
    nav.register('product')
    header = content[0]
    for k in nav.keys('product'):
        rows = []
        for row in content[1:]:
            if row[header.index('product')] == k:
                rows.append({header[i]: str(r) for i, r in enumerate(row)})
        assert list(nav._handle_field('product', k)) == rows
    nav.close()


def test_iter():
    # Test an iterator over the rows of the file.
    nav = Navigator(data_file)
    for i, row in enumerate(nav):
        assert row == [str(r) for r in content[i]]
    nav.close()


def test_filter():
    # Test filtering rows with a filter function.
    nav = Navigator(data_file, header=True)

    def when_few_tires(row):
        if row['product'] == 'tire' and int(row['quantity']) <= 3:
            return True
        else:
            return False

    rows = []
    header = content[0]
    for row in content[1:]:
        dict_row = {header[i]: str(r) for i, r in enumerate(row)}
        if when_few_tires(dict_row):
            rows.append(dict_row)

    for i, row in enumerate(nav.filter(when_few_tires)):
        assert row == rows[i]
    nav.close()


def test_concurrency():
    # Test whether multiple threads can iterate through the file without losing their place.
    nav = Navigator(data_file)
    
    def iterate_rows():
        for i, row in enumerate(nav):
            assert row == [str(r) for r in content[i]]
        for i, row in enumerate(nav):
            assert row == [str(r) for r in content[i]]
        for i, row in enumerate(nav):
            assert row == [str(r) for r in content[i]]
        for i, row in enumerate(nav):
            assert row == [str(r) for r in content[i]]
        nav.close()

    threads = []
    for _ in range(4):
        threads.append(threading.Thread(target=iterate_rows))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    nav.close()
