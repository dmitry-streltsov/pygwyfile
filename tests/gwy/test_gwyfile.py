import unittest
from unittest.mock import patch, call, ANY, Mock

import numpy as np

from gwydb.gwy.gwyfile import Gwyfile
from gwydb.gwy.gwyfile import GwyfileError, GwyfileErrorCMsg
from gwydb.gwy.gwyfile import GwySelection
from gwydb.gwy.gwyfile import GwyPointSelections, GwyPointerSelections
from gwydb.gwy.gwyfile import GwyLineSelections, GwyRectangleSelections
from gwydb.gwy.gwyfile import GwyEllipseSelections
from gwydb.gwy.gwyfile import GwyDataField
from gwydb.gwy.gwyfile import GwyGraphCurve
from gwydb.gwy.gwyfile import GwyGraphModel
from gwydb.gwy.gwyfile import ffi, lib
from gwydb.gwy.gwyfile import read_gwyfile


class Func_read_gwyfile_TestCase(unittest.TestCase):
    """
    Test read_gwyfile function
    """

    def setUp(self):
        self.filename = 'test.gwy'

        patcher_isfile = patch('gwydb.gwy.gwyfile.os.path.isfile',
                               autospec=True)
        self.addCleanup(patcher_isfile.stop)
        self.mock_isfile = patcher_isfile.start()

        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        patcher_Gwyfile = patch('gwydb.gwy.gwyfile.Gwyfile',
                                autospec=True)
        self.addCleanup(patcher_Gwyfile.stop)
        self.mock_Gwyfile = patcher_Gwyfile.start()

        self.error_msg = "Test error message"

    def test_raise_exception_if_file_doesnt_exist(self):
        """
        Raise OSError exception if file does not exist
        """

        self.mock_isfile.return_value = False
        self.assertRaises(OSError, read_gwyfile, self.filename)

    def test_arg_of_gwyfile_read_file(self):
        """If file exists call gwyfile_read_file function.

        Check arguments passed to this function
        """

        self.mock_isfile.return_value = True
        read_gwyfile(self.filename)
        self.mock_isfile.assert_has_calls(
            [call(self.filename)])
        self.mock_lib.gwyfile_read_file.assert_has_calls(
            [call(self.filename.encode('utf-8'), ANY)])

    def test_gwyfile_read_file_fails_without_message(self):
        """Raise GwyfileError exception without message

        Raise GwyfileError exception without message if
        gwyfile_read_file returns NULL and if GwyfileError** is NULL
        """

        self.mock_isfile.return_value = True
        self.mock_lib.gwyfile_read_file.return_value = ffi.NULL
        self.assertRaises(GwyfileError, read_gwyfile, self.filename)

    def test_gwyfile_read_file_fails_with_message(self):
        """Raise GwyError exception with message

        Raise GwyError exception with message if gwyfile_read_file
        returns NULL and is GwyfileError.message is not NULL
        """

        self.mock_isfile.return_value = True
        gwyfile_read_file = self.mock_lib.gwyfile_read_file
        gwyfile_read_file.side_effect = self._side_effect_with_msg
        self.assertRaisesRegex(GwyfileErrorCMsg,
                               self.error_msg,
                               read_gwyfile,
                               self.filename)

    def _side_effect_with_msg(self, *args):
        """
        gwyfile_read_file returns NULL with error_msg
        """

        errorp = args[1]
        c_error_msg = ffi.new("char[]", self.error_msg.encode('utf-8'))
        errorp[0].message = c_error_msg
        return ffi.NULL

    def test_check_returned_value(self):
        """
        Return the object returned by gwyfile_read_file
        """

        self.mock_isfile.return_value = True
        expected_return = self.mock_Gwyfile.return_value
        actual_return = read_gwyfile(self.filename)
        self.assertIs(expected_return, actual_return)


class Gwyfile_init_TestCase(unittest.TestCase):
    """Test constructor of the Gwyfile class

    Gwyfile class is initialized by passing <cdata GwyfileObject*> to
    its constructor
    """

    def test_raise_exception_if_c_gwyfile_is_empty(self):
        """
        Raise GwyfileError exception if <GwyfileObject*> is empty
        """

        c_gwyfile = ffi.NULL
        self.assertRaises(GwyfileError, Gwyfile, c_gwyfile)

    @patch('gwydb.gwy.gwyfile.lib', autospec=True)
    def test_raise_exception_if_top_level_object_is_empty(self, mock_lib):
        """
        Raise GwyfileError exception if top-level object is empty
        """

        c_gwyfile = Mock()
        mock_lib.gwyfile_object_name.return_value = ffi.NULL
        error_msg = 'The top-level object of c_gwyfile is empty'
        self.assertRaisesRegex(GwyfileError,
                               error_msg,
                               Gwyfile,
                               c_gwyfile)

    @patch('gwydb.gwy.gwyfile.lib', autospec=True)
    def test_check_top_level_object_of_c_gwyfile(self, mock_lib):
        """Raise GwyfileError exception if top-level object is not
        'GwyContainer' C string
        """

        c_gwyfile = Mock()
        test_name = ffi.new("char[]", b"non-GwyContainer")
        mock_lib.gwyfile_object_name.return_value = test_name
        self.assertRaises(GwyfileError, Gwyfile, c_gwyfile)

    @patch('gwydb.gwy.gwyfile.lib', autospec=True)
    def test_attribute_of_GwyFile_instance(self, mock_lib):
        """
        Create self.c_gwyfile attribute
        """

        c_gwyfile = Mock()
        test_name = ffi.new("char[]", b"GwyContainer")
        mock_lib.gwyfile_object_name.return_value = test_name
        test_instance = Gwyfile(c_gwyfile)
        self.assertIs(c_gwyfile, test_instance.c_gwyfile)


class Gwyfile_get_channels_ids_TestCase(unittest.TestCase):
    """
    Test get_channels_ids method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile.get_channels_ids = Gwyfile.get_channels_ids

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_libgwyfile_function_returns_non_zero_channels(self):
        """
        Returns list of channels ids if their number is not zero
        """

        enum_chs = self.mock_lib.gwyfile_object_container_enumerate_channels
        enum_chs.side_effect = self._side_effect_non_zero_channels
        ids = self.gwyfile.get_channels_ids(self.gwyfile)
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
        ids = self.gwyfile.get_channels_ids(self.gwyfile)
        self.assertEqual(ids, [])


class Gwyfile_get_title(unittest.TestCase):
    """
    Test get_title method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_title = Gwyfile.get_title
        self.gwyfile._gwyfile_get_object = Mock(autospec=True)
        self.gwyfile._gwyfile_get_object.return_value = ffi.new("char[]",
                                                                b"Title")

        self.channel_id = 0

    def test_check_args_passing_to__gwyfile_get_object(self):
        """
        Check args passing to _gwyfile_get_object method
        """

        self.gwyfile.get_title(self.gwyfile, self.channel_id)
        self.gwyfile._gwyfile_get_object.assert_has_calls(
            [call("/{:d}/data/title".format(self.channel_id))])

    def test_returned_value(self):
        """
        Check returned value of get_title method
        """

        title = self.gwyfile.get_title(self.gwyfile, self.channel_id)
        self.assertEqual(title, 'Title')


class Gwyfile__gwyfile_get_object_TestCase(unittest.TestCase):
    """
    Test _gwyfile_get_object method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile._gwyfile_get_object = Gwyfile._gwyfile_get_object

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.test_key = '/0/data'

    def test_raise_exception_if_data_item_is_not_found(self):
        """
        Raise GwyfileError if data item is not found
        """

        self.mock_lib.gwyfile_object_get.return_value = ffi.NULL
        self.assertRaises(GwyfileError,
                          self.gwyfile._gwyfile_get_object,
                          self.gwyfile, self.test_key)

    def test_raise_exception_if_object_is_not_found(self):
        """
        Raise GwyfileError if object in the data item is empty
        """

        self.mock_lib.gwyfile_item_get_object.return_value = ffi.NULL
        mock_item = self.mock_lib.gwyfile_object_get.return_value
        self.assertRaises(GwyfileError,
                          self.gwyfile._gwyfile_get_object,
                          self.gwyfile, mock_item)

    def test_check_args_of_libgwyfile_functions(self):
        """
        Check arguments passed to Libgwyfile functions
        """

        mock_item = self.mock_lib.gwyfile_object_get.return_value

        self.gwyfile._gwyfile_get_object(self.gwyfile, self.test_key)

        self.mock_lib.gwyfile_object_get.assert_has_calls(
            [call(self.gwyfile.c_gwyfile, self.test_key.encode('utf-8'))])
        self.mock_lib.gwyfile_item_get_object.assert_has_calls(
            [call(mock_item)])

    def test_check_returned_value(self):
        """
        Function returns object returned by gwyfile_item_get_object
        """

        mock_object = self.mock_lib.gwyfile_item_get_object.return_value
        returned_object = self.gwyfile._gwyfile_get_object(self.gwyfile,
                                                           self.test_key)
        self.assertIs(mock_object, returned_object)


class Gwyfile__gwydf_get_data(unittest.TestCase):
    """
    Test _gwydf_get_data method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile._gwydf_get_data = Gwyfile._gwydf_get_data

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.key = '/0/data'
        self.xres = 256
        self.yres = 256
        self.data = np.random.rand(self.xres, self.yres)
        self.falsep = ffi.new("bool*", False)
        self.truep = ffi.new("bool*", True)
        self.errorp = ffi.new("GwyfileError**")
        self.error_msg = "Test error message"

    def test_raise_exception_without_msg_if_df_looks_unacceptable(self):
        """Raise GwyfileError exception without error message

        Raise GwyfileError exception with error message if
        gwyfile_object_datafield_get returns False and
        GwyfileError.message is NULL
        """

        self.mock_lib.gwyfile_object_datafield_get.return_value = self.falsep[
            0]
        self.assertRaises(GwyfileError,
                          self.gwyfile._gwydf_get_data,
                          self.gwyfile,
                          self.key,
                          self.xres,
                          self.yres)

    def test_raise_exception_with_msg_if_df_looks_unacceptable(self):
        """Raise GwyfileError exception with error message

        Raise GwyfileError exception with error message if
        gwyfile_object_datafield_get returns False and
        GwyfileError.message is not NULL
        """

        gwyfile_object_df_get = self.mock_lib.gwyfile_object_datafield_get
        gwyfile_object_df_get.side_effect = self._side_effect_with_msg
        self.assertRaisesRegex(GwyfileErrorCMsg,
                               self.error_msg,
                               self.gwyfile._gwydf_get_data,
                               self.gwyfile,
                               self.key,
                               self.xres,
                               self.yres)

    def _side_effect_with_msg(self, *args):
        """
        gwyfile_object_datafield_get returns False with error_msg
        """

        errorp = args[1]
        c_error_msg = ffi.new("char[]", self.error_msg.encode('utf-8'))
        errorp[0].message = c_error_msg
        return self.falsep[0]

    def test_returned_data(self):
        """
        Check returned data numpy array
        """

        gwyfile_object_df_get = self.mock_lib.gwyfile_object_datafield_get
        gwyfile_object_df_get.side_effect = self._side_effect
        self.df = self.gwyfile._gwyfile_get_object.return_value

        data = self.gwyfile._gwydf_get_data(self.gwyfile,
                                            self.key,
                                            self.xres,
                                            self.yres)

        np.testing.assert_almost_equal(self.data, data)

    def _side_effect(self, *args):

        # first arg is GwyDatafield returned by _gwyfile_get_object
        self.assertEqual(args[0], self.df)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(self.errorp)

        # last arg in Null
        self.assertEqual(args[-1], ffi.NULL)

        # create dict from names and types of pointers in args
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        datap = arg_dict['data']
        datap[0] = ffi.cast("double*", self.data.ctypes.data)

        return self.truep[0]


