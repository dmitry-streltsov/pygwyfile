# -*- coding: utf-8 -*-
"""Gwyfile IO operations using Gwyfile C library http://libgwyfile.sourceforge.net/
"""

import os.path
import numpy as np

from _gwyio import ffi, lib


class GwyfileError(Exception):
    """Class for Gwyfile C Library exceptions"""
    pass


def gwyfile_chanels_dump(filename):
    """Dump all chanels from gwyddion file.
    
    Args:
        filename (str): Name of the gwyddion file.
        
    Returns:
        List of all chanels contained in the gwyddion file.
        Each element of this list is a dictionary returned by gwychanel_dump function:
    
    """
    errorp = ffi.new("GwyfileError**")
    nchanelsp = ffi.new("unsigned int*") 
    
    if not os.path.isfile(filename):
        raise ValueError("Cannot find file {}".format(filename))
    gwyfile_object = lib.gwyfile_read_file(filename.encode('utf-8'), errorp)
    if not gwyfile_object:
        error_msg = ffi.string(errorp[0].message).decode('utf-8')
        raise GwyfileError(error_msg)
    elif not ffi.string(lib.gwyfile_object_name(gwyfile_object)) == b'GwyContainer':
        error_msg = "The top-level object in the file {} is not a GwyContainer".format(filename)
        raise GwyfileError(error_msg)
        
    ids = lib.gwyfile_object_container_enumerate_channels(gwyfile_object, nchanelsp)
    if not ids:
        error_msg = "The number of chanels found in the file {} is zero".format(filename)
        raise GwyfileError(error_msg)
    nchanels = nchanelsp[0]
    chanels_list = []
    for i in range(nchanels):
        chanel = gwychanel_dump(gwyfile_object, ids[i])
        chanels_list.append(chanel)
    return chanels_list
    

def _gwyfile_get_object(gwyfile_object, key):
    """Get the object value with a name "key" from a Gwyfile data object
    
    Args:
        gwyfile_object (GwyfileObject*): A GWY file data object
        key (str): Name of the key, e.g. "/1/data/"
        
    Returns:
        item_object (GwyfileObject*): The value of object with a name "key" in gwyfile_object
    
    """
    item = lib.gwyfile_object_get(gwyfile_object, key.encode('utf-8'))
    if not item:
        raise ValueError("Cannot find the item {}".format(key))
    item_object = lib.gwyfile_item_get_object(item)
    if not item_object:
        raise ValueError("Cannot find the object value of item {}".format(key))
    return item_object


def gwychanel_get_title(gwyfile_object, id):
    """Get title of the chanel with number "id"
    
    Args:
        gwyfile_object (GwyfileObject*): A GWY file data object
        id (int): id number of the chanel in a GWY file
    
    Returns:
        title (str): title of the chanel
        
    """
    title_key = "/{:d}/data/title".format(id)
    title_object = _gwyfile_get_object(gwyfile_object, title_key)
    title = ffi.string(ffi.cast("char*", title_object)).decode('utf-8')
    return title


