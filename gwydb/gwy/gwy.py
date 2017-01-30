import numpy as np
from .gwyfile import Gwyfile


class GwyDatafield():
    """Class for Gwy Datafield representation

    Attributes:
        data (np.float64 array): 2D numpy array with the datafield
        xres (int): Horizontal dimension of the data field in pixels
        yres (int): Vertical dimension of the data field in pixels
        xreal (float): Horizontal size of the data field in physical units
        yreal (float): Vertical size of the data field in physical units
        xoff (double): Horizontal offset of the top-left corner
                       in physical units.
        yoff (double): Vertical offset of the top-left corner
                       in physical units.
        si_unit_xy (str): Physical unit of lateral dimensions,
                          base SI unit, e.g. 'm'
        si_unit_z (str): Physical unit of vertical dimension,
                         base SI unit, e.g. 'm'

    """

    def __init__(self, data, *args, **kwargs):
        """
        Args:
            data (np.float64 array): 2D numpy array with GWY data field
            metadata: Python dictionary with GWY datafield metadata
                      or keyword arguments (e.g. xres = 256, yres = 256)
        
            Shape of the data numpy array must be equal to (xres, yres)

        """

        # Set up default values for non-obligatory metadata fields
        self.xreal = None
        self.yreal = None
        self.xoff = 0.
        self.yoff = 0.
        self.si_unit_xy = ''
        self.si_unit_z = ''

        self.data = data
        if not isinstance(data, np.ndarray):
            raise TypeError("data is not a numpy array")

        # initialize via dictionary 
        for dictionary in args:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        # initialize via keyword arguments
        for key in kwargs:
            setattr(self, key, kwargs[key])

        # Check existence of obligatory attributes xres and yres
        if not (hasattr(self, 'xres') and hasattr(self, 'yres')):
            raise ValueError("xres and yres are obligatory attributes")

        # Check shape of the data array
        if not self.data.shape == (self.xres, self.yres):
            raise ValueError("Shape of the data array is not (xres, yres)")


class GwyChannel():
    """Class for Gwy channel representation.
    Contains at least one datafield.
    Could also contain Mask or Presentation datafields.

    Attributes:
        title (str): Title of the GWY channel
        datafield (GwyDatafield): Datafield of the channel
        mask (GwyDatafield): Mask datafield of the channel or None
        presentation (GwyDatafield): Presentation datafield of the channel
                                     or None

    """

    def __init__(self, title, datafield, mask=None, presentation=None):
        self.title = str(title)

        if isinstance(datafield, GwyDatafield):
            self.datafield = datafield
        else:
            raise TypeError("datafield is not an instance of GwyDatafield or None")

        if isinstance(mask, GwyDatafield) or (mask is None):
            self.mask = mask
        else:
            raise TypeError("mask is not an instance of GwyDatafield or None")

        if isinstance(presentation, GwyDatafield) or (presentation is None):
            self.presentation = presentation
        else:
            raise TypeError("presentation is not an instance of GwyDatafield or None")


class GwyContainer():
    """Class for Gwy container representation.

    Attributes:
        channels: iterable object (e.g. list) of GwyChannel instances

    """

    def __init__(self, channels):
        self.channels = []
        for channel in channels:
            if isinstance(channel, GwyChannel):
                self.channels.append(channel)
            else:
                raise TypeError("One element is not a GwyChannel instance") 


def get_channel(gwyfile, channel_id):
    """Return channel data as GwyChannel object

        Args:
        gwyfile (Gwyfile): instance of Gwyfile class
        channel_id (int): id of the channel
    """

    if not isinstance(gwyfile, Gwyfile):
        raise TypeError("gwyfile is not a Gwyfile instance") 
        
    title = gwyfile.get_title(channel_id)

    metadata = gwyfile.get_metadata(channel_id)
    xres = metadata['xres']
    yres = metadata['yres']
    data = gwyfile.get_data(channel_id, xres, yres)

    channel_df = GwyDatafield(data, metadata)

    if gwyfile._gwyobject_check("/{:d}/mask".format(channel_id)):
        mask_metadata = gwyfile.get_mask_metadata(channel_id)
        mask_xres = mask_metadata['xres']
        mask_yres = mask_metadata['yres']
        mask_data = gwyfile.get_mask_data(channel_id, mask_xres, mask_yres)
        mask_df = GwyDatafield(mask_data, mask_metadata)
    else:
        mask_df = None

    if gwyfile._gwyobject_check("/{:d}/show".format(channel_id)):
        presentation_metadata = gwyfile.get_presentation_metadata(channel_id)
        pres_xres = presentation_metadata['xres']
        pres_yres = presentation_metadata['yres']
        presentation_data = gwyfile.get_presentation_data(channel_id,
                                                          pres_xres,
                                                          pres_yres)

        presentation_df = GwyDatafield(presentation_data,
                                       presentation_metadata)
    else:
        presentation_df = None

    channel = GwyChannel(title, channel_df, mask_df, presentation_df)
    return channel


def get_container(gwyfile):
        """Return GwyContainer object """
        
        if not isinstance(gwyfile, Gwyfile):
            raise TypeError("gwyfile is not a Gwyfile instance")
        ids = gwyfile.get_channels_ids()
        channels = [get_channel(gwyfile, channel_id) for channel_id in ids]
        return GwyContainer(channels)