class Gwyfile__getobject_check(unittest.TestCase):
    """
    Test _getobject_check method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile._gwyobject_check = Gwyfile._gwyobject_check
        self.key = '/0/mask'

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_check_libgwyfile_function_args(self):
        """
        Check args passed to gwyfile_object_get function
        """

        self.gwyfile._gwyobject_check(self.gwyfile, self.key)
        self.mock_lib.gwyfile_object_get.assert_has_calls(
            [call(self.gwyfile.c_gwyfile, self.key.encode('utf-8'))])

    def test_return_False_if_libgwyfile_func_returns_NULL(self):
        """
        Return False if gwyfile_object_get returns NULL
        """

        self.mock_lib.gwyfile_object_get.return_value = ffi.NULL
        value = self.gwyfile._gwyobject_check(self.gwyfile, self.key)
        self.assertIs(value, False)

    def test_return_True_if_libgwyfile_func_returns_nonNULL(self):
        """
        Return True if gwyfile_object_get returns not NULL
        """

        value = self.gwyfile._gwyobject_check(self.gwyfile, self.key)
        self.assertIs(value, True)


class Gwyfile_get_metadata(unittest.TestCase):
    """
    Test get_metadata method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_metadata = Gwyfile.get_metadata
        self.gwyfile._gwydf_get_metadatadata = Mock(autospec=True)

        self.channel_id = 1

    def test_check_args_passing_to__gwydf_get_metadata(self):
        """
        Check arguments passing to _gwydf_get_metadata method
        """

        self.gwyfile.get_metadata(self.gwyfile,
                                  self.channel_id)
        self.gwyfile._gwydf_get_metadata.assert_has_calls(
            [call("/{:d}/data".format(self.channel_id))])

    def test_check_returned_value(self):
        """
        Check value returned by _get_data method
        """

        expected_return = self.gwyfile._gwydf_get_metadata.return_value
        actual_return = self.gwyfile.get_metadata(self.gwyfile,
                                                  self.channel_id)
        self.assertEqual(actual_return, expected_return)


class Gwyfile_get_data(unittest.TestCase):
    """
    Test get_data method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_data = Gwyfile.get_data
        self.gwyfile._gwydf_get_data = Mock(autospec=True)

        self.channel_id = 1
        self.xres = 256
        self.yres = 256

    def test_check_args_passing_to__gwydf_get_data(self):
        """
        Check arguments passing to _gwydf_get_data method
        """

        self.gwyfile.get_data(self.gwyfile,
                              self.channel_id,
                              self.xres,
                              self.yres)
        self.gwyfile._gwydf_get_data.assert_has_calls(
            [call("/{:d}/data".format(self.channel_id),
                  self.xres,
                  self.yres)])

    def test_check_returned_value(self):
        """
        Check value returned by get_data method
        """

        expected_return = self.gwyfile._gwydf_get_data.return_value
        actual_return = self.gwyfile.get_data(self.gwyfile,
                                              self.channel_id,
                                              self.xres,
                                              self.yres)
        self.assertEqual(actual_return, expected_return)


class Gwyfile_get_mask_metadata(unittest.TestCase):
    """
    Test get_mask_metadata method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_mask_metadata = Gwyfile.get_mask_metadata
        self.gwyfile._gwydf_get_metadatadata = Mock(autospec=True)

        self.channel_id = 1

    def test_check_args_passing_to__gwydf_get_metadata(self):
        """
        Check arguments passing to _gwydf_get_metadata method
        """

        self.gwyfile.get_mask_metadata(self.gwyfile,
                                       self.channel_id)
        self.gwyfile._gwydf_get_metadata.assert_has_calls(
            [call("/{:d}/mask".format(self.channel_id))])

    def test_check_returned_value(self):
        """
        Check value returned by get_mask_metadata method
        """

        expected_return = self.gwyfile._gwydf_get_metadata.return_value
        actual_return = self.gwyfile.get_mask_metadata(self.gwyfile,
                                                       self.channel_id)
        self.assertEqual(actual_return, expected_return)


class Gwyfile_get_mask_data(unittest.TestCase):
    """
    Test get_mask_data method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_mask_data = Gwyfile.get_mask_data
        self.gwyfile._gwydf_get_data = Mock(autospec=True)

        self.channel_id = 1
        self.xres = 256
        self.yres = 256

    def test_check_args_passing_to__gwydf_get_data(self):
        """
        Check arguments passing to _gwydf_get_data method
        """

        self.gwyfile.get_mask_data(self.gwyfile,
                                   self.channel_id,
                                   self.xres,
                                   self.yres)
        self.gwyfile._gwydf_get_data.assert_has_calls(
            [call("/{:d}/mask".format(self.channel_id),
                  self.xres,
                  self.yres)])

    def test_check_returned_value(self):
        """
        Check value returned by get_mask_data method
        """

        expected_return = self.gwyfile._gwydf_get_data.return_value
        actual_return = self.gwyfile.get_mask_data(self.gwyfile,
                                                   self.channel_id,
                                                   self.xres,
                                                   self.yres)
        self.assertEqual(actual_return, expected_return)


class Gwyfile_get_presentation_metadata(unittest.TestCase):
    """
    Test get_presentation_metadata method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_presentation_metadata = (
            Gwyfile.get_presentation_metadata)
        self.gwyfile._gwydf_get_metadatadata = Mock(autospec=True)

        self.channel_id = 1

    def test_check_args_passing_to__gwydf_get_metadata(self):
        """
        Check arguments passing to _gwydf_get_metadata method
        """

        self.gwyfile.get_presentation_metadata(self.gwyfile,
                                               self.channel_id)
        self.gwyfile._gwydf_get_metadata.assert_has_calls(
            [call("/{:d}/show".format(self.channel_id))])

    def test_check_returned_value(self):
        """
        Check value returned by get_presentation_metadata method
        """

        expected_return = self.gwyfile._gwydf_get_metadata.return_value
        actual_return = self.gwyfile.get_presentation_metadata(self.gwyfile,
                                                               self.channel_id)
        self.assertEqual(actual_return, expected_return)