def gwychanel_get_metadata(gwyfile_object, id):
    """Get metadata from the chanel with number "id"
    
    Args:
        gwyfile_object (GwyfileObject*): A GWY file data object
        id (int): id number of the chanel in a GWY file
    
    Returns:
        metadata_dic (dictionary): Python dictionary with GWY chanel metadata
            keys of the metadata_dic:
                'xres' (int) - Horisontal dimension in pixels
                'yres' (int) - Vertical dimension in pixels
                'xreal' (float) - Horisontal size in physical units
                'yreal' (float) - Vertical size in physical units
                'xyunit' (str) - Physical units of lateral dimensions, base SI units, e.g. "m"
                'zunit' (str) - Physical unit of vertical dimension, base SI unit, e.g. "m"
    """
    errorp = ffi.new("GwyfileError**")
    xresp = ffi.new("int32_t*")
    yresp = ffi.new("int32_t*")
    xrealp = ffi.new("double*")
    yrealp = ffi.new("double*")
    xyunitp = ffi.new("char**")
    zunitp = ffi.new("char**")
    
    metadata_dic = {}
    
    chanel_key = "/{:d}/data".format(id)
    chanel_object = _gwyfile_get_object(gwyfile_object, chanel_key)
    
    if lib.gwyfile_object_datafield_get(chanel_object, errorp,
                                        ffi.new("char[]", b'xres'), xresp,
                                        ffi.new("char[]", b'yres'), yresp,
                                        ffi.new("char[]", b'xreal'), xrealp,
                                        ffi.new("char[]", b'yreal'), yrealp,
                                        ffi.new("char[]", b'si_unit_xy'), xyunitp,
                                        ffi.new("char[]", b'si_unit_z'), zunitp, 
                                        ffi.NULL):
        metadata_dic['xres'] = xresp[0]
        metadata_dic['yres'] = yresp[0]
        metadata_dic['xreal'] = xrealp[0]
        metadata_dic['yreal'] = yrealp[0]
        metadata_dic['xyunit'] = ffi.string(xyunitp[0]).decode('utf-8')
        metadata_dic['zunit'] = ffi.string(zunitp[0]).decode('utf-8')
        return metadata_dic
    else:
        error_msg = ffi.string(errorp[0].message).decode('utf-8')
        raise GwyfileError(error_msg)
    

def gwychanel_get_dataframe(gwyfile_object, id, xres, yres):
    """Get data array from the GWY chanel
    
    Args:
        gwyfile_object (GwyfileObject*): A GWY file data object
        id (int): id number of the chanel in a GWY file
        xres (int): Horisontal dimension of the chanel in pixels
        yres (int): Vertical dimension of the chanel in pixels
        
    Returns:
        data_array (2D numpy array, float64): Data from the GWY chanel
    """
    data = ffi.new("double[]", xres*yres)
    datap = ffi.new("double**", data)
    errorp = ffi.new("GwyfileError**")

    chanel_key = "/{:d}/data".format(id)
    chanel_object = _gwyfile_get_object(gwyfile_object, chanel_key)
         
    if lib.gwyfile_object_datafield_get(chanel_object, errorp,
                                        ffi.new("char[]", b'data'), datap,
                                        ffi.NULL):
        data_buf = ffi.buffer(datap[0], xres*yres*ffi.sizeof(data))
        data_array = np.frombuffer(data_buf, dtype=np.float64, count=xres*yres).reshape((xres, yres))
        return data_array
    else:
        error_msg = ffi.string(errorp[0].message).decode('utf-8')
        raise GwyfileError(error_msg)


def gwychanel_dump(gwyfile_object, id):
    """Get title, metadata and data from the GWY chanel
    
    Args:
        gwyfile_object (GwyfileObject*): A GWY file data object
        id (int): id number of the chanel in a GWY file
        
    Returns:
        gwychanel_dic (python dictionary):
            gwychanel_dic keys:
                'title' (str): title of the chanel
                'xres' (int): Horisontal dimension in pixels
                'yres' (int): Vertical dimension in pixels
                'xreal' (float): Horisontal size in physical units
                'yreal' (float): Vertical size in physical units
                'xyunit' (str): Physical units of lateral dimensions, base SI units, e.g. "m"
                'zunit' (str): Physical unit of vertical dimension, base SI unit, e.g. "m"
                'data' (2D numpy array, float64): Data from the GWY chanel 
    """
    gwychanel_dic = gwychanel_get_metadata(gwyfile_object, id)
    gwychanel_dic['title'] = gwychanel_get_title(gwyfile_object, id)
    xres = gwychanel_dic['xres']
    yres = gwychanel_dic['yres']
    gwychanel_dic['data'] = gwychanel_get_dataframe(gwyfile_object, id, xres, yres)
    return gwychanel_dic    

