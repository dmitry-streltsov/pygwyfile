import unittest
from unittest.mock import patch, call, ANY, Mock

from gwydb.gwy.gwyfile import read_gwyfile
from gwydb.gwy.gwyfile import GwyfileError
from gwydb.gwy.gwyfile import Gwyfile
from gwydb.gwy.gwyfile import ffi


class Func_read_gwy_TestCase(unittest.TestCase):
    """Test read_gwyfile function"""

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

    def test_raise_exception_if_file_doesnt_exist(self):
        """Raise OSError exception if file does not exist"""

        self.mock_isfile.return_value = False
        self.assertRaises(OSError, read_gwyfile, self.filename)

    def test_function_args(self):
        """If file exists call gwyfile_read_file function.
           Check arguments passed to this function
        """

        self.mock_isfile.return_value = True
        read_gwyfile(self.filename)
        self.mock_isfile.assert_has_calls(
            [call(self.filename)])
        self.mock_lib.gwyfile_read_file.assert_has_calls(
            [call(self.filename.encode('utf-8'), ANY)])

    def test_gwyfile_read_file_fails(self):
        """Raise GwyError exception if file reading fails"""

        self.mock_isfile.return_value = True
        self.mock_lib.gwyfile_read_file.return_value = ffi.NULL
        self.assertRaises(GwyfileError, read_gwyfile, self.filename)

    def test_check_returned_value(self):
        """Return the object returned by gwyfile_read_file"""

        self.mock_isfile.return_value = True
        c_gwyfile = self.mock_lib.gwyfile_read_file.return_value
        returned_object = read_gwyfile(self.filename)
        self.assertIs(c_gwyfile, returned_object)


class Gwyfile_init_TestCase(unittest.TestCase):
    """Test constructor of the Gwyfile class

       Gwyfile class is initialized by passing <cdata GwyfileObject*>
       to its constuctor
    """

    def test_raise_exception_if_c_gwyfile_is_empty(self):
        """Raise GwyfileError exception if <cdata GwyfileObject*> is empty"""

        c_gwyfile = ffi.NULL
        self.assertRaises(GwyfileError, Gwyfile, c_gwyfile)

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
        """Create self.c_gwyfile attribute"""

        c_gwyfile = Mock()
        test_name = ffi.new("char[]", b"GwyContainer")
        mock_lib.gwyfile_object_name.return_value = test_name
        test_instance = Gwyfile(c_gwyfile)
        self.assertIs(c_gwyfile, test_instance.c_gwyfile)


class Gwyfile_TestCase(unittest.TestCase):
    """Test methods of the Gwyfile class"""

    def setUp(self):
        self.gwyfileobj = Mock(spec=Gwyfile)
        self.gwyfileobj.c_gwyfile = Mock()
        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()
        self.test_key = '/0/data'

    def test__gwyfile_get_object_raise_exception_if_item_not_found(self):
        """Raise GwyfileError exception if Item not found.

        If gwyfile_object_get(const GwyfileObject* object, const char* name)
        returns NULL - raise GwyfileError exception
        """

        self.gwyfileobj._gwyfile_get_object = Gwyfile._gwyfile_get_object
        self.mock_lib.gwyfile_object_get.return_value = ffi.NULL
        self.assertRaises(GwyfileError,
                          self.gwyfileobj._gwyfile_get_object,
                          self.gwyfileobj, self.test_key)

    def test__gwyfile_get_object_raise_exception_if_object_not_found(self):
        """Raise GwyfileError exception if Object not found.
           If gwyfile_item_get_object(const GwyfileItem* item)
           returns NULL - raise GwyfileError exception
        """

        self.gwyfileobj._gwyfile_get_object = Gwyfile._gwyfile_get_object
        test_item = Mock()
        self.mock_lib.gwyfile_item_get_object.return_value = ffi.NULL
        self.assertRaises(GwyfileError,
                          self.gwyfileobj._gwyfile_get_object,
                          self.gwyfileobj, test_item)

    def test__gwyfile_get_object_check_function_args(self):
        """Check arguments passed to Libgwyfile functions"""

        self.gwyfileobj._gwyfile_get_object = Gwyfile._gwyfile_get_object
        test_item = self.mock_lib.gwyfile_object_get.return_value

        self.gwyfileobj._gwyfile_get_object(self.gwyfileobj, self.test_key)

        self.mock_lib.gwyfile_object_get.assert_has_calls(
            [call(self.gwyfileobj.c_gwyfile, self.test_key.encode('utf-8'))])
        self.mock_lib.gwyfile_item_get_object.assert_has_calls(
            [call(test_item)])

    def test__gwyfile_get_object_check_returned_object(self):
        """Function returns object returned by gwyfile_item_get_object"""

        self.gwyfileobj._gwyfile_get_object = Gwyfile._gwyfile_get_object
        test_object = self.mock_lib.gwyfile_item_get_object.return_value

        returned_object = self.gwyfileobj._gwyfile_get_object(self.gwyfileobj,
                                                              self.test_key)
        self.assertIs(test_object, returned_object)

    def test__gwydf_get_metadata_raise_exception(self):
        """Raise GwyfileError exception
           if gwyfile_object_datafield_get returns False
        """

        self.gwyfileobj._gwydf_get_metadata = Gwyfile._gwydf_get_metadata
        self.mock_lib.gwyfile_object_datafield_get.return_value = ffi.NULL
        self.assertRaises(GwyfileError,
                          self.gwyfileobj._gwydf_get_metadata,
                          self.gwyfileobj, self.test_key)

    def test__gwydf_get_metadata_check_keys_in_result_dic(self):
        """Check keys in returned dictionary"""

        self.gwyfileobj._gwydf_get_metadata = Gwyfile._gwydf_get_metadata
        metadata_dic = self.gwyfileobj._gwydf_get_metadata(self.gwyfileobj,
                                                           self.test_key)
        self.assertIn('xres', metadata_dic)
        self.assertIn('yres', metadata_dic)
        self.assertIn('xreal', metadata_dic)
        self.assertIn('yres', metadata_dic)
        self.assertIn('xyunit', metadata_dic)
        self.assertIn('zunit', metadata_dic)


if __name__ == '__main__':
    unittest.main()
