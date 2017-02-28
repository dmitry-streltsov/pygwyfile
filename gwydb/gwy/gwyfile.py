"""
Wrapper for GwyfileObject from Libgwyfile C library
"""
import os.path
from abc import ABC, abstractmethod

import numpy as np

from gwydb.gwy._libgwyfile import ffi, lib


class GwyfileError(Exception):
    """
    Exceptions during operations with gwy files
    """

    pass


class GwyfileErrorCMsg(GwyfileError):
    """
    Class for libgwyfile C library exceptions
    """

    def __init__(self, c_error_msg):
        if c_error_msg:
            error_msg = ffi.string(c_error_msg).decode('utf-8')
            super(GwyfileErrorCMsg, self).__init__(error_msg)
        else:
            super(GwyfileErrorCMsg, self).__init__()


class Gwyfile:
    """Wrapper class for GwyfileObject from Libgwyfile C library

    Attributes:
        c_gwyfile (cdata  GwyfileObject*): gwyfile object from
                                           Libgwyfile C library
    """

    def __init__(self, c_gwyfile):
        """
        Args:
            c_gwyfile (cdata GwyfileOjbect*): gwyfile object from
                                              Libgwyfile C library

        The top-level object of the c_gwyfile must be 'GwyContainer'
        """

        if not c_gwyfile:
            raise GwyfileError("c_gwyfile object is empty")

        c_toplevel_object_name = lib.gwyfile_object_name(c_gwyfile)
        if c_toplevel_object_name:
            toplevel_object_name = ffi.string(c_toplevel_object_name)
        else:
            error_msg = 'The top-level object of c_gwyfile is empty'
            raise GwyfileError(error_msg)

        if not toplevel_object_name == b'GwyContainer':
            error_msg = 'The top-level object of c_gwyfile is not ' \
                        ' a GwyContainer'
            raise GwyfileError(error_msg)

        self.c_gwyfile = c_gwyfile

    def check_gwyobject(self, key):
        """Check the presence of the object

        Args:
            key(str): object key

        Returns:
            True if object exists, otherwise False

        """

        item = lib.gwyfile_object_get(self.c_gwyfile, key.encode('utf-8'))
        if not item:
            return False
        else:
            return True

    def get_gwyobject(self, key):
        """Get the object value with a name "key"

        Args:
            key (str): Name of the key, e.g. "/0/data"

        Returns:
            item_object (cdata GwyfileObject*): The value of the object

        """

        item = lib.gwyfile_object_get(self.c_gwyfile, key.encode('utf-8'))
        if not item:
            raise GwyfileError("Cannot find the item \"{}\"".format(key))
        item_object = lib.gwyfile_item_get_object(item)
        if not item_object:
            raise GwyfileError(
                "Cannot find the object value of the item \"{}\"".format(key))
        return item_object


class GwySelection(ABC):
    """Base class for GwySelection objects

    Attributes:
        _get_sel_func (C func):
            Libgwyfile C function to get selection.
            Must be redefined in subclass
        _npoints (int):
            number of points in one selection (e.g. 1 for point sel.)
            Must be redefined in subclass
        data: list
              list of selections

    """
    _get_sel_func = None
    _npoints = 1
    data = []

    @abstractmethod
    def __init__(self, points):
        """
        Args:
            points: list or tuple of points
                    each point is a tuple of coordinates (x, y)
        """
        pass

    @classmethod
    @abstractmethod
    def from_gwy(cls, gwysel):
        """
        Get points from <GwyfileObject*>

        Args:
            gwysel (GwyfileObject*):
                GwySelection object from Libgwyfile
                e.g. GwySelectionPoint object for point selection

        Returns:
            [(x1, y1), ..., (xN, yN)]: list of tuples with point coordinates
            or None :                  if there are no point selections

        """

        nsel = cls._get_selection_nsel(gwysel)
        points = cls._get_selection_points(gwysel, nsel)
        return points

    @classmethod
    def _get_selection_nsel(cls, gwysel):
        """Get number of selections from the object

        Args:
            gwysel (GwyfileObject*):
                GwySelection object from Libgwyfile
                e.g. GwySelectionPoint object for point selection

        Returns:
            nsel (int):
                number of selections of this type in gwysel
        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        nselp = ffi.new("int32_t*")

        if cls._get_sel_func(gwysel,
                             errorp,
                             ffi.new("char[]", b'nsel'),
                             nselp,
                             ffi.NULL):
            nsel = nselp[0]
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

        return nsel

    @classmethod
    def _get_selection_points(cls, gwysel, nsel):
        """Get all points of selection from the gwysel object

        Args:
            gwysel (GwyfileObject*):
                GwySelection object from Libgwyfile
                e.g. GwySelectionPoint object for point selection
            nsel (int):
                number of selections of this type in gwysel

        Returns:
            [(x1, y1), ..., (xN, yN)]: list of tuples with point coordinates
                                       or None if there are no selections

        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)

        if nsel == 0:
            return None
        else:
            data = ffi.new("double[]", 2 * nsel * cls._npoints)
            datap = ffi.new("double**", data)

        if cls._get_sel_func(gwysel,
                             errorp,
                             ffi.new("char[]", b'data'),
                             datap,
                             ffi.NULL):
            data = datap[0]
            points = [(data[i * 2], data[i * 2 + 1])
                      for i in range(nsel * cls._npoints)]
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

        return points

    @staticmethod
    def _combine_points_in_pair(points):
        """ Combine list of points in list of pairs
            [(x1, y1), (x2, y2), ...] -> [((x1, y1), (x2, y2))...]
        """

        pairs = list(zip(tuple(points[::2]),
                         tuple(points[1::2])))
        return pairs

    def __repr__(self):
        return "<{} instance at {}. Selections: {}>".format(
            self.__class__.__name__,
            hex(id(self)),
            len(self.data))


