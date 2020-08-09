from setuptools import setup

with open('README.md', 'r') as fp:
    readme = fp.read()
readme = readme[:readme.index('## About')]

setup_args = {
    'name': 'csvnav',
    'version': '0.1.0',
    'description': 'A python 3 class for memory-efficient navigation of CSV/Text files.',
    'long_description_content_type': 'text/markdown',
    'long_description': readme,
    'license': 'MIT',
    'py_modules': ['csvnav'],
    'author': 'Joel Kaardal',
    'author_email': 'jkaardal@gmail.com',
    'keywords': ['data-science', 'csv', 'machine-learning', 'data-analysis', 'memory-management'],
    'url': 'https://github.com/jkaardal/csvnav',
    'download_url': 'https://pypi.org/project/csvnav/',
}

if __name__ == '__main__':
    setup(**setup_args)
