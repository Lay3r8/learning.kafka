"""
Setup file for shared models package.
Allows installation across microservices: pip install -e ../shared-models
"""
from setuptools import setup

setup(
    name="gaming-shared-models",
    version="1.0.0",
    description="Shared data models for CQRS gaming system",
    py_modules=["models"],  # Single module file, not a package
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",  # For API contract models
    ],
)
