import unittest
from unittest.mock import patch, call, ANY, Mock, MagicMock

import numpy as np

from gwydb.gwy.gwyfile import Gwyfile
from gwydb.gwy.gwyfile import GwyfileError, GwyfileErrorCMsg
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


class Gwyfile__gwydf_get_metadata(unittest.TestCase):
    """
    Test __gwydf_get_metadata method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile._gwydf_get_metadata = Gwyfile._gwydf_get_metadata

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.test_key = '/0/data'
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

    def test_raise_exception_without_msg_if_df_loock_unacceptable(self):
        """Raise GywfileError exception without message

        Raise GwyfileError exception without error message
        if gwyfile_object_datafield_get returns False
        and GwyfileError.message is NULL

        """

        self.mock_lib.gwyfile_object_datafield_get.return_value = self.falsep[
            0]
        self.assertRaises(GwyfileError,
                          self.gwyfile._gwydf_get_metadata,
                          self.gwyfile,
                          self.test_key)

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
                               self.gwyfile._gwydf_get_metadata,
                               self.gwyfile,
                               self.test_key)

    def _side_effect_with_msg(self, *args):
        """
        gwyfile_object_datafield_get returns False with error_msg
        """

        errorp = args[1]
        c_error_msg = ffi.new("char[]", self.error_msg.encode('utf-8'))
        errorp[0].message = c_error_msg
        return self.falsep[0]

    def test_libgwyfile_function_args(self):
        """
        Test args of gwyfile_object_datafield_get C function
        """

        gwyfile_object_df_get = self.mock_lib.gwyfile_object_datafield_get
        gwyfile_object_df_get.side_effect = self._side_effect_check_args
        self.df = self.gwyfile._gwyfile_get_object.return_value
        self.gwyfile._gwydf_get_metadata(self.gwyfile, self.test_key)
        self.gwyfile._gwyfile_get_object.assert_has_calls(
            [call(self.test_key)])

    def _side_effect_check_args(self, *args):
        """
        Check args passing to gwyfile_object_datafield_get C function
        """

        # first arg is GwyDatafield returned by _gwyfile_get_object
        self.assertEqual(args[0], self.df)

        # second arg is GwyfileError**
        assert ffi.typeof(args[1]) == ffi.typeof(self.errorp)

        # last arg in Null
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
        gwyfile_object_df_get = self.mock_lib.gwyfile_object_datafield_get
        gwyfile_object_df_get.side_effect = self._side_effect_return_metadata

        metadata = self.gwyfile._gwydf_get_metadata(self.gwyfile,
                                                    self.test_key)
        self.assertDictEqual(self.test_metadata_dict, metadata)

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

    def test_returned_min_metadata_dict(self):
        """
        Every GwyDataField must contain xres and yres
        """

        self.test_metadata_dict = {'xres': 256, 'yres': 256}
        gwyfile_obj_df_get = self.mock_lib.gwyfile_object_datafield_get
        gwyfile_obj_df_get.side_effect = self._side_effect_return_min_metadata

        metadata = self.gwyfile._gwydf_get_metadata(self.gwyfile,
                                                    self.test_key)

        expected_metadata = {'xres': self.test_metadata_dict['xres'],
                             'yres': self.test_metadata_dict['yres'],
                             'xreal': 0,
                             'yreal': 0,
                             'xoff': 0,
                             'yoff': 0,
                             'si_unit_xy': '',
                             'si_unit_z': ''}

        self.assertDictEqual(metadata, expected_metadata)

    def _side_effect_return_min_metadata(self, *args):

        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['xres'][0] = self.test_metadata_dict['xres']
        arg_dict['yres'][0] = self.test_metadata_dict['yres']

        return self.truep[0]


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
        self.gwyfile.get_presentation_metadata = Gwyfile.get_presentation_metadata
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


class Gwyfile__get_selection_nsel(unittest.TestCase):
    """
    Test _get_selection_nsel method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile._get_selection_nsel = Gwyfile._get_selection_nsel
        self.gwyfile._gwyobject_check = Mock(autospec=True)
        self.key = "/0/select/point"
        self.nsel = 3
        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_return_None_is_there_is_no_selection(self):
        """
        Return None if there is no such selection
        """

        self.gwyfile._gwyobject_check.return_value = None
        func_sel = self.mock_lib.gwyfile_object_selectionpoint_get
        returned_value = self.gwyfile._get_selection_nsel(self.gwyfile,
                                                          self.key,
                                                          func_sel)
        self.assertIsNone(returned_value)

    def test_raise_exception_if_libgwyfile_function_returns_error(self):
        """
        Raise GwyfileError exception if libgwyfile func returns NULL
        """

        func_sel = self.mock_lib.gwyfile_object_selectionpoint_get
        func_sel.return_value = ffi.NULL
        self.assertRaises(GwyfileError,
                          self.gwyfile._get_selection_nsel,
                          self.gwyfile,
                          self.key,
                          func_sel)

    def test_check_returned_value(self):
        """
        Check returned value of _get_selection_nsel method
        """

        func_sel = self.mock_lib.gwyfile_object_selectionpoint_get
        func_sel.side_effect = self._side_effect
        returned_value = self.gwyfile._get_selection_nsel(self.gwyfile,
                                                          self.key,
                                                          func_sel)
        self.assertEqual(returned_value, self.nsel)

    def _side_effect(self, *args):
        """
        Write self.nsel as number of selections in nselp arg
        """
        truep = ffi.new("bool*", True)
        nselp = args[3]
        nselp[0] = self.nsel
        return truep[0]


