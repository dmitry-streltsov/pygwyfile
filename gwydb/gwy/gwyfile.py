"""
Wrapper for GwyfileObject from Libgwyfile C library
"""

import os.path

import numpy as np

from gwydb.gwy._libgwyfile import ffi, lib


class GwyfileError(Exception):
    """
    Class for Gwyfile C library errors
    """

    pass


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
            if errorp[0].message:
                error_msg = ffi.string(errorp[0].message).decode('utf-8')
                raise GwyfileError(error_msg)
            else:
                raise GwyfileError

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
            if errorp[0].message:
                error_msg = ffi.string(errorp[0].message).decode('utf-8')
                raise GwyfileError(error_msg)
            else:
                raise GwyfileError

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

    def get_pointsel(self, channel_id):
        """Get point selections from the channel

        Args:
            channel_id(int): id of the channel

        Returns:
            [(x1, y1), ..., (xN, yN)]: list of tuples with point coordinates
                                       or None if there are no point selections
        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        nselp = ffi.new("int32_t*")

        key = "/{:d}/select/pointer".format(channel_id)
        if not self._gwyobject_check(key):
            return None

        psel = self._gwyfile_get_object(key)

        if lib.gwyfile_object_selectionpoint_get(psel,
                                                 errorp,
                                                 ffi.new("char[]",
                                                         b'nsel'),
                                                 nselp,
                                                 ffi.NULL):
            nsel = nselp[0]
        else:
            if errorp[0].message:
                error_msg = ffi.string(errorp[0].message).decode('utf-8')
                raise GwyfileError(error_msg)
            else:
                raise GwyfileError

        if nsel == 0:
            return None
        else:
            data = ffi.new("double[]", 2*nsel)
            datap = ffi.new("double**", data)

        if lib.gwyfile_object_selectionpoint_get(psel,
                                                 errorp,
                                                 ffi.new("char[]",
                                                         b'data'),
                                                 datap,
                                                 ffi.NULL):
            data = datap[0]
            points = [(data[i * 2], data[i * 2 + 1])
                      for i in range(nsel)]
        else:
            if errorp[0].message:
                error_msg = ffi.string(errorp[0].message).decode('utf-8')
                raise GwyfileError(error_msg)
            else:
                raise GwyfileError

        return points


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
        if errorp[0].message:
            error_msg = ffi.string(errorp[0].message).decode('utf-8')
            raise GwyfileError(error_msg)
        else:
            raise GwyfileError

    return Gwyfile(c_gwyfile)
