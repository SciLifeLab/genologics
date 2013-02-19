from setuptools import setup, find_packages
import sys, os

version = '0.2'

setup(name='genologics',
      version=version,
      description="Python interface to the GenoLogics LIMS (Laboratory Information Management System) server via its REST API.",
      long_description="""A basic module for interacting with the GenoLogics LIMS server via its REST API.
                          The goal is to provide simple access to the most common entities and their attributes in a reasonably Pythonic fashion.""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='genologics api rest',
      author='Per Kraulis',
      author_email='per.kraulis@scilifelab.se',
      url='https://github.com/scilifelab/genologics',
      license='GPLv3',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "requests"
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
