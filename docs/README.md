# Sphinx Documentation

The documentation is built with [Sphinx](http://sphinx-doc.org/index.html). See their documentation for more details.

## Installation

Pre-requisites:

```
pip install sphinx sphinx-rtd-theme
```

## Refresh API Docs

From docs directory:

```
sphinx-apidoc -o source/pydss ../pydss
```

## Build HTML Docs

From docs directory:

```
make clean
make html
```

## Push to GitHub Pages

```
make github
```
