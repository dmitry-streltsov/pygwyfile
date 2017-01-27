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


def get_channel(gwyfile, channel_id):
    """Return channel data as GwyChannel object

        Args:
        gwyfile (Gwyfile): instance of Gwyfile class
        channel_id (int): id of the channel
    """

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

        ids = gwyfile.get_channels_ids()
        channels = [get_channel(channel_id) for channel_id in ids]
        return GwyContainer(channels)
