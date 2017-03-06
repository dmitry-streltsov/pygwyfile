import unittest
from unittest.mock import patch, call, ANY, Mock

from gwydb.gwy.gwyfile import Gwyfile
from gwydb.gwy.gwyfile import GwyfileError, GwyfileErrorCMsg
from gwydb.gwy.gwyfile import ffi, lib


class GwyfileErrorCMsg_exception(unittest.TestCase):
    """Test GwyfileErrorCMsg exception
    """

    @patch.object(GwyfileError, '__init__')
    def test_c_error_msg_is_NULL(self, mock_GwyfileError):
        """Test GwyfileError args if error message is empty
        """
        c_error_msg = ffi.NULL
        GwyfileErrorCMsg(c_error_msg)
        mock_GwyfileError.assert_has_calls(
            [call()])

    @patch.object(GwyfileError, '__init__')
    def test_c_error_msg_is_non_NULL(self, mock_GwyfileError):
        """Test GwyfileError args if error message is not empty
        """
        c_error_msg = ffi.new("char[]", b'Test error message')
        GwyfileErrorCMsg(c_error_msg)
        mock_GwyfileError.assert_has_calls(
            [call('Test error message')])


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
        basename = 'test.gwy'
        self.assertRaises(GwyfileError, Gwyfile, c_gwyfile, basename=basename)

    @patch('gwydb.gwy.gwyfile.lib', autospec=True)
    def test_raise_exception_if_top_level_object_is_empty(self, mock_lib):
        """
        Raise GwyfileError exception if top-level object is empty
        """

        c_gwyfile = Mock()
        mock_lib.gwyfile_object_name.return_value = ffi.NULL
        basename = 'test.gwy'
        error_msg = 'The top-level object of c_gwyfile is empty'
        self.assertRaisesRegex(GwyfileError,
                               error_msg,
                               Gwyfile,
                               c_gwyfile,
                               basename=basename)

    @patch('gwydb.gwy.gwyfile.lib', autospec=True)
    def test_check_top_level_object_of_c_gwyfile(self, mock_lib):
        """Raise GwyfileError exception if top-level object is not
        'GwyContainer' C string
        """

        c_gwyfile = Mock()
        basename = 'test.gwy'
        test_name = ffi.new("char[]", b"non-GwyContainer")
        mock_lib.gwyfile_object_name.return_value = test_name
        self.assertRaises(GwyfileError, Gwyfile, c_gwyfile, basename=basename)

    @patch('gwydb.gwy.gwyfile.lib', autospec=True)
    def test_attribute_of_GwyFile_instance(self, mock_lib):
        """
        Create self.c_gwyfile and filename attributes
        """

        c_gwyfile = Mock()
        basename = 'test.gwy'
        test_name = ffi.new("char[]", b"GwyContainer")
        mock_lib.gwyfile_object_name.return_value = test_name
        test_instance = Gwyfile(c_gwyfile, basename=basename)
        self.assertEqual(c_gwyfile, test_instance.c_gwyfile)
        self.assertEqual(basename, test_instance.filename)


class Gwyfile_from_gwy(unittest.TestCase):
    """ Test from_gwy method of Gwyfile class
    """

    def setUp(self):
        self.filename = 'data/test.gwy'

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

    def test_raise_exception_if_file_doesnt_exist(self):
        """
        Raise OSError exception if file does not exist
        """
        self.mock_isfile.return_value = False
        self.assertRaises(OSError, Gwyfile.from_gwy, self.filename)

    def test_arg_of_gwyfile_read_file(self):
        """If file exists call gwyfile_read_file function.

        Check arguments passed to this function
        """

        self.mock_isfile.return_value = True
        Gwyfile.from_gwy(self.filename)
        self.mock_isfile.assert_has_calls(
            [call(self.filename)])
        self.mock_lib.gwyfile_read_file.assert_has_calls(
            [call(self.filename.encode('utf-8'), ANY)])

    def test_raise_GwyfileErrorCMsg_if_gwyfile_read_file_fails(self):
        """Raise GwyfileErrorCMsg if gwyfile_read_file C func fails
        """

        self.mock_isfile.return_value = True
        self.mock_lib.gwyfile_read_file.return_value = ffi.NULL
        self.assertRaises(GwyfileErrorCMsg, Gwyfile.from_gwy, self.filename)

    def test_args_of_Gwyfile_init(self):
        """Create Gwyfile instance. Check args passed to Gwyfile.__init__
        """
        self.mock_isfile.return_value = True
        c_gwyfile = Mock()
        self.mock_lib.gwyfile_read_file.return_value = c_gwyfile
        Gwyfile.from_gwy(self.filename)
        self.mock_Gwyfile.assert_has_calls(
            [call(c_gwyfile, 'test.gwy')])

    def test_returned_value(self):
        """Return Gwyfile instance
        """
        self.mock_isfile.return_value = True
        expected_return = self.mock_Gwyfile.return_value
        actual_return = Gwyfile.from_gwy(self.filename)
        self.assertEqual(expected_return, actual_return)


