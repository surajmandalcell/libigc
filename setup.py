from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="libigc",
    version="1.0.4",
    author="Suraj Mandal",
    author_email="dev@mandalsuraj.com",
    description="A library for parsing IGC files and extracting thermals",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/surajmandalcell/libigc",
    packages=find_packages(exclude=["tests", "testfiles", "examples"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.6",
    install_requires=[
        "simplekml>=1.3.1",
        "pathlib2>=2.1.0",
    ],
    keywords="igc gliding soaring flight-analysis thermal-detection",
)