class GwyPointSelections(GwySelection):
    """Class for point selections

    Attributes:
        data: non-empty list of points [(x1, y1), ...]
    """

    _npoints = 1  # number of points in one point selection
    _get_sel_func = lib.gwyfile_object_selectionpoint_get

    def __init__(self, points):
        """
        Args:
            points: list or tuple of points (x, y)
        """
        if points:
            self.data = list(points)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(cls, gwysel):
        """
        Get point selections from <GwySelectionPoint*> object

        Args:
            gwysel:
                <GwySelectionPoint*> object from Libgwyfile library

        Returns:
            GwyPointSelections instance initialized by the point selections
            or None if number of points is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            return GwyPointSelections(points)
        else:
            return None


class GwyPointerSelections(GwySelection):
    """Class for pointer selections

    Attributes:
        data: list of points [(x1, y1), ...]
    """

    _npoints = 1  # number of points in one pointer selection
    _get_sel_func = lib.gwyfile_object_selectionpoint_get

    def __init__(self, points):
        if points:
            self.data = list(points)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(cls, gwysel):
        """
        Get point selections from <GwySelectionPointer*> object

        Args:
            gwysel:
                <GwySelectionPointer*> object from Libgwyfile library

        Returns:
            GwyPointerSelections instance initialized by the point selections
            or None if number of points is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            return GwyPointerSelections(points)
        else:
            return None


class GwyLineSelections(GwySelection):
    """Class for line selections

    Attributes:
        data: list of point pairs [((x1, y1), (x2, y2))...]
              (two points for one line selection)
    """

    _npoints = 2  # number of points in one line selection
    _get_sel_func = lib.gwyfile_object_selectionline_get

    def __init__(self, point_pairs):
        if point_pairs:
            self.data = list(point_pairs)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(self, gwysel):
        """
        Get line selections from <GwySelectionLine*> object

        Args:
            gwysel:
                <GwySelectionLine*> object from Libgwyfile library

        Returns:
            GwyLineSelections instance initialized by the point selections
            or None if number of points is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            point_pairs = super()._combine_points_in_pair(points)
            return GwyLineSelections(point_pairs)
        else:
            return None


class GwyRectangleSelections(GwySelection):
    """Class for rectange selections

    Attributes:
        data: list of point pairs [((x1, y1), (x2, y2))...]
              (two points for one rectangle selection)
    """

    _npoints = 2  # number of points in one rectangle selection
    _get_sel_func = lib.gwyfile_object_selectionrectangle_get

    def __init__(self, point_pairs):
        if point_pairs:
            self.data = list(point_pairs)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(self, gwysel):
        """
        Get rectangle selections from <GwySelectionRectangle*> object

        Args:
            gwysel:
                <GwySelectionRectangle*> object from Libgwyfile library

        Returns:
            GwyRectangleSelections instance initialized by the rectangle sel.
            or None if number of points is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            point_pairs = super()._combine_points_in_pair(points)
            return GwyRectangleSelections(point_pairs)
        else:
            return None