class Gwyfile__get_selection_data(unittest.TestCase):
    """
    Test _get_selection_data method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile._get_selection_data = Gwyfile._get_selection_data
        self.gwyfile._gwyobject_check = Mock(autospec=True)
        self.key = "/0/select/point"
        self.npoints = 3
        self.points = [(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]
        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_return_None_is_there_is_no_selection(self):
        """
        Return None if there is no such selection
        """

        self.gwyfile._gwyobject_check.return_value = None
        func_sel = self.mock_lib.gwyfile_object_selectionpoint_get
        returned_value = self.gwyfile._get_selection_data(self.gwyfile,
                                                          self.key,
                                                          func_sel,
                                                          self.npoints)
        self.assertIsNone(returned_value)

    def test_return_None_if_npoints_equals_zero(self):
        """
        Return None if npoints argument equals zero
        """

        func_sel = self.mock_lib.gwyfile_object_selectionpoint_get
        returned_value = self.gwyfile._get_selection_data(self.gwyfile,
                                                          self.key,
                                                          func_sel,
                                                          0)
        self.assertIsNone(returned_value)

    def test_raise_exception_if_libgwyfile_function_returns_error(self):
        """
        Raise GwyfileError exception if libgwyfile func returns NULL
        """

        func_sel = self.mock_lib.gwyfile_object_selectionpoint_get
        func_sel.return_value = ffi.NULL
        self.assertRaises(GwyfileError,
                          self.gwyfile._get_selection_data,
                          self.gwyfile,
                          self.key,
                          func_sel,
                          self.npoints)

    def test_check_returned_value(self):
        """
        Check returned value of _get_selection_data method
        """

        func_sel = self.mock_lib.gwyfile_object_selectionpoint_get
        func_sel.side_effect = self._side_effect
        returned_value = self.gwyfile._get_selection_data(self.gwyfile,
                                                          self.key,
                                                          func_sel,
                                                          self.npoints)
        self.assertEqual(returned_value, self.points)

    def _side_effect(self, *args):
        """
        Write self.points as C array in data arg
        """
        truep = ffi.new("bool*", True)

        # convert self.points to list
        points_list = []
        for point in self.points:
            points_list.append(point[0])
            points_list.append(point[1])

        datap = args[3]
        datap[0] = ffi.new("double[]", points_list)

        return truep[0]


class Gwyfile_get_pointer_sel(unittest.TestCase):
    """
    Test get_pointer_sel method of Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_pointer_sel = Gwyfile.get_pointer_sel
        self.gwyfile._get_selection_nsel = Mock(autospec=True)
        self.gwyfile._get_selection_data = Mock(autospec=True)
        self.channel_id = 1
        self.nsel = 3

    def test_args_of_get_selection_nsel_call(self):
        """
        Get number of pointer selections using _get_selection_nsel method
        """

        expected_key = "/{:d}/select/pointer".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionpoint_get
        self.gwyfile.get_pointer_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_nsel.assert_has_calls(
            [call(expected_key, expected_sel_func)])

    def test_return_None_if_nsel_equals_zero(self):
        """
        Return None if number of pointer selections is zero
        """

        self.gwyfile._get_selection_nsel.return_value = None
        returned_value = self.gwyfile.get_pointer_sel(self.gwyfile,
                                                      self.channel_id)
        self.assertIsNone(returned_value)

    def test_args_of_get_selection_data_call(self):
        """
        Get points using _get_selection_data method
        """

        self.gwyfile._get_selection_nsel.return_value = self.nsel
        expected_key = "/{:d}/select/pointer".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionpoint_get
        self.gwyfile.get_pointer_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_data.assert_has_calls(
            [call(expected_key, expected_sel_func, self.nsel)])

    def test_returned_value(self):
        """
        get_pointer_sel method returns points returned by _get_selection_data
        """

        expected_return = self.gwyfile._get_selection_data.return_value
        actual_return = self.gwyfile.get_pointer_sel(self.gwyfile,
                                                     self.channel_id)
        self.assertEqual(expected_return, actual_return)


