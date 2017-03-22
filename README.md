# pygwyfile
Pygwyfile is a small Python library that provides interface for reading and writing of [Gwyddion](http://gwyddion.net/) GWY files. For operations with GWY files [Libgwyfile](http://libgwyfile.sourceforge.net/) C library is used.

## Installation
Pygwyfile depends on [CFFI](http://cffi.readthedocs.io/en/latest/) to interact with [Libgwyfile](http://libgwyfile.sourceforge.net/) C library and [numpy](http://www.numpy.org/) to represent Gwy Datafields, Gwy GraphCurveModels etc. as numpy arrays.

For CFFI installation see [Installation and Status](http://cffi.readthedocs.io/en/latest/installation.html) section of CFFI documentation.

For example, in Debian system:

1. Install C compiler, libffi library etc. 

```
sudo apt-get install build-essential libssl-dev libffi-dev python-dev
```
2. Install numpy package. See [numpy documentation](https://docs.scipy.org/doc/numpy-1.12.0/user/install.html) for details.

3. Install pygwyfile (Installation in virtual environment is recommended).

```
pip install https://github.com/dmitry-streltsov/pygwyfile
```
## Usage
Here is a simple example that shows how to load a gwy file and save it to another file.

```python
from pygwyfile.gwycontainer import read_gwyfile

container = read_gwyfile("testdatafiles/samples.gwy")

container.to_gwyfile("testdatafiles/test.gwy")
```

## Status
It is initial public release with basic functionality. Gwyddion gwy files serialization and deserialization should work. There are following classes for pythonic representation of various Gwyfile Objects: GwyContainer, GwyChannel, GwyDataField, GwyGraphModel, GwyGraphCurve, GwyPointSelection, GwyPointerSelection, GwyLineSelection, GwyRectangleSelection, GwyEllipseSelection. The project is in active development stage now.