class Gwyfile_get_presentation_data(unittest.TestCase):
    """
    Test get_presentation_data method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_presentation_data = Gwyfile.get_presentation_data
        self.gwyfile._gwydf_get_data = Mock(autospec=True)

        self.channel_id = 1
        self.xres = 256
        self.yres = 256

    def test_check_args_passing_to__gwydf_get_data(self):
        """
        Check arguments passing to _gwydf_get_data method
        """

        self.gwyfile.get_presentation_data(self.gwyfile,
                                           self.channel_id,
                                           self.xres,
                                           self.yres)
        self.gwyfile._gwydf_get_data.assert_has_calls(
            [call("/{:d}/show".format(self.channel_id),
                  self.xres,
                  self.yres)])

    def test_check_returned_value(self):
        """
        Check value returned by get_mask_data method
        """

        expected_return = self.gwyfile._gwydf_get_data.return_value
        actual_return = self.gwyfile.get_presentation_data(self.gwyfile,
                                                           self.channel_id,
                                                           self.xres,
                                                           self.yres)
        self.assertEqual(actual_return, expected_return)


class Gwyfile_get_graphmodel_metadata(unittest.TestCase):
    """
    Test get_graphmodel_metadata of Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_graphmodel_metadata = Gwyfile.get_graphmodel_metadata

        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.graph_id = 1
        self.graphmodel = Mock()

    def test_check_graphmodel_object_exists(self):
        """
        Check existence of the graphmodel object with the graph_id
        """

        key = "/0/graph/graph/{:d}".format(self.graph_id)
        self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                             self.graph_id)
        self.gwyfile._gwyobject_check.assert_has_calls(
            [call(key)])

    def test_return_empty_dic_if_graphmodel_obj_does_not_exist(self):
        """
        Return empty dictionary if graphmodel object does not exist
        """

        self.gwyfile._gwyobject_check.return_value = False
        actual_return = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                             self.graph_id)
        self.assertDictEqual(actual_return, {})

    def test_arg_of_gwyfile_get_object_func(self):
        """
        Get graphmodel object with graph_id
        """

        key = "/0/graph/graph/{:d}".format(self.graph_id)
        self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                             self.graph_id)
        self.gwyfile._gwyfile_get_object.assert_has_calls(
            [call(key)])

    def test_positional_args_of_libgwyfile_func_call(self):
        """
        Call gwyfile_object_graphmodel_get C function.

        First arg of the C func is graphmodel obj
        Second arg of the C func is GwyfileError**
        Last arg of the C func is NULL
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._graphmodel_get_pos_args
        self.gwyfile._gwyfile_get_object.return_value = self.graphmodel
        self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                             self.graph_id)

    def _graphmodel_get_pos_args(self, *args):
        """
        Check first, second and last args of gwyfile_object_graphmodel_get

        First arg of the C function is graphmodel obj
        Second arg of the C function is GwyfileError**
        Last arg of the C function is NULL
        """

        # first arg is graphmodel object returned by _gwyfile_get_object
        self.assertEqual(args[0], self.graphmodel)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(ffi.new("GwyfileError**"))

        # last arg in Null
        self.assertEqual(args[-1], ffi.NULL)

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_number_of_curves(self):
        """
        Test getting number of curves from graphmodel object
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._number_of_curves
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['ncurves'], 3)

    def _number_of_curves(self, *args):
        """
        Return 3 as a number of curves in graphmodel object
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['ncurves'][0] = 3

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_title_field_is_not_empty(self):
        """
        'title' field in graphmodel object is not empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._title_is_not_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['title'], "test title")

    def _title_is_not_empty(self, *args):
        """
        Write "test title" C string to title field
        """

        title = ffi.new("char[]", b"test title")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['title'][0] = title

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_title_field_is_empty(self):
        """
        'title' field in graphmodel object is empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._title_is_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['title'], '')

    def _title_is_empty(self, *args):
        """
        Write NULL to title field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['title'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_top_label_field_is_not_empty(self):
        """
        'top_label' field in graphmodel object is not empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._top_label_is_not_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['top_label'], "test top label")

    def _top_label_is_not_empty(self, *args):
        """
        Write "test top label" C string to 'top_label' field
        """

        top_label = ffi.new("char[]", b"test top label")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['top_label'][0] = top_label

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_top_label_field_is_empty(self):
        """
        'top_label' field in graphmodel object is empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._top_label_is_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['top_label'], '')

    def _top_label_is_empty(self, *args):
        """
        Write NULL to top_label field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['top_label'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_left_label_field_is_not_empty(self):
        """
        'left_label' field in graphmodel object is not empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._left_label_is_not_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['left_label'], "test left label")

    def _left_label_is_not_empty(self, *args):
        """
        Write "test left label" C string to 'left_label' field
        """

        left_label = ffi.new("char[]", b"test left label")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['left_label'][0] = left_label

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_left_label_field_is_empty(self):
        """
        'left_label' field in graphmodel object is empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._left_label_is_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['left_label'], '')

    def _left_label_is_empty(self, *args):
        """
        Write NULL to left_label field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['left_label'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_right_label_field_is_not_empty(self):
        """
        'right_label' field in graphmodel object is not empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._right_label_is_not_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['right_label'], "test right label")

    def _right_label_is_not_empty(self, *args):
        """
        Write "test right label" C string to 'right_label' field
        """

        right_label = ffi.new("char[]", b"test right label")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['right_label'][0] = right_label

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_right_label_field_is_empty(self):
        """
        'right_label' field in graphmodel object is empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._right_label_is_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['right_label'], '')

    def _right_label_is_empty(self, *args):
        """
        Write NULL to right_label field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['right_label'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_bottom_label_field_is_not_empty(self):
        """
        'bottom_label' field in graphmodel object is not empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._bottom_label_is_not_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['bottom_label'], "test bottom label")

    def _bottom_label_is_not_empty(self, *args):
        """
        Write "test bottom label" C string to 'bottom_label' field
        """

        bottom_label = ffi.new("char[]", b"test bottom label")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['bottom_label'][0] = bottom_label

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_bottom_label_field_is_empty(self):
        """
        'bottom_label' field in graphmodel object is empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._bottom_label_is_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['bottom_label'], '')

    def _bottom_label_is_empty(self, *args):
        """
        Write NULL to bottom_label field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['bottom_label'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_x_unit_field_is_not_empty(self):
        """
        'x_unit' field in graphmodel object is not empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._x_unit_is_not_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['x_unit'], 'm')

    def _x_unit_is_not_empty(self, *args):
        """
        Write "m" C string to 'x_unit' field
        """

        x_unit = ffi.new("char[]", b"m")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['x_unit'][0] = x_unit

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_x_unit_field_is_empty(self):
        """
        'x_unit' field in graphmodel object is empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._x_unit_is_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['x_unit'], '')

    def _x_unit_is_empty(self, *args):
        """
        Write NULL to x_unit field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['x_unit'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_y_unit_field_is_not_empty(self):
        """
        'y_unit' field in graphmodel object is not empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._y_unit_is_not_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['y_unit'], 'm')

    def _y_unit_is_not_empty(self, *args):
        """
        Write "m" C string to 'y_unit' field
        """

        y_unit = ffi.new("char[]", b"m")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['y_unit'][0] = y_unit

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_y_unit_field_is_empty(self):
        """
        'y_unit' field in graphmodel object is empty
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._y_unit_is_empty
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['y_unit'], '')

    def _y_unit_is_empty(self, *args):
        """
        Write NULL to y_unit field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['y_unit'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_x_min_set_is_true(self):
        """
        Check metadata dictionary if 'x_min_set' is True
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._x_min_set_is_true
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['x_min_set'], True)
        self.assertEqual(metadata['x_min'], 0.)

    def _x_min_set_is_true(self, *args):
        """
        Write True in 'x_min_set' field and 0. in 'x_min' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)

        arg_dict['x_min_set'][0] = truep[0]
        arg_dict['x_min'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_x_min_set_is_false(self):
        """
        Check metadata dictionary if 'x_min_set' is False
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._x_min_set_is_false
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['x_min_set'], False)
        self.assertIsNone(metadata['x_min'])

    def _x_min_set_is_false(self, *args):
        """
        Write False in 'x_min_set' field and 0. in 'x_min' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        arg_dict['x_min_set'][0] = falsep[0]
        arg_dict['x_min'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_x_max_set_is_true(self):
        """
        Check metadata dictionary if 'x_max_set' is True
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._x_max_set_is_true
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['x_max_set'], True)
        self.assertEqual(metadata['x_max'], 0.)

    def _x_max_set_is_true(self, *args):
        """
        Write True in 'x_max_set' field and 0. in 'x_max' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)

        arg_dict['x_max_set'][0] = truep[0]
        arg_dict['x_max'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_x_max_set_is_false(self):
        """
        Check metadata dictionary if 'x_max_set' is False
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._x_max_set_is_false
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['x_max_set'], False)
        self.assertIsNone(metadata['x_max'])

    def _x_max_set_is_false(self, *args):
        """
        Write False in 'x_max_set' field and 0. in 'x_max' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        arg_dict['x_max_set'][0] = falsep[0]
        arg_dict['x_max'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_min_set_is_true(self):
        """
        Check metadata dictionary if 'y_min_set' is True
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._y_min_set_is_true
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['y_min_set'], True)
        self.assertEqual(metadata['y_min'], 0.)

    def _y_min_set_is_true(self, *args):
        """
        Write True in 'y_min_set' field and 0. in 'y_min' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)

        arg_dict['y_min_set'][0] = truep[0]
        arg_dict['y_min'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_min_set_is_false(self):
        """
        Check metadata dictionary if 'y_min_set' is False
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._y_min_set_is_false
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['y_min_set'], False)
        self.assertIsNone(metadata['y_min'])

    def _y_min_set_is_false(self, *args):
        """
        Write False in 'y_min_set' field and 0. in 'y_min' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        arg_dict['y_min_set'][0] = falsep[0]
        arg_dict['y_min'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_max_set_is_true(self):
        """
        Check metadata dictionary if 'y_max_set' is True
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._y_max_set_is_true
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['y_max_set'], True)
        self.assertEqual(metadata['y_max'], 0.)

    def _y_max_set_is_true(self, *args):
        """
        Write True in 'y_max_set' field and 0. in 'y_max' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)

        arg_dict['y_max_set'][0] = truep[0]
        arg_dict['y_max'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_max_set_is_false(self):
        """
        Check metadata dictionary if 'y_max_set' is False
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._y_max_set_is_false
        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['y_max_set'], False)
        self.assertIsNone(metadata['y_max'])

    def _y_max_set_is_false(self, *args):
        """
        Write False in 'y_max_set' field and 0. in 'y_max' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        arg_dict['y_max_set'][0] = falsep[0]
        arg_dict['y_max'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_x_is_logarithmic_true(self):
        """
        'x_is_logarithmic' field is True
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._x_is_logarithmic

        self.x_is_logarithmic = True

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['x_is_logarithmic'], True)

    def test_x_is_logarithmic_false(self):
        """
        'x_is_logarithmic' field is False
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._x_is_logarithmic

        self.x_is_logarithmic = False

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['x_is_logarithmic'], False)

    def _x_is_logarithmic(self, *args):
        """
        Write self.x_is_logarithmic in 'x_is_logarithmic' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.x_is_logarithmic:
            arg_dict['x_is_logarithmic'][0] = truep[0]
        else:
            arg_dict['x_is_logarithmic'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_is_logarithmic_true(self):
        """
        'y_is_logarithmic' field is True
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._y_is_logarithmic

        self.y_is_logarithmic = True

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['y_is_logarithmic'], True)

    def test_y_is_logarithmic_false(self):
        """
        'y_is_logarithmic' field is False
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._y_is_logarithmic

        self.y_is_logarithmic = False

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['y_is_logarithmic'], False)

    def _y_is_logarithmic(self, *args):
        """
        Write self.y_is_logarithmic in 'y_is_logarithmic' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.y_is_logarithmic:
            arg_dict['y_is_logarithmic'][0] = truep[0]
        else:
            arg_dict['y_is_logarithmic'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_label_visible_is_true(self):
        """
        'label.visible' field is True
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._label_visible

        self.label_visible = True

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['label.visible'], True)

    def test_label_visible_is_false(self):
        """
        'label.visible' field is False
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._label_visible

        self.label_visible = False

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['label.visible'], False)

    def _label_visible(self, *args):
        """
        Write self.label_visible in 'label.visible' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.label_visible:
            arg_dict['label.visible'][0] = truep[0]
        else:
            arg_dict['label.visible'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_label_has_frame_is_true(self):
        """
        'label.has_frame' field is True
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._label_has_frame

        self.label_has_frame = True

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['label.has_frame'], True)

    def test_label_has_frame_is_false(self):
        """
        'label.has_frame' field is False
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._label_has_frame

        self.label_has_frame = False

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['label.has_frame'], False)

    def _label_has_frame(self, *args):
        """
        Write self.label_has_frame in 'label.has_frame' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.label_has_frame:
            arg_dict['label.has_frame'][0] = truep[0]
        else:
            arg_dict['label.has_frame'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_label_reverse_is_true(self):
        """
        'label.reverse' field is True
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._label_reverse

        self.label_reverse = True

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['label.reverse'], True)

    def test_label_reverse_is_false(self):
        """
        'label.reverse' field is False
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._label_reverse

        self.label_reverse = False

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertIs(metadata['label.reverse'], False)

    def _label_reverse(self, *args):
        """
        Write self.label_reverse in 'label.reverse' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.label_reverse:
            arg_dict['label.reverse'][0] = truep[0]
        else:
            arg_dict['label.reverse'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_label_frame_thickness(self):
        """
        Check 'label.frame_thickness' field in metadata dictionary
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._label_frame_thickness

        self.label_frame_thickness = 1

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['label.frame_thickness'],
                         self.label_frame_thickness)

    def _label_frame_thickness(self, *args):
        """
        Write self.label_frame_thickness in 'label.frame_thickness' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['label.frame_thickness'][0] = self.label_frame_thickness
        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_label_position(self):
        """
        Check 'label.position' field in metadata dictionary
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._label_position

        self.label_position = 1

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['label.position'],
                         self.label_position)

    def _label_position(self, *args):
        """
        Write self.label_position in 'label.position' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['label.position'][0] = self.label_position
        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_grid_type(self):
        """
        Check 'grid-type' field in metadata dictionary
        """

        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._grid_type

        self.grid_type = 1

        metadata = self.gwyfile.get_graphmodel_metadata(self.gwyfile,
                                                        self.graph_id)
        self.assertEqual(metadata['grid-type'],
                         self.grid_type)

    def _grid_type(self, *args):
        """
        Write self.grid_type in 'grid-type' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['grid-type'][0] = self.grid_type

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_raise_exception_if_graphmodel_object_looks_unacceptable(self):
        """
        Raise GwyfileErrorCMsg if gwyfile_object_graphmodel_get returns False
        """

        falsep = ffi.new("bool*", False)
        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.return_value = falsep[0]
        self.assertRaises(GwyfileErrorCMsg,
                          self.gwyfile.get_graphmodel_metadata,
                          self.gwyfile,
                          self.graph_id)


class Gwyfile_get_graphmodel_curves(unittest.TestCase):
    """
    Test get_graphmodel_curves method of Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_graphmodel_curves = Gwyfile.get_graphmodel_curves

        self.graph_id = 1  # id of graphmodel object
        self.ncurves = 3   # number of curves in graphmodel object
        self.curves_array = ffi.new("GwyfileObject*[]", self.ncurves)
        self.graphmodel = Mock()

        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_graphmodel_object_does_not_exist(self):
        """
        Return empty list if graphmodel object does not exist
        """

        key = "/0/graph/graph/{:d}".format(self.graph_id)
        self.gwyfile._gwyobject_check.return_value = False

        curves = self.gwyfile.get_graphmodel_curves(self.gwyfile,
                                                    self.graph_id,
                                                    self.ncurves)

        self.gwyfile._gwyobject_check.assert_has_calls(
            [call(key)])

        self.assertListEqual(curves, [])

    def test_raise_exception_if_graphmodel_object_looks_unacceptable(self):
        """
        Raise GwyfileErrorCMsg if gwyfile_object_graphmodel_get returns False
        """

        falsep = ffi.new("bool*", False)
        self.mock_lib.gwyfile_object_graphmodel_get.return_value = falsep[0]
        self.assertRaises(GwyfileErrorCMsg,
                          self.gwyfile.get_graphmodel_curves,
                          self.gwyfile,
                          self.graph_id,
                          self.ncurves)

    def test_get_curves_array(self):
        """
        Get array of curves (GwyfileObjects) from graphmodel object
        """

        self.gwyfile._gwyfile_get_object.return_value = self.graphmodel
        graphmodel_get = self.mock_lib.gwyfile_object_graphmodel_get
        graphmodel_get.side_effect = self._side_effect
        curves = self.gwyfile.get_graphmodel_curves(self.gwyfile,
                                                    self.graph_id,
                                                    self.ncurves)
        self.assertListEqual(curves, list(self.curves_array))

    def _side_effect(self, *args):
        """
        Check args of gwyfile_object_graphmodel_get func
        and write self.curves_array in 'curves' field
        """

        # first arg is GwyDatafield returned by _gwyfile_get_object
        self.assertEqual(args[0], self.graphmodel)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(ffi.new("GwyfileError**"))

        # last arg in Null
        self.assertEqual(args[-1], ffi.NULL)

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['curves'][0] = self.curves_array

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class Gwyfile_get_graphcurvemodel_metadata(unittest.TestCase):
    """
    Test get_graphcurvemodel_metadata method of Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_graphcurvemodel_metadata = (
            Gwyfile.get_graphcurvemodel_metadata)
        self.curve = Mock()
        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.ndata = 256
        self.description = "Curve label"
        self.curve_type = 1
        self.point_type = 1
        self.line_style = 1
        self.point_size = 3
        self.line_size = 3
        self.color_red = 0.1
        self.color_green = 0.2
        self.color_blue = 0.3

    def test_raise_exception_if_graphcurvemodel_looks_unacceptable(self):
        """
        Raise GwyfileErrorCMsg if GwyGraphCurveModel looks unacceptable
        """

        falsep = ffi.new("bool*", False)
        self.mock_lib.gwyfile_object_graphcurvemodel_get.return_value = (
            falsep[0])
        self.assertRaises(GwyfileErrorCMsg,
                          self.gwyfile.get_graphcurvemodel_metadata,
                          self.gwyfile,
                          self.curve)

    def test_positional_args_of_libgwyfile_func_call(self):
        """
        Test positional args in gwyfile_object_graphcurvemodel_get call

        First arg is GwyGraphCurveModel*
        Second arg is GwyfileError**
        Last arg is NULL
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._positional_args_side_effect)
        self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                  self.curve)

    def _positional_args_side_effect(self, *args):
        """
        Check positional args in gwyfile_object_graphcurvemodel_get call
        """

        # first arg is GwyGraphCurveModel
        self.assertEqual(args[0], self.curve)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(ffi.new("GwyfileError**"))

        # last arg in Null
        self.assertEqual(args[-1], ffi.NULL)

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_number_of_curves_in_graphcurvemodel(self):
        """
        Test getting 'ndata' field from GwyGraphCurveModel object
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_number_of_points_side_effect)
        metadata = self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                             self.curve)
        self.assertEqual(metadata['ndata'], self.ndata)

    def _getting_number_of_points_side_effect(self, *args):
        """
        Write self.ndata in 'ndata' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['ndata'][0] = self.ndata

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_description_of_gwycurvemodel(self):
        """
        Test getting 'description' field from GwyGraphCurveModel object
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_description_of_curve)
        metadata = self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                             self.curve)
        self.assertEqual(metadata['description'], self.description)

    def _getting_description_of_curve(self, *args):
        """
        Write self.description in 'description' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['description'][0] = ffi.new("char[]",
                                             self.description.encode('utf-8'))

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_null_description_of_gwycurvemodel(self):
        """
        Test getting NULL in 'description' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_null_description_of_curve)
        metadata = self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                             self.curve)
        self.assertEqual(metadata['description'], '')

    def _getting_null_description_of_curve(self, *args):
        """
        Write Null in 'description' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['description'][0] = ffi.NULL

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_type_of_graphcurvemodel(self):
        """
        Test getting 'type' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_type_of_curve_side_effect)
        metadata = self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                             self.curve)
        self.assertEqual(metadata['type'], self.curve_type)

    def _getting_type_of_curve_side_effect(self, *args):
        """
        Write self.curve_type in 'type' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['type'][0] = self.curve_type

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_point_type_of_graphcurvemodel(self):
        """
        Test getting 'point_type' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_point_type_side_effect)
        metadata = self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                             self.curve)
        self.assertEqual(metadata['point_type'], self.point_type)

    def _getting_point_type_side_effect(self, *args):
        """
        Write self.point_type in 'point_type' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['point_type'][0] = self.point_type

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_line_style_of_graphcurvemodel(self):
        """
        Test getting 'line_style' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_line_style_side_effect)
        metadata = self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                             self.curve)
        self.assertEqual(metadata['line_style'], self.line_style)

    def _getting_line_style_side_effect(self, *args):
        """
        Write self.line_style in 'line_style' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['line_style'][0] = self.line_style

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_point_size_of_graphcurvemodel(self):
        """
        Test getting 'point_size' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_point_size_side_effect)
        metadata = self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                             self.curve)
        self.assertEqual(metadata['point_size'], self.point_size)

    def _getting_point_size_side_effect(self, *args):
        """
        Write self.point_size in 'point_size' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['point_size'][0] = self.point_size

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_line_size_of_graphcurvemodel(self):
        """
        Test getting 'line_size' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_line_size_side_effect)
        metadata = self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                             self.curve)
        self.assertEqual(metadata['line_size'], self.point_size)

    def _getting_line_size_side_effect(self, *args):
        """
        Write self.line_size in 'line_size' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['line_size'][0] = self.line_size

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_color_of_graphcurvemodel(self):
        """
        Test getting 'color.red', 'color.green', 'color.blue' fields
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_color_side_effect)
        metadata = self.gwyfile.get_graphcurvemodel_metadata(self.gwyfile,
                                                             self.curve)
        self.assertEqual(metadata['color.red'], self.color_red)
        self.assertEqual(metadata['color.green'], self.color_green)
        self.assertEqual(metadata['color.blue'], self.color_blue)

    def _getting_color_side_effect(self, *args):
        """
        Write self.color_red, self.color_green, self.color_blue in
        'color.red', 'color.green', 'color.blue' fields and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['color.red'][0] = self.color_red
        arg_dict['color.green'][0] = self.color_green
        arg_dict['color.blue'][0] = self.color_blue

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class Gwyfile_get_graphcurvemodel_data(unittest.TestCase):
    """
    Test get_graphcurvemodel_data method of Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_graphcurvemodel_data = (
            Gwyfile.get_graphcurvemodel_data)
        self.curve = Mock()
        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.npoints = 256
        self.xdata = np.random.rand(self.npoints)
        self.ydata = np.random.rand(self.npoints)

    def test_raise_exception_if_graphcurvemodel_looks_unacceptable(self):
        """
        Raise GwyfileErrorCMsg if GwyGraphCurveModel looks unacceptable
        """

        falsep = ffi.new("bool*", False)
        self.mock_lib.gwyfile_object_graphcurvemodel_get.return_value = (
            falsep[0])
        self.assertRaises(GwyfileErrorCMsg,
                          self.gwyfile.get_graphcurvemodel_data,
                          self.gwyfile,
                          self.curve,
                          self.npoints)

    def test_positional_args_of_libgwyfile_func_call(self):
        """
        Test positional args in gwyfile_object_graphcurvemodel_get call

        First arg is GwyGraphCurveModel*
        Second arg is GwyfileError**
        Last arg is NULL
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._positional_args_side_effect)
        self.gwyfile.get_graphcurvemodel_data(self.gwyfile,
                                              self.curve,
                                              self.npoints)

    def _positional_args_side_effect(self, *args):
        """
        Check positional args in gwyfile_object_graphcurvemodel_get call
        """

        # first arg is GwyGraphCurveModel
        self.assertEqual(args[0], self.curve)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(ffi.new("GwyfileError**"))

        # last arg in Null
        self.assertEqual(args[-1], ffi.NULL)

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_returned_value(self):
        """
        Test the value returned by get_graphcurvemodel_data method"
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._returned_value_side_effect)

        data = self.gwyfile.get_graphcurvemodel_data(self.gwyfile,
                                                     self.curve,
                                                     self.npoints)
        np.testing.assert_almost_equal(self.xdata, data[0])
        np.testing.assert_almost_equal(self.ydata, data[1])

    def _returned_value_side_effect(self, *args):
        """
        Write self.xdata and self.ydata as C arrays to 'xdata' and 'ydata'
        and return True
        """
        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['xdata'][0] = ffi.cast("double*", self.xdata.ctypes.data)
        arg_dict['ydata'][0] = ffi.cast("double*", self.ydata.ctypes.data)

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwyPointSelections_init(unittest.TestCase):
    """Test arguments passing to GwySelection __init__
    """

    @patch.object(GwySelection, '__init__')
    def test_args_of_gwypointselection_init(self, mock_gwysel_cls):
        """Test args of GwySelection.__init__ call
        """

        gwysel = Mock()
        GwyPointSelections(gwysel)
        mock_gwysel_cls.assert_has_calls(
            [call(gwysel=gwysel,
                  get_sel_func=lib.gwyfile_object_selectionpoint_get,
                  npoints=1)])