class Gwyfile_get_point_sel(unittest.TestCase):
    """
    Test get_point_sel method of Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_point_sel = Gwyfile.get_point_sel
        self.gwyfile._get_selection_nsel = Mock(autospec=True)
        self.gwyfile._get_selection_data = Mock(autospec=True)
        self.channel_id = 1
        self.nsel = 3

    def test_args_of_get_selection_nsel_call(self):
        """
        Get number of point selections using _get_selection_nsel method
        """

        expected_key = "/{:d}/select/point".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionpoint_get
        self.gwyfile.get_point_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_nsel.assert_has_calls(
            [call(expected_key, expected_sel_func)])

    def test_return_None_if_nsel_equals_zero(self):
        """
        Return None if number of point selections is zero
        """

        self.gwyfile._get_selection_nsel.return_value = None
        returned_value = self.gwyfile.get_point_sel(self.gwyfile,
                                                    self.channel_id)
        self.assertIsNone(returned_value)

    def test_args_of_get_selection_data_call(self):
        """
        Get points using _get_selection_data method
        """

        self.gwyfile._get_selection_nsel.return_value = self.nsel
        expected_key = "/{:d}/select/point".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionpoint_get
        self.gwyfile.get_point_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_data.assert_has_calls(
            [call(expected_key, expected_sel_func, self.nsel)])

    def test_returned_value(self):
        """
        get_point_sel method returns points returned by _get_selection_data
        """

        expected_return = self.gwyfile._get_selection_data.return_value
        actual_return = self.gwyfile.get_point_sel(self.gwyfile,
                                                   self.channel_id)
        self.assertEqual(expected_return, actual_return)


class Gwyfile_get_line_sel(unittest.TestCase):
    """
    Test get_line_sel method of Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_line_sel = Gwyfile.get_line_sel
        self.gwyfile._get_selection_nsel = MagicMock(autospec=True)
        self.gwyfile._get_selection_data = MagicMock(autospec=True)
        self.channel_id = 1
        self.nsel = 2
        self.points = [(0., 0.), (1., 1.), (2., 2.), (3., 3.)]
        self.lines = [((0., 0.), (1., 1.)), ((2., 2.), (3., 3.))]

    def test_args_of_get_selection_nsel_call(self):
        """
        Get number of line selections using _get_selection_nsel method
        """

        expected_key = "/{:d}/select/line".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionline_get
        self.gwyfile.get_line_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_nsel.assert_has_calls(
            [call(expected_key, expected_sel_func)])

    def test_return_None_if_nsel_equals_zero(self):
        """
        Return None if number of line selections is zero
        """

        self.gwyfile._get_selection_nsel.return_value = None
        returned_value = self.gwyfile.get_line_sel(self.gwyfile,
                                                   self.channel_id)
        self.assertIsNone(returned_value)

    def test_args_of_get_selection_data_call(self):
        """
        Get points using _get_selection_data method
        """

        self.gwyfile._get_selection_nsel.return_value = self.nsel
        npoints = 2 * self.nsel  # there are 2 points in one line selection
        expected_key = "/{:d}/select/line".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionline_get
        self.gwyfile.get_line_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_data.assert_has_calls(
            [call(expected_key, expected_sel_func, npoints)])

    def test_returned_value(self):
        """
        Return points combined in pairs
        """

        self.gwyfile._get_selection_data.return_value = self.points
        expected_return = self.lines
        actual_return = self.gwyfile.get_line_sel(self.gwyfile,
                                                  self.channel_id)
        self.assertEqual(expected_return, actual_return)


