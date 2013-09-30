from distutils.core import setup

setup(
    name            = 'django_fdbsql',
    version         = '0.1.0',
    author          = 'FoundationDB',
    author_email    = 'distribution@foundationdb.com',
    description     = 'Django database backend for the FoundationDB SQL Layer.',
    url             = 'https://github.com/FoundationDB/sql-layer-adapter-django',
    packages        = ['django_fdbsql', 'django_fdbsql.test'],
    scripts         = [],
    license         = 'LICENSE',
    long_description= open('README.rst').read(),
    install_requires = [
        "Django >= 1.3.0"
    ],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Database'
    ]
)