class GwyEllipseSelections(GwySelection):
    """Class for ellipse selections

    Attributes:
        data: list of point pairs [((x1, y1), (x2, y2))...]
              (two points for one ellipse selection)
    """

    _npoints = 2  # number of points in one ellipse selection
    _get_sel_func = lib.gwyfile_object_selectionellipse_get

    def __init__(self, point_pairs):
        if point_pairs:
            self.data = list(point_pairs)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(self, gwysel):
        """
        Get ellipse selections from <GwySelectionEllipse*> object

        Args:
            gwysel:
                <GwySelectionEllipse*> object from Libgwyfile library

        Returns:
            GwyEllipseSelections instance initialized by the ellipse selections
            or None if number of points is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            point_pairs = super()._combine_points_in_pair(points)
            return GwyEllipseSelections(point_pairs)
        else:
            return None


class GwyDataField:
    """Class for GwyDataField representation

    Attributes:
        data (2D numpy array, float64):
            data from the datafield

        meta (python dictionary):
            datafield metadata

    """

    def __init__(self, data, meta=None):
        """
        Args:
            data (2D numpy array, float64):
                data for the datafield
            meta (python dictionary):

                Possible items:

                   'xres' (int):    Horizontal dimension in pixels
                   'yres' (int):    Vertical dimension in pixels
                   =if defined xres, yres must match shape of the data array=

                   'xreal' (float): Horizontal size in physical units
                                    Default value is 1. if not defined.
                   'yreal' (float): Vertical size in physical units
                                    Default value is 1. if not defined.
                   'xoff' (double): Horizontal offset of the top-left corner
                                    in physical units.
                                    Default value is 0. if not defined
                   'yoff' (double): Vertical offset of the top-left corner
                                    in physical units.
                                    Default value is 0. if not defined
                   'si_unit_xy' (str): Physical units of lateral dimensions,
                                       base SI units, e.g. "m"
                                       Default value is '' if not defined
                   'si_unit_z' (str): Physical unit of vertical dimension,
                                      base SI unit, e.g. "m"
                                      Default value is '' if not defined

                Unknown additional items are simply ignored

        """
        if not meta:
            meta = {}

        self.meta = {}

        if 'xres' in meta and 'yres' in meta:
            if data.shape == (meta['xres'], meta['yres']):
                self.data = data
                self.meta['xres'] = meta['xres']
                self.meta['yres'] = meta['yres']
            else:
                raise ValueError("data.shape is not equal "
                                 "meta['xres'], meta['yres']")
        else:
            self.meta['xres'], self.meta['yres'] = data.shape
            self.data = data

        if 'xreal' in meta:
            self.meta['xreal'] = meta['xreal']
        else:
            self.meta['xreal'] = 1.

        if 'yreal' in meta:
            self.meta['yreal'] = meta['yreal']
        else:
            self.meta['yreal'] = 1.

        if 'xoff' in meta:
            self.meta['xoff'] = meta['xoff']
        else:
            self.meta['xoff'] = 0.

        if 'yoff' in meta:
            self.meta['yoff'] = meta['yoff']
        else:
            self.meta['yoff'] = 0.

        if 'si_unit_xy' in meta:
            self.meta['si_unit_xy'] = meta['si_unit_xy']
        else:
            self.meta['si_unit_xy'] = ''

        if 'si_unit_z' in meta:
            self.meta['si_unit_z'] = meta['si_unit_z']
        else:
            self.meta['si_unit_z'] = ''

    @classmethod
    def from_gwy(cls, gwydf):
        """
        Args:
            gwydf (GwyDataField*):
                GwyDataField object from Libgwyfile
        """
        meta = cls._get_meta(gwydf)
        xres = meta['xres']
        yres = meta['yres']
        data = cls._get_data(gwydf, xres, yres)
        return GwyDataField(data=data, meta=meta)

    @staticmethod
    def _get_meta(gwydf):
        """Get metadata from  the datafield

        Args:
            gwydf (GwyDataField*):
                GwyDataField object from Libgwyfile

        Returns:
            meta: Python dictionary with the data field metadata

                Keys of the metadata dictionary:
                    'xres' (int):    Horizontal dimension in pixels
                    'yres' (int):    Vertical dimension in pixels
                    'xreal' (float): Horizontal size in physical units
                    'yreal' (float): Vertical size in physical units
                    'xoff' (double): Horizontal offset of the top-left corner
                                     in physical units.
                    'yoff' (double): Vertical offset of the top-left corner
                                     in physical units.
                    'si_unit_xy' (str): Physical units of lateral dimensions,
                                        base SI units, e.g. "m"
                    'si_unit_z' (str): Physical unit of vertical dimension,
                                       base SI unit, e.g. "m"

        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        xresp = ffi.new("int32_t*")
        yresp = ffi.new("int32_t*")
        xrealp = ffi.new("double*")
        yrealp = ffi.new("double*")
        xoffp = ffi.new("double*")
        yoffp = ffi.new("double*")
        xyunitp = ffi.new("char**")
        zunitp = ffi.new("char**")

        meta = {}

        if lib.gwyfile_object_datafield_get(
                gwydf, errorp,
                ffi.new("char[]", b'xres'), xresp,
                ffi.new("char[]", b'yres'), yresp,
                ffi.new("char[]", b'xreal'), xrealp,
                ffi.new("char[]", b'yreal'), yrealp,
                ffi.new("char[]", b'xoff'), xoffp,
                ffi.new("char[]", b'yoff'), yoffp,
                ffi.new("char[]", b'si_unit_xy'), xyunitp,
                ffi.new("char[]", b'si_unit_z'), zunitp,
                ffi.NULL):
            meta['xres'] = xresp[0]
            meta['yres'] = yresp[0]
            meta['xreal'] = xrealp[0]
            meta['yreal'] = yrealp[0]
            meta['xoff'] = xoffp[0]
            meta['yoff'] = yoffp[0]

            if xyunitp[0]:
                meta['si_unit_xy'] = ffi.string(xyunitp[0]).decode('utf-8')
            else:
                meta['si_unit_xy'] = ''
            if zunitp[0]:
                meta['si_unit_z'] = ffi.string(zunitp[0]).decode('utf-8')
            else:
                meta['si_unit_z'] = ''

            return meta
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

    @staticmethod
    def _get_data(gwydf, xres, yres):
        """Get data array from the GwyDataField

        Args:
            gwydf (GwyDataField*):
                GwyDataField object from Libgwyfile
            xres (int): Horizontal dimension of the data field in pixels
            yres (int): Vertical dimension of the data field in pixels

        Returns:
            data (2D numpy array, float64): data from the data field

        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)

        data = ffi.new("double[]", xres * yres)
        datap = ffi.new("double**", data)

        if lib.gwyfile_object_datafield_get(gwydf, errorp,
                                            ffi.new("char[]", b'data'), datap,
                                            ffi.NULL):
            data_buf = ffi.buffer(datap[0], xres * yres * ffi.sizeof(data))
            data_array = np.frombuffer(data_buf, dtype=np.float64,
                                       count=xres * yres).reshape((xres, yres))
            return data_array
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

    def __repr__(self):
        return "<{} instance at {}.\n meta: {},\n data: {}>".format(
            self.__class__.__name__,
            hex(id(self)),
            self.meta.__repr__(),
            self.data.__repr__())


class GwyGraphCurve:
    """Class for GwyGraphCurveModel representation
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
        meta = cls._get_meta(gwycurve)
        npoints = meta['ndata']
        data = cls._get_data(gwycurve, npoints)
        return GwyGraphCurve(data=data, meta=meta)

    @staticmethod
    def _get_meta(gwycurve):
        """
        Get metadata from GwyGraphCurveModel object

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
        Get data from GwyGraphCurveModel object

        Args:
            curve (GwyfileObject*):
                GwyGraphCurveModel object
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

    def __repr__(self):
        return "<{} instance at {}. Description: {}>".format(
            self.__class__.__name__,
            hex(id(self)),
            self.meta['description'])


class GwyGraphModel:
    """Class for GwyGraphModel representation
    """

    def __init__(self, curves, meta=None):

        self.meta = {}

        if meta is None:
            meta = {}

        for curve in curves:
            if not isinstance(curve, GwyGraphCurve):
                raise TypeError("curves must be a list "
                                "of GwyGraphCurve objects")

        if 'ncurves' in meta:
            if meta['ncurves'] == len(curves):
                self.meta['ncurves'] = meta['ncurves']
                self.curves = curves
            else:
                raise ValueError("meta['ncurves'] is not equal to "
                                 "number of curves")
        else:
            self.meta['ncurves'] = len(curves)
            self.curves = curves

        if 'title' in meta:
            self.meta['title'] = meta['title']
        else:
            self.meta['title'] = ''

        if 'top_label' in meta:
            self.meta['top_label'] = meta['top_label']
        else:
            self.meta['top_label'] = ''

        if 'left_label' in meta:
            self.meta['left_label'] = meta['left_label']
        else:
            self.meta['left_label'] = ''

        if 'right_label' in meta:
            self.meta['right_label'] = meta['right_label']
        else:
            self.meta['right_label'] = ''

        if 'bottom_label' in meta:
            self.meta['bottom_label'] = meta['bottom_label']
        else:
            self.meta['bottom_label'] = ''

        if 'x_unit' in meta:
            self.meta['x_unit'] = meta['x_unit']
        else:
            self.meta['x_unit'] = ''

        if 'y_unit' in meta:
            self.meta['y_unit'] = meta['y_unit']
        else:
            self.meta['y_unit'] = ''

        if 'x_min' in meta:
            self.meta['x_min'] = meta['x_min']
        else:
            self.meta['x_min'] = None

        if 'x_min_set' in meta:
            self.meta['x_min_set'] = meta['x_min_set']
        else:
            self.meta['x_min_set'] = False

        if 'x_max' in meta:
            self.meta['x_max'] = meta['x_max']
        else:
            self.meta['x_max'] = None

        if 'x_max_set' in meta:
            self.meta['x_max_set'] = meta['x_max_set']
        else:
            self.meta['x_max_set'] = False

        if 'y_min' in meta:
            self.meta['y_min'] = meta['y_min']
        else:
            self.meta['y_min'] = None

        if 'y_min_set' in meta:
            self.meta['y_min_set'] = meta['y_min_set']
        else:
            self.meta['y_min_set'] = False

        if 'y_max' in meta:
            self.meta['y_max'] = meta['y_max']
        else:
            self.meta['y_max'] = None

        if 'y_max_set' in meta:
            self.meta['y_max_set'] = meta['y_max_set']
        else:
            self.meta['y_max_set'] = False

        if 'x_is_logarithmic' in meta:
            self.meta['x_is_logarithmic'] = meta['x_is_logarithmic']
        else:
            self.meta['x_is_logarithmic'] = False

        if 'y_is_logarithmic' in meta:
            self.meta['y_is_logarithmic'] = meta['y_is_logarithmic']
        else:
            self.meta['y_is_logarithmic'] = False

        if 'label.visible' in meta:
            self.meta['label.visible'] = meta['label.visible']
        else:
            self.meta['label.visible'] = True

        if 'label.has_frame' in meta:
            self.meta['label.has_frame'] = meta['label.has_frame']
        else:
            self.meta['label.has_frame'] = True

        if 'label.reverse' in meta:
            self.meta['label.reverse'] = meta['label.reverse']
        else:
            self.meta['label.reverse'] = False

        if 'label.frame_thickness' in meta:
            self.meta['label.frame_thickness'] = meta['label.frame_thickness']
        else:
            self.meta['label.frame_thickness'] = 1

        if 'label.position' in meta:
            self.meta['label.position'] = meta['label.position']
        else:
            self.meta['label.position'] = 0

        if 'grid-type' in meta:
            self.meta['grid-type'] = meta['grid-type']
        else:
            self.meta['grid-type'] = 1

    @classmethod
    def from_gwy(cls, gwygraphmodel):
        meta = cls._get_meta(gwygraphmodel)
        ncurves = meta['ncurves']
        gwycurves = cls._get_curves(gwygraphmodel, ncurves)
        curves = [GwyGraphCurve.from_gwy(curve) for curve in gwycurves]
        return GwyGraphModel(curves=curves, meta=meta)

    @staticmethod
    def _get_meta(gwygraphmodel):
        """Get metadata from a GwyGraphModel object (libgwyfile)

        Args:
            gwygraphmodel (GwyGraphModel*):
                GwyGraphModel object from Libgwyfile C library

        Returns:
           meta (dict):
                python dictionary with metadata from the GwyGraphModel
        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        ncurvesp = ffi.new("int32_t*")
        titlep = ffi.new("char**")
        top_labelp = ffi.new("char**")
        left_labelp = ffi.new("char**")
        right_labelp = ffi.new("char**")
        bottom_labelp = ffi.new("char**")
        x_unitp = ffi.new("char**")
        y_unitp = ffi.new("char**")
        x_minp = ffi.new("double*")
        x_min_setp = ffi.new("bool*")
        x_maxp = ffi.new("double*")
        x_max_setp = ffi.new("bool*")
        y_minp = ffi.new("double*")
        y_min_setp = ffi.new("bool*")
        y_maxp = ffi.new("double*")
        y_max_setp = ffi.new("bool*")
        x_is_logarithmicp = ffi.new("bool*")
        y_is_logarithmicp = ffi.new("bool*")
        label_visiblep = ffi.new("bool*")
        label_has_framep = ffi.new("bool*")
        label_reversep = ffi.new("bool*")
        label_frame_thicknessp = ffi.new("int32_t*")
        label_positionp = ffi.new("int32_t*")
        grid_typep = ffi.new("int32_t*")

        meta = {}

        if lib.gwyfile_object_graphmodel_get(gwygraphmodel,
                                             errorp,
                                             ffi.new("char[]",
                                                     b"ncurves"),
                                             ncurvesp,
                                             ffi.new("char[]",
                                                     b"title"),
                                             titlep,
                                             ffi.new("char[]",
                                                     b"top_label"),
                                             top_labelp,
                                             ffi.new("char[]",
                                                     b"left_label"),
                                             left_labelp,
                                             ffi.new("char[]",
                                                     b"right_label"),
                                             right_labelp,
                                             ffi.new("char[]",
                                                     b"bottom_label"),
                                             bottom_labelp,
                                             ffi.new("char[]",
                                                     b"x_unit"),
                                             x_unitp,
                                             ffi.new("char[]",
                                                     b"y_unit"),
                                             y_unitp,
                                             ffi.new("char[]",
                                                     b"x_min"),
                                             x_minp,
                                             ffi.new("char[]",
                                                     b"x_min_set"),
                                             x_min_setp,
                                             ffi.new("char[]",
                                                     b"x_max"),
                                             x_maxp,
                                             ffi.new("char[]",
                                                     b"x_max_set"),
                                             x_max_setp,
                                             ffi.new("char[]",
                                                     b"y_min"),
                                             y_minp,
                                             ffi.new("char[]",
                                                     b"y_min_set"),
                                             y_min_setp,
                                             ffi.new("char[]",
                                                     b"y_max"),
                                             y_maxp,
                                             ffi.new("char[]",
                                                     b"y_max_set"),
                                             y_max_setp,
                                             ffi.new("char[]",
                                                     b"x_is_logarithmic"),
                                             x_is_logarithmicp,
                                             ffi.new("char[]",
                                                     b"y_is_logarithmic"),
                                             y_is_logarithmicp,
                                             ffi.new("char[]",
                                                     b"label.visible"),
                                             label_visiblep,
                                             ffi.new("char[]",
                                                     b"label.has_frame"),
                                             label_has_framep,
                                             ffi.new("char[]",
                                                     b"label.reverse"),
                                             label_reversep,
                                             ffi.new("char[]",
                                                     b"label.frame_thickness"),
                                             label_frame_thicknessp,
                                             ffi.new("char[]",
                                                     b"label.position"),
                                             label_positionp,
                                             ffi.new("char[]",
                                                     b"grid-type"),
                                             grid_typep,
                                             ffi.NULL):
            meta["ncurves"] = ncurvesp[0]

            if titlep[0]:
                title = ffi.string(titlep[0]).decode('utf-8')
                meta["title"] = title
            else:
                meta["title"] = ''

            if top_labelp[0]:
                top_label = ffi.string(top_labelp[0]).decode('utf-8')
                meta["top_label"] = top_label
            else:
                meta["top_label"] = ''

            if left_labelp[0]:
                left_label = ffi.string(left_labelp[0]).decode('utf-8')
                meta["left_label"] = left_label
            else:
                meta["left_label"] = ''

            if right_labelp[0]:
                right_label = ffi.string(right_labelp[0]).decode('utf-8')
                meta["right_label"] = right_label
            else:
                meta["right_label"] = ''

            if bottom_labelp[0]:
                bottom_label = ffi.string(bottom_labelp[0]).decode('utf-8')
                meta["bottom_label"] = bottom_label
            else:
                meta["bottom_label"] = ''

            if x_unitp[0]:
                x_unit = ffi.string(x_unitp[0]).decode('utf-8')
                meta["x_unit"] = x_unit
            else:
                meta["x_unit"] = ''

            if y_unitp[0]:
                y_unit = ffi.string(y_unitp[0]).decode('utf-8')
                meta["y_unit"] = y_unit
            else:
                meta["y_unit"] = ''

            if x_min_setp[0]:
                meta["x_min_set"] = True
                meta["x_min"] = x_minp[0]
            else:
                meta["x_min_set"] = False
                meta["x_min"] = None

            if x_max_setp[0]:
                meta["x_max_set"] = True
                meta["x_max"] = x_maxp[0]
            else:
                meta["x_max_set"] = False
                meta["x_max"] = None

            if y_min_setp[0]:
                meta["y_min_set"] = True
                meta["y_min"] = y_minp[0]
            else:
                meta["y_min_set"] = False
                meta["y_min"] = None

            if y_max_setp[0]:
                meta["y_max_set"] = True
                meta["y_max"] = y_maxp[0]
            else:
                meta["y_max_set"] = False
                meta["y_max"] = None

            if x_is_logarithmicp[0]:
                meta["x_is_logarithmic"] = True
            else:
                meta["x_is_logarithmic"] = False

            if y_is_logarithmicp[0]:
                meta["y_is_logarithmic"] = True
            else:
                meta["y_is_logarithmic"] = False

            if label_visiblep[0]:
                meta["label.visible"] = True
            else:
                meta["label.visible"] = False

            if label_has_framep[0]:
                meta["label.has_frame"] = True
            else:
                meta["label.has_frame"] = False

            if label_reversep[0]:
                meta["label.reverse"] = True
            else:
                meta["label.reverse"] = False

            meta["label.frame_thickness"] = label_frame_thicknessp[0]

            meta["label.position"] = label_positionp[0]

            meta["grid-type"] = grid_typep[0]

            return meta
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

    @staticmethod
    def _get_curves(gwygraphmodel, ncurves):
        """Get list of GwyGraphCurveModel object pointers

        Args:
            gwygraphmodel (GwyGraphModel*):
                GwyGraphModel object from Libgwyfile C library
            ncurves (int):
                number of curves in the GwyGraphModel object

        Returns:
            curves (list):
                list of GwyGraphCurveModel* Libgwyfile objects
        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        curves_arrayp = ffi.new("GwyfileObject***")

        curves = []

        if lib.gwyfile_object_graphmodel_get(gwygraphmodel,
                                             errorp,
                                             ffi.new("char[]",
                                                     b"curves"),
                                             curves_arrayp,
                                             ffi.NULL):
            curves_array = curves_arrayp[0]
            curves = [curves_array[curve_id] for curve_id in range(ncurves)]
            return curves
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

    def __repr__(self):
        return "<{} instance at {}. Title: {}. Curves: {}.>".format(
            self.__class__.__name__,
            hex(id(self)),
            self.meta['title'],
            len(self.curves))


class GwyChannel:
    """Class for GwyChannel representation
    """

    def __init__(self, gwyfile, channel_id):
        self._title = self._get_title(gwyfile, channel_id)
        self._data = self._get_data(gwyfile, channel_id)
        self._mask = self._get_mask(gwyfile, channel_id)
        self._show = self._get_show(gwyfile, channel_id)
        self._point_sel = self._get_point_sel(gwyfile, channel_id)
        self._pointer_sel = self._get_pointer_sel(gwyfile, channel_id)
        self._line_sel = self._get_line_sel(gwyfile, channel_id)
        self._rectangle_sel = self._get_rectangle_sel(gwyfile, channel_id)
        self._ellipse_sel = self._get_ellipse_sel(gwyfile, channel_id)

    @property
    def title(self):
        return self._title

    @property
    def data(self):
        return self._data

    @property
    def mask(self):
        return self._mask

    @property
    def show(self):
        return self._show

    @property
    def point_selections(self):
        return self._point_sel

    @property
    def pointer_selections(self):
        return self._pointer_sel

    @property
    def line_selections(self):
        return self._line_sel

    @property
    def rectangle_selections(self):
        return self._rectangle_sel

    @property
    def ellipse_selections(self):
        return self._ellipse_sel

    @staticmethod
    def _get_title(gwyfile, channel_id):
        key = "/{:d}/data/title".format(channel_id)
        if gwyfile.check_gwyobject(key):
            gwyobject = gwyfile.get_gwyobject(key)
            title = ffi.string(ffi.cast("char*", gwyobject)).decode('utf-8')
            return title
        else:
            raise GwyfileError(
                "Title for channel with id:{:d} is not found".format(
                    channel_id))

    @staticmethod
    def _get_data(gwyfile, channel_id):
        key = "/{:d}/data".format(channel_id)
        if gwyfile.check_gwyobject(key):
            gwydf = gwyfile.get_gwyobject(key)
            return GwyDataField.from_gwy(gwydf)
        else:
            raise GwyfileError(
                "Channel with id:{:d} is not found".format(channel_id))

    @staticmethod
    def _get_mask(gwyfile, channel_id):
        key = "/{:d}/mask".format(channel_id)
        if gwyfile.check_gwyobject(key):
            gwydf = gwyfile.get_gwyobject(key)
            return GwyDataField.from_gwy(gwydf)
        else:
            return None

    @staticmethod
    def _get_show(gwyfile, channel_id):
        key = "/{:d}/show".format(channel_id)
        if gwyfile.check_gwyobject(key):
            gwydf = gwyfile.get_gwyobject(key)
            return GwyDataField.from_gwy(gwydf)
        else:
            return None

    @staticmethod
    def _get_point_sel(gwyfile, channel_id):
        key = "/{:d}/select/point".format(channel_id)
        if gwyfile.check_gwyobject(key):
            gwysel = gwyfile.get_gwyobject(key)
            return GwyPointSelections.from_gwy(gwysel)
        else:
            return None

    @staticmethod
    def _get_pointer_sel(gwyfile, channel_id):
        key = "/{:d}/select/pointer".format(channel_id)
        if gwyfile.check_gwyobject(key):
            gwysel = gwyfile.get_gwyobject(key)
            return GwyPointerSelections.from_gwy(gwysel)
        else:
            return None

    @staticmethod
    def _get_line_sel(gwyfile, channel_id):
        key = "/{:d}/select/line".format(channel_id)
        if gwyfile.check_gwyobject(key):
            gwysel = gwyfile.get_gwyobject(key)
            return GwyLineSelections.from_gwy(gwysel)
        else:
            return None

    @staticmethod
    def _get_rectangle_sel(gwyfile, channel_id):
        key = "/{:d}/select/rectangle".format(channel_id)
        if gwyfile.check_gwyobject(key):
            gwysel = gwyfile.get_gwyobject(key)
            return GwyRectangleSelections.from_gwy(gwysel)
        else:
            return None

    @staticmethod
    def _get_ellipse_sel(gwyfile, channel_id):
        key = "/{:d}/select/ellipse".format(channel_id)
        if gwyfile.check_gwyobject(key):
            gwysel = gwyfile.get_gwyobject(key)
            return GwyEllipseSelections.from_gwy(gwysel)
        else:
            return None

    def __repr__(self):
        return "<{} instance at {}. Title: {}>".format(
            self.__class__.__name__,
            hex(id(self)),
            self.title)


class GwyContainer:
    """Class for GwyContainer representation

    Attributes:
        channels: list of GwyChannel instances
            All channels in Gwyfile instance

        graphs: list of GwyGraphModel instances
            All graphs in Gwyfile instance

    """

    def __init__(self, gwyfile):
        """
        Args:
            gwyfile: instance of Gwyfile object

        """

        self.channels = self._dump_channels(gwyfile)
        self.graphs = self._dump_graphs(gwyfile)

    @staticmethod
    def _get_channel_ids(gwyfile):
        """Get list of channel ids

        Args:
            gwyfile: Gwyfile object

        Returns:
            [list (int)]: list of channel ids, e.g. [0, 1, 2]

        """

        nchannelsp = ffi.new("unsigned int*")
        ids = lib.gwyfile_object_container_enumerate_channels(
            gwyfile.c_gwyfile,
            nchannelsp)
        if ids:
            return [ids[i] for i in range(nchannelsp[0])]
        else:
            return []

    @classmethod
    def _dump_channels(cls, gwyfile):
        """Dump all channels from Gwyfile instance

        Args:
            gwyfile: Gwyfile object

        Returns
            channels: list of GwyChannel objects

        """
        channel_ids = cls._get_channel_ids(gwyfile)
        channels = [GwyChannel(gwyfile, channel_id)
                    for channel_id in channel_ids]
        return channels

    @staticmethod
    def _get_graph_ids(gwyfile):
        """Get list of graphmodel object ids

        Args:
            gwyfile: Gwyfile object

        Returns:
            [list (int)]:
                list of graphmodel object ids, e.g. [1, 2]

        """

        ngraphsp = ffi.new("unsigned int*")
        ids = lib.gwyfile_object_container_enumerate_graphs(gwyfile.c_gwyfile,
                                                            ngraphsp)

        if ids:
            return [ids[i] for i in range(ngraphsp[0])]
        else:
            return []

    @classmethod
    def _dump_graphs(cls, gwyfile):
        """Dump all graphs from Gwyfile instance

        Args:
            gwyfile: Gwyfile object

        Returns
            graphs: list of GwyGraphModel objects

        """

        graph_ids = cls._get_graph_ids(gwyfile)
        graph_keys = ["/0/graph/graph/{:d}".format(graph_id)
                      for graph_id in graph_ids]
        gwygraphmodels = [Gwyfile.get_gwyobject(gwyfile, key)
                          for key in graph_keys]
        graphs = [GwyGraphModel.from_gwy(gwygraphmodel)
                  for gwygraphmodel in gwygraphmodels]
        return graphs

    def __repr__(self):
        return "<{} instance at {}. " \
            "Channels: {}. " \
            "Graphs: {}.>".format(
                self.__class__.__name__,
                hex(id(self)),
                len(self.channels),
                len(self.graphs))


def read_gwyfile(filename):
    """Read gwy file

    Args:
        filename (str): Name of the gwyddion file

    Returns:
        Object of the Gwyfile class

    """

    error = ffi.new("GwyfileError*")
    errorp = ffi.new("GwyfileError**", error)

    if not os.path.isfile(filename):
        raise OSError("Cannot find file {}".format(filename))

    c_gwyfile = lib.gwyfile_read_file(filename.encode('utf-8'), errorp)

    if not c_gwyfile:
        raise GwyfileErrorCMsg(errorp[0].message)

    return Gwyfile(c_gwyfile)
