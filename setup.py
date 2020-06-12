import os
from setuptools import setup, find_packages

with open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md"), encoding="utf-8",
) as f:
    long_description = f.read()


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


requirements = read("requirements.txt").split()

setup(
    name="arkhn_arx",
    packages=find_packages(),
    include_package_data=True,
    version="0.0.5",
    license="MIT License",
    description=" arkhn_arx is a tool to pseudonymize or anonymize datasets while evaluating reidentification risk metrics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Celine Thiriez",
    author_email="contact@arkhn.com",
    url="https://github.com/arkhn/pyarxaas",
    download_url="https://github.com/arkhn/pyarxaas/archive/0.0.1.tar.gz",
    keywords=[
        "arkhn",
        "dataset anonymization",
        "dataset pseudonymization",
        "reidentification risk evaluation",
    ],
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)