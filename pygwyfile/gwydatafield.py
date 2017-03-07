""" Pythonic representation of gwyddion datafield objects

    Classes:
        GwyDataField: pythonic representation of gwyddion datafield

"""
import numpy as np

from pygwyfile._libgwyfile import ffi, lib
from pygwyfile.gwyfile import GwyfileErrorCMsg


class GwyDataField:
    """Class for GwyDataField representation

    Attributes:
        data (2D numpy array, float64):
            data from the datafield

        meta (python dictionary):
            datafield metadata

    Methods:
        from_gwy(gwyobject): Create GwyDataField instance from
        <GwyDataField*> object
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
        """ Create GwyDataField instance from <GwyDataField*> object

        Args:
            gwydf (GwyDataField*):
                GwyDataField object from Libgwyfile

        Returns:
            datafield (GwyDataField):
                GwyDataField instance
        """
        meta = cls._get_meta(gwydf)
        xres = meta['xres']
        yres = meta['yres']
        data = cls._get_data(gwydf, xres, yres)
        return GwyDataField(data=data, meta=meta)

    @staticmethod
    def _get_meta(gwydf):
        """Get metadata from the datafield

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
        """Get data array from <GwyDataField*> object

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
