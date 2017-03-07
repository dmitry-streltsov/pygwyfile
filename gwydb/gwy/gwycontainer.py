""" Gwyddion container pythonic representation

    Classes:
        GwyContainer: class for gwyddion container representation

    Functions:
        read_gwyfile: create GwyContainer instance from gwy file
"""

from gwydb.gwy._libgwyfile import ffi, lib
from gwydb.gwy.gwyfile import Gwyfile
from gwydb.gwy.gwychannel import GwyChannel
from gwydb.gwy.gwygraph import GwyGraphModel


class GwyContainer:
    """Class for GwyContainer representation

    Attributes:
        channels: list of GwyChannel instances
                  All channels in Gwyfile instance

        graphs: list of GwyGraphModel instances
                All graphs in Gwyfile instance

    Methods:
        from_gwy(gwyfile): create GwyContainer instance
                           from Gwyfile object
    """

    def __init__(self, channels=None, graphs=None):
        """
        Args:
            channels: list of GwyChannel instances
            graphs:   list of GwyGraphModel instances
        """
        self.channels = []
        self.graphs = []

        if channels:
            for channel in channels:
                if isinstance(channel, GwyChannel):
                    self.channels.append(channel)
                else:
                    raise TypeError("channels must be a list of "
                                    "GwyChannel instances")

        if graphs:
            for graph in graphs:
                if isinstance(graph, GwyGraphModel):
                    self.graphs.append(graph)
                else:
                    raise TypeError("graphs must be a list of "
                                    "GwyGraphModel instances")

    @classmethod
    def from_gwy(cls, gwyfile):
        """ Create GwyContainer instance from Gwyfile object

        Args:
            gwyfile: instance of Gwyfile object

        Retruns:
            container: instance of GwyContainer class

        """
        if not isinstance(gwyfile, Gwyfile):
            raise TypeError("gwyfile must be an instance of "
                            "Gwyfile class")
        else:
            channels = cls._dump_channels(gwyfile)
            graphs = cls._dump_graphs(gwyfile)
            return GwyContainer(channels=channels,
                                graphs=graphs)

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
        channels = [GwyChannel.from_gwy(gwyfile, channel_id)
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
        gwygraphmodels = [gwyfile.get_gwyitem_object(key)
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
        filename (str): Name of gwyddion file

    Returns:
        Instance of GwyContainer class with data from file

    """
    gwyfile = Gwyfile.from_gwy(filename)
    container = GwyContainer.from_gwy(gwyfile)
    return container
