#!/usr/bin/env python3

from setuptools import setup


setup(
    name='fuo_local',
    version='0.1.3',
    description='feeluown local plugin',
    author='Cosven',
    author_email='yinshaowen241@gmail.com',
    packages=[
        'fuo_local',
    ],
    package_data={
        '': []
        },
    url='https://github.com/feeluown/feeluown-local',
    keywords=['feeluown', 'plugin', 'local'],
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        ),
    install_requires=[
        'feeluown',
        'mutagen>=1.37',
        'marshmallow',
        'fuzzywuzzy',
    ],
    entry_points={
        'fuo.plugins_v1': [
            'local = fuo_local',
        ]
    },
)
