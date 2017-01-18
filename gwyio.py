# -*- coding: utf-8 -*-
"""Gwyfile IO operations using Libgwyfile C library"""
import os.path
import numpy as np

from _libgwyfile import ffi, lib


class GwyfileError(Exception):
    """Class for Gwyfile C Library errors"""
    pass



class GwyDataframe():
    """Class for Gwy Dataframe representation

    Attributes:
        data (np.float64 array): 2D numpy array with the Dataframe data
        xres (int): Horizontal dimension of the dataframe in pixels
        yres (int): Vertical dimension of the dataframe in pixels
        xreal (float): Horizontal size of the dataframe in physical units
        yreal (float): Vertical size of the dataframe in physical units
        xyunit (str): Physical unit of lateral dimensions, base SI unit, e.g. 'm'
        zunit (str): Physical unit of vertical dimension, base SI unit, e.g. 'm'

    """
    def __init__(self, data, metadata):
        """
        Args:
            data (np.float64 array): 2D numpy array with GWY dataframe data
            metadata (dictionary): Python dictionary with GWY dataframe metadata
                                   keys - names of metadata fields (e.g. 'xres')
                                   values - values of metadata fields (e.g. 512)

        """
        self.data = data
        for key in metadata:
            setattr(self, key, metadata[key])



class GwyChannel():
    """Class for Gwy channel representation.
    Contains at least one dataframe.
    Could also contains Mask or Presentation dataframes.

    Attributes:
        title (str): Title of the GWY channel
        dataframe (GwyDataframe): Dataframe of the channel
        mask (GwyDataframe): Mask of the channel
        presentation (GwyDataframe): Presentation of the channel
    """
    def __init__(self, title, dataframe, mask=None, presentation=None):
        self.title = title
        self.dataframe = dataframe
        self.mask = mask
        self.presentation = presentation



def gwyfile_channels_dump(filename):
    """Dump all channels from gwyddion file.
    
    Args:
        filename (str): Name of the gwyddion file.
        
    Returns:
        List of all channels objects contained in the gwyddion file.
    
    """
    errorp = ffi.new("GwyfileError**")
    nchannelsp = ffi.new("unsigned int*") 
    
    if not os.path.isfile(filename):
        raise ValueError("Cannot find file {}".format(filename))
    gwyfile_object = lib.gwyfile_read_file(filename.encode('utf-8'), errorp)
    if not gwyfile_object:
        error_msg = ffi.string(errorp[0].message).decode('utf-8')
        raise GwyfileError(error_msg)
    elif not ffi.string(lib.gwyfile_object_name(gwyfile_object)) == b'GwyContainer':
        error_msg = "The top-level object in the file {} is not a GwyContainer".format(filename)
        raise GwyfileError(error_msg)
        
    ids = lib.gwyfile_object_container_enumerate_channels(gwyfile_object, nchannelsp)
    if not ids:
        error_msg = "The number of channels found in the file {} is zero".format(filename)
        raise GwyfileError(error_msg)
    nchannels = nchannelsp[0]
    channels_list = []
    for i in range(nchannels):
        channel = gwychannel_dump(gwyfile_object, ids[i])
        channels_list.append(channel)
    return channels_list
    

def gwyfile_get_object(gwyfile_object, key):
    """Get the object value with a name "key" from a Gwyfile data object
    
    Args:
        gwyfile_object (cdata GwyfileObject*): A GWY file data object
        key (str): Name of the key, e.g. "/1/data/"
        
    Returns:
        item_object (cdata GwyfileObject*): The value of object with a name "key" in gwyfile_object
    
    """
    item = lib.gwyfile_object_get(gwyfile_object, key.encode('utf-8'))
    if not item:
        raise GwyfileError("Cannot find the item \"{}\"".format(key))
    item_object = lib.gwyfile_item_get_object(item)
    if not item_object:
        raise GwyfileError("Cannot find the object value of item {}".format(key))
    return item_object


def gwychannel_get_title(gwyfile_object, id):
    """Get title of the GWY channel with number "id"
    
    Args:
        gwyfile_object (cdata GwyfileObject*): A GWY file data object
        id (int): id number of the channel in a GWY file
    
    Returns:
        title (str): title of the channel
        
    """
    title_key = "/{:d}/data/title".format(id)
    title_object = gwyfile_get_object(gwyfile_object, title_key)
    title = ffi.string(ffi.cast("char*", title_object)).decode('utf-8')
    return title


