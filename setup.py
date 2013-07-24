from setuptools import setup, find_packages
import sys, os

version = '0.2.3'

setup(name='genologics',
      version=version,
      description="Python interface to the GenoLogics LIMS (Laboratory Information Management System) server via its REST API.",
      long_description="""A basic module for interacting with the GenoLogics LIMS server via its REST API.
                          The goal is to provide simple access to the most common entities and their attributes in a reasonably Pythonic fashion.""",
      classifiers=[
	"Development Status :: 4 - Beta",
	"Environment :: Console",
	"Intended Audience :: Developers",
	"Intended Audience :: Healthcare Industry",
	"Intended Audience :: Science/Research",
	"License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
	"Operating System :: POSIX :: Linux",
	"Programming Language :: Python",
	"Topic :: Scientific/Engineering :: Medical Science Apps."
	],
      keywords='genologics api rest',
      author='Per Kraulis',
      author_email='per.kraulis@scilifelab.se',
      maintainer='Roman Valls Guimera',
      maintainer_email='roman@scilifelab.se',
      url='https://github.com/scilifelab/genologics',
      license='GPLv3',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      scripts=["scripts/attach_caliper_files.py"],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "requests"
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
