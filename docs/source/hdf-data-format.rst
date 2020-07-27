Data Format
###########
This page describes how PyDSS exports data in an HDF file. Each PyDSS project
creates ``<project-path>/store.h5`` to store exported data for all scenarios.

Layout
******
Each scenario's data is stored under ``Exports/<scenario-name>``.

Data stored for an element property for individual elements is stored in an HDF dataset ::

    Exports/<scenario-name>/ElementProperties/<element-class>/<property>

This dataset includes columns for each individual element.

Data stored for an element property across elements of a given type is stored in an HDF dataset ::

    Exports/<scenario-name>/SummedElementProperties/<element-class>/<property>

PyDSS stores metadata for each dataset in HDF attributes as well as other datasets.

Attributes per dataset:

- ``type``: Describes what type of data is stored.

  - ``per_time_point``:  Data is stored at every time point; indices are shared.
  - ``value``:  Only a single value is stored for each element.
  - ``filtered``:  Data is stored after being filtered; indices are stored for each element.
  - ``metadata``:  Metadata for another dataset.
  - ``time_step``:  Data are time indices, tied to ``filtered``.

- ``length``: Number of rows of valid data written to the dataset.

Metadata datasets per dataset:


