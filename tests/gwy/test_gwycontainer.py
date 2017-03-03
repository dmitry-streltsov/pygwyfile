import unittest
from unittest.mock import patch, call, Mock

from gwydb.gwy._libgwyfile import ffi
from gwydb.gwy.gwyfile import Gwyfile
from gwydb.gwy.gwycontainer import GwyContainer, read_gwyfile
from gwydb.gwy.gwychannel import GwyChannel, GwyDataField
from gwydb.gwy.gwygraph import GwyGraphModel


class GwyContainer_get_channel_ids_TestCase(unittest.TestCase):
    """
    Test _get_channel_ids method in GwyContainer class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()

        patcher_lib = patch('gwydb.gwy.gwycontainer.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_libgwyfile_function_returns_non_zero_channels(self):
        """
        Returns list of channel ids if their number is not zero
        """

        enum_chs = self.mock_lib.gwyfile_object_container_enumerate_channels
        enum_chs.side_effect = self._side_effect_non_zero_channels
        ids = GwyContainer._get_channel_ids(self.gwyfile)
        self.assertEqual(ids, [0, 1, 2])

    def _side_effect_non_zero_channels(self, c_gwyfile, nchannelsp):
        """
        Returns 3 channels with ids = 0, 1 and 2
        """

        nchannelsp[0] = 3
        ids = ffi.new("int[]", [0, 1, 2])
        return ids

    def test_libgwyfile_function_returns_null(self):
        """
        Returns empty list if libgwyfile function returns NULL
        """

        enum_ch = self.mock_lib.gwyfile_object_container_enumerate_channels
        enum_ch.return_value = ffi.NULL
        ids = GwyContainer._get_channel_ids(self.gwyfile)
        self.assertEqual(ids, [])


class GwyContainer_get_graph_ids_TestCase(unittest.TestCase):
    """
    Test _get_graph_ids method in GwyContainer class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()

        patcher_lib = patch('gwydb.gwy.gwycontainer.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_libgwyfile_function_returns_non_zero_channels(self):
        """
        Returns list of graph ids if their number is not zero
        """

        self.mock_lib.gwyfile_object_container_enumerate_graphs.side_effect = (
            self._side_effect_non_zero_graphs)
        ids = GwyContainer._get_graph_ids(self.gwyfile)
        self.assertEqual(ids, [1, 2])

    def _side_effect_non_zero_graphs(self, c_gwyfile, ngraphsp):
        """
        Returns 2 graphs with ids = 1 and 2
        """

        ngraphsp[0] = 2
        ids = ffi.new("int[]", [1, 2])
        return ids

    def test_libgwyfile_function_returns_null(self):
        """
        Returns empty list if libgwyfile function returns NULL
        """

        enum_graphs = self.mock_lib.gwyfile_object_container_enumerate_graphs
        enum_graphs.return_value = ffi.NULL
        ids = GwyContainer._get_graph_ids(self.gwyfile)
        self.assertEqual(ids, [])


class GwyContainer_dump_channels(unittest.TestCase):
    """Test _dump_channels method of GwyContainer class
    """

    @patch.object(GwyContainer, '_get_channel_ids')
    def test_no_channels_in_container(self, mock_get_channel_ids):
        """Return empty list if channel_ids list is empty
        """
        mock_get_channel_ids.return_value = []
        gwyfile = Mock(spec=Gwyfile)
        channels = GwyContainer._dump_channels(gwyfile)
        self.assertEqual(channels, [])

    @patch('gwydb.gwy.gwycontainer.GwyChannel', autospec=True)
    @patch.object(GwyContainer, '_get_channel_ids')
    def test_convert_channel_ids_to_GwyChannel_list(self,
                                                    mock_get_channel_ids,
                                                    mock_GwyChannel):
        """Convert list of channel_ids to list of GwyChannel objects
        and return the latter
        """
        channel_ids = [0, 1, 2]
        mock_get_channel_ids.return_value = channel_ids
        gwyfile = Mock(spec=Gwyfile)
        channels = GwyContainer._dump_channels(gwyfile)

        self.assertListEqual(channels,
                             [mock_GwyChannel.from_gwy(gwyfile, channel_id)
                              for channel_id in channel_ids])


class GwyContainer_dump_graphs(unittest.TestCase):
    """Test _dump_graphs method of GwyContainer class
    """

    @patch.object(GwyContainer, '_get_graph_ids')
    def test_no_graphs_in_container(self, mock_get_graph_ids):
        """Return empty list if graph_ids list is empty
        """
        mock_get_graph_ids.return_value = []
        gwyfile = Mock(spec=Gwyfile)
        graphs = GwyContainer._dump_graphs(gwyfile)
        self.assertEqual(graphs, [])

    @patch.object(Gwyfile, 'get_gwyobject')
    @patch('gwydb.gwy.gwycontainer.GwyGraphModel', autospec=True)
    @patch.object(GwyContainer, '_get_graph_ids')
    def test_getting_gwygraphmodel_objects(self,
                                           mock_get_graph_ids,
                                           mock_GwyGraphModel,
                                           mock_get_gwyobject):
        """Get <GwyGraphModel*> objects from gwyfile
        """
        graph_ids = [1, 2, 3]
        graph_keys = ["/0/graph/graph/1",
                      "/0/graph/graph/2",
                      "/0/graph/graph/3"]
        mock_get_graph_ids.return_value = graph_ids
        gwyfile = Mock(spec=Gwyfile)
        mock_get_gwyobject.return_value = Mock()
        GwyContainer._dump_graphs(gwyfile)
        mock_get_gwyobject.assert_has_calls(
            [call(gwyfile, graph_key) for graph_key in graph_keys])

    @patch.object(Gwyfile, 'get_gwyobject')
    @patch.object(GwyGraphModel, 'from_gwy')
    @patch.object(GwyContainer, '_get_graph_ids')
    def test_returned_value(self,
                            mock_get_graph_ids,
                            mock_GwyGraphModel,
                            mock_get_gwyobject):
        """Convert <GwyGraphModel*> object to GwyGraphModel objects
        and return the latter
        """
        graph_ids = [1, 2, 3]
        mock_get_graph_ids.return_value = graph_ids
        gwygraphmodels = [Mock() for graph_id in graph_ids]
        gwyfile = Mock(spec=Gwyfile)
        mock_get_gwyobject.return_value = gwygraphmodels
        graphs = GwyContainer._dump_graphs(gwyfile)
        self.assertListEqual(graphs,
                             [mock_GwyGraphModel(gwygraphmodel)
                              for gwygraphmodel in gwygraphmodels])


class GwyContainer_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyContainer
    """

    def test_raise_TypeError_if_gwyfile_is_not_Gwyfile(self):
        """Raise TypeError exception if gwyfile is not a Gwyfile
        instance
        """
        self.assertRaises(TypeError,
                          GwyContainer.from_gwy,
                          gwyfile='test_string')

    @patch('gwydb.gwy.gwycontainer.GwyContainer', autospec=True)
    @patch.object(GwyContainer, '_dump_graphs')
    @patch.object(GwyContainer, '_dump_channels')
    def test_from_gwy_method_of_GwyContainer(self,
                                             mock_dump_channels,
                                             mock_dump_graphs,
                                             mock_GwyContainer):
        gwyfile = Mock(spec=Gwyfile)
        gwyfile.filename = 'test.gwy'
        channels = [Mock(spec=GwyChannel), Mock(spec=GwyChannel)]
        graphs = [Mock(spec=GwyGraphModel)]
        mock_dump_channels.return_value = channels
        mock_dump_graphs.return_value = graphs
        mock_GwyContainer.return_value = Mock(spec=GwyContainer)
        container = GwyContainer.from_gwy(gwyfile)
        mock_dump_channels.assert_has_calls(
            [call(gwyfile)])
        mock_dump_graphs.assert_has_calls(
            [call(gwyfile)])
        mock_GwyContainer.assert_has_calls(
            [call(filename=gwyfile.filename,
                  channels=channels,
                  graphs=graphs)])
        self.assertEqual(container, mock_GwyContainer.return_value)


class GwyContainer_init(unittest.TestCase):
    """Test constructor of GwyContainer
    """

    def test_raise_TypeError_if_channels_is_not_list_of_GwyChannel(self):
        """Raise TypeError if channels is not list of GwyChannel instances
        """
        self.assertRaises(TypeError,
                          GwyContainer,
                          filename='test.gwy',
                          channels=[Mock(GwyDataField)])

    def test_raise_TypeError_if_graphs_is_not_list_of_GwyGraphModel(self):
        """Raise TypeError if channels is not list of GwyGraphModel instances
        """
        self.assertRaises(TypeError,
                          GwyContainer,
                          filename='test.gwy',
                          graphs=[Mock(GwyChannel)])

    def test_if_channels_exist(self):
        """channels is a list of GwyChannel, graphs is None
        """
        filename = 'test.gwy'
        channels = [Mock(GwyChannel), Mock(GwyChannel)]
        container = GwyContainer(filename=filename, channels=channels)
        self.assertEqual(container.channels, channels)
        self.assertEqual(container.graphs, [])

    def test_if_graphs_exist(self):
        """graphs is a list of GwyGraphModel, channels is None
        """
        filename = 'test.gwy'
        graphs = [Mock(GwyGraphModel), Mock(GwyGraphModel)]
        container = GwyContainer(filename=filename, graphs=graphs)
        self.assertEqual(container.graphs, graphs)
        self.assertEqual(container.channels, [])

    def test_channels_and_graphs_are_None(self):
        """both channels and graphs are None
        """
        filename = 'test.gwy'
        container = GwyContainer(filename=filename)
        self.assertEqual(container.channels, [])
        self.assertEqual(container.graphs, [])

    def test_channels_and_graphs_are_not_None(self):
        """channels is a list of GwyChannel, graphs is a list of GwyGraphModel
        """
        filename = 'test.gwy'
        channels = [Mock(GwyChannel), Mock(GwyChannel)]
        graphs = [Mock(GwyGraphModel), Mock(GwyGraphModel)]
        container = GwyContainer(filename=filename,
                                 channels=channels,
                                 graphs=graphs)
        self.assertEqual(container.channels, channels)
        self.assertEqual(container.graphs, graphs)
        self.assertEqual(container.filename, filename)


class Func_read_gwyfile_TestCase(unittest.TestCase):
    """
    Test read_gwyfile function
    """

    @patch.object(GwyContainer, 'from_gwy')
    @patch.object(Gwyfile, 'from_gwy')
    def test_create_Gwyfile_instance(self, mock_gwyfile, mock_gwycontainer):
        """Create Gwyfile instance from file data
        """
        filename = 'testfile.gwy'
        read_gwyfile(filename)
        mock_gwyfile.assert_has_calls(
            [call(filename)])

    @patch.object(GwyContainer, 'from_gwy')
    @patch.object(Gwyfile, 'from_gwy')
    def test_create_GwyContainer_instance(self,
                                          mock_gwyfile,
                                          mock_gwycontainer):
        """Create GwyContainer instance from Gwyfile instance
        """

        filename = 'testfile.gwy'
        gwyfile = Mock(spec=Gwyfile)
        mock_gwyfile.return_value = gwyfile

        read_gwyfile(filename)

        mock_gwycontainer.assert_has_calls(
            [call(gwyfile)])

    @patch.object(GwyContainer, 'from_gwy')
    @patch.object(Gwyfile, 'from_gwy')
    def test_returned_value(self,
                            mock_gwyfile,
                            mock_gwycontainer):
        """Return created GwyContainer instance
        """
        filename = 'testfile.gwy'
        container = Mock(spec=GwyContainer)
        mock_gwycontainer.return_value = container

        actual_return = read_gwyfile(filename)
        expected_return = container

        self.assertEqual(actual_return, expected_return)
