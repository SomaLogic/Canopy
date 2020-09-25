from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='canopy',
    python_requires='>3.8.0',
    version='0.2',
    packages=find_packages(),
    url='http://confluence.sladmin.com/display/INGEN/Canopy',
    license='',
    author='SomaLogic',
    author_email='helpdesk@somalogic.com',
    description='SomaLogic Python Data Analysis Library',
    long_description=long_description,
    scripts=[
        'bin/canopy_concat_adats',
        'bin/canopy_check_adat',
        'bin/canopy_smart_concat_adats',
    ],
    install_requires=[
        'pandas>=1.0.0',
        'numpy>=1.18.1',
    ],
)
