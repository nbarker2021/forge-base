"""
Setup script for the EntropyCore Python SDK.

Usage:
    pip install -e .
    or
    python setup.py sdist bdist_wheel
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="entropy-core",
    version="1.0.0",
    description="Quantum-grade cryptographic entropy without quantum hardware",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="EntropyCore Team",
    author_email="team@entropycore.dev",
    url="https://github.com/entropycore/entropy-core",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "websocket-client>=1.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "mypy>=1.8.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Security :: Cryptography",
        "Topic :: Scientific/Engineering :: Mathematics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="entropy cryptography random rng rule30 cellular-automaton verifiable",
    project_urls={
        "Bug Reports": "https://github.com/entropycore/entropy-core/issues",
        "Source": "https://github.com/entropycore/entropy-core",
    },
)
