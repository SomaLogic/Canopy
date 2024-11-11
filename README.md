# The Python `SomaData` Package from Somalogic, Inc.

[![License:
MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://choosealicense.com/licenses/mit/)
![PyPI Downloads](https://img.shields.io/pypi/dm/somadata?label=PyPI%20downloads)

-----

## Overview

This document accompanies the Python package `somadata`, which loads the SomaLogic, Inc. structured text data file called an `*.adat`.  The `somadata.Adat` object is an extension of the `pandas.DataFrame` class. The package provides auxiliary functions for extracting relevant information from the ADAT object once in the Python environment. Basic familiarity with the Python environment is assumed, as is the ability to install contributed packages from the Python Package Installer (pip)

-----

<a name="toptoc"></a>
## Table of Contents:

1. [Installation](#installation)
2. [Basic Use](#basics)
3. [Reading ADAT text files](#reading)
4. [Wrangling Data](#wrangling)
5. [Adding Metadata](#add-metadata)
6. [Slicing Data](#slicing)
7. [SomaScan Version Lifting](#lifting)
8. [Writing an ADAT text file](#writing)
9. [Example Data Analysis](#example)

<a name="installation"></a>

## Installation
The easiest way to install `SomaData` is to install directly from PyPI

PIP:

```bash
pip install SomaData
```

Alternatively one can install from the GitHub repository.

GitHub:

``` bash
pip install git+https://github.com/SomaLogic/Canopy.git#egg=somadata
```

Alternatively, if you wish to develop or change the source code, you may clone the repository and install manually via:

``` bash
git clone https://github.com/SomaLogic/Canopy.git
pip install -e ./somadata
```

### Dependencies

`Python >=3.8` is required to install `somadata`. The following package dependencies are installed on a `pip install`:
  - `pandas >= 1.1.0`
  - `numpy >= 1.19.1`

[return to top](#toptoc)

<a name="basics"></a>

## Basics

Upon installation, load `somadata` as normal:

[return to top](#toptoc)


```python
import somadata
```

### For a traversable index of the library:


```python
help(somadata)
# help(somadata.adat) ... etc
```

    Help on package somadata:

    NAME
        somadata

    PACKAGE CONTENTS
        adat
        annotations
        base (package)
        data (package)
        errors
        io (package)
        tools (package)

    FILE
        /Users/tjohnson/code/repos/SomaData/somadata/__init__.py




### Internal Objects

The `somadata` package comes with one internal object available to users to run canned examples (or analyses). It can be accessed by perform the import:

  - `from somadata.data.example_data import example_data`

## Main Features (I/O)

  - Loading data (Import)
      - Import a text file in the `*.adat` format into a `Python` session as an `adat` object.
  - Wrangling data (Manipulation)
      - Subset, reorder, and list various fields of an `adat` object.
  - Exporting data (Output)
      - Write out an `adat` object as a `*.adat` text file.

-----
<a name="reading"></a>

### Loading an ADAT


[return to top](#toptoc)

Loading the sample file from within the somadata library via its path


```python
adat = somadata.read_adat('./somadata/data/example_data.adat')
type(adat)
```




    somadata.adat.Adat




```python
adat.shape
```




    (192, 5284)




```python
adat.columns
```




    MultiIndex([( '10000-28', '3', 'SL019233', ...),
                (  '10001-7', '3', 'SL002564', ...),
                ( '10003-15', '3', 'SL019245', ...),
                ( '10006-25', '3', 'SL019228', ...),
                ( '10008-43', '3', 'SL019234', ...),
                ( '10011-65', '3', 'SL019246', ...),
                (  '10012-5', '3', 'SL014669', ...),
                ( '10013-34', '3', 'SL025418', ...),
                ( '10014-31', '3', 'SL007803', ...),
                ('10015-119', '3', 'SL014924', ...),
                ...
                (  '9981-18', '3', 'SL018293', ...),
                (  '9983-97', '3', 'SL019202', ...),
                (  '9984-12', '3', 'SL019205', ...),
                (  '9986-14', '3', 'SL005356', ...),
                (  '9989-12', '3', 'SL019194', ...),
                (  '9993-11', '3', 'SL019212', ...),
                ( '9994-217', '3', 'SL019217', ...),
                (   '9995-6', '3', 'SL013164', ...),
                (  '9997-12', '3', 'SL019215', ...),
                (   '9999-1', '3', 'SL019231', ...)],
               names=['SeqId', 'SeqIdVersion', 'SomaId', 'TargetFullName', 'Target', 'UniProt', 'EntrezGeneID', 'EntrezGeneSymbol', 'Organism', 'Units', 'Type', 'Dilution', 'PlateScale_Reference', 'CalReference', 'Cal_Example_Adat_Set001', 'ColCheck', 'CalQcRatio_Example_Adat_Set001_170255', 'QcReference_170255', 'Cal_Example_Adat_Set002', 'CalQcRatio_Example_Adat_Set002_170255'], length=5284)




```python
from IPython.display import HTML
#Display the first five rows and columns of the adat
HTML(adat.iloc[:5,:5].to_html()) # Need to use HTML & to_html() here to display nicely for this README
# Output is left-right scrollable in both this readme and Jupyter notebooks
```




<table border="1" class="dataframe">
  <thead>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>SeqId</th>
      <th>10000-28</th>
      <th>10001-7</th>
      <th>10003-15</th>
      <th>10006-25</th>
      <th>10008-43</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>SeqIdVersion</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>SomaId</th>
      <th>SL019233</th>
      <th>SL002564</th>
      <th>SL019245</th>
      <th>SL019228</th>
      <th>SL019234</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>TargetFullName</th>
      <th>Beta-crystallin B2</th>
      <th>RAF proto-oncogene serine/threonine-protein kinase</th>
      <th>Zinc finger protein 41</th>
      <th>ETS domain-containing protein Elk-1</th>
      <th>Guanylyl cyclase-activating protein 1</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Target</th>
      <th>CRBB2</th>
      <th>c-Raf</th>
      <th>ZNF41</th>
      <th>ELK1</th>
      <th>GUC1A</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>UniProt</th>
      <th>P43320</th>
      <th>P04049</th>
      <th>P51814</th>
      <th>P19419</th>
      <th>P43080</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>EntrezGeneID</th>
      <th>1415</th>
      <th>5894</th>
      <th>7592</th>
      <th>2002</th>
      <th>2978</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>EntrezGeneSymbol</th>
      <th>CRYBB2</th>
      <th>RAF1</th>
      <th>ZNF41</th>
      <th>ELK1</th>
      <th>GUCA1A</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Organism</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Units</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Type</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Dilution</th>
      <th>20</th>
      <th>20</th>
      <th>0.5</th>
      <th>20</th>
      <th>20</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>PlateScale_Reference</th>
      <th>687.4</th>
      <th>227.8</th>
      <th>126.9</th>
      <th>634.2</th>
      <th>585.0</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>CalReference</th>
      <th>687.4</th>
      <th>227.8</th>
      <th>126.9</th>
      <th>634.2</th>
      <th>585.0</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Cal_Example_Adat_Set001</th>
      <th>1.01252025</th>
      <th>1.01605709</th>
      <th>0.95056180</th>
      <th>0.99607350</th>
      <th>0.94051447</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>ColCheck</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>CalQcRatio_Example_Adat_Set001_170255</th>
      <th>1.008</th>
      <th>0.970</th>
      <th>1.046</th>
      <th>1.042</th>
      <th>1.036</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>QcReference_170255</th>
      <th>505.4</th>
      <th>223.9</th>
      <th>119.6</th>
      <th>667.2</th>
      <th>587.5</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Cal_Example_Adat_Set002</th>
      <th>1.01476233</th>
      <th>1.03686846</th>
      <th>1.15258856</th>
      <th>0.93581231</th>
      <th>0.96201283</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>CalQcRatio_Example_Adat_Set002_170255</th>
      <th>1.067</th>
      <th>1.007</th>
      <th>0.981</th>
      <th>1.026</th>
      <th>0.998</th>
    </tr>
    <tr>
      <th>PlateId</th>
      <th>PlateRunDate</th>
      <th>ScannerID</th>
      <th>PlatePosition</th>
      <th>SlideId</th>
      <th>Subarray</th>
      <th>SampleId</th>
      <th>SampleType</th>
      <th>PercentDilution</th>
      <th>SampleMatrix</th>
      <th>Barcode</th>
      <th>Barcode2d</th>
      <th>SampleName</th>
      <th>SampleNotes</th>
      <th>AliquotingNotes</th>
      <th>SampleDescription</th>
      <th>AssayNotes</th>
      <th>TimePoint</th>
      <th>ExtIdentifier</th>
      <th>SsfExtId</th>
      <th>SampleGroup</th>
      <th>SiteId</th>
      <th>TubeUniqueID</th>
      <th>CLI</th>
      <th>HybControlNormScale</th>
      <th>RowCheck</th>
      <th>NormScale_20</th>
      <th>NormScale_0_005</th>
      <th>NormScale_0_5</th>
      <th>ANMLFractionUsed_20</th>
      <th>ANMLFractionUsed_0_005</th>
      <th>ANMLFractionUsed_0_5</th>
      <th>Age</th>
      <th>Sex</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th rowspan="5" valign="top">Example Adat Set001</th>
      <th rowspan="5" valign="top">2020-06-18</th>
      <th rowspan="5" valign="top">SG15214400</th>
      <th>H9</th>
      <th>258495800012</th>
      <th>3</th>
      <th>1</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.98185998</th>
      <th>PASS</th>
      <th>1.03693580</th>
      <th>0.85701624</th>
      <th>0.77717491</th>
      <th>0.914</th>
      <th>0.869</th>
      <th>0.903</th>
      <th>76</th>
      <th>F</th>
      <td>476.5</td>
      <td>310.1</td>
      <td>100.3</td>
      <td>602.8</td>
      <td>561.8</td>
    </tr>
    <tr>
      <th>H8</th>
      <th>258495800004</th>
      <th>7</th>
      <th>2</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.96671829</th>
      <th>PASS</th>
      <th>0.96022505</th>
      <th>0.84858420</th>
      <th>0.85201953</th>
      <th>0.937</th>
      <th>0.956</th>
      <th>0.973</th>
      <th>55</th>
      <th>F</th>
      <td>474.4</td>
      <td>293.5</td>
      <td>101.8</td>
      <td>561.9</td>
      <td>541.9</td>
    </tr>
    <tr>
      <th>H7</th>
      <th>258495800010</th>
      <th>8</th>
      <th>3</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>1.00193072</th>
      <th>PASS</th>
      <th>0.98411617</th>
      <th>1.03270156</th>
      <th>0.91519153</th>
      <th>0.907</th>
      <th>0.919</th>
      <th>0.915</th>
      <th>47</th>
      <th>M</th>
      <td>415.6</td>
      <td>299.6</td>
      <td>3030.1</td>
      <td>563.9</td>
      <td>423.9</td>
    </tr>
    <tr>
      <th>H6</th>
      <th>258495800003</th>
      <th>4</th>
      <th>4</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.94017961</th>
      <th>PASS</th>
      <th>1.07839878</th>
      <th>0.94626841</th>
      <th>0.91246731</th>
      <th>0.934</th>
      <th>0.919</th>
      <th>0.912</th>
      <th>37</th>
      <th>M</th>
      <td>442.6</td>
      <td>247.9</td>
      <td>112.9</td>
      <td>563.7</td>
      <td>469.8</td>
    </tr>
    <tr>
      <th>H5</th>
      <th>258495800009</th>
      <th>4</th>
      <th>5</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.94621098</th>
      <th>PASS</th>
      <th>0.84679446</th>
      <th>0.92904553</th>
      <th>0.77413056</th>
      <th>0.707</th>
      <th>0.894</th>
      <th>0.708</th>
      <th>71</th>
      <th>F</th>
      <td>465.7</td>
      <td>710.7</td>
      <td>95.9</td>
      <td>791.0</td>
      <td>443.5</td>
    </tr>
  </tbody>
</table>



You may also access the dict header metadata via:


```python
adat.header_metadata
```




    {'!AdatId': 'GID-1234-56-789-abcdef',
     '!Version': '1.2',
     '!AssayType': 'PharmaServices',
     '!AssayVersion': 'V4',
     '!AssayRobot': 'Fluent 1 L-307',
     '!Legal': 'Experiment details and data have been processed to protect Personally Identifiable Information (PII) and comply with existing privacy laws.',
     '!CreatedBy': 'PharmaServices',
     '!CreatedDate': '2020-07-24',
     '!EnteredBy': 'Technician1',
     '!ExpDate': '2020-06-18, 2020-07-20',
     '!GeneratedBy': 'Px (Build:  : ), Canopy_0.1.1',
     '!RunNotes': "2 columns ('Age' and 'Sex') have been added to this ADAT. Age has been randomly increased or decreased by 1-2 years to protect patient information",
     '!ProcessSteps': 'Raw RFU, Hyb Normalization, medNormInt (SampleId), plateScale, Calibration, anmlQC, qcCheck, anmlSMP',
     '!ProteinEffectiveDate': '2019-08-06',
     '!StudyMatrix': 'EDTA Plasma',
     '!PlateType': '',
     '!LabLocation': 'SLUS',
     '!StudyOrganism': '',
     '!Title': 'Example Adat Set001, Example Adat Set002',
     '!AssaySite': 'SW',
     '!CalibratorId': '170261',
     '!ReportConfig': {'analysisSteps': [{'stepType': 'hybNorm',
        'referenceSource': 'intraplate',
        'includeSampleTypes': ['QC', 'Calibrator', 'Buffer']},
       {'stepName': 'medNormInt',
        'stepType': 'medNorm',
        'includeSampleTypes': ['Calibrator', 'Buffer'],
        'referenceSource': 'intraplate',
        'referenceFields': ['SampleId']},
       {'stepType': 'plateScale',
        'referenceSource': 'Reference_v4_Plasma_Calibrator_170261'},
       {'stepType': 'calibrate',
        'referenceSource': 'Reference_v4_Plasma_Calibrator_170261'},
       {'stepName': 'anmlQC',
        'stepType': 'ANML',
        'effectSizeCutoff': 2.0,
        'minFractionUsed': 0.3,
        'includeSampleTypes': ['QC'],
        'referenceSource': 'Reference_v4_Plasma_ANML'},
       {'stepType': 'qcCheck',
        'QCReferenceSource': 'Reference_v4_Plasma_QC_ANML_170255',
        'tailsCriteriaLower': 0.8,
        'tailsCriteriaUpper': 1.2,
        'tailThreshold': 15.0,
        'QCAdditionalReferenceSources': ['Reference_v4_Plasma_QC_ANML_170259',
         'Reference_v4_Plasma_QC_ANML_170260'],
        'prenormalized': True},
       {'stepName': 'anmlSMP',
        'stepType': 'ANML',
        'effectSizeCutoff': 2.0,
        'minFractionUsed': 0.3,
        'includeSampleTypes': ['Sample'],
        'referenceSource': 'Reference_v4_Plasma_ANML'}],
      'qualityReports': ['SQS Report'],
      'filter': {'proteinEffectiveDate': '2019-08-06'}},
     'HybNormReference': 'intraplate',
     'MedNormReference': 'intraplate',
     'NormalizationAlgorithm': 'ANML',
     'PlateScale_ReferenceSource': 'Reference_v4_Plasma_Calibrator_170261',
     'PlateScale_Scalar_Example_Adat_Set001': '1.08091554',
     'PlateScale_PassFlag_Example_Adat_Set001': 'PASS',
     'CalibrationReference': 'Reference_v4_Plasma_Calibrator_170261',
     'CalPlateTailPercent_Example_Adat_Set001': '0.1',
     'PlateTailPercent_Example_Adat_Set001': '1.2',
     'PlateTailTest_Example_Adat_Set001': 'PASS',
     'PlateScale_Scalar_Example_Adat_Set002': '1.09915270',
     'PlateScale_PassFlag_Example_Adat_Set002': 'PASS',
     'CalPlateTailPercent_Example_Adat_Set002': '2.6',
     'PlateTailPercent_Example_Adat_Set002': '4.2',
     'PlateTailTest_Example_Adat_Set002': 'PASS'}



SomaData's Adat object inherits the pandas printing methods which displays nicely in Jupyter Notebooks when using `IPython.display.display()`.

<a name="wrangling"></a>

### Wrangling
Dataframe `columns` Contain Feature Information

[return to top](#toptoc)


```python
# Using the `adat` loaded from above
aptamer_df = adat.columns.to_frame(index=False)
type(aptamer_df)
```




    pandas.core.frame.DataFrame




```python
HTML(aptamer_df.head(5).to_html())
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>SeqId</th>
      <th>SeqIdVersion</th>
      <th>SomaId</th>
      <th>TargetFullName</th>
      <th>Target</th>
      <th>UniProt</th>
      <th>EntrezGeneID</th>
      <th>EntrezGeneSymbol</th>
      <th>Organism</th>
      <th>Units</th>
      <th>Type</th>
      <th>Dilution</th>
      <th>PlateScale_Reference</th>
      <th>CalReference</th>
      <th>Cal_Example_Adat_Set001</th>
      <th>ColCheck</th>
      <th>CalQcRatio_Example_Adat_Set001_170255</th>
      <th>QcReference_170255</th>
      <th>Cal_Example_Adat_Set002</th>
      <th>CalQcRatio_Example_Adat_Set002_170255</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>10000-28</td>
      <td>3</td>
      <td>SL019233</td>
      <td>Beta-crystallin B2</td>
      <td>CRBB2</td>
      <td>P43320</td>
      <td>1415</td>
      <td>CRYBB2</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>20</td>
      <td>687.4</td>
      <td>687.4</td>
      <td>1.01252025</td>
      <td>PASS</td>
      <td>1.008</td>
      <td>505.4</td>
      <td>1.01476233</td>
      <td>1.067</td>
    </tr>
    <tr>
      <th>1</th>
      <td>10001-7</td>
      <td>3</td>
      <td>SL002564</td>
      <td>RAF proto-oncogene serine/threonine-protein kinase</td>
      <td>c-Raf</td>
      <td>P04049</td>
      <td>5894</td>
      <td>RAF1</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>20</td>
      <td>227.8</td>
      <td>227.8</td>
      <td>1.01605709</td>
      <td>PASS</td>
      <td>0.970</td>
      <td>223.9</td>
      <td>1.03686846</td>
      <td>1.007</td>
    </tr>
    <tr>
      <th>2</th>
      <td>10003-15</td>
      <td>3</td>
      <td>SL019245</td>
      <td>Zinc finger protein 41</td>
      <td>ZNF41</td>
      <td>P51814</td>
      <td>7592</td>
      <td>ZNF41</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>0.5</td>
      <td>126.9</td>
      <td>126.9</td>
      <td>0.95056180</td>
      <td>PASS</td>
      <td>1.046</td>
      <td>119.6</td>
      <td>1.15258856</td>
      <td>0.981</td>
    </tr>
    <tr>
      <th>3</th>
      <td>10006-25</td>
      <td>3</td>
      <td>SL019228</td>
      <td>ETS domain-containing protein Elk-1</td>
      <td>ELK1</td>
      <td>P19419</td>
      <td>2002</td>
      <td>ELK1</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>20</td>
      <td>634.2</td>
      <td>634.2</td>
      <td>0.99607350</td>
      <td>PASS</td>
      <td>1.042</td>
      <td>667.2</td>
      <td>0.93581231</td>
      <td>1.026</td>
    </tr>
    <tr>
      <th>4</th>
      <td>10008-43</td>
      <td>3</td>
      <td>SL019234</td>
      <td>Guanylyl cyclase-activating protein 1</td>
      <td>GUC1A</td>
      <td>P43080</td>
      <td>2978</td>
      <td>GUCA1A</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>20</td>
      <td>585.0</td>
      <td>585.0</td>
      <td>0.94051447</td>
      <td>PASS</td>
      <td>1.036</td>
      <td>587.5</td>
      <td>0.96201283</td>
      <td>0.998</td>
    </tr>
  </tbody>
</table>



### Accessing feature data

The `.to_frame()` method creates a lookup table that links the feature names in the `adat` object to the annotation data in `columns`:


```python
col_df = adat.columns.to_frame(index=False)
type(col_df)
```




    pandas.core.frame.DataFrame




```python
HTML(col_df.head(5).to_html())
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>SeqId</th>
      <th>SeqIdVersion</th>
      <th>SomaId</th>
      <th>TargetFullName</th>
      <th>Target</th>
      <th>UniProt</th>
      <th>EntrezGeneID</th>
      <th>EntrezGeneSymbol</th>
      <th>Organism</th>
      <th>Units</th>
      <th>Type</th>
      <th>Dilution</th>
      <th>PlateScale_Reference</th>
      <th>CalReference</th>
      <th>Cal_Example_Adat_Set001</th>
      <th>ColCheck</th>
      <th>CalQcRatio_Example_Adat_Set001_170255</th>
      <th>QcReference_170255</th>
      <th>Cal_Example_Adat_Set002</th>
      <th>CalQcRatio_Example_Adat_Set002_170255</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>10000-28</td>
      <td>3</td>
      <td>SL019233</td>
      <td>Beta-crystallin B2</td>
      <td>CRBB2</td>
      <td>P43320</td>
      <td>1415</td>
      <td>CRYBB2</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>20</td>
      <td>687.4</td>
      <td>687.4</td>
      <td>1.01252025</td>
      <td>PASS</td>
      <td>1.008</td>
      <td>505.4</td>
      <td>1.01476233</td>
      <td>1.067</td>
    </tr>
    <tr>
      <th>1</th>
      <td>10001-7</td>
      <td>3</td>
      <td>SL002564</td>
      <td>RAF proto-oncogene serine/threonine-protein kinase</td>
      <td>c-Raf</td>
      <td>P04049</td>
      <td>5894</td>
      <td>RAF1</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>20</td>
      <td>227.8</td>
      <td>227.8</td>
      <td>1.01605709</td>
      <td>PASS</td>
      <td>0.970</td>
      <td>223.9</td>
      <td>1.03686846</td>
      <td>1.007</td>
    </tr>
    <tr>
      <th>2</th>
      <td>10003-15</td>
      <td>3</td>
      <td>SL019245</td>
      <td>Zinc finger protein 41</td>
      <td>ZNF41</td>
      <td>P51814</td>
      <td>7592</td>
      <td>ZNF41</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>0.5</td>
      <td>126.9</td>
      <td>126.9</td>
      <td>0.95056180</td>
      <td>PASS</td>
      <td>1.046</td>
      <td>119.6</td>
      <td>1.15258856</td>
      <td>0.981</td>
    </tr>
    <tr>
      <th>3</th>
      <td>10006-25</td>
      <td>3</td>
      <td>SL019228</td>
      <td>ETS domain-containing protein Elk-1</td>
      <td>ELK1</td>
      <td>P19419</td>
      <td>2002</td>
      <td>ELK1</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>20</td>
      <td>634.2</td>
      <td>634.2</td>
      <td>0.99607350</td>
      <td>PASS</td>
      <td>1.042</td>
      <td>667.2</td>
      <td>0.93581231</td>
      <td>1.026</td>
    </tr>
    <tr>
      <th>4</th>
      <td>10008-43</td>
      <td>3</td>
      <td>SL019234</td>
      <td>Guanylyl cyclase-activating protein 1</td>
      <td>GUC1A</td>
      <td>P43080</td>
      <td>2978</td>
      <td>GUCA1A</td>
      <td>Human</td>
      <td>RFU</td>
      <td>Protein</td>
      <td>20</td>
      <td>585.0</td>
      <td>585.0</td>
      <td>0.94051447</td>
      <td>PASS</td>
      <td>1.036</td>
      <td>587.5</td>
      <td>0.96201283</td>
      <td>0.998</td>
    </tr>
  </tbody>
</table>



### Display features


```python
adat.columns.get_level_values('SeqId')[:20] # first 20 features
```




    Index(['10000-28', '10001-7', '10003-15', '10006-25', '10008-43', '10011-65',
           '10012-5', '10013-34', '10014-31', '10015-119', '10021-1', '10022-207',
           '10023-32', '10024-44', '10030-8', '10034-16', '10035-6', '10036-201',
           '10037-98', '10040-63'],
          dtype='object', name='SeqId')



### Get # Features


```python
adat.shape[1]
```




    5284



### Clinical Data

Dataframe `index` Contains Sample Information


```python
# Using the `adat` loaded from above
sample_df = adat.index.to_frame(index=False)
type(sample_df)
```




    pandas.core.frame.DataFrame




```python
HTML(sample_df.head(5).to_html())
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>PlateId</th>
      <th>PlateRunDate</th>
      <th>ScannerID</th>
      <th>PlatePosition</th>
      <th>SlideId</th>
      <th>Subarray</th>
      <th>SampleId</th>
      <th>SampleType</th>
      <th>PercentDilution</th>
      <th>SampleMatrix</th>
      <th>Barcode</th>
      <th>Barcode2d</th>
      <th>SampleName</th>
      <th>SampleNotes</th>
      <th>AliquotingNotes</th>
      <th>SampleDescription</th>
      <th>AssayNotes</th>
      <th>TimePoint</th>
      <th>ExtIdentifier</th>
      <th>SsfExtId</th>
      <th>SampleGroup</th>
      <th>SiteId</th>
      <th>TubeUniqueID</th>
      <th>CLI</th>
      <th>HybControlNormScale</th>
      <th>RowCheck</th>
      <th>NormScale_20</th>
      <th>NormScale_0_005</th>
      <th>NormScale_0_5</th>
      <th>ANMLFractionUsed_20</th>
      <th>ANMLFractionUsed_0_005</th>
      <th>ANMLFractionUsed_0_5</th>
      <th>Age</th>
      <th>Sex</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Example Adat Set001</td>
      <td>2020-06-18</td>
      <td>SG15214400</td>
      <td>H9</td>
      <td>258495800012</td>
      <td>3</td>
      <td>1</td>
      <td>Sample</td>
      <td>20</td>
      <td>Plasma-PPT</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>0.98185998</td>
      <td>PASS</td>
      <td>1.03693580</td>
      <td>0.85701624</td>
      <td>0.77717491</td>
      <td>0.914</td>
      <td>0.869</td>
      <td>0.903</td>
      <td>76</td>
      <td>F</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Example Adat Set001</td>
      <td>2020-06-18</td>
      <td>SG15214400</td>
      <td>H8</td>
      <td>258495800004</td>
      <td>7</td>
      <td>2</td>
      <td>Sample</td>
      <td>20</td>
      <td>Plasma-PPT</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>0.96671829</td>
      <td>PASS</td>
      <td>0.96022505</td>
      <td>0.84858420</td>
      <td>0.85201953</td>
      <td>0.937</td>
      <td>0.956</td>
      <td>0.973</td>
      <td>55</td>
      <td>F</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Example Adat Set001</td>
      <td>2020-06-18</td>
      <td>SG15214400</td>
      <td>H7</td>
      <td>258495800010</td>
      <td>8</td>
      <td>3</td>
      <td>Sample</td>
      <td>20</td>
      <td>Plasma-PPT</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>1.00193072</td>
      <td>PASS</td>
      <td>0.98411617</td>
      <td>1.03270156</td>
      <td>0.91519153</td>
      <td>0.907</td>
      <td>0.919</td>
      <td>0.915</td>
      <td>47</td>
      <td>M</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Example Adat Set001</td>
      <td>2020-06-18</td>
      <td>SG15214400</td>
      <td>H6</td>
      <td>258495800003</td>
      <td>4</td>
      <td>4</td>
      <td>Sample</td>
      <td>20</td>
      <td>Plasma-PPT</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>0.94017961</td>
      <td>PASS</td>
      <td>1.07839878</td>
      <td>0.94626841</td>
      <td>0.91246731</td>
      <td>0.934</td>
      <td>0.919</td>
      <td>0.912</td>
      <td>37</td>
      <td>M</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Example Adat Set001</td>
      <td>2020-06-18</td>
      <td>SG15214400</td>
      <td>H5</td>
      <td>258495800009</td>
      <td>4</td>
      <td>5</td>
      <td>Sample</td>
      <td>20</td>
      <td>Plasma-PPT</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>0.94621098</td>
      <td>PASS</td>
      <td>0.84679446</td>
      <td>0.92904553</td>
      <td>0.77413056</td>
      <td>0.707</td>
      <td>0.894</td>
      <td>0.708</td>
      <td>71</td>
      <td>F</td>
    </tr>
  </tbody>
</table>



<a name="add-metadata"></a>
### Modifying Metadata

The `Adat` index and columns are `pandas.MultiIndex` objects.  Several convenience functions exist to help you modify these objects.  Typically, the row metadata (axis=0) represents data describing the sample or the individual from whom the sample was collected.  The column metadata (axis=1) contains data regarding the SOMAmer reagent, the reagent's target and scalars applied to columns during normalization, these columns are not usually edited by the end user but can be using the same methods demonstrated on row metadata below.


[return to top](#toptoc)

#### Add Row Metadata

Row metadata is sample level information which could include added clinical data like age, sex or clinical measurements. The Adat class facilitates managing this data.



```python
# using ittertools to simulate some metadata:
from itertools import cycle, islice
import pandas as pd

# for demonstration we will simulate two types of metadata.  Metadata stored in a list and metadata stored with key-value pairs.
metadata_list = list(islice(cycle(['A', 'B', 'X', 'Y']), adat.shape[0]))
metadata_dictionary = {k:v for k, v in zip(adat.index.get_level_values('SampleId').to_list(), metadata_list)}
```

#### Add unlabeled metadata

You might do this if you know your metadata and `Adat` are ordered the same way but you are not using a shared key.

[return to top](#toptoc)


```python
new_meta_adat = adat.insert_meta(0,'GroupData', metadata_list)
# this will produce a new Adat file with group data in the right most column of the index
new_meta_adat.index.to_frame(index=False).loc[0:6, ['PlateId', 'SampleId', 'GroupData']]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>PlateId</th>
      <th>SampleId</th>
      <th>GroupData</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Example Adat Set001</td>
      <td>1</td>
      <td>A</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Example Adat Set001</td>
      <td>2</td>
      <td>B</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Example Adat Set001</td>
      <td>3</td>
      <td>X</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Example Adat Set001</td>
      <td>4</td>
      <td>Y</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Example Adat Set001</td>
      <td>5</td>
      <td>A</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Example Adat Set001</td>
      <td>6</td>
      <td>B</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Example Adat Set001</td>
      <td>7</td>
      <td>X</td>
    </tr>
  </tbody>
</table>
</div>



#### Add Keyed Metadata

You might have data coming in as key value pairs from another data source. In that case it is easier to insert metadata using those keys:


[return to top](#toptoc)


```python
# The arguments are `axis` 0 for row metadata, 1 for column metadata, `name` the name of the new index,
#`key_meta_name` the nameo of the axis used to match the keys. `values_dict` the dictionary containing the new data
new_meta_adat = adat.insert_keyed_meta(0,'GroupData', 'SampleId', metadata_dictionary)
# this will produce a new Adat file with group data in the right most column of the index
new_meta_adat.index.to_frame(index=False).loc[0:6, ['PlateId', 'SampleId', 'GroupData']]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>PlateId</th>
      <th>SampleId</th>
      <th>GroupData</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Example Adat Set001</td>
      <td>1</td>
      <td>A</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Example Adat Set001</td>
      <td>2</td>
      <td>B</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Example Adat Set001</td>
      <td>3</td>
      <td>X</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Example Adat Set001</td>
      <td>4</td>
      <td>Y</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Example Adat Set001</td>
      <td>5</td>
      <td>A</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Example Adat Set001</td>
      <td>6</td>
      <td>B</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Example Adat Set001</td>
      <td>7</td>
      <td>X</td>
    </tr>
  </tbody>
</table>
</div>



#### Replace Metadata with Unlabeled Metadata

You might do this if you know your metadata and `Adat` are ordered the same way but you are not using a shared key.


[return to top](#toptoc)


```python
new_meta_adat = adat.replace_meta(0,'SampleName', metadata_list)
# this will produce a new Adat file with group data in the right most column of the index
new_meta_adat.index.to_frame(index=False).loc[0:6, ['PlateId', 'SampleId', 'SampleName']]

```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>PlateId</th>
      <th>SampleId</th>
      <th>SampleName</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Example Adat Set001</td>
      <td>1</td>
      <td>A</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Example Adat Set001</td>
      <td>2</td>
      <td>B</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Example Adat Set001</td>
      <td>3</td>
      <td>X</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Example Adat Set001</td>
      <td>4</td>
      <td>Y</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Example Adat Set001</td>
      <td>5</td>
      <td>A</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Example Adat Set001</td>
      <td>6</td>
      <td>B</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Example Adat Set001</td>
      <td>7</td>
      <td>X</td>
    </tr>
  </tbody>
</table>
</div>



### Replace Metadata with Keyed Metadata

You might need to replace metadata based on another document using key-value pairs.

[return to top](#toptoc)


```python
#Here we replace the values in `SampleName` with the values from `metadata_dictionary`
new_meta_adat = adat.replace_keyed_meta(0,'SampleName', metadata_dictionary, 'SampleId')
# this will produce a new Adat file with group data in the right most column of the index
new_meta_adat.index.to_frame(index=False).loc[0:6, ['PlateId', 'SampleId', 'SampleName']]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>PlateId</th>
      <th>SampleId</th>
      <th>SampleName</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Example Adat Set001</td>
      <td>1</td>
      <td>A</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Example Adat Set001</td>
      <td>2</td>
      <td>B</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Example Adat Set001</td>
      <td>3</td>
      <td>X</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Example Adat Set001</td>
      <td>4</td>
      <td>Y</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Example Adat Set001</td>
      <td>5</td>
      <td>A</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Example Adat Set001</td>
      <td>6</td>
      <td>B</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Example Adat Set001</td>
      <td>7</td>
      <td>X</td>
    </tr>
  </tbody>
</table>
</div>



### Math
You may perform mathematical transformations on the feature data via apply or calling those functions and passing the entire dataframe.


```python
import numpy as np
# Using the `adat` loaded from above
log10_adat = adat.apply(np.log10)  # equivalent to `np.log10(adat)`
rounded_adat = adat.apply(round, args=[5,])  # equivalent to `round(adat, 5)`
sqrt_adat = adat.apply(np.sqrt)  # equivlane to `np.sqrt(adat)`
```

<a name="slicing"></a>

### Subsetting/Slicing the Dataframe

You may extract certain subgroups of samples and/or features. SomaData augments the pandas dataframe with a number of helper functions to aid the user.

[return to top](#toptoc)


```python
# Extract rows of only calibrator-type samples
calibrator_adat = adat.pick_on_meta(axis=0, name='SampleType', values=['Calibrator'])

# Exclude calibrator-type samples
non_calibrator_adat = adat.exclude_on_meta(axis=0, name='SampleType', values=['Calibrator'])

# Extract columns containing features that start with 'MMP'
target_names = adat.columns.get_level_values('Target')
mmp_names = [target for target in target_names if target.startswith('MMP')]
mmp_adat = adat.pick_on_meta(axis=1, name='Target', values=mmp_names)
mmp_adat
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead tr th {
        text-align: left;
    }

    .dataframe thead tr:last-of-type th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>SeqId</th>
      <th>15419-15</th>
      <th>2579-17</th>
      <th>2788-55</th>
      <th>2789-26</th>
      <th>2838-53</th>
      <th>4160-49</th>
      <th>4496-60</th>
      <th>4924-32</th>
      <th>4925-54</th>
      <th>5002-76</th>
      <th>5268-49</th>
      <th>6425-87</th>
      <th>8479-4</th>
      <th>9172-69</th>
      <th>9719-145</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>SeqIdVersion</th>
      <th>3</th>
      <th>5</th>
      <th>1</th>
      <th>2</th>
      <th>1</th>
      <th>1</th>
      <th>2</th>
      <th>1</th>
      <th>2</th>
      <th>1</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>SomaId</th>
      <th>SL012374</th>
      <th>SL000527</th>
      <th>SL000524</th>
      <th>SL000525</th>
      <th>SL003332</th>
      <th>SL000124</th>
      <th>SL000522</th>
      <th>SL000521</th>
      <th>SL000523</th>
      <th>SL002646</th>
      <th>SL003331</th>
      <th>SL007616</th>
      <th>SL000645</th>
      <th>SL000526</th>
      <th>SL003331</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>TargetFullName</th>
      <th>Matrix metalloproteinase-20</th>
      <th>Matrix metalloproteinase-9</th>
      <th>Stromelysin-1</th>
      <th>Matrilysin</th>
      <th>Matrix metalloproteinase-17</th>
      <th>72 kDa type IV collagenase</th>
      <th>Macrophage metalloelastase</th>
      <th>Interstitial collagenase</th>
      <th>Collagenase 3</th>
      <th>Matrix metalloproteinase-14</th>
      <th>Matrix metalloproteinase-16</th>
      <th>Matrix metalloproteinase-19</th>
      <th>Stromelysin-2</th>
      <th>Neutrophil collagenase</th>
      <th>Matrix metalloproteinase-16</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Target</th>
      <th>MMP20</th>
      <th>MMP-9</th>
      <th>MMP-3</th>
      <th>MMP-7</th>
      <th>MMP-17</th>
      <th>MMP-2</th>
      <th>MMP-12</th>
      <th>MMP-1</th>
      <th>MMP-13</th>
      <th>MMP-14</th>
      <th>MMP-16</th>
      <th>MMP19</th>
      <th>MMP-10</th>
      <th>MMP-8</th>
      <th>MMP-16</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>UniProt</th>
      <th>O60882</th>
      <th>P14780</th>
      <th>P08254</th>
      <th>P09237</th>
      <th>Q9ULZ9</th>
      <th>P08253</th>
      <th>P39900</th>
      <th>P03956</th>
      <th>P45452</th>
      <th>P50281</th>
      <th>P51512</th>
      <th>Q99542</th>
      <th>P09238</th>
      <th>P22894</th>
      <th>P51512</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>EntrezGeneID</th>
      <th>9313</th>
      <th>4318</th>
      <th>4314</th>
      <th>4316</th>
      <th>4326</th>
      <th>4313</th>
      <th>4321</th>
      <th>4312</th>
      <th>4322</th>
      <th>4323</th>
      <th>4325</th>
      <th>4327</th>
      <th>4319</th>
      <th>4317</th>
      <th>4325</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>EntrezGeneSymbol</th>
      <th>MMP20</th>
      <th>MMP9</th>
      <th>MMP3</th>
      <th>MMP7</th>
      <th>MMP17</th>
      <th>MMP2</th>
      <th>MMP12</th>
      <th>MMP1</th>
      <th>MMP13</th>
      <th>MMP14</th>
      <th>MMP16</th>
      <th>MMP19</th>
      <th>MMP10</th>
      <th>MMP8</th>
      <th>MMP16</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Organism</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Units</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Type</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Dilution</th>
      <th>20</th>
      <th>0.5</th>
      <th>0.5</th>
      <th>20</th>
      <th>20</th>
      <th>0.5</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>0.5</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>PlateScale_Reference</th>
      <th>937.5</th>
      <th>19472.3</th>
      <th>117.2</th>
      <th>2392.9</th>
      <th>1520.6</th>
      <th>14888.5</th>
      <th>1014.9</th>
      <th>7611.5</th>
      <th>376.6</th>
      <th>632.1</th>
      <th>565.8</th>
      <th>5063.4</th>
      <th>1534.0</th>
      <th>1088.5</th>
      <th>1166.8</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>CalReference</th>
      <th>937.5</th>
      <th>19472.3</th>
      <th>117.2</th>
      <th>2392.9</th>
      <th>1520.6</th>
      <th>14888.5</th>
      <th>1014.9</th>
      <th>7611.5</th>
      <th>376.6</th>
      <th>632.1</th>
      <th>565.8</th>
      <th>5063.4</th>
      <th>1534.0</th>
      <th>1088.5</th>
      <th>1166.8</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Cal_Example_Adat_Set001</th>
      <th>1.06947296</th>
      <th>1.01957222</th>
      <th>0.98404702</th>
      <th>0.90131455</th>
      <th>1.13783298</th>
      <th>0.98961103</th>
      <th>0.96180819</th>
      <th>0.91162239</th>
      <th>0.98689727</th>
      <th>1.02497162</th>
      <th>0.97906212</th>
      <th>0.97843478</th>
      <th>0.95061040</th>
      <th>0.94709823</th>
      <th>1.02243253</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>ColCheck</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>CalQcRatio_Example_Adat_Set001_170255</th>
      <th>1.132</th>
      <th>1.002</th>
      <th>0.893</th>
      <th>1.130</th>
      <th>0.955</th>
      <th>0.987</th>
      <th>1.014</th>
      <th>1.054</th>
      <th>1.023</th>
      <th>0.987</th>
      <th>1.024</th>
      <th>1.005</th>
      <th>1.023</th>
      <th>1.029</th>
      <th>1.003</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>QcReference_170255</th>
      <th>793.4</th>
      <th>10420.6</th>
      <th>124.2</th>
      <th>9482.5</th>
      <th>1252.0</th>
      <th>16044.7</th>
      <th>1115.3</th>
      <th>13192.8</th>
      <th>394.4</th>
      <th>492.1</th>
      <th>559.2</th>
      <th>6162.7</th>
      <th>1946.6</th>
      <th>845.5</th>
      <th>1171.0</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Cal_Example_Adat_Set002</th>
      <th>1.02380692</th>
      <th>1.00117741</th>
      <th>1.31243001</th>
      <th>0.67812509</th>
      <th>1.09317038</th>
      <th>0.98499534</th>
      <th>0.95953484</th>
      <th>0.95154455</th>
      <th>0.90594178</th>
      <th>1.08143713</th>
      <th>0.98143972</th>
      <th>0.98821187</th>
      <th>0.92700024</th>
      <th>1.03983569</th>
      <th>1.02055454</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>CalQcRatio_Example_Adat_Set002_170255</th>
      <th>1.192</th>
      <th>1.009</th>
      <th>0.821</th>
      <th>1.123</th>
      <th>1.083</th>
      <th>1.028</th>
      <th>1.006</th>
      <th>1.025</th>
      <th>0.991</th>
      <th>0.949</th>
      <th>1.002</th>
      <th>0.990</th>
      <th>1.010</th>
      <th>1.039</th>
      <th>0.951</th>
    </tr>
    <tr>
      <th>PlateId</th>
      <th>PlateRunDate</th>
      <th>ScannerID</th>
      <th>PlatePosition</th>
      <th>SlideId</th>
      <th>Subarray</th>
      <th>SampleId</th>
      <th>SampleType</th>
      <th>PercentDilution</th>
      <th>SampleMatrix</th>
      <th>Barcode</th>
      <th>Barcode2d</th>
      <th>SampleName</th>
      <th>SampleNotes</th>
      <th>AliquotingNotes</th>
      <th>SampleDescription</th>
      <th>AssayNotes</th>
      <th>TimePoint</th>
      <th>ExtIdentifier</th>
      <th>SsfExtId</th>
      <th>SampleGroup</th>
      <th>SiteId</th>
      <th>TubeUniqueID</th>
      <th>CLI</th>
      <th>HybControlNormScale</th>
      <th>RowCheck</th>
      <th>NormScale_20</th>
      <th>NormScale_0_005</th>
      <th>NormScale_0_5</th>
      <th>ANMLFractionUsed_20</th>
      <th>ANMLFractionUsed_0_005</th>
      <th>ANMLFractionUsed_0_5</th>
      <th>Age</th>
      <th>Sex</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th rowspan="5" valign="top">Example Adat Set001</th>
      <th rowspan="5" valign="top">2020-06-18</th>
      <th rowspan="5" valign="top">SG15214400</th>
      <th>H9</th>
      <th>258495800012</th>
      <th>3</th>
      <th>1</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.98185998</th>
      <th>PASS</th>
      <th>1.03693580</th>
      <th>0.85701624</th>
      <th>0.77717491</th>
      <th>0.914</th>
      <th>0.869</th>
      <th>0.903</th>
      <th>76</th>
      <th>F</th>
      <td>729.9</td>
      <td>16230.2</td>
      <td>177.9</td>
      <td>11903.3</td>
      <td>1378.1</td>
      <td>11997.2</td>
      <td>2455.9</td>
      <td>20988.1</td>
      <td>442.5</td>
      <td>414.2</td>
      <td>712.5</td>
      <td>8965.5</td>
      <td>2030.6</td>
      <td>2181.5</td>
      <td>1096.4</td>
    </tr>
    <tr>
      <th>H8</th>
      <th>258495800004</th>
      <th>7</th>
      <th>2</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.96671829</th>
      <th>PASS</th>
      <th>0.96022505</th>
      <th>0.84858420</th>
      <th>0.85201953</th>
      <th>0.937</th>
      <th>0.956</th>
      <th>0.973</th>
      <th>55</th>
      <th>F</th>
      <td>873.3</td>
      <td>17253.4</td>
      <td>152.8</td>
      <td>16508.8</td>
      <td>1652.0</td>
      <td>14574.6</td>
      <td>1595.0</td>
      <td>11498.5</td>
      <td>501.1</td>
      <td>505.9</td>
      <td>629.9</td>
      <td>8669.7</td>
      <td>1301.6</td>
      <td>1571.2</td>
      <td>1149.0</td>
    </tr>
    <tr>
      <th>H7</th>
      <th>258495800010</th>
      <th>8</th>
      <th>3</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>1.00193072</th>
      <th>PASS</th>
      <th>0.98411617</th>
      <th>1.03270156</th>
      <th>0.91519153</th>
      <th>0.907</th>
      <th>0.919</th>
      <th>0.915</th>
      <th>47</th>
      <th>M</th>
      <td>993.0</td>
      <td>13094.1</td>
      <td>127.5</td>
      <td>7577.0</td>
      <td>1711.7</td>
      <td>14468.7</td>
      <td>503.3</td>
      <td>14697.7</td>
      <td>2883.2</td>
      <td>445.8</td>
      <td>510.6</td>
      <td>6728.9</td>
      <td>1067.3</td>
      <td>1528.9</td>
      <td>1027.8</td>
    </tr>
    <tr>
      <th>H6</th>
      <th>258495800003</th>
      <th>4</th>
      <th>4</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.94017961</th>
      <th>PASS</th>
      <th>1.07839878</th>
      <th>0.94626841</th>
      <th>0.91246731</th>
      <th>0.934</th>
      <th>0.919</th>
      <th>0.912</th>
      <th>37</th>
      <th>M</th>
      <td>906.5</td>
      <td>20991.4</td>
      <td>155.0</td>
      <td>8673.7</td>
      <td>1667.5</td>
      <td>9913.1</td>
      <td>438.4</td>
      <td>20819.0</td>
      <td>375.2</td>
      <td>644.8</td>
      <td>547.8</td>
      <td>8629.0</td>
      <td>1162.4</td>
      <td>1173.7</td>
      <td>1091.6</td>
    </tr>
    <tr>
      <th>H5</th>
      <th>258495800009</th>
      <th>4</th>
      <th>5</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.94621098</th>
      <th>PASS</th>
      <th>0.84679446</th>
      <th>0.92904553</th>
      <th>0.77413056</th>
      <th>0.707</th>
      <th>0.894</th>
      <th>0.708</th>
      <th>71</th>
      <th>F</th>
      <td>747.0</td>
      <td>8070.4</td>
      <td>124.0</td>
      <td>20423.7</td>
      <td>1426.6</td>
      <td>11345.0</td>
      <td>1954.5</td>
      <td>16168.9</td>
      <td>356.9</td>
      <td>446.4</td>
      <td>541.7</td>
      <td>8125.2</td>
      <td>1667.0</td>
      <td>1048.6</td>
      <td>1132.6</td>
    </tr>
    <tr>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th rowspan="5" valign="top">Example Adat Set002</th>
      <th rowspan="5" valign="top">2020-07-20</th>
      <th rowspan="5" valign="top">SG15214400</th>
      <th>A2</th>
      <th>258495800108</th>
      <th>3</th>
      <th>188</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.96699908</th>
      <th>PASS</th>
      <th>0.95993275</th>
      <th>1.08910138</th>
      <th>0.99491979</th>
      <th>0.566</th>
      <th>0.912</th>
      <th>0.719</th>
      <th>38</th>
      <th>F</th>
      <td>714.7</td>
      <td>19877.3</td>
      <td>114.5</td>
      <td>15151.9</td>
      <td>894.7</td>
      <td>17266.2</td>
      <td>682.8</td>
      <td>27419.4</td>
      <td>480.3</td>
      <td>705.1</td>
      <td>527.9</td>
      <td>6638.2</td>
      <td>3919.7</td>
      <td>1787.5</td>
      <td>1191.1</td>
    </tr>
    <tr>
      <th>A12</th>
      <th>258495800104</th>
      <th>2</th>
      <th>189</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.91482584</th>
      <th>PASS</th>
      <th>1.21880129</th>
      <th>1.01022697</th>
      <th>0.99244374</th>
      <th>0.918</th>
      <th>0.919</th>
      <th>0.926</th>
      <th>40</th>
      <th>F</th>
      <td>865.8</td>
      <td>25801.4</td>
      <td>123.6</td>
      <td>15711.6</td>
      <td>1308.4</td>
      <td>16598.3</td>
      <td>1369.2</td>
      <td>15153.5</td>
      <td>474.2</td>
      <td>655.0</td>
      <td>592.2</td>
      <td>8953.9</td>
      <td>2494.9</td>
      <td>2156.2</td>
      <td>1391.5</td>
    </tr>
    <tr>
      <th>A11</th>
      <th>258495800108</th>
      <th>5</th>
      <th>190</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.88282283</th>
      <th>PASS</th>
      <th>1.36699142</th>
      <th>1.16271427</th>
      <th>1.19673587</th>
      <th>0.927</th>
      <th>0.981</th>
      <th>0.964</th>
      <th>43</th>
      <th>M</th>
      <td>869.7</td>
      <td>13728.5</td>
      <td>140.9</td>
      <td>11437.3</td>
      <td>1353.5</td>
      <td>17996.2</td>
      <td>1344.2</td>
      <td>10575.3</td>
      <td>433.7</td>
      <td>439.8</td>
      <td>530.7</td>
      <td>6193.9</td>
      <td>2067.6</td>
      <td>2466.6</td>
      <td>1114.8</td>
    </tr>
    <tr>
      <th>A10</th>
      <th>258495800105</th>
      <th>5</th>
      <th>191</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.95792282</th>
      <th>PASS</th>
      <th>1.30590374</th>
      <th>0.98395166</th>
      <th>0.97460119</th>
      <th>0.835</th>
      <th>0.963</th>
      <th>0.944</th>
      <th>55</th>
      <th>M</th>
      <td>529.2</td>
      <td>13298.2</td>
      <td>161.7</td>
      <td>14210.8</td>
      <td>1026.0</td>
      <td>14549.0</td>
      <td>1466.1</td>
      <td>9683.8</td>
      <td>291.6</td>
      <td>435.8</td>
      <td>676.1</td>
      <td>9584.8</td>
      <td>1799.5</td>
      <td>1347.8</td>
      <td>1194.2</td>
    </tr>
    <tr>
      <th>A1</th>
      <th>258495800110</th>
      <th>5</th>
      <th>192</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.97384118</th>
      <th>PASS</th>
      <th>1.30710646</th>
      <th>0.93230123</th>
      <th>1.00804341</th>
      <th>0.793</th>
      <th>0.963</th>
      <th>0.933</th>
      <th>56</th>
      <th>F</th>
      <td>1934.4</td>
      <td>7567.8</td>
      <td>133.0</td>
      <td>13614.3</td>
      <td>1220.2</td>
      <td>16223.8</td>
      <td>1110.9</td>
      <td>7737.4</td>
      <td>364.2</td>
      <td>3407.0</td>
      <td>645.2</td>
      <td>7867.1</td>
      <td>1720.9</td>
      <td>1888.2</td>
      <td>1293.8</td>
    </tr>
  </tbody>
</table>
<p>192 rows × 15 columns</p>
</div>



<a name="lifting"></a>

### Lifting ADAT data between assay versions.

Adat data can be lifted from one SomaScan Assay version's RFU space to another SomaScan Assay version's RFU space. This is achieved by scaling SOMAmer reagent measurement columns using scale factors available at [menu.somalogic.com](https://menu.somalogic.com/) and built in to this tool in the `Adat.lift()` method.

The example Adat exists in SomaScan Version V4.0 assay space (also called 5K in some literature).  In this example we will lift to SomaScan V5.0 (11K) assay space.  It is important to know that only SOMAmer reagent measurements in both assay versions can be lifted. When lifting from a smaller to a larger plex (as demonstrated) the resulting `Adat` will remain in the smaller plex size.  When lifting from a larger to smaller plex size reagents that don't exist in the small plex size will be scaled by 1.0.  The end user might choose to redact the lifted `Adat` to the smaller plex to better merge data.

The tool will raise in error if the end user attempts to lift an `Adat` object to its current version or an unsupported assay version.


#### Assay version mapping:

SomaScan data can be referred to by the assay version i.e. 'V5.0' or by the plex size i.e. '11K'. The tool can use either 'V5.0' or '11K' interchangeably in it's input.  The mapping between these terms is shown in the table below:
<table>
    <tr>
        <th>SomaScan Assay Version</th>
        <th>SomaScan Plex</th>
        <th>SomaScan Menu Size</th>
    </tr>
    <tr>
        <td>V4</td>
        <td>5K</td>
        <td>5284</td>
    </tr>
    <tr>
        <td>V4.1</td>
        <td>7K</td>
        <td>7596</td>
    </tr>
    <tr>
        <td>V5.0</td>
        <td>11K</td>
        <td>11083</td>
    </tr>

</table>


[return to top](#toptoc)



```python
lifted_adat = adat.lift('V5.0')
```


```python
lifted_adat
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead tr th {
        text-align: left;
    }

    .dataframe thead tr:last-of-type th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>SeqId</th>
      <th>10000-28</th>
      <th>10001-7</th>
      <th>10003-15</th>
      <th>10006-25</th>
      <th>10008-43</th>
      <th>10011-65</th>
      <th>10012-5</th>
      <th>10013-34</th>
      <th>10014-31</th>
      <th>10015-119</th>
      <th>...</th>
      <th>9981-18</th>
      <th>9983-97</th>
      <th>9984-12</th>
      <th>9986-14</th>
      <th>9989-12</th>
      <th>9993-11</th>
      <th>9994-217</th>
      <th>9995-6</th>
      <th>9997-12</th>
      <th>9999-1</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>SeqIdVersion</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>...</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
      <th>3</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>SomaId</th>
      <th>SL019233</th>
      <th>SL002564</th>
      <th>SL019245</th>
      <th>SL019228</th>
      <th>SL019234</th>
      <th>SL019246</th>
      <th>SL014669</th>
      <th>SL025418</th>
      <th>SL007803</th>
      <th>SL014924</th>
      <th>...</th>
      <th>SL018293</th>
      <th>SL019202</th>
      <th>SL019205</th>
      <th>SL005356</th>
      <th>SL019194</th>
      <th>SL019212</th>
      <th>SL019217</th>
      <th>SL013164</th>
      <th>SL019215</th>
      <th>SL019231</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>TargetFullName</th>
      <th>Beta-crystallin B2</th>
      <th>RAF proto-oncogene serine/threonine-protein kinase</th>
      <th>Zinc finger protein 41</th>
      <th>ETS domain-containing protein Elk-1</th>
      <th>Guanylyl cyclase-activating protein 1</th>
      <th>Inositol polyphosphate 5-phosphatase OCRL-1</th>
      <th>SAM pointed domain-containing Ets transcription factor</th>
      <th>Fc_MOUSE</th>
      <th>Zinc finger protein SNAI2</th>
      <th>Voltage-gated potassium channel subunit beta-2</th>
      <th>...</th>
      <th>Protein FAM234B</th>
      <th>Inactive serine protease 35</th>
      <th>Protein YIPF6</th>
      <th>Neuropeptide W</th>
      <th>Leucine-rich repeat-containing protein 24</th>
      <th>Zinc finger protein 264</th>
      <th>Potassium-transporting ATPase subunit beta</th>
      <th>Deoxyuridine 5'-triphosphate nucleotidohydrolase, mitochondrial</th>
      <th>UBX domain-containing protein 4</th>
      <th>Interferon regulatory factor 6</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Target</th>
      <th>CRBB2</th>
      <th>c-Raf</th>
      <th>ZNF41</th>
      <th>ELK1</th>
      <th>GUC1A</th>
      <th>OCRL</th>
      <th>SPDEF</th>
      <th>Fc_MOUSE</th>
      <th>SLUG</th>
      <th>KCAB2</th>
      <th>...</th>
      <th>K1467</th>
      <th>PRS35</th>
      <th>YIPF6</th>
      <th>Neuropeptide W</th>
      <th>LRC24</th>
      <th>ZN264</th>
      <th>ATP4B</th>
      <th>DUT</th>
      <th>UBXN4</th>
      <th>IRF6</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>UniProt</th>
      <th>P43320</th>
      <th>P04049</th>
      <th>P51814</th>
      <th>P19419</th>
      <th>P43080</th>
      <th>Q01968</th>
      <th>O95238</th>
      <th>Q99LC4</th>
      <th>O43623</th>
      <th>Q13303</th>
      <th>...</th>
      <th>A2RU67</th>
      <th>Q8N3Z0</th>
      <th>Q96EC8</th>
      <th>Q8N729</th>
      <th>Q50LG9</th>
      <th>O43296</th>
      <th>P51164</th>
      <th>P33316</th>
      <th>Q92575</th>
      <th>O14896</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>EntrezGeneID</th>
      <th>1415</th>
      <th>5894</th>
      <th>7592</th>
      <th>2002</th>
      <th>2978</th>
      <th>4952</th>
      <th>25803</th>
      <th></th>
      <th>6591</th>
      <th>8514</th>
      <th>...</th>
      <th>57613</th>
      <th>167681</th>
      <th>286451</th>
      <th>283869</th>
      <th>441381</th>
      <th>9422</th>
      <th>496</th>
      <th>1854</th>
      <th>23190</th>
      <th>3664</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>EntrezGeneSymbol</th>
      <th>CRYBB2</th>
      <th>RAF1</th>
      <th>ZNF41</th>
      <th>ELK1</th>
      <th>GUCA1A</th>
      <th>OCRL</th>
      <th>SPDEF</th>
      <th></th>
      <th>SNAI2</th>
      <th>KCNAB2</th>
      <th>...</th>
      <th>KIAA1467</th>
      <th>PRSS35</th>
      <th>YIPF6</th>
      <th>NPW</th>
      <th>LRRC24</th>
      <th>ZNF264</th>
      <th>ATP4B</th>
      <th>DUT</th>
      <th>UBXN4</th>
      <th>IRF6</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Organism</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Mouse</th>
      <th>Human</th>
      <th>Human</th>
      <th>...</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
      <th>Human</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Units</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>...</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
      <th>RFU</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Type</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>...</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
      <th>Protein</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Dilution</th>
      <th>20</th>
      <th>20</th>
      <th>0.5</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>...</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
      <th>20</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>PlateScale_Reference</th>
      <th>687.4</th>
      <th>227.8</th>
      <th>126.9</th>
      <th>634.2</th>
      <th>585.0</th>
      <th>2807.1</th>
      <th>1623.3</th>
      <th>499.6</th>
      <th>857.2</th>
      <th>443.3</th>
      <th>...</th>
      <th>643.9</th>
      <th>430.0</th>
      <th>627.5</th>
      <th>3644.5</th>
      <th>449.4</th>
      <th>953.3</th>
      <th>1971.1</th>
      <th>1275.6</th>
      <th>4426.9</th>
      <th>851.9</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>CalReference</th>
      <th>687.4</th>
      <th>227.8</th>
      <th>126.9</th>
      <th>634.2</th>
      <th>585.0</th>
      <th>2807.1</th>
      <th>1623.3</th>
      <th>499.6</th>
      <th>857.2</th>
      <th>443.3</th>
      <th>...</th>
      <th>643.9</th>
      <th>430.0</th>
      <th>627.5</th>
      <th>3644.5</th>
      <th>449.4</th>
      <th>953.3</th>
      <th>1971.1</th>
      <th>1275.6</th>
      <th>4426.9</th>
      <th>851.9</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Cal_Example_Adat_Set001</th>
      <th>1.01252025</th>
      <th>1.01605709</th>
      <th>0.95056180</th>
      <th>0.99607350</th>
      <th>0.94051447</th>
      <th>1.05383489</th>
      <th>1.17290462</th>
      <th>1.07095391</th>
      <th>1.03464092</th>
      <th>1.07466667</th>
      <th>...</th>
      <th>0.98035932</th>
      <th>1.04878049</th>
      <th>1.03513692</th>
      <th>0.96341431</th>
      <th>1.01444695</th>
      <th>1.04551437</th>
      <th>0.98299422</th>
      <th>0.97426106</th>
      <th>0.96896272</th>
      <th>0.96042841</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>ColCheck</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>...</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
      <th>PASS</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>CalQcRatio_Example_Adat_Set001_170255</th>
      <th>1.008</th>
      <th>0.970</th>
      <th>1.046</th>
      <th>1.042</th>
      <th>1.036</th>
      <th>0.975</th>
      <th>1.010</th>
      <th>0.953</th>
      <th>0.978</th>
      <th>0.975</th>
      <th>...</th>
      <th>0.982</th>
      <th>0.949</th>
      <th>1.003</th>
      <th>0.938</th>
      <th>1.017</th>
      <th>0.998</th>
      <th>1.071</th>
      <th>0.985</th>
      <th>0.960</th>
      <th>0.974</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>QcReference_170255</th>
      <th>505.4</th>
      <th>223.9</th>
      <th>119.6</th>
      <th>667.2</th>
      <th>587.5</th>
      <th>2617.6</th>
      <th>1340.6</th>
      <th>443.0</th>
      <th>1289.4</th>
      <th>441.5</th>
      <th>...</th>
      <th>700.7</th>
      <th>393.2</th>
      <th>612.6</th>
      <th>3089.2</th>
      <th>455.1</th>
      <th>885.6</th>
      <th>1389.7</th>
      <th>950.9</th>
      <th>5560.7</th>
      <th>1033.6</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>Cal_Example_Adat_Set002</th>
      <th>1.01476233</th>
      <th>1.03686846</th>
      <th>1.15258856</th>
      <th>0.93581231</th>
      <th>0.96201283</th>
      <th>1.03133955</th>
      <th>1.21250373</th>
      <th>1.18192572</th>
      <th>0.98926717</th>
      <th>1.13173347</th>
      <th>...</th>
      <th>0.96075798</th>
      <th>1.15250603</th>
      <th>1.12013567</th>
      <th>1.08296437</th>
      <th>0.99314917</th>
      <th>1.08268030</th>
      <th>1.02784586</th>
      <th>0.97351752</th>
      <th>0.94828953</th>
      <th>0.92900763</th>
    </tr>
    <tr>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>CalQcRatio_Example_Adat_Set002_170255</th>
      <th>1.067</th>
      <th>1.007</th>
      <th>0.981</th>
      <th>1.026</th>
      <th>0.998</th>
      <th>1.013</th>
      <th>1.078</th>
      <th>0.996</th>
      <th>0.971</th>
      <th>0.941</th>
      <th>...</th>
      <th>0.982</th>
      <th>0.993</th>
      <th>0.990</th>
      <th>0.929</th>
      <th>0.978</th>
      <th>0.961</th>
      <th>1.022</th>
      <th>0.970</th>
      <th>1.027</th>
      <th>0.997</th>
    </tr>
    <tr>
      <th>PlateId</th>
      <th>PlateRunDate</th>
      <th>ScannerID</th>
      <th>PlatePosition</th>
      <th>SlideId</th>
      <th>Subarray</th>
      <th>SampleId</th>
      <th>SampleType</th>
      <th>PercentDilution</th>
      <th>SampleMatrix</th>
      <th>Barcode</th>
      <th>Barcode2d</th>
      <th>SampleName</th>
      <th>SampleNotes</th>
      <th>AliquotingNotes</th>
      <th>SampleDescription</th>
      <th>AssayNotes</th>
      <th>TimePoint</th>
      <th>ExtIdentifier</th>
      <th>SsfExtId</th>
      <th>SampleGroup</th>
      <th>SiteId</th>
      <th>TubeUniqueID</th>
      <th>CLI</th>
      <th>HybControlNormScale</th>
      <th>RowCheck</th>
      <th>NormScale_20</th>
      <th>NormScale_0_005</th>
      <th>NormScale_0_5</th>
      <th>ANMLFractionUsed_20</th>
      <th>ANMLFractionUsed_0_005</th>
      <th>ANMLFractionUsed_0_5</th>
      <th>Age</th>
      <th>Sex</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th rowspan="5" valign="top">Example Adat Set001</th>
      <th rowspan="5" valign="top">2020-06-18</th>
      <th rowspan="5" valign="top">SG15214400</th>
      <th>H9</th>
      <th>258495800012</th>
      <th>3</th>
      <th>1</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.98185998</th>
      <th>PASS</th>
      <th>1.03693580</th>
      <th>0.85701624</th>
      <th>0.77717491</th>
      <th>0.914</th>
      <th>0.869</th>
      <th>0.903</th>
      <th>76</th>
      <th>F</th>
      <td>386.0</td>
      <td>309.5</td>
      <td>97.6</td>
      <td>449.1</td>
      <td>396.6</td>
      <td>4965.9</td>
      <td>1106.7</td>
      <td>274.9</td>
      <td>786.3</td>
      <td>567.2</td>
      <td>...</td>
      <td>551.9</td>
      <td>352.5</td>
      <td>408.4</td>
      <td>3027.5</td>
      <td>538.8</td>
      <td>686.3</td>
      <td>5202.4</td>
      <td>2188.4</td>
      <td>12697.7</td>
      <td>966.5</td>
    </tr>
    <tr>
      <th>H8</th>
      <th>258495800004</th>
      <th>7</th>
      <th>2</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.96671829</th>
      <th>PASS</th>
      <th>0.96022505</th>
      <th>0.84858420</th>
      <th>0.85201953</th>
      <th>0.937</th>
      <th>0.956</th>
      <th>0.973</th>
      <th>55</th>
      <th>F</th>
      <td>384.3</td>
      <td>292.9</td>
      <td>99.1</td>
      <td>418.6</td>
      <td>382.6</td>
      <td>2149.6</td>
      <td>1307.8</td>
      <td>324.1</td>
      <td>779.4</td>
      <td>371.8</td>
      <td>...</td>
      <td>689.3</td>
      <td>358.2</td>
      <td>456.0</td>
      <td>5724.5</td>
      <td>470.3</td>
      <td>663.0</td>
      <td>1195.9</td>
      <td>2302.7</td>
      <td>13247.8</td>
      <td>824.2</td>
    </tr>
    <tr>
      <th>H7</th>
      <th>258495800010</th>
      <th>8</th>
      <th>3</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>1.00193072</th>
      <th>PASS</th>
      <th>0.98411617</th>
      <th>1.03270156</th>
      <th>0.91519153</th>
      <th>0.907</th>
      <th>0.919</th>
      <th>0.915</th>
      <th>47</th>
      <th>M</th>
      <td>336.6</td>
      <td>299.0</td>
      <td>2948.3</td>
      <td>420.1</td>
      <td>299.3</td>
      <td>2306.6</td>
      <td>1290.9</td>
      <td>348.6</td>
      <td>845.0</td>
      <td>416.8</td>
      <td>...</td>
      <td>547.0</td>
      <td>382.0</td>
      <td>503.9</td>
      <td>3380.7</td>
      <td>405.3</td>
      <td>647.6</td>
      <td>1552.4</td>
      <td>1183.2</td>
      <td>11072.1</td>
      <td>1145.8</td>
    </tr>
    <tr>
      <th>H6</th>
      <th>258495800003</th>
      <th>4</th>
      <th>4</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.94017961</th>
      <th>PASS</th>
      <th>1.07839878</th>
      <th>0.94626841</th>
      <th>0.91246731</th>
      <th>0.934</th>
      <th>0.919</th>
      <th>0.912</th>
      <th>37</th>
      <th>M</th>
      <td>358.5</td>
      <td>247.4</td>
      <td>109.9</td>
      <td>420.0</td>
      <td>331.7</td>
      <td>2261.4</td>
      <td>1184.1</td>
      <td>362.0</td>
      <td>4348.0</td>
      <td>374.6</td>
      <td>...</td>
      <td>561.9</td>
      <td>384.4</td>
      <td>477.7</td>
      <td>1361.8</td>
      <td>493.0</td>
      <td>643.5</td>
      <td>1005.3</td>
      <td>1399.4</td>
      <td>9082.4</td>
      <td>804.6</td>
    </tr>
    <tr>
      <th>H5</th>
      <th>258495800009</th>
      <th>4</th>
      <th>5</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.94621098</th>
      <th>PASS</th>
      <th>0.84679446</th>
      <th>0.92904553</th>
      <th>0.77413056</th>
      <th>0.707</th>
      <th>0.894</th>
      <th>0.708</th>
      <th>71</th>
      <th>F</th>
      <td>377.2</td>
      <td>709.3</td>
      <td>93.3</td>
      <td>589.3</td>
      <td>313.1</td>
      <td>1949.4</td>
      <td>990.0</td>
      <td>272.8</td>
      <td>787.7</td>
      <td>723.8</td>
      <td>...</td>
      <td>480.0</td>
      <td>343.0</td>
      <td>742.3</td>
      <td>4846.0</td>
      <td>487.7</td>
      <td>701.4</td>
      <td>1132.4</td>
      <td>9852.9</td>
      <td>38461.1</td>
      <td>2865.9</td>
    </tr>
    <tr>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th rowspan="5" valign="top">Example Adat Set002</th>
      <th rowspan="5" valign="top">2020-07-20</th>
      <th rowspan="5" valign="top">SG15214400</th>
      <th>A2</th>
      <th>258495800108</th>
      <th>3</th>
      <th>188</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.96699908</th>
      <th>PASS</th>
      <th>0.95993275</th>
      <th>1.08910138</th>
      <th>0.99491979</th>
      <th>0.566</th>
      <th>0.912</th>
      <th>0.719</th>
      <th>38</th>
      <th>F</th>
      <td>393.3</td>
      <td>954.0</td>
      <td>124.2</td>
      <td>719.8</td>
      <td>1284.4</td>
      <td>1312.0</td>
      <td>750.7</td>
      <td>312.1</td>
      <td>727.7</td>
      <td>829.2</td>
      <td>...</td>
      <td>454.3</td>
      <td>301.8</td>
      <td>531.0</td>
      <td>1658.5</td>
      <td>541.8</td>
      <td>861.5</td>
      <td>1352.3</td>
      <td>11604.6</td>
      <td>45580.6</td>
      <td>3687.1</td>
    </tr>
    <tr>
      <th>A12</th>
      <th>258495800104</th>
      <th>2</th>
      <th>189</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.91482584</th>
      <th>PASS</th>
      <th>1.21880129</th>
      <th>1.01022697</th>
      <th>0.99244374</th>
      <th>0.918</th>
      <th>0.919</th>
      <th>0.926</th>
      <th>40</th>
      <th>F</th>
      <td>337.4</td>
      <td>281.6</td>
      <td>82.5</td>
      <td>625.5</td>
      <td>26153.5</td>
      <td>1856.4</td>
      <td>1004.8</td>
      <td>297.4</td>
      <td>734.0</td>
      <td>388.3</td>
      <td>...</td>
      <td>636.7</td>
      <td>292.7</td>
      <td>410.7</td>
      <td>9236.8</td>
      <td>487.6</td>
      <td>629.3</td>
      <td>1910.9</td>
      <td>1855.0</td>
      <td>9778.6</td>
      <td>1004.4</td>
    </tr>
    <tr>
      <th>A11</th>
      <th>258495800108</th>
      <th>5</th>
      <th>190</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.88282283</th>
      <th>PASS</th>
      <th>1.36699142</th>
      <th>1.16271427</th>
      <th>1.19673587</th>
      <th>0.927</th>
      <th>0.981</th>
      <th>0.964</th>
      <th>43</th>
      <th>M</th>
      <td>372.9</td>
      <td>270.8</td>
      <td>204.2</td>
      <td>472.6</td>
      <td>446.1</td>
      <td>1733.8</td>
      <td>1067.7</td>
      <td>354.3</td>
      <td>745.7</td>
      <td>410.7</td>
      <td>...</td>
      <td>566.0</td>
      <td>364.5</td>
      <td>448.2</td>
      <td>2597.7</td>
      <td>515.6</td>
      <td>621.4</td>
      <td>1113.3</td>
      <td>1302.7</td>
      <td>8766.2</td>
      <td>770.8</td>
    </tr>
    <tr>
      <th>A10</th>
      <th>258495800105</th>
      <th>5</th>
      <th>191</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.95792282</th>
      <th>PASS</th>
      <th>1.30590374</th>
      <th>0.98395166</th>
      <th>0.97460119</th>
      <th>0.835</th>
      <th>0.963</th>
      <th>0.944</th>
      <th>55</th>
      <th>M</th>
      <td>320.4</td>
      <td>319.1</td>
      <td>105.9</td>
      <td>527.1</td>
      <td>370.8</td>
      <td>1701.9</td>
      <td>756.9</td>
      <td>266.4</td>
      <td>618.4</td>
      <td>453.9</td>
      <td>...</td>
      <td>536.3</td>
      <td>309.1</td>
      <td>434.0</td>
      <td>5167.2</td>
      <td>522.8</td>
      <td>588.2</td>
      <td>891.1</td>
      <td>2466.6</td>
      <td>15455.9</td>
      <td>1190.4</td>
    </tr>
    <tr>
      <th>A1</th>
      <th>258495800110</th>
      <th>5</th>
      <th>192</th>
      <th>Sample</th>
      <th>20</th>
      <th>Plasma-PPT</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th>0.97384118</th>
      <th>PASS</th>
      <th>1.30710646</th>
      <th>0.93230123</th>
      <th>1.00804341</th>
      <th>0.793</th>
      <th>0.963</th>
      <th>0.933</th>
      <th>56</th>
      <th>F</th>
      <td>370.3</td>
      <td>288.1</td>
      <td>187.2</td>
      <td>469.9</td>
      <td>438.5</td>
      <td>1777.9</td>
      <td>787.3</td>
      <td>249.4</td>
      <td>930.8</td>
      <td>423.7</td>
      <td>...</td>
      <td>601.9</td>
      <td>285.9</td>
      <td>467.0</td>
      <td>2564.2</td>
      <td>590.0</td>
      <td>673.2</td>
      <td>1036.7</td>
      <td>2142.1</td>
      <td>7950.7</td>
      <td>722.8</td>
    </tr>
  </tbody>
</table>
<p>192 rows × 5284 columns</p>
</div>




```python
# because some common documentation refers to plex size instead of assay version the tool also supports lifing by naming plex size.
lifted_adat = adat.lift('11K')
```


```python
# Observing the Lin's CCC of the lifting scale factors.
from somadata.data import getSomaScanLiftCCC

# the method returns a pandas dataframe containing the available lift Lins's CCC values:
ccc = getSomaScanLiftCCC()

ccc
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Serum Lin's CCC v5.0 11K to v4.1 7K</th>
      <th>Plasma Lin's CCC v5.0 11K to v4.1 7K</th>
      <th>Serum Lin's CCC v5.0 11K to v4.0 5K</th>
      <th>Plasma Lin's CCC v5.0 11K to v4.0 5K</th>
      <th>Serum Lin's CCC v4.1 7K to v4.0 5K</th>
      <th>Plasma Lin's CCC v4.1 7K to v4.0 5K</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>10000-28</th>
      <td>0.977</td>
      <td>0.982</td>
      <td>0.970</td>
      <td>0.966</td>
      <td>0.967</td>
      <td>0.963</td>
    </tr>
    <tr>
      <th>10001-7</th>
      <td>0.857</td>
      <td>0.961</td>
      <td>0.819</td>
      <td>0.860</td>
      <td>0.875</td>
      <td>0.875</td>
    </tr>
    <tr>
      <th>10003-15</th>
      <td>0.759</td>
      <td>0.787</td>
      <td>0.761</td>
      <td>0.674</td>
      <td>0.774</td>
      <td>0.668</td>
    </tr>
    <tr>
      <th>10006-25</th>
      <td>0.937</td>
      <td>0.927</td>
      <td>0.903</td>
      <td>0.864</td>
      <td>0.937</td>
      <td>0.877</td>
    </tr>
    <tr>
      <th>10008-43</th>
      <td>0.951</td>
      <td>0.939</td>
      <td>0.915</td>
      <td>0.879</td>
      <td>0.925</td>
      <td>0.908</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>9993-11</th>
      <td>0.823</td>
      <td>0.855</td>
      <td>0.704</td>
      <td>0.753</td>
      <td>0.714</td>
      <td>0.711</td>
    </tr>
    <tr>
      <th>9994-217</th>
      <td>0.492</td>
      <td>0.964</td>
      <td>0.502</td>
      <td>0.767</td>
      <td>0.809</td>
      <td>0.778</td>
    </tr>
    <tr>
      <th>9995-6</th>
      <td>0.975</td>
      <td>0.976</td>
      <td>0.965</td>
      <td>0.916</td>
      <td>0.983</td>
      <td>0.922</td>
    </tr>
    <tr>
      <th>9997-12</th>
      <td>0.877</td>
      <td>0.955</td>
      <td>0.857</td>
      <td>0.892</td>
      <td>0.926</td>
      <td>0.885</td>
    </tr>
    <tr>
      <th>9999-1</th>
      <td>0.909</td>
      <td>0.962</td>
      <td>0.870</td>
      <td>0.883</td>
      <td>0.944</td>
      <td>0.898</td>
    </tr>
  </tbody>
</table>
<p>11083 rows × 6 columns</p>
</div>



### Lin's CCC Between Lifted and Assay Space Native Data
The tool allows you to display Lin's concordance correlation coefficient ([Lin 1989](https://pubmed.ncbi.nlm.nih.gov/2720055/)) derived during the calculation of the lifting scale factors.  This metric allows you to see how well lifted data is expected to correlate with date collected originally in the target assay data signal space.  A Lin's CCC close to 1.0 indicates strong correlation indicating the signal would be highly concordant with the lifted value if the sample data were collected in the target assay version space.



```python
# your exact transformation's Lin's CCC can be selected by filtering the column that contains your matrix and versions
# Lin's CCC are symmetrical v5.0 -> v4.0 == v4.0 -> v5.0.
ccc["Plasma Lin's CCC v5.0 11K to v4.0 5K"]
```




    10000-28    0.966
    10001-7     0.860
    10003-15    0.674
    10006-25    0.864
    10008-43    0.879
                ...
    9993-11     0.753
    9994-217    0.767
    9995-6      0.916
    9997-12     0.892
    9999-1      0.883
    Name: Plasma Lin's CCC v5.0 11K to v4.0 5K, Length: 11083, dtype: float64



<a name="writing"></a>

### Writing an `ADAT` file


In order to store or share analysis the user may need to write out an ADAT file.  This utility supports writing to the file system.


[return to top](#toptoc)


```python
adat.to_adat('/tmp/out_file.adat')
```

<a name="example"></a>

# Typical Analyses
Although it is beyond the scope of the `SomaData` package, below are 3
sample analyses that typical users/clients would perform on SomaLogic data.
They are not intended to be a definitive guide in statistical
analysis and existing packages do exist in the `Python` universe that perform parts
or extensions of these techniques. Many variations of the workflows below
exist, however the framework highlights how one could perform standard
preliminary analyses on SomaLogic data for:
 - Two-group differential expression (t-test)
 - Binary classification (logistic regression)
 - Linear regression

[return to top](#toptoc)

## Compare Groups (M/F) via t-test


```python
from somadata.data.example_data import example_data # Example ADAT included with SomaData
from scipy.stats import ttest_ind
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from io import StringIO
```

### Display the shape of the adat (rows, columns)


```python
example_data.shape
```




    (192, 5284)



### Describe the sample types within the adat and display their counts


```python
Counter(example_data.index.get_level_values('SampleType'))
```




    Counter({'Sample': 170, 'Calibrator': 10, 'Buffer': 6, 'QC': 6})



### Prepare the adat for analysis


```python
filtered_transformed_data = (
    example_data
        .exclude_on_meta(axis=0, name='Sex', values=[''])            # rm NAs if present
        .pick_on_meta(axis=0, name='SampleType', values=['Sample'])  # rm control samples
        .apply(np.log10)                                             # log10-transform
)

clean_data = (
    filtered_transformed_data
        .insert_keyed_meta(                                          # map Sex -> 0/1
            axis=0,
            key_meta_name='Sex',
            inserted_meta_name='Group',
            values_dict={'M': 1, 'F': 0}
        )
        .apply(lambda x: x - x.mean(), axis=0)                       # center features
        .apply(lambda x: x / x.std(), axis=0)                        # scale features
)
```

### Display the grouping counts


```python
print(clean_data.index.to_frame()['Sex'].value_counts())
print(clean_data.index.to_frame()['Group'].value_counts())
```

    Sex
    F    85
    M    85
    Name: count, dtype: int64
    Group
    0    85
    1    85
    Name: count, dtype: int64


### Split the adat based on `Group` and perform t-test across all aptamers


```python
tt_g0 = clean_data.pick_on_meta(axis=0, name='Group', values=[0])
tt_g1 = clean_data.pick_on_meta(axis=0, name='Group', values=[1])

tt_res = ttest_ind(tt_g0, tt_g1)
t_tests = list(zip(clean_data.columns.get_level_values('TargetFullName'), tt_res.pvalue))
```

### Sort the results and display the 12 aptamers with the most significant p-values


```python
t_tests_sorted = sorted(t_tests, key=lambda x: x[1])
tt_top_12_analytes = [name for name, p_value in t_tests_sorted[:12]]
tt_top_12_analytes
```




    ['Prostate-specific antigen',
     'Pregnancy zone protein',
     'Kunitz-type protease inhibitor 3',
     'Follicle stimulating hormone',
     'Ectonucleotide pyrophosphatase/phosphodiesterase family member 2',
     'Beta-defensin 104',
     'Luteinizing hormone',
     'Cysteine-rich secretory protein 2',
     'Human Chorionic Gonadotropin',
     'Serum amyloid P-component',
     'SLIT and NTRK-like protein 4',
     'Neurotrimin']



### Plot the `Group` log(RFU) for each aptamer


```python
tt_df= (
    filtered_transformed_data
        .pick_meta(axis=1, names=['TargetFullName'])
        .pick_on_meta(axis=1, name='TargetFullName', values=tt_top_12_analytes)[tt_top_12_analytes]
        .reset_index()
)

tt_melted_df = pd.melt(tt_df, value_vars=tt_top_12_analytes, id_vars='Sex', value_name='log10(RFU)')

tt_p = sns.catplot(
    x='Sex',
    y='log10(RFU)',
    col='TargetFullName',
    data=tt_melted_df,
    kind='box',
    col_wrap=3,
    sharey=False
)
tt_p.set_titles(row_template='{row_name}', col_template='{col_name}')
plt.show()
```



![png](README_files/output_71_0.png)



## Logistic Regression (Predict Sex)


```python
# Import the libraries that we need for this analysis
from sklearn.model_selection import train_test_split
from sklearn import metrics
from scipy.stats import pearsonr
import statsmodels.api as sm
from IPython.display import HTML
```

### Prepare the data for LogisticRegression


```python
# Wrangle `clean_data` into a simpler form
logr_x_df = (
    clean_data
        .pick_meta(axis=1, names=['SeqId', 'TargetFullName'])
        .reset_index(drop=True)
)
logr_y_df = (
    clean_data.index.get_level_values('Group')
)

# Split the dataset into train and test, holding back 25 samples for testing
logr_x_train, logr_x_test, logr_y_train, logr_y_test = train_test_split(logr_x_df, logr_y_df, test_size=25, random_state=0)
```

### Perform univariate logistic regression for each aptamer



```python
logr_apt_perf = []
for seq_info in logr_x_train:
    x = sm.add_constant(logr_x_train[seq_info]) # Need to add the intercept term since sm.GLM does not automatically do it
    mod = sm.GLM(logr_y_train, x, family=sm.families.Binomial())
    res = mod.fit()
    logr_apt_perf.append(res.summary2().tables[1].loc[[seq_info]])
```

### Wrangle the GLM results of each aptamer into a dataframe and sort them by p-value



```python
logr_df = pd.concat(logr_apt_perf).reset_index()
logr_df['SeqId'] = [x[0] for x in logr_df['index']]
logr_df['TargetFullName'] = [x[1] for x in logr_df['index']]
logr_df = logr_df.drop('index', axis=1)
logr_df = logr_df[['SeqId', 'TargetFullName', 'Coef.', 'Std.Err.', 'z', 'P>|z|', '[0.025', '0.975]']].set_index('SeqId')
logr_df_sorted = logr_df.sort_values('P>|z|')
HTML(logr_df_sorted.head(20).to_html()) # Need to use HTML here to display nicely for this README
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>TargetFullName</th>
      <th>Coef.</th>
      <th>Std.Err.</th>
      <th>z</th>
      <th>P&gt;|z|</th>
      <th>[0.025</th>
      <th>0.975]</th>
    </tr>
    <tr>
      <th>SeqId</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>6580-29</th>
      <td>Pregnancy zone protein</td>
      <td>-3.079818</td>
      <td>0.489558</td>
      <td>-6.291020</td>
      <td>3.153866e-10</td>
      <td>-4.039334</td>
      <td>-2.120302</td>
    </tr>
    <tr>
      <th>5763-67</th>
      <td>Beta-defensin 104</td>
      <td>2.974778</td>
      <td>0.478400</td>
      <td>6.218181</td>
      <td>5.029509e-10</td>
      <td>2.037131</td>
      <td>3.912425</td>
    </tr>
    <tr>
      <th>3032-11</th>
      <td>Follicle stimulating hormone</td>
      <td>-1.505718</td>
      <td>0.250398</td>
      <td>-6.013292</td>
      <td>1.817935e-09</td>
      <td>-1.996490</td>
      <td>-1.014946</td>
    </tr>
    <tr>
      <th>7926-13</th>
      <td>Kunitz-type protease inhibitor 3</td>
      <td>2.887475</td>
      <td>0.482526</td>
      <td>5.984087</td>
      <td>2.176067e-09</td>
      <td>1.941742</td>
      <td>3.833208</td>
    </tr>
    <tr>
      <th>16892-23</th>
      <td>Ectonucleotide pyrophosphatase/phosphodiesterase family member 2</td>
      <td>-2.335113</td>
      <td>0.396641</td>
      <td>-5.887216</td>
      <td>3.927542e-09</td>
      <td>-3.112516</td>
      <td>-1.557710</td>
    </tr>
    <tr>
      <th>9282-12</th>
      <td>Cysteine-rich secretory protein 2</td>
      <td>1.768026</td>
      <td>0.309050</td>
      <td>5.720837</td>
      <td>1.060006e-08</td>
      <td>1.162299</td>
      <td>2.373754</td>
    </tr>
    <tr>
      <th>2953-31</th>
      <td>Luteinizing hormone</td>
      <td>-1.319728</td>
      <td>0.240323</td>
      <td>-5.491466</td>
      <td>3.986115e-08</td>
      <td>-1.790753</td>
      <td>-0.848702</td>
    </tr>
    <tr>
      <th>4914-10</th>
      <td>Human Chorionic Gonadotropin</td>
      <td>-1.244551</td>
      <td>0.229781</td>
      <td>-5.416240</td>
      <td>6.086534e-08</td>
      <td>-1.694914</td>
      <td>-0.794188</td>
    </tr>
    <tr>
      <th>8468-19</th>
      <td>Prostate-specific antigen</td>
      <td>5.841131</td>
      <td>1.113030</td>
      <td>5.247953</td>
      <td>1.537986e-07</td>
      <td>3.659632</td>
      <td>8.022630</td>
    </tr>
    <tr>
      <th>2474-54</th>
      <td>Serum amyloid P-component</td>
      <td>1.434929</td>
      <td>0.279218</td>
      <td>5.139108</td>
      <td>2.760458e-07</td>
      <td>0.887673</td>
      <td>1.982185</td>
    </tr>
    <tr>
      <th>8428-102</th>
      <td>Neurotrimin</td>
      <td>-1.264317</td>
      <td>0.246142</td>
      <td>-5.136543</td>
      <td>2.798380e-07</td>
      <td>-1.746745</td>
      <td>-0.781888</td>
    </tr>
    <tr>
      <th>9002-36</th>
      <td>Serpin A11</td>
      <td>-1.087385</td>
      <td>0.219035</td>
      <td>-4.964434</td>
      <td>6.890169e-07</td>
      <td>-1.516685</td>
      <td>-0.658084</td>
    </tr>
    <tr>
      <th>3066-12</th>
      <td>Galectin-3</td>
      <td>-1.005615</td>
      <td>0.206735</td>
      <td>-4.864276</td>
      <td>1.148764e-06</td>
      <td>-1.410808</td>
      <td>-0.600423</td>
    </tr>
    <tr>
      <th>5116-62</th>
      <td>Roundabout homolog 2</td>
      <td>-1.291594</td>
      <td>0.270447</td>
      <td>-4.775767</td>
      <td>1.790237e-06</td>
      <td>-1.821661</td>
      <td>-0.761527</td>
    </tr>
    <tr>
      <th>7139-14</th>
      <td>SLIT and NTRK-like protein 4</td>
      <td>1.018520</td>
      <td>0.218625</td>
      <td>4.658761</td>
      <td>3.181183e-06</td>
      <td>0.590023</td>
      <td>1.447016</td>
    </tr>
    <tr>
      <th>8484-24</th>
      <td>Leptin</td>
      <td>-0.991585</td>
      <td>0.219260</td>
      <td>-4.522415</td>
      <td>6.113800e-06</td>
      <td>-1.421326</td>
      <td>-0.561843</td>
    </tr>
    <tr>
      <th>5934-1</th>
      <td>Ferritin</td>
      <td>1.012300</td>
      <td>0.227525</td>
      <td>4.449188</td>
      <td>8.619536e-06</td>
      <td>0.566360</td>
      <td>1.458240</td>
    </tr>
    <tr>
      <th>15324-58</th>
      <td>Ferritin light chain</td>
      <td>1.002813</td>
      <td>0.226429</td>
      <td>4.428822</td>
      <td>9.474919e-06</td>
      <td>0.559021</td>
      <td>1.446606</td>
    </tr>
    <tr>
      <th>4234-8</th>
      <td>Interleukin-1 receptor-like 1</td>
      <td>1.134058</td>
      <td>0.258632</td>
      <td>4.384831</td>
      <td>1.160761e-05</td>
      <td>0.627149</td>
      <td>1.640968</td>
    </tr>
    <tr>
      <th>2696-87</th>
      <td>Persephin</td>
      <td>1.412833</td>
      <td>0.323348</td>
      <td>4.369389</td>
      <td>1.245947e-05</td>
      <td>0.779083</td>
      <td>2.046584</td>
    </tr>
  </tbody>
</table>



### Fit model


```python
logr_top_analytes = [(index, row['TargetFullName']) for index, row in logr_df_sorted.head(5).iterrows()] # Select the top 5 aptamers based on p-value
x = sm.add_constant(logr_x_train[logr_top_analytes])
logr_mod = sm.GLM(logr_y_train, x, family=sm.families.Binomial())
logr_res = logr_mod.fit()
logr_res.summary()
```




<table class="simpletable">
<caption>Generalized Linear Model Regression Results</caption>
<tr>
  <th>Dep. Variable:</th>           <td>y</td>        <th>  No. Observations:  </th>  <td>   145</td>
</tr>
<tr>
  <th>Model:</th>                  <td>GLM</td>       <th>  Df Residuals:      </th>  <td>   139</td>
</tr>
<tr>
  <th>Model Family:</th>        <td>Binomial</td>     <th>  Df Model:          </th>  <td>     5</td>
</tr>
<tr>
  <th>Link Function:</th>         <td>Logit</td>      <th>  Scale:             </th> <td>  1.0000</td>
</tr>
<tr>
  <th>Method:</th>                <td>IRLS</td>       <th>  Log-Likelihood:    </th> <td> -8.4167</td>
</tr>
<tr>
  <th>Date:</th>            <td>Fri, 01 Mar 2024</td> <th>  Deviance:          </th> <td>  16.833</td>
</tr>
<tr>
  <th>Time:</th>                <td>13:19:34</td>     <th>  Pearson chi2:      </th>  <td>  17.8</td>
</tr>
<tr>
  <th>No. Iterations:</th>         <td>10</td>        <th>  Pseudo R-squ. (CS):</th>  <td>0.7186</td>
</tr>
<tr>
  <th>Covariance Type:</th>     <td>nonrobust</td>    <th>                     </th>     <td> </td>
</tr>
</table>
<table class="simpletable">
<tr>
                                          <td></td>                                            <th>coef</th>     <th>std err</th>      <th>z</th>      <th>P>|z|</th>  <th>[0.025</th>    <th>0.975]</th>
</tr>
<tr>
  <th>const</th>                                                                            <td>    1.6106</td> <td>    1.178</td> <td>    1.367</td> <td> 0.172</td> <td>   -0.699</td> <td>    3.920</td>
</tr>
<tr>
  <th>('6580-29', 'Pregnancy zone protein')</th>                                            <td>   -7.0008</td> <td>    3.112</td> <td>   -2.250</td> <td> 0.024</td> <td>  -13.099</td> <td>   -0.902</td>
</tr>
<tr>
  <th>('5763-67', 'Beta-defensin 104')</th>                                                 <td>    2.7821</td> <td>    1.255</td> <td>    2.217</td> <td> 0.027</td> <td>    0.322</td> <td>    5.242</td>
</tr>
<tr>
  <th>('3032-11', 'Follicle stimulating hormone')</th>                                      <td>   -1.1722</td> <td>    0.818</td> <td>   -1.432</td> <td> 0.152</td> <td>   -2.776</td> <td>    0.432</td>
</tr>
<tr>
  <th>('7926-13', 'Kunitz-type protease inhibitor 3')</th>                                  <td>    2.2901</td> <td>    1.053</td> <td>    2.174</td> <td> 0.030</td> <td>    0.226</td> <td>    4.354</td>
</tr>
<tr>
  <th>('16892-23', 'Ectonucleotide pyrophosphatase/phosphodiesterase family member 2')</th> <td>   -3.6045</td> <td>    1.498</td> <td>   -2.407</td> <td> 0.016</td> <td>   -6.540</td> <td>   -0.669</td>
</tr>
</table>




```python
# Create confusion matrix
x = sm.add_constant(logr_x_test[logr_top_analytes])
logr_predictions = [1 if val > 0.5 else 0 for val in logr_res.predict(x)]
cm = metrics.confusion_matrix(logr_y_test.values, logr_predictions)
```


```python
# Print out performance metrics via Pandas
tp = cm[1, 1]
tn = cm[0, 0]
fp = cm[0, 1]
fn = cm[1, 0]
logr_perf_df = pd.DataFrame.from_records({
    'Sensitivity': tp / (tp + fn),
    'Specificity': tn / (tn + fp),
    'Accuracy': (tp + tn) / sum(sum(cm)),
    'PPV': tp / (tp + fp),
    'NPV': tn / (tn + fn)
}, index=['Value'])
HTML(logr_perf_df.to_html())
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Accuracy</th>
      <th>NPV</th>
      <th>PPV</th>
      <th>Sensitivity</th>
      <th>Specificity</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Value</th>
      <td>1.0</td>
      <td>1.0</td>
      <td>1.0</td>
      <td>1.0</td>
      <td>1.0</td>
    </tr>
  </tbody>
</table>




```python
# Display the confusion matrix
plt.figure(figsize=(3,3))
sns.heatmap(cm, annot=True, fmt=".3f", linewidths=.5, square=True, cmap='Blues')
plt.ylabel('Actual label')
plt.xlabel('Predicted label')
all_sample_title = 'Accuracy Score: {0}'.format(100 * logr_perf_df['Accuracy'].values[0])
plt.title(all_sample_title)
plt.show()
```



![png](README_files/output_84_0.png)



## Linear Regression (Predict Age)
We use the same `clean_data` as the logistic regression analysis above.

### Wrangle data


```python
# Wrangle `clean_data` into a simpler form
linr_x_df = (
    clean_data
        .pick_meta(axis=1, names=['SeqId', 'TargetFullName'])
        .reset_index(drop=True)
)
linr_y = (
    [float(age) for age in clean_data.index.get_level_values('Age')]
)

# Split the dataset into train and test, holding back 25 samples for testing
linr_x_train, linr_x_test, linr_y_train, linr_y_test = train_test_split(linr_x_df, linr_y, test_size=25, random_state=5)
```

### Perform univariate linear regression for each aptamer



```python
linr_apt_perf = []
for seq_info in linr_x_df:
    x = sm.add_constant(linr_x_train[seq_info])
    mod = sm.OLS(linr_y_train, x)
    res = mod.fit()
    linr_apt_perf.append(res.summary2().tables[1].loc[[seq_info]])
```

### Wrangle the GLM results of each aptamer into a dataframe and sort them by p-value



```python
linr_res_df = pd.concat(linr_apt_perf).reset_index()
linr_res_df['SeqId'] = [x[0] for x in linr_res_df['index']]
linr_res_df['TargetFullName'] = [x[1] for x in linr_res_df['index']]
linr_res_df = linr_res_df.drop('index', axis=1)
linr_res_df = linr_res_df[['SeqId', 'TargetFullName', 'Coef.', 'Std.Err.', 't', 'P>|t|', '[0.025', '0.975]']].set_index('SeqId')
linr_sorted_res_df = linr_res_df.sort_values('P>|t|')
HTML(linr_sorted_res_df.head(20).to_html())
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>TargetFullName</th>
      <th>Coef.</th>
      <th>Std.Err.</th>
      <th>t</th>
      <th>P&gt;|t|</th>
      <th>[0.025</th>
      <th>0.975]</th>
    </tr>
    <tr>
      <th>SeqId</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>3045-72</th>
      <td>Pleiotrophin</td>
      <td>6.713339</td>
      <td>0.865578</td>
      <td>7.755906</td>
      <td>1.506400e-12</td>
      <td>5.002359</td>
      <td>8.424320</td>
    </tr>
    <tr>
      <th>4374-45</th>
      <td>Growth/differentiation factor 15</td>
      <td>6.766537</td>
      <td>0.902926</td>
      <td>7.494011</td>
      <td>6.377086e-12</td>
      <td>4.981730</td>
      <td>8.551343</td>
    </tr>
    <tr>
      <th>3024-18</th>
      <td>Alpha-2-antiplasmin</td>
      <td>-6.258739</td>
      <td>0.895850</td>
      <td>-6.986373</td>
      <td>9.854830e-11</td>
      <td>-8.029558</td>
      <td>-4.487920</td>
    </tr>
    <tr>
      <th>6392-7</th>
      <td>WNT1-inducible-signaling pathway protein 2</td>
      <td>6.206203</td>
      <td>0.895426</td>
      <td>6.931007</td>
      <td>1.321588e-10</td>
      <td>4.436222</td>
      <td>7.976185</td>
    </tr>
    <tr>
      <th>8480-29</th>
      <td>EGF-containing fibulin-like extracellular matrix protein 1</td>
      <td>6.179473</td>
      <td>0.900370</td>
      <td>6.863260</td>
      <td>1.889770e-10</td>
      <td>4.399719</td>
      <td>7.959227</td>
    </tr>
    <tr>
      <th>15640-54</th>
      <td>Transgelin</td>
      <td>6.159769</td>
      <td>0.905043</td>
      <td>6.806048</td>
      <td>2.552783e-10</td>
      <td>4.370777</td>
      <td>7.948761</td>
    </tr>
    <tr>
      <th>15533-97</th>
      <td>Macrophage scavenger receptor types I and II</td>
      <td>5.986741</td>
      <td>0.907615</td>
      <td>6.596127</td>
      <td>7.616175e-10</td>
      <td>4.192666</td>
      <td>7.780815</td>
    </tr>
    <tr>
      <th>15386-7</th>
      <td>Fatty acid-binding protein, adipocyte</td>
      <td>6.130562</td>
      <td>0.931954</td>
      <td>6.578182</td>
      <td>8.355679e-10</td>
      <td>4.288376</td>
      <td>7.972748</td>
    </tr>
    <tr>
      <th>16818-200</th>
      <td>CUB domain-containing protein 1</td>
      <td>5.919909</td>
      <td>0.902842</td>
      <td>6.556970</td>
      <td>9.321408e-10</td>
      <td>4.135268</td>
      <td>7.704550</td>
    </tr>
    <tr>
      <th>4496-60</th>
      <td>Macrophage metalloelastase</td>
      <td>6.149946</td>
      <td>0.940133</td>
      <td>6.541570</td>
      <td>1.009072e-09</td>
      <td>4.291592</td>
      <td>8.008299</td>
    </tr>
    <tr>
      <th>3362-61</th>
      <td>Chordin-like protein 1</td>
      <td>5.765444</td>
      <td>0.913703</td>
      <td>6.309975</td>
      <td>3.287540e-09</td>
      <td>3.959334</td>
      <td>7.571554</td>
    </tr>
    <tr>
      <th>4541-49</th>
      <td>Cell adhesion molecule-related/down-regulated by oncogenes</td>
      <td>-5.703166</td>
      <td>0.906248</td>
      <td>-6.293164</td>
      <td>3.578780e-09</td>
      <td>-7.494540</td>
      <td>-3.911793</td>
    </tr>
    <tr>
      <th>3600-2</th>
      <td>Chitotriosidase-1</td>
      <td>5.831590</td>
      <td>0.951184</td>
      <td>6.130871</td>
      <td>8.071212e-09</td>
      <td>3.951391</td>
      <td>7.711789</td>
    </tr>
    <tr>
      <th>2609-59</th>
      <td>Cystatin-C</td>
      <td>5.577894</td>
      <td>0.934072</td>
      <td>5.971588</td>
      <td>1.773159e-08</td>
      <td>3.731521</td>
      <td>7.424267</td>
    </tr>
    <tr>
      <th>3234-23</th>
      <td>Coiled-coil domain-containing protein 80</td>
      <td>5.647487</td>
      <td>0.948795</td>
      <td>5.952270</td>
      <td>1.949244e-08</td>
      <td>3.772010</td>
      <td>7.522963</td>
    </tr>
    <tr>
      <th>14133-93</th>
      <td>Interleukin-1 receptor type 2</td>
      <td>-5.489368</td>
      <td>0.926319</td>
      <td>-5.926004</td>
      <td>2.216438e-08</td>
      <td>-7.320415</td>
      <td>-3.658321</td>
    </tr>
    <tr>
      <th>19601-15</th>
      <td>Ankyrin repeat and SOCS box protein 9</td>
      <td>5.412074</td>
      <td>0.930313</td>
      <td>5.817474</td>
      <td>3.755863e-08</td>
      <td>3.573131</td>
      <td>7.251018</td>
    </tr>
    <tr>
      <th>9793-145</th>
      <td>Immunoglobulin superfamily DCC subclass member 4</td>
      <td>-5.292703</td>
      <td>0.911239</td>
      <td>-5.808247</td>
      <td>3.927116e-08</td>
      <td>-7.093942</td>
      <td>-3.491463</td>
    </tr>
    <tr>
      <th>2677-1</th>
      <td>Epidermal growth factor receptor</td>
      <td>-5.341396</td>
      <td>0.919656</td>
      <td>-5.808039</td>
      <td>3.931061e-08</td>
      <td>-7.159272</td>
      <td>-3.523520</td>
    </tr>
    <tr>
      <th>4968-50</th>
      <td>Macrophage-capping protein</td>
      <td>5.345710</td>
      <td>0.926458</td>
      <td>5.770050</td>
      <td>4.721157e-08</td>
      <td>3.514387</td>
      <td>7.177033</td>
    </tr>
  </tbody>
</table>



### Feed top 8 SOMAmers into statsmodels OLS regression


```python
linr_top_analytes = [(index, row['TargetFullName']) for index, row in linr_sorted_res_df.head(8).iterrows()]
x = sm.add_constant(linr_x_train[linr_top_analytes])
mod = sm.OLS(linr_y_train, x).fit()
mod.summary()
```




<table class="simpletable">
<caption>OLS Regression Results</caption>
<tr>
  <th>Dep. Variable:</th>            <td>y</td>        <th>  R-squared:         </th> <td>   0.501</td>
</tr>
<tr>
  <th>Model:</th>                   <td>OLS</td>       <th>  Adj. R-squared:    </th> <td>   0.471</td>
</tr>
<tr>
  <th>Method:</th>             <td>Least Squares</td>  <th>  F-statistic:       </th> <td>   17.05</td>
</tr>
<tr>
  <th>Date:</th>             <td>Fri, 01 Mar 2024</td> <th>  Prob (F-statistic):</th> <td>2.29e-17</td>
</tr>
<tr>
  <th>Time:</th>                 <td>13:20:02</td>     <th>  Log-Likelihood:    </th> <td> -522.29</td>
</tr>
<tr>
  <th>No. Observations:</th>      <td>   145</td>      <th>  AIC:               </th> <td>   1063.</td>
</tr>
<tr>
  <th>Df Residuals:</th>          <td>   136</td>      <th>  BIC:               </th> <td>   1089.</td>
</tr>
<tr>
  <th>Df Model:</th>              <td>     8</td>      <th>                     </th>     <td> </td>
</tr>
<tr>
  <th>Covariance Type:</th>      <td>nonrobust</td>    <th>                     </th>     <td> </td>
</tr>
</table>
<table class="simpletable">
<tr>
                                      <td></td>                                         <th>coef</th>     <th>std err</th>      <th>t</th>      <th>P>|t|</th>  <th>[0.025</th>    <th>0.975]</th>
</tr>
<tr>
  <th>const</th>                                                                     <td>   55.5436</td> <td>    0.765</td> <td>   72.602</td> <td> 0.000</td> <td>   54.031</td> <td>   57.057</td>
</tr>
<tr>
  <th>('3045-72', 'Pleiotrophin')</th>                                               <td>    1.6913</td> <td>    1.197</td> <td>    1.413</td> <td> 0.160</td> <td>   -0.676</td> <td>    4.059</td>
</tr>
<tr>
  <th>('4374-45', 'Growth/differentiation factor 15')</th>                           <td>    1.2404</td> <td>    1.258</td> <td>    0.986</td> <td> 0.326</td> <td>   -1.247</td> <td>    3.728</td>
</tr>
<tr>
  <th>('3024-18', 'Alpha-2-antiplasmin')</th>                                        <td>   -2.5113</td> <td>    0.910</td> <td>   -2.758</td> <td> 0.007</td> <td>   -4.312</td> <td>   -0.711</td>
</tr>
<tr>
  <th>('6392-7', 'WNT1-inducible-signaling pathway protein 2')</th>                  <td>    1.5143</td> <td>    0.997</td> <td>    1.519</td> <td> 0.131</td> <td>   -0.457</td> <td>    3.486</td>
</tr>
<tr>
  <th>('8480-29', 'EGF-containing fibulin-like extracellular matrix protein 1')</th> <td>    2.1363</td> <td>    0.972</td> <td>    2.197</td> <td> 0.030</td> <td>    0.214</td> <td>    4.059</td>
</tr>
<tr>
  <th>('15640-54', 'Transgelin')</th>                                                <td>    1.2006</td> <td>    1.010</td> <td>    1.189</td> <td> 0.237</td> <td>   -0.796</td> <td>    3.198</td>
</tr>
<tr>
  <th>('15533-97', 'Macrophage scavenger receptor types I and II')</th>              <td>    0.8792</td> <td>    1.223</td> <td>    0.719</td> <td> 0.474</td> <td>   -1.540</td> <td>    3.298</td>
</tr>
<tr>
  <th>('15386-7', 'Fatty acid-binding protein, adipocyte')</th>                      <td>    1.1453</td> <td>    1.180</td> <td>    0.971</td> <td> 0.333</td> <td>   -1.188</td> <td>    3.479</td>
</tr>
</table>
<table class="simpletable">
<tr>
  <th>Omnibus:</th>       <td> 2.712</td> <th>  Durbin-Watson:     </th> <td>   2.042</td>
</tr>
<tr>
  <th>Prob(Omnibus):</th> <td> 0.258</td> <th>  Jarque-Bera (JB):  </th> <td>   2.501</td>
</tr>
<tr>
  <th>Skew:</th>          <td>-0.322</td> <th>  Prob(JB):          </th> <td>   0.286</td>
</tr>
<tr>
  <th>Kurtosis:</th>      <td> 3.008</td> <th>  Cond. No.          </th> <td>    4.53</td>
</tr>
</table><br/><br/>Notes:<br/>[1] Standard Errors assume that the covariance matrix of the errors is correctly specified.



### Compute predictions on test set


```python
x = sm.add_constant(linr_x_test[linr_top_analytes])
linr_predictions = mod.predict(x)
linr_pred_df = pd.DataFrame({
    'Actual Age': linr_y_test,
    'Predicted Age': linr_predictions
})

linr_pred_df['Pred Error'] = linr_pred_df['Predicted Age'] - linr_pred_df['Actual Age']
```

### Compute model performance


```python
# Lin's Concordance Correl. Coef.
# Accounts for location + scale shifts
def linCCC(x, y):
    if len(x) != len(y):
        raise Exception('Arrays are not the same length!')
    a = 2 * pearsonr(x, y)[0] * np.std(x, ddof=1) * np.std(y, ddof=1)
    b = np.var(x, ddof=1) + np.var(y, ddof=1) + (np.mean(x) - np.mean(y))**2
    return a / b

n = linr_x_test.shape[0]
p = len(linr_top_analytes)

# Regression metrics
linr_metrics_df = pd.DataFrame({
    'rss': linr_pred_df['Pred Error'].apply(lambda x: x**2).sum(), # residual sum of squares
    'tss': sum((linr_pred_df['Actual Age'] - linr_pred_df['Actual Age'].mean()) ** 2), # total sum of squares
    'R2': pearsonr(linr_pred_df['Actual Age'], linr_pred_df['Predicted Age'])[0] ** 2, # R-squared Pearson approx.
    'MAE': np.mean(np.abs(linr_pred_df['Pred Error'])), # Mean absolute error
    'RMSE': np.sqrt(np.mean(linr_pred_df['Pred Error'] ** 2)), # Root mean squared error
    'CCC': linCCC(linr_predictions, linr_y_test) # Lins concordance correlation coefficient
}, index=['Value'])

linr_metrics_df['rsq'] = 1 - (linr_metrics_df['rss'] / linr_metrics_df['tss']) # R-squared
linr_metrics_df['rsqadj'] = max(0, 1 - (1 - linr_metrics_df['rsq'][0]) * (n - 1) / (n - p - 1)), # Adjusted R-squared

HTML(linr_metrics_df.to_html())
```




<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>rss</th>
      <th>tss</th>
      <th>R2</th>
      <th>MAE</th>
      <th>RMSE</th>
      <th>CCC</th>
      <th>rsq</th>
      <th>rsqadj</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Value</th>
      <td>989.768231</td>
      <td>2771.84</td>
      <td>0.674484</td>
      <td>5.214434</td>
      <td>6.292116</td>
      <td>0.752326</td>
      <td>0.64292</td>
      <td>0.46438</td>
    </tr>
  </tbody>
</table>



### Visualize performance via concordance plot of predicted and actual values


```python
f, ax = plt.subplots(1, figsize=(5, 5), dpi=150)
plot_range = [linr_pred_df[['Actual Age', 'Predicted Age']].min().min() * 0.95, linr_pred_df[['Actual Age', 'Predicted Age']].max().max() * 1.05]
ax.plot(plot_range, plot_range, c='g')
ax.scatter(linr_pred_df['Actual Age'], linr_pred_df['Predicted Age'], alpha=0.5)
ax.set(
    xlim=plot_range,
    xlabel='Actual Age',
    ylim=plot_range,
    ylabel='Predicted Age',
    title='Concordance in Predicted vs. Actual Age'
)
plt.show()
```



![png](README_files/output_98_0.png)



### Closing Remarks

  - Many variants of above possible.
  - Goal to provide general framework to handle SomaLogic data.
  - Not definitive guide in statistical theory, etc.

-----

## MIT LICENSE

  - See [LICENSE](LICENSE)
  - The MIT
        License:
      - <https://choosealicense.com/licenses/mit/>
      - [https://tldrlegal.com/license/mit-license/](https://tldrlegal.com/license/mit-license)

-----


[return to top](#toptoc)


```python

```