class GwyPointSelections_class(unittest.TestCase):
    """Test  GwyPointSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 3

        self.data = [(1., 1.), (2., 2.), (3., 3.)]
        # C array representation of self.data
        self.cdata = ffi.new("double[]", [1., 1., 2., 2., 3., 3.])

        patcher_lib = (
            patch('gwydb.gwy.gwyfile.GwyPointSelections._get_sel_func',
                  autospec=True))
        self.addCleanup(patcher_lib.stop)
        self.get_sel_func = patcher_lib.start()

    def test_raise_exception_in_get_selection_nsel(self):
        """Raise GwyfileErrorCMsg in GwySelection._get_selection_nsel

        Raise GwyfileErrorCMsg in GwySelection._get_selection_nsel
        if get_sel_func returns False
        """
        falsep = ffi.new("bool*", False)
        self.get_sel_func.return_value = falsep[0]
        self.assertRaises(GwyfileErrorCMsg,
                          GwySelection._get_selection_nsel,
                          self.gwysel,
                          self.get_sel_func)

    def test_raise_exception_in_get_selection_points(self):
        """Raise GwyfileErrorCMsg in GwySelection._get_selection_points

        Raise GwyfileErrorCMsg in GwySelection._get_selection_points
        if get_sel_func returns False
        """
        falsep = ffi.new("bool*", False)
        self.get_sel_func.return_value = falsep[0]
        npoints = 1
        self.assertRaises(GwyfileErrorCMsg,
                          GwySelection._get_selection_points,
                          self.gwysel,
                          self.get_sel_func,
                          self.nsel,
                          npoints)

    def test_pos_arguments(self):
        """Test positional arguments in gwyfile_object_selectionpoint_get

        First argument must be GwySelectionPoint libgwyfile object
        Second argument must be GwyfileError** libgwyfile object
        Last argument must be NULL
        """

        self.get_sel_func.side_effect = self._test_pos_args_side_effect
        GwyPointSelections(self.gwysel)

    def _test_pos_args_side_effect(self, *args):
        # first arg is GwyfileSelectionPoint object
        self.assertEqual(args[0], self.gwysel)

        # second arg is GwyfileError**
        self.assertEqual(ffi.typeof(args[1]),
                         ffi.typeof(ffi.new("GwyfileError**")))

        # last arg in Null
        self.assertEqual(args[-1], ffi.NULL)

        # Function should return True if object looks acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_data_property_if_nsel_is_not_zero(self):
        """Test data property if number of selections is not zero
        """
        self.get_sel_func.side_effect = self._test_data_side_effect
        point_sel = GwyPointSelections(self.gwysel)
        self.assertListEqual(self.data, point_sel.data)

    def test_data_property_if_nsel_is_zero(self):
        """data property should be None if number of selections is zero
        """
        self.nsel = 0
        self.get_sel_func.side_effect = self._test_data_side_effect
        point_sel = GwyPointSelections(self.gwysel)
        self.assertIsNone(point_sel.data)

    def _test_data_side_effect(self, *args):
        """ Write self.nsel in 'nsel' field, self.cdata in 'data' field
        and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        if 'nsel' in arg_dict:
            arg_dict['nsel'][0] = self.nsel
        if 'data' in arg_dict:
            arg_dict['data'][0] = self.cdata

        # Function should return True if object looks acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwyPointerSelections_init(unittest.TestCase):
    """Test arguments passing to GwySelection __init__
    """

    @patch.object(GwySelection, '__init__')
    def test_args_of_gwypointselection_init(self, mock_gwysel_cls):
        """Test args of GwySelection.__init__ call
        """
        gwysel = Mock()
        GwyPointerSelections(gwysel)
        mock_gwysel_cls.assert_has_calls(
            [call(gwysel=gwysel,
                  get_sel_func=lib.gwyfile_object_selectionpoint_get,
                  npoints=1)])


