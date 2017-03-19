""" Gwyddion container pythonic representation

    Classes:
        GwyContainer: class for gwyddion container representation

    Functions:
        read_gwyfile: create GwyContainer instance from gwy file
"""
import os.path
import weakref

from pygwyfile._libgwyfile import ffi, lib
from pygwyfile.gwyfile import Gwyfile, new_gwycontainer
from pygwyfile.gwyfile import add_gwyitem_to_gwycontainer
from pygwyfile.gwyfile import write_gwycontainer_to_gwyfile
from pygwyfile.gwychannel import GwyChannel
from pygwyfile.gwygraph import GwyGraphModel

# weak key dictionary to keep alive gwygraphs objects
# in gwycontainer
_container_graphs_dic = weakref.WeakKeyDictionary()


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

    def __init__(self, filename=None, channels=None, graphs=None):
        """
        Args:
            filename (string): basename of the file the GwyContainer
                               is currently associated with.
            channels: list of GwyChannel instances
            graphs:   list of GwyGraphModel instances
        """
        self.filename = filename
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
            filename = cls._get_filename(gwyfile)
            channels = cls._dump_channels(gwyfile)
            graphs = cls._dump_graphs(gwyfile)
            return GwyContainer(filename=filename,
                                channels=channels,
                                graphs=graphs)

    def to_gwy(self):
        """ Create a new GWY container object with data from this container

        Returns:
            gwycontainer (<GwyfileObject*>):
                The newly created Gwy container object
        """
        gwycontainer = new_gwycontainer()
        _container_graphs_dic[gwycontainer] = []

        for channel_id, channel in enumerate(self.channels):
            channel.to_gwy(gwycontainer, channel_id)

        for graph_id, graph in enumerate(self.graphs):
            gwygraph = graph.to_gwy()

            # graph enumeration in gwyddion starts with 1
            key = "/0/graph/graph/{:d}".format(graph_id + 1)
            gwyitem = Gwyfile.new_gwyitem_object(key, gwygraph)

            if not add_gwyitem_to_gwycontainer(gwyitem, gwycontainer):
                continue

            # gwycontainer object keeps alive gwygraph objects
            _container_graphs_dic[gwycontainer].append(gwygraph)

            if graph.visible is not None:
                key_visible = '/'.join((key, 'visible'))
                gwyitem_visible = Gwyfile.new_gwyitem_bool(key_visible,
                                                           graph.visible)
                add_gwyitem_to_gwycontainer(gwyitem_visible, gwycontainer)

        return gwycontainer

    def to_gwyfile(self, filename=None):
        """ Write this container to gwy file.
            The file will be overwritten if it exists.

        Args:
            filename (string): name of the gwy file or None.
                               If None, self.filename attribute is used
        """
        if filename is None:
            filename = self.filename

        gwycontainer = self.to_gwy()
        abspath = os.path.abspath(filename)
        gwyitem = Gwyfile.new_gwyitem_string("/filename", abspath)
        add_gwyitem_to_gwycontainer(gwyitem, gwycontainer)
        write_gwycontainer_to_gwyfile(gwycontainer, filename)

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

        # Create list of tuples
        # First element of each tuple is a key for GwyGraphModel data item
        # Second element of each tuple is a key for boolean item
        #     (wheter the graph should be displayed in a window when the file
        #      is loaded)
        graph_keys = [("/0/graph/graph/{:d}".format(graph_id),
                       "/0/graph/graph/{:d}/visible".format(graph_id))
                      for graph_id in graph_ids]

        # Create list of tuples (<cdata GwyGraphModel*>, visibility_flag)
        # First element is <cdata GwyGraphModel*> object
        # Second element is its visibility flag (boolean)
        gwygraphmodels = [(gwyfile.get_gwyitem_object(key[0]),
                           gwyfile.get_gwyitem_bool(key[1]))
                          for key in graph_keys]
        graphs = []

        for gwygraphmodel in gwygraphmodels:
            graph = GwyGraphModel.from_gwy(gwygraphmodel[0])
            graph.visible = gwygraphmodel[1]
            graphs.append(graph)
        return graphs

    @staticmethod
    def _get_filename(gwyfile):
        """Get the name of file The GwyContainer is currently associated with.

        Args:
            gwyfile (Gwyfile): Gwyfile object

        Returns:
            basename (string): basename of the file

        """
        pathname = gwyfile.get_gwyitem_string("/filename")
        if pathname is None:
            return None
        else:
            basename = os.path.basename(pathname)
            return basename

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
