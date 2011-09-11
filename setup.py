import os
from setuptools import setup

if os.path.isfile('README.rst'):
    long_description = open('README.rst').read()
else:
    long_description = 'See http://pypi.python.org/pypi/django-minify/'

setup(
    name = 'django-minify',
    version = '1.4',
    author = 'Rick van Hattem',
    author_email = 'Rick.van.Hattem@Fawo.nl',
    description = '''django-minify is a django app that combines and minifies
        css and javascript files.''',
    url='https://github.com/WoLpH/django-minify',
    license = 'BSD',
    packages=['django_minify'],
    long_description=long_description,
    test_suite='nose.collector',
    setup_requires=['nose'],
    classifiers=[
        'License :: OSI Approved :: BSD License',
    ],
)
