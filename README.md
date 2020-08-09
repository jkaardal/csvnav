## CSVNAV: a python 3 class for memory-efficient navigation of CSV/Text files.

This package can be installed with pip:
```
pip install csvnav
```
or by downloading this repo and using setup tools:
```sh
python setup.py install
```
run from within the `csvnav` directory.

The file `csvnav.py` is a python module containing the class `Navigator`. When instantiated, `Navigator` will open a given path and then store pointers to the location of each row in the opened file. In the simplest case, one can use the instantiation sort of like a list. For instance, if I have a file "inventory.csv" containing the following CSV data:
```
time,product,quantity
5,tire,4
8,sparkplug,20
2,battery,120
10,tire,2
11,tire,3
30,sparkplug,35
```
I can instantiate the class and query rows by index:
```python
from csvnav import Navigator

nav = Navigator('./inventory.csv', header=True, delimiter=',')
print(nav[0])
print(nav[2])
print(nav.size(force=True))

nav.close()
```
where the output would be:
```
{'product': 'tire', 'quantity': '4', 'time': '5'}
{'product': 'battery', 'quantity': '120', 'time': '2'}
6
```
Note that the number of data rows (excluding any skipped lines and the header) can be printed by calling `Navigator.size(force=True)`. In this case, `force=True` means that the number of data rows in the file will be determined even if the last row in the file has not be accessed yet. If the last row had been accessed, `force=False` would return the same result. However, if the last row had not yet been accessed, `force=False` would return `None`. Another thing to note is that the rows are returned as a dictionary. As long as `Navigator.header` contains a list of the column names (done automatically from the first row of the CSV file after any skipped lines when `header=True` in instantiation or when column names are provided with the `Navigator.set_header()` method), the rows will be returned as a dictionary. Otherwise, the rows are returned as lists. For example, if "inventory.csv" did not have a header then the output would be:
```
['5', 'tire', '4']
['2', 'battery', '120']
6
```
The `Navigator` class is also iterable and will iterate through rows in order:
```python
for row in nav:
    print(row)
```
gives the output (assuming we have a header):
```
{'time': '5', 'product': 'tire', 'quantity': '4'}
{'time': '8', 'product': 'sparkplug', 'quantity': '20'}
{'time': '2', 'product': 'battery', 'quantity': '120'}
{'time': '10', 'product': 'tire', 'quantity': '2'}
{'time': '11', 'product': 'tire', 'quantity': '3'}
{'time': '30', 'product': 'sparkplug', 'quantity': '35'}
```

If we only want to iterate through a subset of rows that match a condition, we can use the `Navigator.filter` method:
```python
from csvnav import Navigator

nav = Navigator('./inventory.csv', header=True, delimiter=',')

def when_few_tires(row):
    if row['product'] == 'tire' and int(row['quantity']) <= 3:
        return True
    else:
        return False

for row in nav.filter(when_few_tires):
    print(row)

nav.close()
```
will produce the output:
```
{'time': '10', 'product': 'tire', 'quantity': '2'}
{'time': '11', 'product': 'tire', 'quantity': '3'} 
```

Another usage of the class is to group pointers by column name (assuming `Navigator.header` is set). This can be done with the `Navigator.register` method.
The following code will then group rows by product and show how this data can be accessed:
```python
from csvnav import Navigator

nav = Navigator('./inventory.csv', header=True, delimiter=',')

nav.register('product') # can also provide a list of columns to register each

print(nav.fields)
print(nav.keys('product'))
for k, v in nav.items('product'):
    print(k, list(v))

nav.close()
```
will print out the following groups (list of dict or list):
```
dict_keys(['product'])
dict_keys(['tire', 'sparkplug', 'battery'])
tire [{'time': '5', 'product': 'tire', 'quantity': '4'}, {'time': '10', 'product': 'tire', 'quantity': '2'}, {'time': '11', 'product': 'tire', 'quantity': '3'}]
sparkplug [{'time': '8', 'product': 'sparkplug', 'quantity': '20'}, {'time': '30', 'product': 'sparkplug', 'quantity': '35'}]
battery [{'time': '2', 'product': 'battery', 'quantity': '120'}]
```
Note that groups are then accessed by two "indexes", namely the column name and the key.

The `Navigator` class should be thread safe and an instance can be shared between threads. `Navigator` has some more functionality that I have not described here but this covers the basics. Refer to the docstrings of the various methods of the `Navigator` class for more information.

## About

This code is a generalization of some more application-specific code I wrote while working on analyzing data in large CSV files. I decided to release this code since I think it has some educational value and may be useful to others. This code has been released with permission from the Markov Corporation.
