"""
Wrapper for GwyfileObject from Libgwyfile C library
"""

import os.path

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


class Gwyfile():
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

    def get_channels_ids(self):
        """Get list of channels ids

        Returns:
            [list (int)]: list of channels ids, e.g. [0, 1, 2]

        """

        nchannelsp = ffi.new("unsigned int*")
        ids = lib.gwyfile_object_container_enumerate_channels(self.c_gwyfile,
                                                              nchannelsp)
        if ids:
            return [ids[i] for i in range(nchannelsp[0])]
        else:
            return []

    def get_graph_ids(self):
        """Get list of graph model object ids

        Returns:
            [list (int)]:
                list of graph model objects ids, e.g. [1, 2]

        """

        ngraphsp = ffi.new("unsigned int*")
        ids = lib.gwyfile_object_container_enumerate_graphs(self.c_gwyfile,
                                                            ngraphsp)

        if ids:
            return [ids[i] for i in range(ngraphsp[0])]
        else:
            return []

    def get_title(self, channel_id):
        """Get title of the channel

        Args:
            channel_id (int): id of the channel

        Returns:
            title (str): title of the channel

        """

        title_key = "/{:d}/data/title".format(channel_id)
        title_object = self._gwyfile_get_object(title_key)
        title = ffi.string(ffi.cast("char*", title_object)).decode('utf-8')
        return title

    def get_metadata(self, channel_id):
        """Get metadata from  the channel data field

        Args:
            channel_id (int): id of the channel

        Returns:
            metadata (dict): Python dictionary with the channel
                             data field metadata.

                               Keys of the metadata dictionary:
                                 'xres' (int): Horizontal dimension in pixels
                                 'yres' (int): Vertical dimension in pixels
                                 'xreal' (float): Horizontal size in
                                                  physical units
                                 'yreal' (float): Vertical size in
                                                  physical units
                                 'xoff' (double): Horizontal offset of
                                                  the top-left corner
                                                  in physical units.
                                 'yoff' (double): Vertical offset of
                                                  the top-left corner
                                                  in physical units.
                                 'si_unit_xy' (str): Physical units of lateral
                                                     dimensions, base SI units,
                                                     e.g. "m"
                                 'si_unit_z' (str): Physical unit of vertical
                                                    dimension, base SI unit,
                                                    e.g. "m"

        """

        key = "/{:d}/data".format(channel_id)
        metadata = self._gwydf_get_metadata(key)
        return metadata

    def get_data(self, channel_id, xres, yres):
        """Get data from the channel data field

        Args:
            channel_id (int): id of the channel
            xres (int): Horizontal dimension of the data field in pixels
            yres (int): Vertical dimension of the data field in pixels

        Returns:
            data (2D numpy array, float64): data field from the channel

        """

        key = "/{:d}/data".format(channel_id)
        data = self._gwydf_get_data(key, xres, yres)
        return data

    def get_mask_metadata(self, channel_id):
        """Get metadata from the mask

        Args:
            channel_id (int): id of the channel

        Returns:
            metadata (dict): Python dictionary with the mask metadata
                keys of the metadata dictionary:
                  'xres' (int): Horizontal dimension in pixels
                  'yres' (int): Vertical dimension in pixels
                  'xreal' (float): Horizontal size in physical units
                  'yreal' (float): Vertical size in physical units
                  'xoff' (double): Horizontal offset of
                                   the top-left corner
                                   in physical units.
                  'yoff' (double): Vertical offset of
                                   the top-left corner
                                   in physical units.
                  'si_unit_xy' (str): Physical units of lateral dimensions,
                                      base SI units, e.g. "m"
                  'si_unit_z' (str): Physical unit of vertical dimension,
                                     base SI unit, e.g. "m"

        """

        key = "/{:d}/mask".format(channel_id)
        metadata = self._gwydf_get_metadata(key)
        return metadata

    def get_mask_data(self, channel_id, xres, yres):
        """Get data from the mask

        Args:
            channel_id (int): id of the channel
            xres (int): Horizontal dimension of the data field in pixels
            yres (int): Vertical dimension of the data field in pixels

        Returns:
            data (2D numpy array, float64): data field from the mask

        """

        key = "/{:d}/mask".format(channel_id)
        data = self._gwydf_get_data(key, xres, yres)
        return data

    def get_presentation_metadata(self, channel_id):
        """Get metadata from the presentation

        Args:
            channel_id (int): id of the channel

        Returns:
            metadata (dictionary): Python dictionary with GWY
                keys of the metadata:
                    'xres' (int): Horizontal dimension in pixels
                    'yres' (int): Vertical dimension in pixels
                    'xreal' (float): Horizontal size in physical units
                    'yreal' (float): Vertical size in physical units
                    'xoff' (double): Horizontal offset of
                                     the top-left corner
                                     in physical units.
                    'yoff' (double): Vertical offset of
                                     the top-left corner
                                     in physical units.
                    'si_unit_xy' (str): Physical units of lateral dimensions,
                                        base SI units, e.g. "m"
                    'si_unit_z' (str): Physical unit of vertical dimension,
                                       base SI unit, e.g. "m"

        """

        key = "/{:d}/show".format(channel_id)
        metadata = self._gwydf_get_metadata(key)
        return metadata

    def get_presentation_data(self, channel_id, xres, yres):
        """Get data from the presentation

        Args:
            channel_id (int): id of the channel
            xres (int): Horizontal dimension of the data field in pixels
            yres (int): Vertical dimension of the data field in pixels

        Returns:
            data (2D numpy array, float64): data field from the presentation

        """

        key = "/{:d}/show".format(channel_id)
        data = self._gwydf_get_data(key, xres, yres)
        return data

    def _gwyfile_get_object(self, key):
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

    def _gwydf_get_metadata(self, key):
        """Get metadata from  the data field (channel, mask or presentation)

        Args:
            key (str): name of the data field (e.g. "/0/data/")

        Returns:
            metadata (dict.): Python dictionary with the data field metadata

                                  Keys of the metadata dictionary:
                                      'xres' (int): Horizontal dimension
                                                    in pixels
                                      'yres' (int): Vertical dimension
                                                    in pixels
                                      'xreal' (float): Horizontal size
                                                       in physical units
                                      'yreal' (float): Vertical size
                                                       in physical units
                                      'xoff' (double): Horizontal offset of
                                                       the top-left corner
                                                       in physical units.
                                      'yoff' (double): Vertical offset of
                                                       the top-left corner
                                                       in physical units.
                                      'si_unit_xy' (str): Physical units of
                                                          lateral dimensions,
                                                          base SI units,
                                                          e.g. "m"
                                      'si_unit_z' (str): Physical unit of
                                                         vertical dimension,
                                                         base SI unit,
                                                         e.g. "m"

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

        metadata = {}

        df = self._gwyfile_get_object(key)

        if lib.gwyfile_object_datafield_get(
                df, errorp,
                ffi.new("char[]", b'xres'), xresp,
                ffi.new("char[]", b'yres'), yresp,
                ffi.new("char[]", b'xreal'), xrealp,
                ffi.new("char[]", b'yreal'), yrealp,
                ffi.new("char[]", b'xoff'), xoffp,
                ffi.new("char[]", b'yoff'), yoffp,
                ffi.new("char[]", b'si_unit_xy'), xyunitp,
                ffi.new("char[]", b'si_unit_z'), zunitp,
                ffi.NULL):
            metadata['xres'] = xresp[0]
            metadata['yres'] = yresp[0]
            metadata['xreal'] = xrealp[0]
            metadata['yreal'] = yrealp[0]
            metadata['xoff'] = xoffp[0]
            metadata['yoff'] = yoffp[0]

            if xyunitp[0]:
                metadata['si_unit_xy'] = ffi.string(xyunitp[0]).decode('utf-8')
            else:
                metadata['si_unit_xy'] = ''
            if zunitp[0]:
                metadata['si_unit_z'] = ffi.string(zunitp[0]).decode('utf-8')
            else:
                metadata['si_unit_z'] = ''

            return metadata
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

    def _gwydf_get_data(self, key, xres, yres):
        """Get data array from the GWY data field (e.g. channel, mask, presentation)

        Args:
            key (str): name of the data field (e.g. "/0/data")
            xres (int): Horizontal dimension of the data field in pixels
            yres (int): Vertical dimension of the data field in pixels

        Returns:
            data (2D numpy array, float64): data from the data field

        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)

        df = self._gwyfile_get_object(key)

        data = ffi.new("double[]", xres*yres)
        datap = ffi.new("double**", data)

        if lib.gwyfile_object_datafield_get(df, errorp,
                                            ffi.new("char[]", b'data'), datap,
                                            ffi.NULL):
            data_buf = ffi.buffer(datap[0], xres*yres*ffi.sizeof(data))
            data_array = np.frombuffer(data_buf, dtype=np.float64,
                                       count=xres*yres).reshape((xres, yres))
            return data_array
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

    def _gwyobject_check(self, key):
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

    def get_pointer_sel(self, channel_id):
        """Get pointer selections from the channel

        Args:
            channel_id(int): id of the channel

        Returns:
            [(x1, y1), ..., (xN, yN)]: list of tuples with point coordinates

            or None :                  if there are no pointer selections
        """

        key = "/{:d}/select/pointer".format(channel_id)
        func = lib.gwyfile_object_selectionpoint_get
        nsel = self._get_selection_nsel(key, func)

        if nsel is None:
            return None
        
        npoints = nsel  # one point in one pointer selection
        points = self._get_selection_data(key, func, npoints)
        return points

    def get_point_sel(self, channel_id):
        """Get point selections from the channel

        Args:
            channel_id(int): id of the channel

        Returns:
            [(x1, y1), ..., (xN, yN)]: list of tuples with point coordinates

            or None :                  if there are no point selections

        """
        
        key = "/{:d}/select/point".format(channel_id)
        func = lib.gwyfile_object_selectionpoint_get
        nsel = self._get_selection_nsel(key, func)

        if nsel is None:
            return None
        
        npoints = nsel  # one point in one point selection
        points = self._get_selection_data(key, func, npoints)
        return points

    def get_line_sel(self, channel_id):
        """Get line selections from the channel

        Args:
             channel_id(int): id of the channel

        Returns:
            [((x1, y1), (x2, y2)) ...]: list, which elements are tuples
                                        with end points coordinates of lines
                                        in line selection

            or None:                    if there are no line selections

        """

        key = "/{:d}/select/line".format(channel_id)
        func = lib.gwyfile_object_selectionline_get
        nsel = self._get_selection_nsel(key, func)

        if nsel is None:
            return None
        
        npoints = nsel * 2  # two point in one line selection
        points = self._get_selection_data(key, func, npoints)

        # combine points in pairs
        lines = list(zip(tuple(points[::2]),    # first point of each line
                         tuple(points[1::2])))  # last point of each line
        return lines

    def get_rectangle_sel(self, channel_id):
        """Get rectangle selections from the channel

        Args:
            channel_id (int) : id of the channel

        Returns:
            [((x1, y1), (x2, y2)) ...]: list, which elements are tuples
                                        with top-left and bottom-right points
                                        coordinates of rectangle in selection


            or None:                    if there are no point selections
        """

        key = "/{:d}/select/rectangle".format(channel_id)
        func = lib.gwyfile_object_selectionrectangle_get
        nsel = self._get_selection_nsel(key, func)

        if nsel is None:
            return None
        
        npoints = nsel * 2  # two point in one rectangle selection
        points = self._get_selection_data(key, func, npoints)

        # combine points in pairs
        rectangles = list(zip(tuple(points[::2]),    # top-left point
                              tuple(points[1::2])))  # bottom-right point
        return rectangles

    def get_ellipse_sel(self, channel_id):
        """Get ellipse selections from the channel

        Args:
            channel_id (int) : id of the channel

        Returns:
            [((x1, y1), (x2, y2)) ...]: list, which elements are tuples
                                        with two points
                                        of ellipse in selection


            or None:                    if there are no point selections
        """

        key = "/{:d}/select/ellipse".format(channel_id)
        func = lib.gwyfile_object_selectionellipse_get
        nsel = self._get_selection_nsel(key, func)

        if nsel is None:
            return None
        
        npoints = nsel * 2  # two point in one ellipse selection
        points = self._get_selection_data(key, func, npoints)
        
        # combine points in pairs
        ellipse = list(zip(tuple(points[::2]),
                           tuple(points[1::2])))
        return ellipse

    def _get_selection_nsel(self, key, func):
        """Get number of selections from the object
        
        Args:
            key (string):
                key for the object, e.g. "/0/select/point"
            func (function):
                C function to get selection,
                e.g. lib.gwyfile_object_selectionpoint_get

        Returns:
            nsel (int):
                number of selections of this type for the object
        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        nselp = ffi.new("int32_t*")

        if not self._gwyobject_check(key):
            return None

        psel = self._gwyfile_get_object(key)

        if func(psel,
                errorp,
                ffi.new("char[]", b'nsel'),
                nselp,
                ffi.NULL):
            nsel = nselp[0]
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

        return nsel

    def _get_selection_data(self, key, func, npoints):
        """Get all points of selection for the object
        
        Args:
            key (string):
                key for the object, e.g. "/0/select/point"
            func (function):
                C function to get selection,
                e.g. lib.gwyfile_object)selectionpoint_get
            npoints (int):
                number of points in selection

        Returns:
            [(x1, y1), ..., (xN, yN)]: list of tuples with point coordinates

            or None :                  if there are no point selections
    
        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        nselp = ffi.new("int32_t*")

        if not self._gwyobject_check(key):
            return None

        psel = self._gwyfile_get_object(key)

        if npoints == 0:
            return None
        else:
            data = ffi.new("double[]", 2*npoints)
            datap = ffi.new("double**", data)

        if func(psel,
                errorp,
                ffi.new("char[]", b'data'),
                datap,
                ffi.NULL):
            data = datap[0]
            points = [(data[i * 2], data[i * 2 + 1])
                      for i in range(npoints)]
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

        return points

    def get_graphmodel_metadata(self, graph_id):
        """Get information from a GwyGraphModel object (libgwyfile)

        Args:
            graph_id (int):
                id of the GwyGraphModel object

        Returns:
           metadata (dict):
                python dictionary with information from the GwyGraphModel
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

        metadata = {}

        key = "/0/graph/graph/{:d}".format(graph_id)

        if not self._gwyobject_check(key):
            return metadata

        graphmodel = self._gwyfile_get_object(key)

        if lib.gwyfile_object_graphmodel_get(graphmodel,
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
            metadata["ncurves"] = ncurvesp[0]

            if titlep[0]:
                title = ffi.string(titlep[0]).decode('utf-8')
                metadata["title"] = title
            else:
                metadata["title"] = ''

            if top_labelp[0]:
                top_label = ffi.string(top_labelp[0]).decode('utf-8')
                metadata["top_label"] = top_label
            else:
                metadata["top_label"] = ''

            if left_labelp[0]:
                left_label = ffi.string(left_labelp[0]).decode('utf-8')
                metadata["left_label"] = left_label
            else:
                metadata["left_label"] = ''

            if right_labelp[0]:
                right_label = ffi.string(right_labelp[0]).decode('utf-8')
                metadata["right_label"] = right_label
            else:
                metadata["right_label"] = ''

            if bottom_labelp[0]:
                bottom_label = ffi.string(bottom_labelp[0]).decode('utf-8')
                metadata["bottom_label"] = bottom_label
            else:
                metadata["bottom_label"] = ''

            if x_unitp[0]:
                x_unit = ffi.string(x_unitp[0]).decode('utf-8')
                metadata["x_unit"] = x_unit
            else:
                metadata["x_unit"] = ''

            if y_unitp[0]:
                y_unit = ffi.string(y_unitp[0]).decode('utf-8')
                metadata["y_unit"] = y_unit
            else:
                metadata["y_unit"] = ''

            metadata["x_min"] = x_minp[0]

            if x_min_setp[0]:
                metadata["x_min_set"] = True
            else:
                metadata["x_min_set"] = False

            metadata["x_max"] = x_maxp[0]

            if x_max_setp[0]:
                metadata["x_max_set"] = True
            else:
                metadata["x_max_set"] = False

            metadata["y_min"] = y_minp[0]

            if y_min_setp[0]:
                metadata["y_min_set"] = True
            else:
                metadata["y_min_set"] = False

            metadata["y_max"] = y_maxp[0]

            if y_max_setp[0]:
                metadata["y_max_set"] = True
            else:
                metadata["y_max_set"] = False

            if x_is_logarithmicp[0]:
                metadata["x_is_logarithmic"] = True
            else:
                metadata["x_is_logarithmic"] = False

            if y_is_logarithmicp[0]:
                metadata["y_is_logarithmic"] = True
            else:
                metadata["y_is_logarithmic"] = False

            if label_visiblep[0]:
                metadata["label.visible"] = True
            else:
                metadata["label.visible"] = False

            if label_has_framep[0]:
                metadata["label.has_fame"] = True
            else:
                metadata["label.has_frame"] = False

            if label_reversep[0]:
                metadata["label.reverse"] = True
            else:
                metadata["label.reverse"] = False

            metadata["label.frame_thickness"] = label_frame_thicknessp[0]

            metadata["label.position"] = label_positionp[0]

            metadata["grid-type"] = grid_typep[0]

            return metadata
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

    def get_graphmodel_curves(self, graph_id, ncurves):
        """Get list of GwyGraphCurveModel object pointers

        Args:
            graph_id (int):
                id of the GwyGraphModel object
            ncurves (int):
                number of curves in the GwyGraphModel object

        Returns:
            curves [list of 'GwyfileObject *']
        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        curves_arrayp = ffi.new("GwyfileObject***")

        curves = []

        key = "/0/graph/graph/{:d}".format(graph_id)

        if not self._gwyobject_check(key):
            return curves

        graphmodel = self._gwyfile_get_object(key)

        if lib.gwyfile_object_graphmodel_get(graphmodel,
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
