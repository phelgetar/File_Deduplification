#!/usr/bin/env python3
#
# setup.py — Packaging script for File Deduplication Project

from setuptools import setup, find_packages

setup(
    name="file-deduplicator",
    version="0.4.11",
    description="AI-powered tool for file deduplication, classification, and sorting",
    author="Tim Canady",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "python-dotenv>=1.0.0",
        "PyYAML>=6.0",
        "sqlalchemy>=2.0.21",
        "pymysql>=1.1.0",
        "pymupdf>=1.22.5",
        "python-docx>=1.0.0",
        "mutagen>=1.45.1",
        "pillow",
        "requests",
        "PySimpleGUI>=4.60.5",
    ],
    extras_require={
        # CLIP-based image content analysis (core/image_content_analyzer.py)
        "ai": [
            "torch",
            "transformers",
            "pillow-heif",
        ],
    },
    entry_points={
        'console_scripts': [
            'dedupe=core.main:main'
        ]
    },
    python_requires='>=3.9'
)
