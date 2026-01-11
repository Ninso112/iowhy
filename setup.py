#!/usr/bin/env python3
"""
Setup configuration for iowhy package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="iowhy",
    version="0.1.0",
    description="A lightweight Linux CLI tool to identify disk I/O bottlenecks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="",
    license="GPLv3",
    python_requires=">=3.6",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "iowhy=iowhy.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
    ],
)
