""" Pythonic representation of gwyddion GwyGraphModel and GwyGraphCurveModel
    objects.

    Classes:
        GwyGraphCurve: pythonic representation of GwyGraphCurveModel gwy object
        GwyGraphModel: pythonic representation of GwyGraphModel gwy object

"""

import numpy as np

from gwydb.gwy._libgwyfile import ffi, lib
from gwydb.gwy.gwyfile import GwyfileErrorCMsg


class GwyGraphCurve:
    """Class for GwyGraphCurveModel representation

    Attributes:
        data (2D numpy array, float64):
           abscissa and ordinate data of the same length

        meta (python dictionary): curve metadata

    Methods:
        from_gwy(gwyobject): Create GwyGraphCurve instance from
                             <GwyGraphCurveModel*> object

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

    def __repr__(self):
        return "<{} instance at {}. Description: {}>".format(
            self.__class__.__name__,
            hex(id(self)),
            self.meta['description'])


class GwyGraphModel:
    """Class for GwyGraphModel representation

    Attributes:
        curves (list): list of GwyGraphCurve instances
        meta (dictionary): dictionary with graph metadata

    Methods:
        from_gwy(gwyobject): create GwyGraphModel instance
                             from <GwyGraphModel*> object

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
        """Create GwyGraphModel instance from <GwyGraphModel*> object

        Args:
            gwygraphmodel (<GwyGraphModel*>):
                <GwyGraphModel*> object from Libgwyfile

        Returns:
            graph (GwyGraphModel): instance of GwyGraphModel class

        """
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