def gwydataframe_get_metadata(gwyfile_object, key):
    """Get metadata from the dataframe (channel, mask or presentation)

    Args:
        gwyfile_object (cdata GwyfileObject*): GWY file data object
        key (str): name of the dataframe in the GWY file (e.g. "/0/data")

    Returns:
        metadata_dic (dictionary): Python dictionary with GWY dataframe metadata
            keys of the metadata_dic:
                'xres' (int): Horizontal dimension in pixels
                'yres' (int): Vertical dimension in pixels
                'xreal' (float): Horizontal size in physical units
                'yreal' (float): Vertical size in physical units
                'xyunit' (str): Physical units of lateral dimensions, base SI units, e.g. "m"
                'zunit' (str): Physical unit of vertical dimension, base SI unit, e.g. "m"    
    """
    errorp = ffi.new("GwyfileError**")
    xresp = ffi.new("int32_t*")
    yresp = ffi.new("int32_t*")
    xrealp = ffi.new("double*")
    yrealp = ffi.new("double*")
    xyunitp = ffi.new("char**")
    zunitp = ffi.new("char**")
    
    metadata_dic = {}
    
    df_object = gwyfile_get_object(gwyfile_object, key)
    
    if lib.gwyfile_object_datafield_get(df_object, errorp,
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

    
def gwychannel_get_metadata(gwyfile_object, id):
    """Get metadata from the channel with number "id"
    
    Args:
        gwyfile_object (cdata GwyfileObject*): A GWY file data object
        id (int): id number of the channel in the GWY file
    
    Returns:
        metadata_dic (dictionary): Python dictionary with GWY channel metadata
            keys of the metadata_dic:
                'xres' (int): Horizontal dimension in pixels
                'yres' (int): Vertical dimension in pixels
                'xreal' (float): Horizontal size in physical units
                'yreal' (float): Vertical size in physical units
                'xyunit' (str): Physical units of lateral dimensions, base SI units, e.g. "m"
                'zunit' (str): Physical unit of vertical dimension, base SI unit, e.g. "m"

    """
    key = "/{:d}/data".format(id)
    metadata_dic = gwydataframe_get_metadata(gwyfile_object, key)
    return metadata_dic


def gwymask_get_metadata(gwyfile_object, id):
    """Get metadata from the mask of the channel with number "id"

    Args:
        gwyfile_object (cdata GwyfileObject*): A GWY file data object
        id (int): id number of the channel in the GWY file
    
    Returns:
        metadata_dic (dictionary): Python dictionary with GWY channel metadata
            keys of the metadata_dic:
                'xres' (int): Horizontal dimension in pixels
                'yres' (int): Vertical dimension in pixels
                'xreal' (float): Horizontal size in physical units
                'yreal' (float): Vertical size in physical units
                'xyunit' (str): Physical units of lateral dimensions, base SI units, e.g. "m"
                'zunit' (str): Physical unit of vertical dimension, base SI unit, e.g. "m"

    """
    key = "/{:d}/mask".format(id)
    metadata_dic = gwydataframe_get_metadata(gwyfile_object, key)
    return metadata_dic


def gwypresentation_get_metadata(gwyfile_object, id):
    """Get metadata from the presentation of the channel with number "id"

    Args:
        gwyfile_object (cdata GwyfileObject*): A GWY file data object
        id (int): id number of the channel in the GWY file
    
    Returns:
        metadata_dic (dictionary): Python dictionary with GWY channel metadata
            keys of the metadata_dic:
                'xres' (int): Horizontal dimension in pixels
                'yres' (int): Vertical dimension in pixels
                'xreal' (float): Horizontal size in physical units
                'yreal' (float): Vertical size in physical units
                'xyunit' (str): Physical units of lateral dimensions, base SI units, e.g. "m"
                'zunit' (str): Physical unit of vertical dimension, base SI unit, e.g. "m"

    """
    key = "/{:d}/show".format(id)
    metadata_dic = gwydataframe_get_metadata(gwyfile_object, key)
    return metadata_dic
    

def gwydataframe_get_data(gwyfile_object, key, xres, yres):
    """Get data array from the GWY dataframe (e.g. channel, mask, presentation)
    
    Args:
        gwyfile_object (cdata GwyfileObject*): GWY file data object
        key (str): name of the dataframe in the GWY file (e.g. "/0/data")
        xres (int): Horizontal dimension of the dataframe in pixels
        yres (int): Vertical dimension of the dataframe in pixels
        
    Returns:
        data_array (2D numpy array, float64): Data from the GWY dataframe

    """
    data = ffi.new("double[]", xres*yres)
    datap = ffi.new("double**", data)
    errorp = ffi.new("GwyfileError**")

    df_object = gwyfile_get_object(gwyfile_object, key)

    if lib.gwyfile_object_datafield_get(df_object, errorp,
                                        ffi.new("char[]", b'data'), datap,
                                        ffi.NULL):
        data_buf = ffi.buffer(datap[0], xres*yres*ffi.sizeof(data))
        data_array = np.frombuffer(data_buf, dtype=np.float64,
                                   count=xres*yres).reshape((xres, yres))
        return data_array
    else:
        error_msg = ffi.string(errorp[0].message).decode('utf-8')
        raise GwyfileError(error_msg)



def gwychannel_get_data(gwyfile_object, id, xres, yres):
    """Get data array from the GWY channel
    
    Args:
        gwyfile_object (cdata GwyfileObject*): GWY file data object
        id (int): id number of the channel in the GWY file
        xres (int): Horizontal dimension of the channel in pixels
        yres (int): Vertical dimension of the channel in pixels
        
    Returns:
        data (2D numpy array, float64): Data from the GWY channel

    """
    key = "/{:d}/data".format(id)
    data = gwydataframe_get_data(gwyfile_object, key, xres, yres)
    return data


def gwymask_get_data(gwyfile_object, id, xres, yres):
    """Get data array from the GWY mask
    
    Args:
        gwyfile_object (cdata GwyfileObject*): GWY file data object
        id (int): id number of the mask dataframe in the GWY file
        xres (int): Horizontal dimension of the mask dataframe in pixels
        yres (int): Vertical dimension of the mask dataframe in pixels
        
    Returns:
        data (2D numpy array, float64): Data from the GWY mask dataframe

    """
    key = "/{:d}/mask".format(id)
    data = gwydataframe_get_data(gwyfile_object, key, xres, yres)
    return data


def gwypresentation_get_data(gwyfile_object, id, xres, yres):
    """Get data array from the GWY presentation
    
    Args:
        gwyfile_object (cdata GwyfileObject*): GWY file data object
        id (int): id number of the presentation dataframe in the GWY file
        xres (int): Horizontal dimension of the presentation dataframe in pixels
        yres (int): Vertical dimension of the presentation dataframe in pixels
        
    Returns:
        data (2D numpy array, float64): Data from the GWY presentation dataframe

    """
    key = "/{:d}/show".format(id)
    data = gwydataframe_get_data(gwyfile_object, key, xres, yres)
    return data

    
def gwyobject_check(gwyfile_object, key):
    """Check the presence of object in GWY file
    
    Args:
        gwyfile_object (cdata GwyfileObject*): GWY file data object
        key (str): object name
    """
    item = lib.gwyfile_object_get(gwyfile_object, key.encode('utf-8'))
    if not item:
        return False
    else:
        return True

    
def gwychannel_check_mask(gwyfile_object, id):
    """Check if GWY channel has mask.
    
    Args:
        gwyfile_object (cdata GwyfileObject*): GWY file data object
        id (int): id number of the channel in the GWY file

    Returns:
        bool: True if the channel has mask, otherwise False
    """
    key = "/{:d}/mask".format(id)
    return gwyobject_check(gwyfile_object, key)


def gwychannel_check_presentation(gwyfile_object, id):
    """Check if GWY channel has presentation.

    Args:
        gwyfile_object (cdata GwyfileObject*): GWY file data object
        id (int): id number of the channel in the GWY file

    Returns:
        bool: True if the channel has presentation, otherwise False
    """
    key = "/{:d}/show".format(id)
    return gwyobject_check(gwyfile_object, key)

    
def gwychannel_dump(gwyfile_object, id):
    """Get title, metadata and data from the GWY channel
    
    Args:
        gwyfile_object (cdata GwyfileObject*): A GWY file data object
        id (int): id number of the channel in a GWY file
        
    Returns:
        gwychannel (GwyChannel): Object with GWY channel data

    """
    title = gwychannel_get_title(gwyfile_object, id)

    # Create channel dataframe object
    metadata = gwychannel_get_metadata(gwyfile_object, id)
    data = gwychannel_get_data(gwyfile_object, id,
                               xres=metadata['xres'],
                               yres=metadata['yres'])
    data_df = GwyDataframe(data, metadata)

    # Create mask dataframe object if mask exists
    if gwychannel_check_mask(gwyfile_object, id):
        mask_metadata = gwymask_get_metadata(gwyfile_object, id)
        mask_data = gwymask_get_data(gwyfile_object, id,
                                     xres=mask_metadata['xres'],
                                     yres=mask_metadata['yres'])
        mask_df = GwyDataframe(mask_data, mask_metadata)
    else:
        mask_df = None

    # Create presentation dataframe object if presentation exists
    if gwychannel_check_presentation(gwyfile_object, id):
        presentation_metadata = gwypresentation_get_metadata(gwyfile_object,
                                                             id)
        presentation_data = gwypresentation_get_data(gwyfile_object,
                                                     id,
                                                     xres=presentation_metadata['xres'],
                                                     yres=presentation_metadata['yres'])
        presentation_df = GwyDataframe(presentation_data, presentation_metadata)
    else:
        presentation_df = None

    return GwyChannel(title=title,
                      dataframe=data_df,
                      mask=mask_df,
                      presentation=presentation_df)