class Gwyfile__get_gwyitem_value(unittest.TestCase):
    """ Tests for Gwyfile._get_gwyitem_value method """
    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile._get_gwyitem_value = Gwyfile._get_gwyitem_value
        self.cfunc = Mock()
        self.item_key = '/0/data/title'

        patcher_lib = patch('gwydb.gwy.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_args_of_gwyfile_object_get(self):
        """Get data item from Gwy file object"""
        self.mock_lib.gwyfile_object_get.return_value = ffi.NULL
        self.gwyfile._get_gwyitem_value(self.gwyfile,
                                        self.item_key,
                                        self.cfunc)
        self.mock_lib.gwyfile_object_get.assert_has_calls(
            [call(self.gwyfile.c_gwyfile, self.item_key.encode('utf-8'))])

    def test_return_None_if_data_item_is_not_found(self):
        """Return None if data item is not found"""
        self.mock_lib.gwyfile_object_get.return_value = ffi.NULL
        actual_return = self.gwyfile._get_gwyitem_value(self.gwyfile,
                                                        self.item_key,
                                                        self.cfunc)
        self.assertIsNone(actual_return)

    def test_return_data_item_value_if_data_item_is_found(self):
        """Return data item value if data item is found"""
        item = self.mock_lib.gwyfile_object_get.return_value
        actual_return = self.gwyfile._get_gwyitem_value(self.gwyfile,
                                                        self.item_key,
                                                        self.cfunc)
        self.cfunc.assert_has_calls([call(item)])
        self.assertEqual(actual_return, self.cfunc.return_value)


class Gwyfile_get_gwyitem_bool(unittest.TestCase):
    """ Tests for Gwyfile.get_gwyitem_bool method """
    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_gwyitem_bool = Gwyfile.get_gwyitem_bool
        self.gwyfile._get_gwyitem_value = Mock(autospec=True)
        self.item_key = '/0/data/visible'

    def test_return_False_if_data_item_is_not_found(self):
        """ Return False if data item is not found """
        self.gwyfile._get_gwyitem_value.return_value = None
        actual_return = self.gwyfile.get_gwyitem_bool(self.gwyfile,
                                                      self.item_key)
        self.assertIs(actual_return, False)

    def test_return_False_if_data_item_value_is_False(self):
        """ Return Flase if data item value is False """
        falsep = ffi.new("bool*", False)
        self.gwyfile._get_gwyitem_value.return_value = falsep[0]
        actual_return = self.gwyfile.get_gwyitem_bool(self.gwyfile,
                                                      self.item_key)
        self.assertIs(actual_return, False)

    def test_return_True_if_data_item_value_is_True(self):
        """ Return True if data item value is True """
        truep = ffi.new("bool*", True)
        self.gwyfile._get_gwyitem_value.return_value = truep[0]
        actual_return = self.gwyfile.get_gwyitem_bool(self.gwyfile,
                                                      self.item_key)
        self.assertIs(actual_return, True)

    def test_args_of_get_gwyitem_value_call(self):
        """ Test args of Gwyfile._get_gwyitem_value call"""
        self.gwyfile._get_gwyitem_value.return_value = None
        self.gwyfile.get_gwyitem_bool(self.gwyfile, self.item_key)
        self.gwyfile._get_gwyitem_value.assert_has_calls(
            [call(self.item_key, lib.gwyfile_item_get_bool)])


class Gwyfile_get_gwyitem_string(unittest.TestCase):
    """ Tests for Gwyfile.get_gwyitem_string method """
    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_gwyitem_string = Gwyfile.get_gwyitem_string
        self.gwyfile._get_gwyitem_value = Mock(autospec=True)
        self.item_key = '/0/data/title'

    def test_return_None_if_data_item_is_not_found(self):
        """ Return None if data item is not found """
        self.gwyfile._get_gwyitem_value.return_value = None
        actual_return = self.gwyfile.get_gwyitem_string(self.gwyfile,
                                                        self.item_key)
        self.assertIs(actual_return, None)

    def test_return_string_value_if_data_item_is_found(self):
        """ Return data item string value if data item is found """
        cvalue = ffi.new("char[]", b'Title')
        self.gwyfile._get_gwyitem_value.return_value = cvalue
        actual_return = self.gwyfile.get_gwyitem_string(self.gwyfile,
                                                        self.item_key)
        self.assertEqual(actual_return, 'Title')

    def test_args_of_get_gwyitem_value_call(self):
        """ Test args of Gwyfile._get_gwyitem_value call"""
        self.gwyfile._get_gwyitem_value.return_value = None
        self.gwyfile.get_gwyitem_string(self.gwyfile, self.item_key)
        self.gwyfile._get_gwyitem_value.assert_has_calls(
            [call(self.item_key, lib.gwyfile_item_get_string)])


class Gwyfile_get_gwyitem_object(unittest.TestCase):
    """ Tests for Gwyfile.get_gwyitem_object method"""
    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_gwyitem_object = Gwyfile.get_gwyitem_object
        self.gwyfile._get_gwyitem_value = Mock(autospec=True)
        self.item_key = '/0/data'

    def test_return_None_if_data_item_is_not_found(self):
        """ Return None if data item is not found """
        self.gwyfile._get_gwyitem_value.return_value = None
        actual_return = self.gwyfile.get_gwyitem_object(self.gwyfile,
                                                        self.item_key)
        self.assertIs(actual_return, None)

    def test_return_string_value_if_data_item_is_found(self):
        """ Return data item object if data item is found """
        gwyobject = Mock()
        self.gwyfile._get_gwyitem_value.return_value = gwyobject
        actual_return = self.gwyfile.get_gwyitem_object(self.gwyfile,
                                                        self.item_key)
        self.assertEqual(actual_return, gwyobject)

    def test_args_of_get_gwyitem_value_call(self):
        """ Test args of Gwyfile._get_gwyitem_value call"""
        self.gwyfile._get_gwyitem_value.return_value = None
        self.gwyfile.get_gwyitem_object(self.gwyfile, self.item_key)
        self.gwyfile._get_gwyitem_value.assert_has_calls(
            [call(self.item_key, lib.gwyfile_item_get_object)])


if __name__ == '__main__':
    unittest.main()
