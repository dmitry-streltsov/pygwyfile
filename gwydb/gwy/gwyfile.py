""" Wrapper for GwyfileObject from Libgwyfile C library """

import os.path

import numpy as np

from ._libgwyfile import ffi, lib


class GwyfileError(Exception):
    """ Class for Gwyfile C library errors"""

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

        toplevel_object_name = ffi.string(lib.gwyfile_object_name(c_gwyfile))
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
                                 'xyunit' (str): Physical units of lateral
                                                 dimensions, base SI units,
                                                 e.g. "m"
                                 'zunit' (str): Physical unit of vertical
                                                dimension, base SI unit,
                                                e.g. "m"

        """

        key = "/{:d}/data".format(channel_id)
        metadata = self._gwydf_get_metadata(key)
        return metadata

    def get_data(self, channel_id):
        """Get data from the channel data field

        Args:
            channel_id (int): id of the channel

        Returns:
            data (2D numpy array, float64): data field from the channel

        """

        key = "/{:d}/data".format(channel_id)
        data = self._gwydf_get_data(key)
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
                  'xyunit' (str): Physical units of lateral dimensions,
                                  base SI units, e.g. "m"
                  'zunit' (str): Physical unit of vertical dimension,
                                 base SI unit, e.g. "m"

        """

        key = "/{:d}/mask".format(channel_id)
        metadata = self._gwydf_get_metadata(key)
        return metadata

    def get_mask_data(self, channel_id):
        """Get data from the mask

        Args:
            channel_id (int): id of the channel

        Returns:
            data (2D numpy array, float64): data field from the mask

        """

        key = "/{:d}/mask".format(channel_id)
        data = self._gwydf_get_data(key)
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
                    'xyunit' (str): Physical units of lateral dimensions,
                                    base SI units, e.g. "m"
                    'zunit' (str): Physical unit of vertical dimension,
                                   base SI unit, e.g. "m"

        """

        key = "/{:d}/show".format(channel_id)
        metadata = self._gwydf_get_metadata(key)
        return metadata

    def get_presentation_data(self, channel_id):
        """Get data from the presentation

        Args:
            channel_id (int): id of the channel

        Returns:
            data (2D numpy array, float64): data field from the presentation

        """

        key = "/{:d}/show".format(channel_id)
        data = self._gwydf_get_data(key)
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
                                      'xyunit' (str): Physical units of lateral
                                                      dimensions,
                                                      base SI units, e.g. "m"
                                      'zunit' (str): Physical unit of vertical
                                                     dimension, base SI unit,
                                                     e.g. "m"

        """

        errorp = ffi.new("GwyfileError**")
        xresp = ffi.new("int32_t*")
        yresp = ffi.new("int32_t*")
        xrealp = ffi.new("double*")
        yrealp = ffi.new("double*")
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
                ffi.new("char[]", b'si_unit_xy'), xyunitp,
                ffi.new("char[]", b'si_unit_z'), zunitp,
                ffi.NULL):
            metadata['xres'] = xresp[0]
            metadata['yres'] = yresp[0]
            metadata['xreal'] = xrealp[0]
            metadata['yreal'] = yrealp[0]
            metadata['xyunit'] = ffi.string(xyunitp[0]).decode('utf-8')
            metadata['zunit'] = ffi.string(zunitp[0]).decode('utf-8')
            return metadata
        else:
            error_msg = ffi.string(errorp[0].message).decode('utf-8')
            raise GwyfileError(error_msg)

    def _gwydf_get_data(self, key):
        """Get data array from the GWY data field (e.g. channel, mask, presentation)

        Args:
            key (str): name of the data field (e.g. "/0/data")

        Returns:
            data (2D numpy array, float64): data from the data field

        """

        xresp = ffi.new("int32_t*")
        yresp = ffi.new("int32_t*")
        errorp = ffi.new("GwyfileError**")

        df = self._gwyfile_get_object(key)

        if lib.gwyfile_object_datafield_get(df, errorp,
                                            ffi.new("char[]", b'xres'), xresp,
                                            ffi.new("char[]", b'yres'), yresp,
                                            ffi.NULL):
            xres = xresp[0]
            yres = yresp[0]
        else:
            error_msg = ffi.string(errorp[0].message).decode('utf-8')
            raise GwyfileError(error_msg)

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
            error_msg = ffi.string(errorp[0].message).decode('utf-8')
            raise GwyfileError(error_msg)

    def _gwyobject_check(self, key):
        """Check the presence of the object

        Args:
            key(str): object key

        """

        item = lib.gwyfile_object_get(self.c_gwyfile, key.encode('utf-8'))
        if not item:
            return False
        else:
            return True

    def get_channel(self, channel_id):
        """Return channel data as GwyChannel object

        Args:
            channel_id (int): id of the channels
        """

        title = self.get_title(channel_id)

        data = self.get_data(channel_id)
        metadata = self.get_metadata(channel_id)
        channel_df = GwyDatafield(data, metadata)

        if self._gwyobject_check("/{:d}/mask".format(channel_id)):
            mask_metadata = self.get_mask_metadata(channel_id)
            mask_data = self.get_mask_data(channel_id)
            mask_df = GwyDatafield(mask_data, mask_metadata)
        else:
            mask_df = None

        if self._gwyobject_check("/{:d}/show".format(channel_id)):
            presentation_data = self.get_presentation_data(channel_id)
            presentation_metadata = self.get_presentation_metadata(channel_id)
            presentation_df = GwyDatafield(presentation_data,
                                           presentation_metadata)
        else:
            presentation_df = None

        channel = GwyChannel(title, channel_df, mask_df, presentation_df)
        return channel

    def get_container(self):
        """Return GwyContainer object

        """

        ids = self.get_channels_ids()
        channels = [self.get_channel(channel_id) for channel_id in ids]
        return GwyContainer(channels)


