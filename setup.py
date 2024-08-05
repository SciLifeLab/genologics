import glob

from setuptools import find_packages, setup

from genologics.version import __version__

# Fetch version from git tags.
# if git is not available (PyPi package), use stored version.py.


try:
    with open("requirements.txt") as rq:
        requires = rq.readlines()
except:
    requires = ["requests"]

setup(
    name="genologics",
    version=__version__,
    description="Python interface to the Illumina Basespace Clarity LIMS (Laboratory Information Management System) server via its REST API.",
    long_description="""A basic module for interacting with the Illumina Basespace Clarity LIMS server via its REST API.
                          The goal is to provide simple access to the most common entities and their attributes in a reasonably Pythonic fashion.""",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
    keywords="genologics api rest clarity lims illumina",
    author="Per Kraulis",
    author_email="per.kraulis@scilifelab.se",
    maintainer="Chuan Wang",
    maintainer_email="chuan.wang@scilifelab.se",
    url="https://github.com/scilifelab/genologics",
    license="MIT",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    scripts=glob.glob("scripts/*.py"),
    include_package_data=True,
    zip_safe=False,
    install_requires=["requests"],
    python_requires=">=3.12",
    entry_points="""
      # -*- Entry points: -*-
      """,
)
