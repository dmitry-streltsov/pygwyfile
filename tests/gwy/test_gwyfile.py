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


class Gwyfile_get_channels_ids_TestCase(unittest.TestCase):
    """Test get_channels_ids function in Gwyfile class """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile.get_channels_ids = Gwyfile.get_channels_ids

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

    def test_libgwyfile_function_returns_non_zero_channels(self):
        """Returns list of channels ids if their number is not zero"""

        self.mock_lib.gwyfile_object_container_enumerate_channels.side_effect = self._side_effect_non_zero_channels
        ids = self.gwyfile.get_channels_ids(self.gwyfile)
        self.assertEqual(ids, [0, 1, 2])

    def _side_effect_non_zero_channels(self, c_gwyfile, nchannelsp):
        nchannelsp[0] = 3
        ids = ffi.new("int[]", [0, 1, 2])
        return ids

    def test_libgwyfile_function_returns_null(self):
        """Returns empty list if libgwyfile function returns NULL"""
        self.mock_lib.gwyfile_object_container_enumerate_channels.return_value = ffi.NULL
        ids = self.gwyfile.get_channels_ids(self.gwyfile)
        self.assertEqual(ids, [])


class Gwyfile__gwyfile_get_object_TestCase(unittest.TestCase):
    """Test _gwyfile_get_object function in Gwyfile class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile._gwyfile_get_object = Gwyfile._gwyfile_get_object

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.test_key = '/0/data'

    def test_raise_exception_if_data_item_is_not_found(self):
        """Raise GwyfileError if data item is not found"""
        self.mock_lib.gwyfile_object_get.return_value = ffi.NULL
        self.assertRaises(GwyfileError,
                          self.gwyfile._gwyfile_get_object,
                          self.gwyfile, self.test_key)

    def test_raise_exception_if_object_is_not_found(self):
        """Raise GwyfileError if object in the data item is empty"""
        self.mock_lib.gwyfile_item_get_object.return_value = ffi.NULL
        mock_item = self.mock_lib.gwyfile_object_get.return_value
        self.assertRaises(GwyfileError,
                          self.gwyfile._gwyfile_get_object,
                          self.gwyfile, mock_item)

    def test_check_args_of_libgwyfile_functions(self):
        """Check arguments passed to Libgwyfile functions"""

        mock_item = self.mock_lib.gwyfile_object_get.return_value

        self.gwyfile._gwyfile_get_object(self.gwyfile, self.test_key)

        self.mock_lib.gwyfile_object_get.assert_has_calls(
            [call(self.gwyfile.c_gwyfile, self.test_key.encode('utf-8'))])
        self.mock_lib.gwyfile_item_get_object.assert_has_calls(
            [call(mock_item)])

    def test_check_returned_value(self):
        """Function returns object returned by gwyfile_item_get_object"""

        mock_object = self.mock_lib.gwyfile_item_get_object.return_value
        returned_object = self.gwyfile._gwyfile_get_object(self.gwyfile,
                                                           self.test_key)
        self.assertIs(mock_object, returned_object)


class Gwyfile__gwydf_get_metadata(unittest.TestCase):
    """Test __gwydf_get_metadata in Gwyfile class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()
        self.gwyfile._gwydf_get_metadata = Gwyfile._gwydf_get_metadata

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        self.test_key = '/0/data'
        self.falsep = ffi.new("bool*", False)
        self.truep = ffi.new("bool*", True)
        self.errorp = ffi.new("GwyfileError**")
        self.metadata_dict = {'xres': ffi.typeof(ffi.new("int32_t*")),
                              'yres': ffi.typeof(ffi.new("int32_t*")),
                              'xreal': ffi.typeof(ffi.new("double*")),
                              'yreal': ffi.typeof(ffi.new("double*")),
                              'xoff': ffi.typeof(ffi.new("double*")),
                              'yoff': ffi.typeof(ffi.new("double*")),
                              'si_unit_xy': ffi.typeof(ffi.new("char**")),
                              'si_unit_z': ffi.typeof(ffi.new("char**"))}

    def test_raise_exception_if_datafield_looks_unacceptable(self):
        """Raise GwyfilleError if gwyfile_object_datafield_get returns False"""

        self.mock_lib.gwyfile_object_datafield_get.return_value = self.falsep[0]
        self.assertRaises(GwyfileError, self.gwyfile._gwydf_get_metadata,
                          self.gwyfile, self.test_key)

    def test_libgwyfile_function_args(self):
        """Test args of gwyfile_object_datafield_get C function """

        self.mock_lib.gwyfile_object_datafield_get.side_effect = self._side_effect_check_args
        self.gwyfile._gwydf_get_metadata(self.gwyfile, self.test_key)

    def _side_effect_check_args(self, *args):
        """Check args passing to gwyfile_object_datafield_get C function"""

        # first arg is GwyDataField object
        self.assertIsInstance(args[0], Mock)

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


if __name__ == '__main__':
    unittest.main()