class Gwyfile_get_rectangle_sel(unittest.TestCase):
    """
    Test get_rectangle_sel method of Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_rectangle_sel = Gwyfile.get_rectangle_sel
        self.gwyfile._get_selection_nsel = MagicMock(autospec=True)
        self.gwyfile._get_selection_data = MagicMock(autospec=True)
        self.channel_id = 1
        self.nsel = 2
        self.points = [(0., 0.), (1., 1.), (2., 2.), (3., 3.)]
        self.rectangles = [((0., 0.), (1., 1.)), ((2., 2.), (3., 3.))]

    def test_args_of_get_selection_nsel_call(self):
        """
        Get number of rectangle selections using _get_selection_nsel method
        """

        expected_key = "/{:d}/select/rectangle".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionrectangle_get
        self.gwyfile.get_rectangle_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_nsel.assert_has_calls(
            [call(expected_key, expected_sel_func)])

    def test_return_None_if_nsel_equals_zero(self):
        """
        Return None if number of line selections is zero
        """

        self.gwyfile._get_selection_nsel.return_value = None
        returned_value = self.gwyfile.get_rectangle_sel(self.gwyfile,
                                                        self.channel_id)
        self.assertIsNone(returned_value)

    def test_args_of_get_selection_data_call(self):
        """
        Get points of selections using _get_selection_data method
        """

        self.gwyfile._get_selection_nsel.return_value = self.nsel
        npoints = 2 * self.nsel  # there are 2 pts in one rectangle selection
        expected_key = "/{:d}/select/rectangle".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionrectangle_get
        self.gwyfile.get_rectangle_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_data.assert_has_calls(
            [call(expected_key, expected_sel_func, npoints)])

    def test_returned_value(self):
        """
        Return points of selections combined in pairs
        """

        self.gwyfile._get_selection_data.return_value = self.points
        expected_return = self.rectangles
        actual_return = self.gwyfile.get_rectangle_sel(self.gwyfile,
                                                       self.channel_id)
        self.assertEqual(expected_return, actual_return)


class Gwyfile_get_ellipse_sel(unittest.TestCase):
    """
    Test get_ellipse_sel method of Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_ellipse_sel = Gwyfile.get_ellipse_sel
        self.gwyfile._get_selection_nsel = MagicMock(autospec=True)
        self.gwyfile._get_selection_data = MagicMock(autospec=True)
        self.channel_id = 1
        self.nsel = 2
        self.points = [(0., 0.), (1., 1.), (2., 2.), (3., 3.)]
        self.ellipses = [((0., 0.), (1., 1.)), ((2., 2.), (3., 3.))]

    def test_args_of_get_selection_nsel_call(self):
        """
        Get number of ellipse selections using _get_selection_nsel method
        """

        expected_key = "/{:d}/select/ellipse".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionellipse_get
        self.gwyfile.get_ellipse_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_nsel.assert_has_calls(
            [call(expected_key, expected_sel_func)])

    def test_return_None_if_nsel_equals_zero(self):
        """
        Return None if number of line selections is zero
        """

        self.gwyfile._get_selection_nsel.return_value = None
        returned_value = self.gwyfile.get_ellipse_sel(self.gwyfile,
                                                      self.channel_id)
        self.assertIsNone(returned_value)

    def test_args_of_get_selection_data_call(self):
        """
        Get points of selections using _get_selection_data method
        """

        self.gwyfile._get_selection_nsel.return_value = self.nsel
        npoints = 2 * self.nsel  # there are 2 points in one ellipse selection
        expected_key = "/{:d}/select/ellipse".format(self.channel_id)
        expected_sel_func = lib.gwyfile_object_selectionellipse_get
        self.gwyfile.get_ellipse_sel(self.gwyfile, self.channel_id)
        self.gwyfile._get_selection_data.assert_has_calls(
            [call(expected_key, expected_sel_func, npoints)])

    def test_returned_value(self):
        """
        Return points of selections combined in pairs
        """

        self.gwyfile._get_selection_data.return_value = self.points
        expected_return = self.ellipses
        actual_return = self.gwyfile.get_ellipse_sel(self.gwyfile,
                                                     self.channel_id)
        self.assertEqual(expected_return, actual_return)


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


if __name__ == '__main__':
    unittest.main()
