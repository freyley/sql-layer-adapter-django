from distutils.core import setup

setup(
    name            = 'django_fdbsql',
    version         = '1.0.0',
    author          = 'FoundationDB',
    author_email    = 'distribution@foundationdb.com',
    description     = 'Django database backend for the FoundationDB SQL Layer.',
    url             = 'https://github.com/FoundationDB/sql-layer-adapter-django',
    packages        = ['django_fdbsql', 'django_fdbsql.test'],
    scripts         = [],
    license         = 'LICENSE',
    long_description= open('README.rst').read(),
    install_requires = [
        "Django >= 1.3.0",
        "Django  < 1.7.0"
    ],
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Database'
    ]
)

