#!/usr/bin/env python3
#
# setup.py — Packaging script for File Deduplication Project

from setuptools import setup, find_packages

setup(
    name="file-deduplicator",
    version="0.1.0",
    description="AI-powered tool for file deduplication, classification, and sorting",
    author="Tim Canady",
    author_email="you@example.com",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "python-docx>=1.0.0",
        "mutagen>=1.45.1",
        "pymupdf>=1.22.5",
        "rich>=13.5.2"
    ],
    entry_points={
        'console_scripts': [
            'dedupe=main:main'
        ]
    },
    python_requires='>=3.9'
)
