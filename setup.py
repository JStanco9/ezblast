from setuptools import setup, find_packages

with open('README.md', "r") as rf:
    long_description = rf.read()

setup(
    name='ezblast',
    version='0.1.0',
    author='John Stanco',
    description='Command-line tool for ncbi BLAST search',
    entry_points={
        'console_scripts': ['ezblast=ezblast.cli:main']
    },
    long_description=long_description,
    packages=find_packages(),
    install_requires=[]
)
