from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='nara',
      version=version,
      description="curses based maildir email client with gmail-threading",
      long_description="""\
longdesc""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='curses maildir email mua gmail',
      author='Dominic LoBue',
      author_email='dominic.lobue@gmail.com',
      url='nottaken.net',
      license='gpl',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
            'urwid>=0.9.8.4',
            'blist',
          'sqlobject',
          'pypubsub',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
