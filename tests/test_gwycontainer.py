import unittest
from unittest.mock import patch, call, Mock

from pygwyfile._libgwyfile import ffi
from pygwyfile.gwyfile import Gwyfile
from pygwyfile.gwycontainer import GwyContainer, read_gwyfile
from pygwyfile.gwychannel import GwyChannel, GwyDataField
from pygwyfile.gwygraph import GwyGraphModel


class GwyContainer_get_channel_ids_TestCase(unittest.TestCase):
    """
    Test _get_channel_ids method in GwyContainer class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()

        patcher_lib = patch('pygwyfile.gwycontainer.lib', autospec=True)
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

        patcher_lib = patch('pygwyfile.gwycontainer.lib', autospec=True)
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

    @patch('pygwyfile.gwycontainer.GwyChannel', autospec=True)
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

    @patch('pygwyfile.gwycontainer.GwyGraphModel', autospec=True)
    @patch.object(GwyContainer, '_get_graph_ids')
    def test_getting_gwygraphmodel_objects(self,
                                           mock_get_graph_ids,
                                           mock_GwyGraphModel):
        """Get <GwyGraphModel*> objects and their visibility flags
           from Gwyfile object
        """
        graph_ids = [1, 2, 3]
        graph_keys = ["/0/graph/graph/{:d}".format(graph_id)
                      for graph_id in graph_ids]
        graph_vis_keys = ["/0/graph/graph/{:d}/visible".format(graph_id)
                          for graph_id in graph_ids]
        mock_get_graph_ids.return_value = graph_ids
        gwyfile = Mock(spec=Gwyfile)
        GwyContainer._dump_graphs(gwyfile)
        gwyfile.get_gwyitem_object.assert_has_calls(
            [call(graph_key) for graph_key in graph_keys])
        gwyfile.get_gwyitem_bool.assert_has_calls(
            [call(graph_vis_key) for graph_vis_key in graph_vis_keys])

    @patch.object(GwyGraphModel, 'from_gwy')
    @patch.object(GwyContainer, '_get_graph_ids')
    def test_returned_value(self,
                            mock_get_graph_ids,
                            mock_GwyGraphModel):
        """Convert <GwyGraphModel*> object to GwyGraphModel objects
        and return the latter
        """
        graph_ids = [1, 2, 3]
        mock_get_graph_ids.return_value = graph_ids
        gwygraphmodels = [Mock() for graph_id in graph_ids]
        gwyfile = Mock(spec=Gwyfile)
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

    @patch('pygwyfile.gwycontainer.GwyContainer', autospec=True)
    @patch.object(GwyContainer, '_get_filename')
    @patch.object(GwyContainer, '_dump_graphs')
    @patch.object(GwyContainer, '_dump_channels')
    def test_from_gwy_method_of_GwyContainer(self,
                                             mock_dump_channels,
                                             mock_dump_graphs,
                                             mock_get_filename,
                                             mock_GwyContainer):
        gwyfile = Mock(spec=Gwyfile)
        channels = [Mock(spec=GwyChannel), Mock(spec=GwyChannel)]
        graphs = [Mock(spec=GwyGraphModel)]
        filename = 'sample.gwy'
        mock_get_filename.return_value = filename
        mock_dump_channels.return_value = channels
        mock_dump_graphs.return_value = graphs
        mock_GwyContainer.return_value = Mock(spec=GwyContainer)
        container = GwyContainer.from_gwy(gwyfile)
        mock_get_filename.assert_has_calls(
            [call(gwyfile)])
        mock_dump_channels.assert_has_calls(
            [call(gwyfile)])
        mock_dump_graphs.assert_has_calls(
            [call(gwyfile)])
        mock_GwyContainer.assert_has_calls(
            [call(filename=filename, channels=channels, graphs=graphs)])
        self.assertEqual(container, mock_GwyContainer.return_value)


class GwyContainer_init(unittest.TestCase):
    """Test constructor of GwyContainer
    """

    def test_raise_TypeError_if_channels_is_not_list_of_GwyChannel(self):
        """Raise TypeError if channels is not list of GwyChannel instances
        """
        self.assertRaises(TypeError,
                          GwyContainer,
                          channels=[Mock(GwyDataField)])

    def test_raise_TypeError_if_graphs_is_not_list_of_GwyGraphModel(self):
        """Raise TypeError if channels is not list of GwyGraphModel instances
        """
        self.assertRaises(TypeError,
                          GwyContainer,
                          graphs=[Mock(GwyChannel)])

    def test_if_channels_exist(self):
        """channels is a list of GwyChannel, graphs is None
        """
        channels = [Mock(GwyChannel), Mock(GwyChannel)]
        container = GwyContainer(channels=channels)
        self.assertEqual(container.channels, channels)
        self.assertEqual(container.graphs, [])

    def test_if_graphs_exist(self):
        """graphs is a list of GwyGraphModel, channels is None
        """
        graphs = [Mock(GwyGraphModel), Mock(GwyGraphModel)]
        container = GwyContainer(graphs=graphs)
        self.assertEqual(container.graphs, graphs)
        self.assertEqual(container.channels, [])

    def test_channels_and_graphs_are_None(self):
        """both channels and graphs are None
        """
        container = GwyContainer()
        self.assertEqual(container.channels, [])
        self.assertEqual(container.graphs, [])

    def test_channels_and_graphs_are_not_None(self):
        """channels is a list of GwyChannel, graphs is a list of GwyGraphModel
        """
        channels = [Mock(GwyChannel), Mock(GwyChannel)]
        graphs = [Mock(GwyGraphModel), Mock(GwyGraphModel)]
        container = GwyContainer(channels=channels, graphs=graphs)
        self.assertEqual(container.channels, channels)
        self.assertEqual(container.graphs, graphs)


class GwyContainer_get_filename(unittest.TestCase):
    """ Tests for GwyContainer._get_filename method"""

    def test_return_None_if_filename_is_unset(self):
        """Return None if "/filename" field is unset in GwyContainer"""
        gwyfile = Mock(spec=Gwyfile)
        gwyfile.get_gwyitem_string.return_value = None
        actual_return = GwyContainer._get_filename(gwyfile)
        gwyfile.get_gwyitem_string.assert_has_calls(
            [call("/filename")])
        self.assertIsNone(actual_return)

    def test_return_basename_of_the_file_if_filename_is_set(self):
        """Return basename "/filename" field is set in GwyContainer"""
        gwyfile = Mock(spec=Gwyfile)
        pathname = "/home/user/data/sample.gwy"
        basename = "sample.gwy"
        gwyfile.get_gwyitem_string.return_value = pathname
        actual_return = GwyContainer._get_filename(gwyfile)
        self.assertEqual(actual_return, basename)


class GwyContainer_to_gwyfile(unittest.TestCase):
    """ Tests for GwyContainer.to_gwyfile method"""
    def setUp(self):
        self.gwycontainer = Mock(spec=GwyContainer)
        self.gwycontainer.to_gwy = Mock(autospec=True)
        self.gwycontainer.to_gwyfile = GwyContainer.to_gwyfile
        self.gwycontainer.filename = 'filename.gwy'
        self.filename = 'another_filename.gwy'

    @patch('pygwyfile.gwycontainer.os.path', autospec=True)
    @patch('pygwyfile.gwycontainer.Gwyfile', autospec=True)
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.write_gwycontainer_to_gwyfile',
           autospec=True)
    def test_create_gwycontainer(self,
                                 mock_write_gwy,
                                 mock_add_gwyitem,
                                 mock_gwyfile,
                                 mock_path):
        """ Create gwycontainer (GwyfileObject*) from this container"""
        self.gwycontainer.to_gwyfile(self.gwycontainer, self.filename)
        self.gwycontainer.to_gwy.assert_has_calls(
            [call()])

    @patch('pygwyfile.gwycontainer.os.path', autospec=True)
    @patch('pygwyfile.gwycontainer.Gwyfile', autospec=True)
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.write_gwycontainer_to_gwyfile',
           autospec=True)
    def test_convert_filename_to_abspath(self,
                                         mock_write_gwy,
                                         mock_add_gwyitem,
                                         mock_gwyfile,
                                         mock_path):
        """Convert filename argument to abspath"""
        self.gwycontainer.to_gwyfile(self.gwycontainer, self.filename)
        mock_path.abspath.assert_has_calls(
            [call(self.filename)])

    @patch('pygwyfile.gwycontainer.os.path', autospec=True)
    @patch('pygwyfile.gwycontainer.Gwyfile', autospec=True)
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.write_gwycontainer_to_gwyfile',
           autospec=True)
    def test_use_filename_attribute_if_filename_arg_is_None(self,
                                                            mock_write_gwy,
                                                            mock_add_gwyitem,
                                                            mock_gwyfile,
                                                            mock_path):
        """Use filename attribute of GwyContainer instance if filename arg.
        is None
        """
        self.gwycontainer.to_gwyfile(self.gwycontainer)
        mock_path.abspath.assert_has_calls(
            [call(self.gwycontainer.filename)])

    @patch('pygwyfile.gwycontainer.os.path', autospec=True)
    @patch('pygwyfile.gwycontainer.new_gwyitem_string', autospec=True)
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.write_gwycontainer_to_gwyfile',
           autospec=True)
    def test_convert_abspath_to_gwyitem(self,
                                        mock_write_gwy,
                                        mock_add_gwyitem,
                                        mock_new_gwyitem_string,
                                        mock_path):
        """ Convert filename abspath to string gwyitem"""
        self.gwycontainer.to_gwyfile(self.gwycontainer, self.filename)
        mock_new_gwyitem_string.assert_has_calls(
            [call("/filename", mock_path.abspath.return_value)])

    @patch('pygwyfile.gwycontainer.os.path', autospec=True)
    @patch('pygwyfile.gwycontainer.new_gwyitem_string', autospec=True)
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.write_gwycontainer_to_gwyfile',
           autospec=True)
    def test_add_filename_gwyitem_to_gwycontainer(self,
                                                  mock_write_gwy,
                                                  mock_add_gwyitem,
                                                  mock_new_gwyitem_string,
                                                  mock_path):
        """ Add created filename string gwyitem to created gwycontainer"""
        self.gwycontainer.to_gwyfile(self.gwycontainer, self.filename)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_string.return_value,
                  self.gwycontainer.to_gwy.return_value)])

    @patch('pygwyfile.gwycontainer.os.path', autospec=True)
    @patch('pygwyfile.gwycontainer.Gwyfile', autospec=True)
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.write_gwycontainer_to_gwyfile',
           autospec=True)
    def test_write_gwycontainer_to_file(self,
                                        mock_write_gwy,
                                        mock_add_gwyitem,
                                        mock_gwyfile,
                                        mock_path):
        """ Write gwycontainer to file"""
        self.gwycontainer.to_gwyfile(self.gwycontainer, self.filename)
        mock_write_gwy.assert_has_calls(
            [call(self.gwycontainer.to_gwy.return_value,
                  self.filename)])


class Func_read_gwyfile_TestCase(unittest.TestCase):
    """ Test read_gwyfile function"""

    @patch.object(GwyContainer, 'from_gwy')
    @patch.object(Gwyfile, 'from_gwy')
    def test_create_Gwyfile_instance(self, mock_gwyfile, mock_gwycontainer):
        """Create Gwyfile instance from file data"""
        filename = 'testfile.gwy'
        read_gwyfile(filename)
        mock_gwyfile.assert_has_calls(
            [call(filename)])

    @patch.object(GwyContainer, 'from_gwy')
    @patch.object(Gwyfile, 'from_gwy')
    def test_create_GwyContainer_instance(self,
                                          mock_gwyfile,
                                          mock_gwycontainer):
        """Create GwyContainer instance from Gwyfile instance"""
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
        """Return created GwyContainer instance"""
        filename = 'testfile.gwy'
        container = Mock(spec=GwyContainer)
        mock_gwycontainer.return_value = container

        actual_return = read_gwyfile(filename)
        expected_return = container

        self.assertEqual(actual_return, expected_return)


class GwyContainer_to_gwy(unittest.TestCase):
    """ Tests for to_gwy method of GwyContainer"""
    def setUp(self):
        self.gwycontainer = Mock(spec=GwyContainer)
        self.gwycontainer.to_gwy = GwyContainer.to_gwy
        self.gwycontainer._add_channels_to_gwycontainer = Mock(autospec=True)
        self.gwycontainer._add_graphs_to_gwycontainer = Mock(autospec=True)

    @patch('pygwyfile.gwycontainer.new_gwycontainer', autospec=True)
    def test_create_new_empty_gwycontainer_object(self, mock_new_gwycontainer):
        """ Create new empty gwycontainer"""
        self.gwycontainer.to_gwy(self.gwycontainer)
        mock_new_gwycontainer.assert_has_calls(
            [call()])

    @patch('pygwyfile.gwycontainer.new_gwycontainer', autospec=True)
    def test_add_channels_to_gwycontainer_object(self, mock_new_gwycontainer):
        """ Add channels to created gwycontainer"""
        self.gwycontainer.to_gwy(self.gwycontainer)
        self.gwycontainer._add_channels_to_gwycontainer.assert_has_calls(
            [call(mock_new_gwycontainer.return_value)])

    @patch('pygwyfile.gwycontainer.new_gwycontainer', autospec=True)
    def test_add_graphs_to_gwycontainer_object(self, mock_new_gwycontainer):
        """ Add graphs to gwycontainer """
        self.gwycontainer.to_gwy(self.gwycontainer)
        self.gwycontainer._add_graphs_to_gwycontainer.assert_has_calls(
            [call(mock_new_gwycontainer.return_value)])

    @patch('pygwyfile.gwycontainer.new_gwycontainer', autospec=True)
    def test_return_gwycontainer(self, mock_new_gwycontainer):
        """ Return created gwycontainer"""
        actual_return = self.gwycontainer.to_gwy(self.gwycontainer)
        self.assertEqual(actual_return, mock_new_gwycontainer.return_value)


class GwyContainer_add_channels_to_gwycontainer(unittest.TestCase):
    """Tests for _add_channels_to_gwycontainer method of GwyContainer class"""
    def setUp(self):
        self.container = Mock(spec=GwyContainer)
        self.gwycontainer = Mock()
        self.container._add_channels_to_gwycontainer = (
            GwyContainer._add_channels_to_gwycontainer)
        self.channel0 = Mock(spec=GwyChannel)
        self.channel1 = Mock(spec=GwyChannel)
        self.container.channels = [self.channel0, self.channel1]

    def test_converting_channels_to_gwychannels(self):
        """ Convert channels to gwychannels and add them to gwycontainer"""
        self.container._add_channels_to_gwycontainer(self.container,
                                                     self.gwycontainer)
        self.channel0.to_gwy.side_effect = self._ch0_to_gwy_side_effect
        self.channel1.to_gwy.side_effect = self._ch1_to_gwy_side_effect

    def _ch0_to_gwy_side_effect(self, *args):
        self.assertEqual(args[0], self.gwycontainer)
        self.assertEqual(args[1], 0)

    def _ch1_to_gwy_side_effect(self, *args):
        self.assertEqual(args[0], self.gwycontainer)
        self.assertEqual(args[1], 1)


class GwyContainer_add_graphs_to_gwycontainer(unittest.TestCase):
    """Tests for _add_graphs_to_gwycontainer method of GwyContainer class"""
    def setUp(self):
        self.container = Mock(spec=GwyContainer)
        self.gwycontainer = Mock()
        self.container._add_graphs_to_gwycontainer = (
            GwyContainer._add_graphs_to_gwycontainer)
        self.graph1 = Mock(spec=GwyGraphModel)
        self.graph2 = Mock(spec=GwyGraphModel)
        self.container.graphs = [self.graph1, self.graph2]

    @patch('pygwyfile.gwycontainer._container_graphs_dic')
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.new_gwyitem_object', autospec=True)
    def test_convert_graphs_to_gwygraph_objects(self,
                                                mock_new_gwyitem_object,
                                                mock_add_gwyitem,
                                                mock_weadref_dic):
        """ Convert graphs to gwygraphmodel objects"""
        self.container._add_graphs_to_gwycontainer(self.container,
                                                   self.gwycontainer)
        self.graph1.to_gwy.assert_has_calls(
            [call()])
        self.graph2.to_gwy.assert_has_calls(
            [call()])

    @patch('pygwyfile.gwycontainer._container_graphs_dic')
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.new_gwyitem_object', autospec=True)
    def test_create_new_gwyitems_from_gwygraphmodel_objects(
            self,
            mock_new_gwyitem_object,
            mock_add_gwyitem,
            mock_weadref_dic):
        """ Create new gwyitems from the gwygraphmodel objects"""
        self.container._add_graphs_to_gwycontainer(self.container,
                                                   self.gwycontainer)
        mock_new_gwyitem_object.assert_has_calls(
            [call('/0/graph/graph/1', self.graph1.to_gwy.return_value),
             call('/0/graph/graph/2', self.graph2.to_gwy.return_value)])

    @patch('pygwyfile.gwycontainer._container_graphs_dic')
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.new_gwyitem_object', autospec=True)
    def test_add_gwyitems_to_gwycontainer(self,
                                          mock_new_gwyitem_object,
                                          mock_add_gwyitem,
                                          mock_weadref_dic):
        """ Add created gwyitems to the gwycontainer"""
        self.container._add_graphs_to_gwycontainer(self.container,
                                                   self.gwycontainer)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_object.return_value,
                  self.gwycontainer)])

    @patch('pygwyfile.gwycontainer._container_graphs_dic')
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.new_gwyitem_object', autospec=True)
    def test_append_weakref_dictionary_with_gwygraph_objects(
            self,
            mock_new_gwyitem_object,
            mock_add_gwyitem,
            mock_weadref_dic):
        """ Append _container_graphs_dic weakref key dictionary to
            prevent removing gwygraph objects by garbage collector
        """
        self.container._add_graphs_to_gwycontainer(self.container,
                                                   self.gwycontainer)
        mock_weadref_dic[self.gwycontainer].append.assert_has_calls(
            [call(self.graph1.to_gwy.return_value),
             call(self.graph2.to_gwy.return_value)])

    @patch('pygwyfile.gwycontainer._container_graphs_dic')
    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.new_gwyitem_object', autospec=True)
    def test_add_graph_visibility_to_gwycontainer(self,
                                                  mock_new_gwyitem_object,
                                                  mock_add_gwyitem,
                                                  mock_weadref_dic):
        """ Add graph visibility data item to gwycontainer """
        self.container._add_graph_visibility_to_gwycontainer = (
            Mock(autospec=True))
        self.container._add_graphs_to_gwycontainer(self.container,
                                                   self.gwycontainer)
        self.container._add_graph_visibility_to_gwycontainer.assert_has_calls(
            [call(self.graph1, self.gwycontainer, "/0/graph/graph/1"),
             call(self.graph2, self.gwycontainer, "/0/graph/graph/2")])


class GwyContainer_add_graph_visibility_to_gwycontainer(unittest.TestCase):
    """Tests for GwyContainer._add_graph_visibility_to_gwycontainer"""
    def setUp(self):
        self.gwycontainer = Mock()
        self.graph = Mock(spec=GwyGraphModel)
        self.graph.visible = True
        self.key = "/0/graph/graph/1"

    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.new_gwyitem_bool', autospec=True)
    def test_convert_visible_to_bool_gwyitem(self,
                                             mock_new_gwyitem_bool,
                                             mock_add_gwyitem):
        """ Create bool gwyitem from visible attribute"""
        GwyContainer._add_graph_visibility_to_gwycontainer(self.graph,
                                                           self.gwycontainer,
                                                           self.key)
        mock_new_gwyitem_bool.assert_has_calls(
            [call("/0/graph/graph/1/visible", self.graph.visible)])

    @patch('pygwyfile.gwycontainer.add_gwyitem_to_gwycontainer', autospec=True)
    @patch('pygwyfile.gwycontainer.new_gwyitem_bool', autospec=True)
    def test_add_gwyitems_to_gwycontainer(self,
                                          mock_new_gwyitem_bool,
                                          mock_add_gwyitem):
        """ Add bool gwyitem to gwycontainer"""
        GwyContainer._add_graph_visibility_to_gwycontainer(self.graph,
                                                           self.gwycontainer,
                                                           self.key)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_bool.return_value,
                  self.gwycontainer)])


if __name__ == '__main__':
    unittest.main()
