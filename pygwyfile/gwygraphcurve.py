""" Pythonic representation of gwyddion GwyGraphCurveModel objects.

    Classes:
        GwyGraphCurve: pythonic representation of GwyGraphCurveModel gwy object
"""
import numpy as np

from pygwyfile._libgwyfile import ffi, lib
from pygwyfile.gwyfile import GwyfileErrorCMsg


class GwyGraphCurve:
    """Class for GwyGraphCurveModel representation

    Attributes:
        data (2D numpy array, float64):
           abscissa and ordinate data of the same length

        meta (python dictionary): curve metadata

    Methods:
        from_gwy(gwyobject): Create GwyGraphCurve instance from
                             <GwyGraphCurveModel*> object
        to_gwy(): Create  GWY file <GwyGraphCurveModel*> object
                  from GwyGraphCurve instance

    """

    def __init__(self, data, meta=None):
        """
        Args:
            data (2D numpy array, float64):
                abscissa and ordinate data of the same size
            meta (python dictionary):

                Possible items:
                    'ndata' (int): number of points in the curve
                    'description' (string): curve label
                    'type' (int): GwyGraphCurveType
                    'point_type' (int): GwyGraphPointType
                    'line_style' (int): GdkLineStyle
                    'point_size' (int): Point size
                    'line_size' (int):  Line width
                    'color.red' (float): Red component from the range [0, 1]
                    'color.green' (float): Green component from the range
                                                                    [0, 1]
                    'color.blue' (float): Blue component from the range
                                                                  [0, 1]

        """
        self.meta = {}

        if not meta:
            meta = {}

        if 'ndata' in meta:
            if data.shape == (2, meta['ndata']):
                self.data = data
                self.meta['ndata'] = meta['ndata']
            else:
                raise ValueError("data.shape is not equal (2, meta['ndata'])")
        else:
            if len(data.shape) == 2 and data.shape[0] == 2:
                self.data = data
                self.meta['ndata'] = data.shape[1]
            else:
                raise ValueError("data.shape is not equal (2, ndata)")

        if 'description' in meta:
            self.meta['description'] = meta['description']
        else:
            self.meta['description'] = ''

        if 'type' in meta:
            self.meta['type'] = meta['type']
        else:
            self.meta['type'] = 1  # points

        if 'point_type' in meta:
            self.meta['point_type'] = meta['point_type']
        else:
            self.meta['point_type'] = 2  # circle

        if 'line_style' in meta:
            self.meta['line_style'] = meta['line_style']
        else:
            self.meta['line_style'] = 0  # lines are drawn solid

        if 'point_size' in meta:
            self.meta['point_size'] = meta['point_size']
        else:
            self.meta['point_size'] = 1

        if 'line_size' in meta:
            self.meta['line_size'] = meta['line_size']
        else:
            self.meta['line_size'] = 1

        if 'color.red' in meta:
            self.meta['color.red'] = meta['color.red']
        else:
            self.meta['color.red'] = 0.

        if 'color.green' in meta:
            self.meta['color.green'] = meta['color.green']
        else:
            self.meta['color.green'] = 0.

        if 'color.blue' in meta:
            self.meta['color.blue'] = meta['color.blue']
        else:
            self.meta['color.blue'] = 0.

    @classmethod
    def from_gwy(cls, gwycurve):
        """ Create GwyGraphCurve instance from
            <GwyGraphCurveModel*> object
        """
        meta = cls._get_meta(gwycurve)
        npoints = meta['ndata']
        data = cls._get_data(gwycurve, npoints)
        return GwyGraphCurve(data=data, meta=meta)

    @staticmethod
    def _get_meta(gwycurve):
        """
        Get metadata from <GwyGraphCurveModel*> object

        Args:
            curve (GwyfileObject*):
                GwyGraphCurveModel object

        Returns:
            metadata (dict):
                GwyGraphCurveModel metadaat

        """
        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        ndatap = ffi.new("int32_t*")
        descriptionp = ffi.new("char**")
        typep = ffi.new("int32_t*")
        point_typep = ffi.new("int32_t*")
        line_stylep = ffi.new("int32_t*")
        point_sizep = ffi.new("int32_t*")
        line_sizep = ffi.new("int32_t*")
        color_redp = ffi.new("double*")
        color_greenp = ffi.new("double*")
        color_bluep = ffi.new("double*")

        metadata = {}

        if not lib.gwyfile_object_graphcurvemodel_get(gwycurve,
                                                      errorp,
                                                      ffi.new('char[]',
                                                              b'ndata'),
                                                      ndatap,
                                                      ffi.new('char[]',
                                                              b'description'),
                                                      descriptionp,
                                                      ffi.new('char[]',
                                                              b'type'),
                                                      typep,
                                                      ffi.new('char[]',
                                                              b'point_type'),
                                                      point_typep,
                                                      ffi.new('char[]',
                                                              b'line_style'),
                                                      line_stylep,
                                                      ffi.new('char[]',
                                                              b'point_size'),
                                                      point_sizep,
                                                      ffi.new('char[]',
                                                              b'line_size'),
                                                      line_sizep,
                                                      ffi.new('char[]',
                                                              b'color.red'),
                                                      color_redp,
                                                      ffi.new('char[]',
                                                              b'color.green'),
                                                      color_greenp,
                                                      ffi.new('char[]',
                                                              b'color.blue'),
                                                      color_bluep,
                                                      ffi.NULL):
            raise GwyfileErrorCMsg(errorp[0].message)
        else:
            metadata['ndata'] = ndatap[0]

            if descriptionp[0]:
                description = ffi.string(descriptionp[0]).decode('utf-8')
                metadata['description'] = description
            else:
                metadata['description'] = ''

            metadata['type'] = typep[0]
            metadata['point_type'] = point_typep[0]
            metadata['line_style'] = line_stylep[0]
            metadata['point_size'] = point_sizep[0]
            metadata['line_size'] = line_sizep[0]
            metadata['color.red'] = color_redp[0]
            metadata['color.green'] = color_greenp[0]
            metadata['color.blue'] = color_bluep[0]
        return metadata

    @staticmethod
    def _get_data(gwycurve, npoints):
        """
        Get data from <GwyGraphCurveModel*> object

        Args:
            curve (GwyfileObject*):
                <GwyGraphCurveModel*> object from Libgwyfile
            npoints (int):
                number of points in the curve

        Returns:
            data (np.float64 numpy array):
                2D numpy array with shape (2, npoints)
                with xdata (data[0]) and ydata (data[1])
        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)

        xdata = ffi.new("double[]", npoints)
        xdatap = ffi.new("double**", xdata)

        ydata = ffi.new("double[]", npoints)
        ydatap = ffi.new("double**", ydata)

        if not lib.gwyfile_object_graphcurvemodel_get(gwycurve,
                                                      errorp,
                                                      ffi.new('char[]',
                                                              b'xdata'),
                                                      xdatap,
                                                      ffi.new('char[]',
                                                              b'ydata'),
                                                      ydatap,
                                                      ffi.NULL):
            raise GwyfileErrorCMsg(errorp[0].message)
        else:
            xdata_buf = ffi.buffer(xdatap[0], npoints * ffi.sizeof(xdata))
            xdata_array = np.frombuffer(xdata_buf, dtype=np.float64,
                                        count=npoints)
            ydata_buf = ffi.buffer(ydatap[0], npoints * ffi.sizeof(ydata))
            ydata_array = np.frombuffer(ydata_buf, dtype=np.float64,
                                        count=npoints)
            data_array = np.vstack((xdata_array, ydata_array))
            return data_array

    def to_gwy(self):
        """ Get a new GWY file GwyGraphCurveModel object

        Returns:
            <GwyfileObject*>: GwyGraphCurveModel object

        """
        args = []

        ndata = ffi.cast("int32_t", self.meta['ndata'])
        args.append(ndata)

        xdata = self.data[0]
        xdatap = ffi.cast("double*", xdata.ctypes.data)
        args.append(ffi.new("char[]", b"xdata"))
        args.append(xdatap)

        ydata = self.data[1]
        ydatap = ffi.cast("double*", ydata.ctypes.data)
        args.append(ffi.new("char[]", b"ydata"))
        args.append(ydatap)

        if self.meta['description'] is not None:
            args.append(ffi.new("char[]", b'description'))
            args.append(ffi.new("char[]",
                                self.meta['description'].encode('utf-8')))

        if self.meta['type'] is not None:
            args.append(ffi.new("char[]", b'type'))
            args.append(ffi.cast("int32_t", self.meta['type']))

        if self.meta['point_type'] is not None:
            args.append(ffi.new("char[]", b'point_type'))
            args.append(ffi.cast("int32_t", self.meta['point_type']))

        if self.meta['line_style'] is not None:
            args.append(ffi.new("char[]", b'line_style'))
            args.append(ffi.cast("int32_t", self.meta['line_style']))

        if self.meta['point_size'] is not None:
            args.append(ffi.new("char[]", b'point_size'))
            args.append(ffi.cast("int32_t", self.meta['point_size']))

        if self.meta['line_size'] is not None:
            args.append(ffi.new("char[]", b'line_size'))
            args.append(ffi.cast("int32_t", self.meta['line_size']))

        if self.meta['color.red'] is not None:
            args.append(ffi.new("char[]", b'color.red'))
            args.append(ffi.cast("double", self.meta['color.red']))

        if self.meta['color.green'] is not None:
            args.append(ffi.new("char[]", b'color.green'))
            args.append(ffi.cast("double", self.meta['color.green']))

        if self.meta['color.blue'] is not None:
            args.append(ffi.new("char[]", b'color.blue'))
            args.append(ffi.cast("double", self.meta['color.blue']))

        args.append(ffi.NULL)

        gwycurve = lib.gwyfile_object_new_graphcurvemodel(*args)
        return gwycurve

    def __repr__(self):
        return "<{} instance at {}. Description: {}>".format(
            self.__class__.__name__,
            hex(id(self)),
            self.meta['description'])