class GwyPointerSelections_data(unittest.TestCase):
    """Test data property of GwyPointerSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 2

        self.data = [(1., 1.), (2., 2.)]
        # C array representation of self.data
        self.cdata = ffi.new("double[]", [1., 1., 2., 2.])

        patcher_lib = (
            patch('gwydb.gwy.gwyfile.GwyPointerSelections._get_sel_func',
                  autospec=True))
        self.addCleanup(patcher_lib.stop)
        self.get_sel_func = patcher_lib.start()

    def test_data_property_if_nsel_is_not_zero(self):
        """Test data property if number of selections is not zero
        """
        self.get_sel_func.side_effect = self._test_data_side_effect
        pointer_sel = GwyPointerSelections(self.gwysel)
        self.assertListEqual(self.data, pointer_sel.data)

    def test_data_property_if_nsel_is_zero(self):
        """data property should be None if number of selections is zero
        """
        self.nsel = 0
        self.get_sel_func.side_effect = self._test_data_side_effect
        pointer_sel = GwyPointerSelections(self.gwysel)
        self.assertIsNone(pointer_sel.data)

    def _test_data_side_effect(self, *args):
        """ Write self.nsel in 'nsel' field, self.cdata in 'data' field
        and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        if 'nsel' in arg_dict:
            arg_dict['nsel'][0] = self.nsel
        if 'data' in arg_dict:
            arg_dict['data'][0] = self.cdata

        # Function should return True if object looks acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwyLineSelections_init(unittest.TestCase):
    """Test arguments passing to GwySelection __init__
    """

    @patch.object(GwySelection, '__init__')
    def test_args_of_gwyselection_init(self, mock_gwysel_cls):
        """Test args of GwySelection.__init__ call
        """
        gwysel = Mock()
        GwyLineSelections(gwysel)
        mock_gwysel_cls.assert_has_calls(
            [call(gwysel=gwysel,
                  get_sel_func=lib.gwyfile_object_selectionline_get,
                  npoints=2)])


class GwyLineSelections_data(unittest.TestCase):
    """Test data property of GwyLineSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 2

        self.data = [((1., 1.), (2., 2.)), ((3., 3.), (4., 4.))]
        # C array representation of self.data
        self.cdata = ffi.new("double[]", [1., 1., 2., 2., 3., 3., 4., 4.])

        patcher_lib = (
            patch('gwydb.gwy.gwyfile.GwyLineSelections._get_sel_func',
                  autospec=True))
        self.addCleanup(patcher_lib.stop)
        self.get_sel_func = patcher_lib.start()

    def test_data_property_if_nsel_is_not_zero(self):
        """Test data property if number of selections is not zero
        """
        self.get_sel_func.side_effect = self._test_data_side_effect
        line_sel = GwyLineSelections(self.gwysel)
        self.assertListEqual(self.data, line_sel.data)

    def test_data_property_if_nsel_is_zero(self):
        """data property should be None if number of selections is zero
        """
        self.nsel = 0
        self.get_sel_func.side_effect = self._test_data_side_effect
        line_sel = GwyLineSelections(self.gwysel)
        self.assertIsNone(line_sel.data)

    def _test_data_side_effect(self, *args):
        """ Write self.nsel in 'nsel' field, self.cdata in 'data' field
        and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        if 'nsel' in arg_dict:
            arg_dict['nsel'][0] = self.nsel
        if 'data' in arg_dict:
            arg_dict['data'][0] = self.cdata

        # Function should return True if object looks acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwyRectangleSelections_init(unittest.TestCase):
    """Test arguments passing to GwySelection __init__
    """

    @patch.object(GwySelection, '__init__')
    def test_args_of_gwyselection_init(self, mock_gwysel_cls):
        """Test args of GwySelection.__init__ call
        """
        gwysel = Mock()
        GwyRectangleSelections(gwysel)
        mock_gwysel_cls.assert_has_calls(
            [call(gwysel=gwysel,
                  get_sel_func=lib.gwyfile_object_selectionrectangle_get,
                  npoints=2)])


class GwyRectangleSelections_data(unittest.TestCase):
    """Test data property of GwyRectangleSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 2

        self.data = [((1., 1.), (2., 2.)), ((3., 3.), (4., 4.))]
        # C array representation of self.data
        self.cdata = ffi.new("double[]", [1., 1., 2., 2., 3., 3., 4., 4.])

        patcher_lib = (
            patch('gwydb.gwy.gwyfile.GwyRectangleSelections._get_sel_func',
                  autospec=True))
        self.addCleanup(patcher_lib.stop)
        self.get_sel_func = patcher_lib.start()

    def test_data_property_if_nsel_is_not_zero(self):
        """Test data property if number of selections is not zero
        """
        self.get_sel_func.side_effect = self._test_data_side_effect
        rect_sel = GwyRectangleSelections(self.gwysel)
        self.assertListEqual(self.data, rect_sel.data)

    def test_data_property_if_nsel_is_zero(self):
        """data property should be None if number of selections is zero
        """
        self.nsel = 0
        self.get_sel_func.side_effect = self._test_data_side_effect
        rect_sel = GwyRectangleSelections(self.gwysel)
        self.assertIsNone(rect_sel.data)

    def _test_data_side_effect(self, *args):
        """ Write self.nsel in 'nsel' field, self.cdata in 'data' field
        and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        if 'nsel' in arg_dict:
            arg_dict['nsel'][0] = self.nsel
        if 'data' in arg_dict:
            arg_dict['data'][0] = self.cdata

        # Function should return True if object looks acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwyEllipseSelections_init(unittest.TestCase):
    """Test arguments passing to GwySelection __init__
    """

    @patch.object(GwySelection, '__init__')
    def test_args_of_gwyselection_init(self, mock_gwysel_cls):
        """Test args of GwySelection.__init__ call
        """
        gwysel = Mock()
        GwyEllipseSelections(gwysel)
        mock_gwysel_cls.assert_has_calls(
            [call(gwysel=gwysel,
                  get_sel_func=lib.gwyfile_object_selectionellipse_get,
                  npoints=2)])


