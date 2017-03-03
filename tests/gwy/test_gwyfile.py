import unittest
from unittest.mock import patch, call, ANY, Mock

from gwydb.gwy.gwyfile import Gwyfile
from gwydb.gwy.gwyfile import GwyfileError, GwyfileErrorCMsg
from gwydb.gwy.gwyfile import ffi


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


class Gwyfile_get_gwyitem(unittest.TestCase):
    """Test get_gwyitem method in Gwyfile class
    """
    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile.get_gwyitem = Gwyfile.get_gwyitem

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.test_key = '/0/data/title/'

    def test_return_None_if_item_is_not_found(self):
        """Return None if item is not found """
        self.mock_lib.gwyfile_object_get.return_value = ffi.NULL
        actual_return = self.gwyfile.get_gwyitem(self.gwyfile,
                                                 self.test_key)
        self.assertIsNone(actual_return)

    def test_return_item_if_item_is_found(self):
        """ Return <GwyfileItem*> object if item is found """
        item = Mock()
        self.mock_lib.gwyfile_object_get.return_value = item
        actual_return = self.gwyfile.get_gwyitem(self.gwyfile,
                                                 self.test_key)
        self.assertEqual(actual_return, item)

    def test_args_of_lib_function(self):
        """ Test arguments passing to gwyfile_object_get C function """
        self.gwyfile.get_gwyitem(self.gwyfile, self.test_key)
        self.mock_lib.gwyfile_object_get.assert_has_calls(
            [call(self.gwyfile.c_gwyfile, self.test_key.encode('utf-8'))])


class Gwyfile_get_gwyobject_TestCase(unittest.TestCase):
    """
    Test get_gwyobject method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile.get_gwyobject = Gwyfile.get_gwyobject

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
                          self.gwyfile.get_gwyobject,
                          self.gwyfile, self.test_key)

    def test_raise_exception_if_object_is_not_found(self):
        """
        Raise GwyfileError if object in the data item is empty
        """

        self.mock_lib.gwyfile_item_get_object.return_value = ffi.NULL
        mock_item = self.mock_lib.gwyfile_object_get.return_value
        self.assertRaises(GwyfileError,
                          self.gwyfile.get_gwyobject,
                          self.gwyfile, mock_item)

    def test_check_args_of_libgwyfile_functions(self):
        """
        Check arguments passed to Libgwyfile functions
        """

        mock_item = self.mock_lib.gwyfile_object_get.return_value

        self.gwyfile.get_gwyobject(self.gwyfile, self.test_key)

        self.mock_lib.gwyfile_object_get.assert_has_calls(
            [call(self.gwyfile.c_gwyfile, self.test_key.encode('utf-8'))])
        self.mock_lib.gwyfile_item_get_object.assert_has_calls(
            [call(mock_item)])

    def test_check_returned_value(self):
        """
        Function returns object returned by gwyfile_item_get_object
        """

        mock_object = self.mock_lib.gwyfile_item_get_object.return_value
        returned_object = self.gwyfile.get_gwyobject(self.gwyfile,
                                                     self.test_key)
        self.assertIs(mock_object, returned_object)


class Gwyfile__getobject_check(unittest.TestCase):
    """
    Test _getobject_check method in Gwyfile class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile.check_gwyobject = Gwyfile.check_gwyobject
        self.key = '/0/mask'

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_check_libgwyfile_function_args(self):
        """
        Check args passed to gwyfile_object_get function
        """

        self.gwyfile.check_gwyobject(self.gwyfile, self.key)
        self.mock_lib.gwyfile_object_get.assert_has_calls(
            [call(self.gwyfile.c_gwyfile, self.key.encode('utf-8'))])

    def test_return_False_if_libgwyfile_func_returns_NULL(self):
        """
        Return False if gwyfile_object_get returns NULL
        """

        self.mock_lib.gwyfile_object_get.return_value = ffi.NULL
        value = self.gwyfile.check_gwyobject(self.gwyfile, self.key)
        self.assertIs(value, False)

    def test_return_True_if_libgwyfile_func_returns_nonNULL(self):
        """
        Return True if gwyfile_object_get returns not NULL
        """

        value = self.gwyfile.check_gwyobject(self.gwyfile, self.key)
        self.assertIs(value, True)


if __name__ == '__main__':
    unittest.main()