class GwyDatafield():
    """Class for Gwy Datafield representation

    Attributes:
        data (np.float64 array): 2D numpy array with the datafield
        xres (int): Horizontal dimension of the data field in pixels
        yres (int): Vertical dimension of the data field in pixels
        xreal (float): Horizontal size of the data field in physical units
        yreal (float): Vertical size of the data field in physical units
        xyunit (str): Physical unit of lateral dimensions,
                      base SI unit, e.g. 'm'
        zunit (str): Physical unit of vertical dimension,
                     base SI unit, e.g. 'm'

    """

    def __init__(self, data, metadata):
        """
        Args:
            data (np.float64 array): 2D numpy array with GWY data field
            metadata (dictionary): Python dictionary with
                                   GWY datafield metadata

        """

        self.data = data
        for key in metadata:
            setattr(self, key, metadata[key])


class GwyChannel():
    """Class for Gwy channel representation.
    Contains at least one datafield.
    Could also contain Mask or Presentation datafields.

    Attributes:
        title (str): Title of the GWY channel
        datafield (GwyDatafield): Datafield of the channel
        mask (GwyDatafield): Mask of the channel
        presentation (GwyDatafield): Presentation of the channel

    """

    def __init__(self, title, datafield, mask=None, presentation=None):
        self.title = title
        self.datafield = datafield
        self.mask = mask
        self.presentation = presentation


class GwyContainer():
    """Class for Gwy container representation.

    Attributes:
        channels (list): list of GwyChannel objects

    """

    def __init__(self, channels):
        self.channels = channels


def read_gwyfile(filename):
    """Read gwy file

    Args:
        filename (str): Name of the gwyddion file

    Returns:
        Object of the Gwyfile class

    """

    errorp = ffi.new("GwyfileError**")

    if not os.path.isfile(filename):
        raise OSError("Cannot read file {}".format(filename))

    c_gwyfile = lib.gwyfile_read_file(filename.encode('utf-8'), errorp)

    if not c_gwyfile:
        error_msg = ffi.string(errorp[0].message).decode('utf-8')
        raise GwyfileError(error_msg)

    return c_gwyfile