class GwyEllipseSelections_data(unittest.TestCase):
    """Test data property of GwyEllipseSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 2

        self.data = [((1., 1.), (2., 2.)), ((3., 3.), (4., 4.))]
        # C array representation of self.data
        self.cdata = ffi.new("double[]", [1., 1., 2., 2., 3., 3., 4., 4.])

        patcher_lib = (
            patch('gwydb.gwy.gwyfile.GwyEllipseSelections._get_sel_func',
                  autospec=True))
        self.addCleanup(patcher_lib.stop)
        self.get_sel_func = patcher_lib.start()

    def test_data_property_if_nsel_is_not_zero(self):
        """Test data property if number of selections is not zero
        """
        self.get_sel_func.side_effect = self._test_data_side_effect
        ellipse_sel = GwyEllipseSelections(self.gwysel)
        self.assertListEqual(self.data, ellipse_sel.data)

    def test_data_property_if_nsel_is_zero(self):
        """data property should be None if number of selections is zero
        """
        self.nsel = 0
        self.get_sel_func.side_effect = self._test_data_side_effect
        ellipse_sel = GwyEllipseSelections(self.gwysel)
        self.assertIsNone(ellipse_sel.data)

    def _test_data_side_effect(self, *args):
        """ Write self.nsel in 'nsel' field, self.cdata in 'data' field
        and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        if 'nsel' in arg_dict:
            arg_dict['nsel'][0] = self.nsel
        if 'data' in arg_dict:
            arg_dict['data'][0] = self.cdata

        # Function should return True if object looks acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwyDataField_init(unittest.TestCase):
    """Test __init__ method of GwyDataField class
    """
    @patch.object(GwyDataField, '_get_data')
    @patch.object(GwyDataField, '_get_meta')
    def test_GwyDataField_init(self, mock_get_meta, mock_get_data):
        cgwydf = Mock()
        test_meta = {'xres': 256,
                     'yres': 256,
                     'xreal': 1e-6,
                     'yreal': 1e-6,
                     'xoff': 0,
                     'yoff': 0,
                     'si_unit_xy': 'm',
                     'si_unit_z': 'A'}
        test_data = np.random.rand(256, 256)
        mock_get_meta.return_value = test_meta
        mock_get_data.return_value = test_data
        gwydf = GwyDataField(cgwydf)
        self.assertDictEqual(test_meta, gwydf.meta)
        np.testing.assert_almost_equal(test_data, gwydf.data)


class GwyDataField_get_meta(unittest.TestCase):
    """Test _get_meta method of GwyDataFieldself.test_metadata_dict = {'xres': 256,
                                   'yres': 256,
                                   'xreal': 1e-6,
                                   'yreal': 1e-6,
                                   'xoff': 0,
                                   'yoff': 0,
                                   'si_unit_xy': 'm',
                                   'si_unit_z': 'A'}
    """

    def setUp(self):
        self.cgwydf = Mock()
        self.mock_gwydf = Mock(spec=GwyDataField)
        self.mock_gwydf._get_meta = GwyDataField._get_meta

        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.falsep = ffi.new("bool*", False)
        self.truep = ffi.new("bool*", True)
        self.errorp = ffi.new("GwyfileError**")
        self.error_msg = "Test error message"
        self.metadata_dict = {'xres': ffi.typeof(ffi.new("int32_t*")),
                              'yres': ffi.typeof(ffi.new("int32_t*")),
                              'xreal': ffi.typeof(ffi.new("double*")),
                              'yreal': ffi.typeof(ffi.new("double*")),
                              'xoff': ffi.typeof(ffi.new("double*")),
                              'yoff': ffi.typeof(ffi.new("double*")),
                              'si_unit_xy': ffi.typeof(ffi.new("char**")),
                              'si_unit_z': ffi.typeof(ffi.new("char**"))}

    def test_raise_exception_if_df_loock_unacceptable(self):
        """Raise GywfileErrorCMsg if gwyfile_object_datafield_get returns False
        """

        self.mock_lib.gwyfile_object_datafield_get.return_value = (
            self.falsep[0])
        self.assertRaises(GwyfileErrorCMsg,
                          self.mock_gwydf._get_meta,
                          self.cgwydf)

    def test_libgwyfile_function_args(self):
        """
        Test args of gwyfile_object_datafield_get C function
        """

        self.mock_lib.gwyfile_object_datafield_get.side_effect = (
            self._side_effect_check_args)
        self.mock_gwydf._get_meta(self.cgwydf)

    def _side_effect_check_args(self, *args):
        """
        Check args passing to gwyfile_object_datafield_get C function
        """

        # first arg is GwyDatafield object from Libgwyfile
        self.assertEqual(args[0], self.cgwydf)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(self.errorp)

        # last arg in NULL
        self.assertEqual(args[-1], ffi.NULL)

        # create dict from names and types of pointers in args
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointer_types = [ffi.typeof(pointer) for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointer_types))

        self.assertDictEqual(arg_dict, self.metadata_dict)

        return self.truep[0]

    def test_returned_metadata_dict(self):
        """
        Returns dictionary with metadata
        """

        self.test_metadata_dict = {'xres': 256,
                                   'yres': 256,
                                   'xreal': 1e-6,
                                   'yreal': 1e-6,
                                   'xoff': 0,
                                   'yoff': 0,
                                   'si_unit_xy': 'm',
                                   'si_unit_z': 'A'}
        self.mock_lib.gwyfile_object_datafield_get.side_effect = (
            self._side_effect_return_metadata)

        meta = self.mock_gwydf._get_meta(self.cgwydf)
        self.assertDictEqual(self.test_metadata_dict, meta)

    def _side_effect_return_metadata(self, *args):

        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        for key in arg_dict:
            if key not in ['si_unit_xy', 'si_unit_z']:
                arg_dict[key][0] = self.test_metadata_dict[key]
            else:
                metadata_value = self.test_metadata_dict[key].encode('utf-8')
                metadata_c_str = ffi.new("char[]", metadata_value)
                arg_dict[key][0] = metadata_c_str
        return self.truep[0]


class GwyDataField_get_data(unittest.TestCase):
    """Test _get_data method of GwyDataField class
    """

    def setUp(self):
        self.cgwydf = Mock()
        self.mock_gwydf = Mock(spec=GwyDataField)
        self.mock_gwydf._get_data = GwyDataField._get_data

        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.falsep = ffi.new("bool*", False)
        self.truep = ffi.new("bool*", True)
        self.errorp = ffi.new("GwyfileError**")
        self.error_msg = "Test error message"

        self.xres = 256
        self.yres = 256
        self.data = np.random.rand(self.xres, self.yres)

    def test_raise_exception__df_looks_unacceptable(self):
        """Raise GwyfileErrorCMsg if datafield object loosk unacceptable

        Raise GwyfileErrorCMsg exception if
        gwyfile_object_datafield_get returns False
        """

        self.mock_lib.gwyfile_object_datafield_get.return_value = (
            self.falsep[0])
        self.assertRaises(GwyfileErrorCMsg,
                          self.mock_gwydf._get_data,
                          self.cgwydf,
                          self.xres,
                          self.yres)

    def test_returned_data(self):
        """
        Check returned value
        """

        self.mock_lib.gwyfile_object_datafield_get.side_effect = (
            self._side_effect)

        data = self.mock_gwydf._get_data(self.cgwydf,
                                         self.xres,
                                         self.yres)

        np.testing.assert_almost_equal(self.data, data)

    def _side_effect(self, *args):

        # first arg is GwyDatafield object from Libgwyfile
        self.assertEqual(args[0], self.cgwydf)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(self.errorp)

        # last arg in NULL
        self.assertEqual(args[-1], ffi.NULL)

        # create dict from names and types of pointers in args
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        datap = arg_dict['data']
        datap[0] = ffi.cast("double*", self.data.ctypes.data)

        return self.truep[0]


class GwyGraphCurve_init(unittest.TestCase):
    """Test __init__ method of GwyGraphCurve class
    """
    @patch.object(GwyGraphCurve, '_get_data')
    @patch.object(GwyGraphCurve, '_get_meta')
    def test_GwyGraphCurve_init(self, mock_get_meta, mock_get_data):
        cgwycurve = Mock()
        test_meta = {'ndata': 256,
                     'description': "Curve label",
                     'curve_type': 1}
        test_data = np.random.rand(2, 256)
        mock_get_meta.return_value = test_meta
        mock_get_data.return_value = test_data
        gwycurve = GwyGraphCurve(cgwycurve)
        self.assertDictEqual(test_meta, gwycurve.meta)
        np.testing.assert_almost_equal(test_data, gwycurve.data)


class GwyGraphCurve_get_meta(unittest.TestCase):
    """
    Test _get_meta method of GwyGraphCurve class
    """

    def setUp(self):
        self.gwycurve = Mock()
        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.ndata = 256
        self.description = "Curve label"
        self.curve_type = 1
        self.point_type = 1
        self.line_style = 1
        self.point_size = 3
        self.line_size = 3
        self.color_red = 0.1
        self.color_green = 0.2
        self.color_blue = 0.3

    def test_raise_exception_if_graphcurvemodel_looks_unacceptable(self):
        """
        Raise GwyfileErrorCMsg if GwyGraphCurveModel looks unacceptable
        """

        falsep = ffi.new("bool*", False)
        self.mock_lib.gwyfile_object_graphcurvemodel_get.return_value = (
            falsep[0])
        self.assertRaises(GwyfileErrorCMsg,
                          GwyGraphCurve._get_meta,
                          self.gwycurve)

    def test_positional_args_of_libgwyfile_func_call(self):
        """
        Test positional args in gwyfile_object_graphcurvemodel_get call

        First arg is GwyGraphCurveModel*
        Second arg is GwyfileError**
        Last arg is NULL
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._positional_args_side_effect)
        GwyGraphCurve._get_meta(self.gwycurve)

    def _positional_args_side_effect(self, *args):
        """
        Check positional args in gwyfile_object_graphcurvemodel_get call
        """

        # first arg is GwyGraphCurveModel
        self.assertEqual(args[0], self.gwycurve)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(ffi.new("GwyfileError**"))

        # last arg in Null
        self.assertEqual(args[-1], ffi.NULL)

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_number_of_curves_in_graphcurvemodel(self):
        """
        Test getting 'ndata' field from GwyGraphCurveModel object
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_number_of_points_side_effect)
        meta = GwyGraphCurve._get_meta(self.gwycurve)
        self.assertEqual(meta['ndata'], self.ndata)

    def _getting_number_of_points_side_effect(self, *args):
        """
        Write self.ndata in 'ndata' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['ndata'][0] = self.ndata

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_description_of_gwycurvemodel(self):
        """
        Test getting 'description' field from GwyGraphCurveModel object
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_description_of_curve)
        meta = GwyGraphCurve._get_meta(self.gwycurve)
        self.assertEqual(meta['description'], self.description)

    def _getting_description_of_curve(self, *args):
        """
        Write self.description in 'description' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['description'][0] = ffi.new("char[]",
                                             self.description.encode('utf-8'))

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_null_description_of_gwycurvemodel(self):
        """
        Test getting NULL in 'description' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_null_description_of_curve)
        meta = GwyGraphCurve._get_meta(self.gwycurve)
        self.assertEqual(meta['description'], '')

    def _getting_null_description_of_curve(self, *args):
        """
        Write Null in 'description' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['description'][0] = ffi.NULL

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_type_of_graphcurvemodel(self):
        """
        Test getting 'type' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_type_of_curve_side_effect)
        meta = GwyGraphCurve._get_meta(self.gwycurve)
        self.assertEqual(meta['type'], self.curve_type)

    def _getting_type_of_curve_side_effect(self, *args):
        """
        Write self.curve_type in 'type' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['type'][0] = self.curve_type

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_point_type_of_graphcurvemodel(self):
        """
        Test getting 'point_type' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_point_type_side_effect)
        meta = GwyGraphCurve._get_meta(self.gwycurve)
        self.assertEqual(meta['point_type'], self.point_type)

    def _getting_point_type_side_effect(self, *args):
        """
        Write self.point_type in 'point_type' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['point_type'][0] = self.point_type

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_line_style_of_graphcurvemodel(self):
        """
        Test getting 'line_style' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_line_style_side_effect)
        meta = GwyGraphCurve._get_meta(self.gwycurve)
        self.assertEqual(meta['line_style'], self.line_style)

    def _getting_line_style_side_effect(self, *args):
        """
        Write self.line_style in 'line_style' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['line_style'][0] = self.line_style

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_point_size_of_graphcurvemodel(self):
        """
        Test getting 'point_size' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_point_size_side_effect)
        meta = GwyGraphCurve._get_meta(self.gwycurve)
        self.assertEqual(meta['point_size'], self.point_size)

    def _getting_point_size_side_effect(self, *args):
        """
        Write self.point_size in 'point_size' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['point_size'][0] = self.point_size

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_line_size_of_graphcurvemodel(self):
        """
        Test getting 'line_size' field from GwyGraphCurveModel
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_line_size_side_effect)
        meta = GwyGraphCurve._get_meta(self.gwycurve)
        self.assertEqual(meta['line_size'], self.point_size)

    def _getting_line_size_side_effect(self, *args):
        """
        Write self.line_size in 'line_size' field and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['line_size'][0] = self.line_size

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_getting_color_of_graphcurvemodel(self):
        """
        Test getting 'color.red', 'color.green', 'color.blue' fields
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._getting_color_side_effect)
        meta = GwyGraphCurve._get_meta(self.gwycurve)
        self.assertEqual(meta['color.red'], self.color_red)
        self.assertEqual(meta['color.green'], self.color_green)
        self.assertEqual(meta['color.blue'], self.color_blue)

    def _getting_color_side_effect(self, *args):
        """
        Write self.color_red, self.color_green, self.color_blue in
        'color.red', 'color.green', 'color.blue' fields and return True
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['color.red'][0] = self.color_red
        arg_dict['color.green'][0] = self.color_green
        arg_dict['color.blue'][0] = self.color_blue

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwyGraphCurve_get_data(unittest.TestCase):
    """
    Test _get_data method of GwyGraphCurve class
    """

    def setUp(self):
        self.gwycurve = Mock()
        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.npoints = 256
        self.xdata = np.random.rand(self.npoints)
        self.ydata = np.random.rand(self.npoints)

    def test_raise_exception_if_graphcurvemodel_looks_unacceptable(self):
        """
        Raise GwyfileErrorCMsg if GwyGraphCurveModel looks unacceptable
        """

        falsep = ffi.new("bool*", False)
        self.mock_lib.gwyfile_object_graphcurvemodel_get.return_value = (
            falsep[0])
        self.assertRaises(GwyfileErrorCMsg,
                          GwyGraphCurve._get_data,
                          self.gwycurve,
                          self.npoints)

    def test_positional_args_of_libgwyfile_func_call(self):
        """
        Test positional args in gwyfile_object_graphcurvemodel_get call

        First arg is GwyGraphCurveModel*
        Second arg is GwyfileError**
        Last arg is NULL
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._positional_args_side_effect)
        GwyGraphCurve._get_data(self.gwycurve, self.npoints)

    def _positional_args_side_effect(self, *args):
        """
        Check positional args in gwyfile_object_graphcurvemodel_get call
        """

        # first arg is GwyGraphCurveModel
        self.assertEqual(args[0], self.gwycurve)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(ffi.new("GwyfileError**"))

        # last arg in Null
        self.assertEqual(args[-1], ffi.NULL)

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_returned_value(self):
        """
        Test the value returned by _get_data method"
        """

        self.mock_lib.gwyfile_object_graphcurvemodel_get.side_effect = (
            self._returned_value_side_effect)

        data = GwyGraphCurve._get_data(self.gwycurve, self.npoints)
        np.testing.assert_almost_equal(self.xdata, data[0])
        np.testing.assert_almost_equal(self.ydata, data[1])

    def _returned_value_side_effect(self, *args):
        """
        Write self.xdata and self.ydata as C arrays to 'xdata' and 'ydata'
        and return True
        """
        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['xdata'][0] = ffi.cast("double*", self.xdata.ctypes.data)
        arg_dict['ydata'][0] = ffi.cast("double*", self.ydata.ctypes.data)

        # C func returns true if the graphcurvemodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwyGraphModel_get_meta(unittest.TestCase):
    """Test _get_meta method of GwyGraphModel class
    """

    def setUp(self):
        self.gwygraphmodel = Mock()

        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_getting_number_of_curves(self):
        """
        Test getting number of curves from graphmodel object
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._get_number_of_curves)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['ncurves'], 3)

    def _get_number_of_curves(self, *args):
        """
        Return 3 as a number of curves in graphmodel object
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['ncurves'][0] = 3

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_title_field_is_not_empty(self):
        """
        'title' field in graphmodel object is not empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._title_is_not_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['title'], "test title")

    def _title_is_not_empty(self, *args):
        """
        Write "test title" C string to title field
        """

        title = ffi.new("char[]", b"test title")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['title'][0] = title

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_title_field_is_empty(self):
        """
        'title' field in graphmodel object is empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._title_is_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['title'], '')

    def _title_is_empty(self, *args):
        """
        Write NULL to title field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['title'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_top_label_field_is_not_empty(self):
        """
        'top_label' field in graphmodel object is not empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._top_label_is_not_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['top_label'], "test top label")

    def _top_label_is_not_empty(self, *args):
        """
        Write "test top label" C string to 'top_label' field
        """

        top_label = ffi.new("char[]", b"test top label")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['top_label'][0] = top_label

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_top_label_field_is_empty(self):
        """
        'top_label' field in graphmodel object is empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._top_label_is_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['top_label'], '')

    def _top_label_is_empty(self, *args):
        """
        Write NULL to top_label field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['top_label'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_left_label_field_is_not_empty(self):
        """
        'left_label' field in graphmodel object is not empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._left_label_is_not_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['left_label'], "test left label")

    def _left_label_is_not_empty(self, *args):
        """
        Write "test left label" C string to 'left_label' field
        """

        left_label = ffi.new("char[]", b"test left label")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['left_label'][0] = left_label

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_left_label_field_is_empty(self):
        """
        'left_label' field in graphmodel object is empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._left_label_is_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['left_label'], '')

    def _left_label_is_empty(self, *args):
        """
        Write NULL to left_label field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['left_label'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_right_label_field_is_not_empty(self):
        """
        'right_label' field in graphmodel object is not empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._right_label_is_not_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['right_label'], "test right label")

    def _right_label_is_not_empty(self, *args):
        """
        Write "test right label" C string to 'right_label' field
        """

        right_label = ffi.new("char[]", b"test right label")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['right_label'][0] = right_label

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_right_label_field_is_empty(self):
        """
        'right_label' field in graphmodel object is empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._right_label_is_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['right_label'], '')

    def _right_label_is_empty(self, *args):
        """
        Write NULL to right_label field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['right_label'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_bottom_label_field_is_not_empty(self):
        """
        'bottom_label' field in graphmodel object is not empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._bottom_label_is_not_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['bottom_label'], "test bottom label")

    def _bottom_label_is_not_empty(self, *args):
        """
        Write "test bottom label" C string to 'bottom_label' field
        """

        bottom_label = ffi.new("char[]", b"test bottom label")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['bottom_label'][0] = bottom_label

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_bottom_label_field_is_empty(self):
        """
        'bottom_label' field in graphmodel object is empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._bottom_label_is_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['bottom_label'], '')

    def _bottom_label_is_empty(self, *args):
        """
        Write NULL to bottom_label field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['bottom_label'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_x_unit_field_is_not_empty(self):
        """
        'x_unit' field in graphmodel object is not empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._x_unit_is_not_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['x_unit'], 'm')

    def _x_unit_is_not_empty(self, *args):
        """
        Write "m" C string to 'x_unit' field
        """

        x_unit = ffi.new("char[]", b"m")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['x_unit'][0] = x_unit

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_x_unit_field_is_empty(self):
        """
        'x_unit' field in graphmodel object is empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._x_unit_is_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['x_unit'], '')

    def _x_unit_is_empty(self, *args):
        """
        Write NULL to x_unit field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['x_unit'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_y_unit_field_is_not_empty(self):
        """
        'y_unit' field in graphmodel object is not empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._y_unit_is_not_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['y_unit'], 'm')

    def _y_unit_is_not_empty(self, *args):
        """
        Write "m" C string to 'y_unit' field
        """

        y_unit = ffi.new("char[]", b"m")

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['y_unit'][0] = y_unit

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_y_unit_field_is_empty(self):
        """
        'y_unit' field in graphmodel object is empty
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._y_unit_is_empty)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['y_unit'], '')

    def _y_unit_is_empty(self, *args):
        """
        Write NULL to y_unit field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['y_unit'][0] = ffi.NULL

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_x_min_set_is_true(self):
        """
        Check metadata dictionary if 'x_min_set' is True
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._x_min_set_is_true)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['x_min_set'], True)
        self.assertEqual(meta['x_min'], 0.)

    def _x_min_set_is_true(self, *args):
        """
        Write True in 'x_min_set' field and 0. in 'x_min' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)

        arg_dict['x_min_set'][0] = truep[0]
        arg_dict['x_min'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_x_min_set_is_false(self):
        """
        Check metadata dictionary if 'x_min_set' is False
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._x_min_set_is_false)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['x_min_set'], False)
        self.assertIsNone(meta['x_min'])

    def _x_min_set_is_false(self, *args):
        """
        Write False in 'x_min_set' field and 0. in 'x_min' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        arg_dict['x_min_set'][0] = falsep[0]
        arg_dict['x_min'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_x_max_set_is_true(self):
        """
        Check metadata dictionary if 'x_max_set' is True
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._x_max_set_is_true)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['x_max_set'], True)
        self.assertEqual(meta['x_max'], 0.)

    def _x_max_set_is_true(self, *args):
        """
        Write True in 'x_max_set' field and 0. in 'x_max' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)

        arg_dict['x_max_set'][0] = truep[0]
        arg_dict['x_max'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_x_max_set_is_false(self):
        """
        Check metadata dictionary if 'x_max_set' is False
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._x_max_set_is_false)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['x_max_set'], False)
        self.assertIsNone(meta['x_max'])

    def _x_max_set_is_false(self, *args):
        """
        Write False in 'x_max_set' field and 0. in 'x_max' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        arg_dict['x_max_set'][0] = falsep[0]
        arg_dict['x_max'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_min_set_is_true(self):
        """
        Check metadata dictionary if 'y_min_set' is True
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._y_min_set_is_true)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['y_min_set'], True)
        self.assertEqual(meta['y_min'], 0.)

    def _y_min_set_is_true(self, *args):
        """
        Write True in 'y_min_set' field and 0. in 'y_min' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)

        arg_dict['y_min_set'][0] = truep[0]
        arg_dict['y_min'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_min_set_is_false(self):
        """
        Check metadata dictionary if 'y_min_set' is False
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._y_min_set_is_false)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['y_min_set'], False)
        self.assertIsNone(meta['y_min'])

    def _y_min_set_is_false(self, *args):
        """
        Write False in 'y_min_set' field and 0. in 'y_min' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        arg_dict['y_min_set'][0] = falsep[0]
        arg_dict['y_min'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_max_set_is_true(self):
        """
        Check metadata dictionary if 'y_max_set' is True
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._y_max_set_is_true)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['y_max_set'], True)
        self.assertEqual(meta['y_max'], 0.)

    def _y_max_set_is_true(self, *args):
        """
        Write True in 'y_max_set' field and 0. in 'y_max' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)

        arg_dict['y_max_set'][0] = truep[0]
        arg_dict['y_max'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_max_set_is_false(self):
        """
        Check metadata dictionary if 'y_max_set' is False
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._y_max_set_is_false)
        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['y_max_set'], False)
        self.assertIsNone(meta['y_max'])

    def _y_max_set_is_false(self, *args):
        """
        Write False in 'y_max_set' field and 0. in 'y_max' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        arg_dict['y_max_set'][0] = falsep[0]
        arg_dict['y_max'][0] = 0.

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_x_is_logarithmic_true(self):
        """
        'x_is_logarithmic' field is True
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._x_is_logarithmic)

        self.x_is_logarithmic = True

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['x_is_logarithmic'], True)

    def test_x_is_logarithmic_false(self):
        """
        'x_is_logarithmic' field is False
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._x_is_logarithmic)

        self.x_is_logarithmic = False

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['x_is_logarithmic'], False)

    def _x_is_logarithmic(self, *args):
        """
        Write self.x_is_logarithmic in 'x_is_logarithmic' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.x_is_logarithmic:
            arg_dict['x_is_logarithmic'][0] = truep[0]
        else:
            arg_dict['x_is_logarithmic'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_y_is_logarithmic_true(self):
        """
        'y_is_logarithmic' field is True
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._y_is_logarithmic)

        self.y_is_logarithmic = True

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['y_is_logarithmic'], True)

    def test_y_is_logarithmic_false(self):
        """
        'y_is_logarithmic' field is False
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._y_is_logarithmic)

        self.y_is_logarithmic = False

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['y_is_logarithmic'], False)

    def _y_is_logarithmic(self, *args):
        """
        Write self.y_is_logarithmic in 'y_is_logarithmic' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.y_is_logarithmic:
            arg_dict['y_is_logarithmic'][0] = truep[0]
        else:
            arg_dict['y_is_logarithmic'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_label_visible_is_true(self):
        """
        'label.visible' field is True
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._label_visible)

        self.label_visible = True

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['label.visible'], True)

    def test_label_visible_is_false(self):
        """
        'label.visible' field is False
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._label_visible)

        self.label_visible = False

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['label.visible'], False)

    def _label_visible(self, *args):
        """
        Write self.label_visible in 'label.visible' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.label_visible:
            arg_dict['label.visible'][0] = truep[0]
        else:
            arg_dict['label.visible'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_label_has_frame_is_true(self):
        """
        'label.has_frame' field is True
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._label_has_frame)

        self.label_has_frame = True

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['label.has_frame'], True)

    def test_label_has_frame_is_false(self):
        """
        'label.has_frame' field is False
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._label_has_frame)

        self.label_has_frame = False

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['label.has_frame'], False)

    def _label_has_frame(self, *args):
        """
        Write self.label_has_frame in 'label.has_frame' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.label_has_frame:
            arg_dict['label.has_frame'][0] = truep[0]
        else:
            arg_dict['label.has_frame'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_label_reverse_is_true(self):
        """
        'label.reverse' field is True
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._label_reverse)

        self.label_reverse = True

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['label.reverse'], True)

    def test_label_reverse_is_false(self):
        """
        'label.reverse' field is False
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._label_reverse)

        self.label_reverse = False

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertIs(meta['label.reverse'], False)

    def _label_reverse(self, *args):
        """
        Write self.label_reverse in 'label.reverse' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        truep = ffi.new("bool*", True)
        falsep = ffi.new("bool*", False)

        if self.label_reverse:
            arg_dict['label.reverse'][0] = truep[0]
        else:
            arg_dict['label.reverse'][0] = falsep[0]

        # C func returns true if the graphmodel object loock acceptable
        return truep[0]

    def test_label_frame_thickness(self):
        """
        Check 'label.frame_thickness' field in metadata dictionary
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._label_frame_thickness)

        self.label_frame_thickness = 1

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['label.frame_thickness'],
                         self.label_frame_thickness)

    def _label_frame_thickness(self, *args):
        """
        Write self.label_frame_thickness in 'label.frame_thickness' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['label.frame_thickness'][0] = self.label_frame_thickness
        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_label_position(self):
        """
        Check 'label.position' field in metadata dictionary
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._label_position)

        self.label_position = 1

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['label.position'], self.label_position)

    def _label_position(self, *args):
        """
        Write self.label_position in 'label.position' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['label.position'][0] = self.label_position
        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_grid_type(self):
        """
        Check 'grid-type' field in metadata dictionary
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._grid_type)

        self.grid_type = 1

        meta = GwyGraphModel._get_meta(self.gwygraphmodel)
        self.assertEqual(meta['grid-type'], self.grid_type)

    def _grid_type(self, *args):
        """
        Write self.grid_type in 'grid-type' field
        """

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['grid-type'][0] = self.grid_type

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]

    def test_raise_exception_if_graphmodel_object_looks_unacceptable(self):
        """
        Raise GwyfileErrorCMsg if gwyfile_object_graphmodel_get returns False
        """

        falsep = ffi.new("bool*", False)
        self.mock_lib.gwyfile_object_graphmodel_get.return_value = (
            falsep[0])
        self.assertRaises(GwyfileErrorCMsg,
                          GwyGraphModel,
                          self.gwygraphmodel)


class GwyGraphModel_get_curves(unittest.TestCase):
    """
    Test _get_curves method of GwyGraphModel class
    """

    def setUp(self):
        self.ncurves = 3   # number of curves in graphmodel object
        self.curves_array = ffi.new("GwyfileObject*[]", self.ncurves)
        self.gwygraphmodel = Mock()

        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_raise_exception_if_graphmodel_object_looks_unacceptable(self):
        """
        Raise GwyfileErrorCMsg if gwyfile_object_graphmodel_get returns False
        """

        falsep = ffi.new("bool*", False)
        self.mock_lib.gwyfile_object_graphmodel_get.return_value = falsep[0]
        self.assertRaises(GwyfileErrorCMsg,
                          GwyGraphModel._get_curves,
                          self.gwygraphmodel,
                          self.ncurves)

    def test_get_curves_array(self):
        """
        Get array of curves (GwyfileObjects) from graphmodel object
        """

        self.mock_lib.gwyfile_object_graphmodel_get.side_effect = (
            self._side_effect)
        curves = GwyGraphModel._get_curves(self.gwygraphmodel,
                                           self.ncurves)
        self.assertListEqual(curves, list(self.curves_array))

    def _side_effect(self, *args):
        """
        Check args of gwyfile_object_graphmodel_get func
        and write self.curves_array in 'curves' field
        """

        # first arg is GwyDatafield returned by _gwyfile_get_object
        self.assertEqual(args[0], self.gwygraphmodel)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(ffi.new("GwyfileError**"))

        # last arg in Null
        self.assertEqual(args[-1], ffi.NULL)

        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['curves'][0] = self.curves_array

        # C func returns true if the graphmodel object loock acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwyGraphModel_init(unittest.TestCase):
    """Test __init__ method of GwyGraphModel class
    """

    @patch.object(GwyGraphCurve, '__init__')
    @patch.object(GwyGraphModel, '_get_curves')
    @patch.object(GwyGraphModel, '_get_meta')
    def test_GwyGraphModel_init(self,
                                mock_get_meta,
                                mock_get_curves,
                                mock_gwygraphcurve):
        cgwygraphmodel = Mock()
        test_meta = {'ncurves': 3,
                     'title': 'Profiles',
                     'x_unit': 'm',
                     'y_unit': 'm'}
        cgwycurves_array = ffi.new("GwyfileObject*[]", test_meta['ncurves'])
        mock_get_meta.return_value = test_meta
        mock_get_curves.return_value = cgwycurves_array
        mock_gwygraphcurve.return_value = None

        graphmodel = GwyGraphModel(cgwygraphmodel)
        self.assertDictEqual(test_meta, graphmodel.meta)
        mock_gwygraphcurve.assert_has_calls(
            [call(curve) for curve in cgwycurves_array])
        self.assertEqual(graphmodel.curves, graphmodel._curves)


if __name__ == '__main__':
    unittest.main()
