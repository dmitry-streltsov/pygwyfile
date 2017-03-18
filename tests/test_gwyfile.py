import unittest
from unittest.mock import patch, call, ANY, Mock

from pygwyfile.gwyfile import Gwyfile
from pygwyfile.gwyfile import GwyfileError, GwyfileErrorCMsg
from pygwyfile.gwyfile import ffi, lib
from pygwyfile.gwyfile import new_gwycontainer, add_gwyitem_to_gwycontainer


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
        self.assertRaises(GwyfileError, Gwyfile, c_gwyfile)

    @patch('pygwyfile.gwyfile.lib', autospec=True)
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

    @patch('pygwyfile.gwyfile.lib', autospec=True)
    def test_check_top_level_object_of_c_gwyfile(self, mock_lib):
        """Raise GwyfileError exception if top-level object is not
        'GwyContainer' C string
        """

        c_gwyfile = Mock()
        test_name = ffi.new("char[]", b"non-GwyContainer")
        mock_lib.gwyfile_object_name.return_value = test_name
        self.assertRaises(GwyfileError, Gwyfile, c_gwyfile)

    @patch('pygwyfile.gwyfile.lib', autospec=True)
    def test_attribute_of_GwyFile_instance(self, mock_lib):
        """
        Create self.c_gwyfile attribute
        """

        c_gwyfile = Mock()
        test_name = ffi.new("char[]", b"GwyContainer")
        mock_lib.gwyfile_object_name.return_value = test_name
        test_instance = Gwyfile(c_gwyfile)
        self.assertIs(c_gwyfile, test_instance.c_gwyfile)


class Gwyfile_from_gwy(unittest.TestCase):
    """ Test from_gwy method of Gwyfile class
    """

    def setUp(self):
        self.filename = 'test.gwy'

        patcher_isfile = patch('pygwyfile.gwyfile.os.path.isfile',
                               autospec=True)
        self.addCleanup(patcher_isfile.stop)
        self.mock_isfile = patcher_isfile.start()

        patcher_lib = patch('pygwyfile.gwyfile.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()

        patcher_Gwyfile = patch('pygwyfile.gwyfile.Gwyfile',
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
            [call(c_gwyfile)])

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

        patcher_lib = patch('pygwyfile.gwyfile.lib',
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


class Gwyfile_new_gwyitem(unittest.TestCase):
    """ Tests for _new_gwyitem method of Gwyfile class"""

    def test_new_gwyitem(self):
        """ Test Gwyfile._new_gwyitem"""
        cfunc = Mock()
        item_key = '/test_key'
        cvalue = Mock()
        actual_return = Gwyfile._new_gwyitem(cfunc, item_key, cvalue)
        self.assertEqual(actual_return, cfunc.return_value)
        cfunc.assert_has_calls(
            [call(item_key.encode('utf-8'), cvalue)])


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


class Gwyfile_new_gwyitem_bool(unittest.TestCase):
    """Tests for Gwyfile.new_gwyitem_bool method"""
    def setUp(self):
        self.Gwyfile = Mock(spec=Gwyfile)

        patcher_new_gwyitem = patch.object(Gwyfile, '_new_gwyitem')
        self.mock_new_gwyitem = patcher_new_gwyitem.start()
        self.addCleanup(patcher_new_gwyitem.stop)

        self.item_key = '/key'
        self.value = True
        self.gwyitem = Mock()

    def test_return_value(self):
        """Test return value"""
        self.mock_new_gwyitem.side_effect = self._side_effect
        actual_return = Gwyfile.new_gwyitem_bool(self.item_key, self.value)
        self.assertEqual(actual_return,
                         self.gwyitem)

    def _side_effect(self, *args):
        """ Test arguments of gwyfile_item_new_bool C func call"""
        self.assertEqual(args[0], lib.gwyfile_item_new_bool)
        self.assertEqual(args[1], self.item_key)
        self.assertEqual(bool(args[2]), self.value)
        return self.gwyitem


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


class Gwyfile_new_gwyitem_string(unittest.TestCase):
    """Tests for Gwyfile.new_gwyitem_string method"""
    def setUp(self):
        self.Gwyfile = Mock(spec=Gwyfile)

        patcher_new_gwyitem = patch.object(Gwyfile, '_new_gwyitem')
        self.mock_new_gwyitem = patcher_new_gwyitem.start()
        self.addCleanup(patcher_new_gwyitem.stop)

        self.item_key = '/key'
        self.value = 'test string'
        self.gwyitem = Mock()

    def test_return_None_if_value_is_None(self):
        """Return None if value string is None"""
        actual_return = Gwyfile.new_gwyitem_string(self.item_key,
                                                   None)
        self.assertIsNone(actual_return)

    def test_return_value(self):
        """Test return value"""
        self.mock_new_gwyitem.side_effect = self._side_effect
        actual_return = Gwyfile.new_gwyitem_string(self.item_key, self.value)
        self.assertEqual(actual_return,
                         self.gwyitem)

    def _side_effect(self, *args):
        """ Test arguments of gwyfile_item_new_string_copy C func call"""
        self.assertEqual(args[0], lib.gwyfile_item_new_string_copy)
        self.assertEqual(args[1], self.item_key)
        self.assertEqual(ffi.string(args[2]), self.value.encode('utf-8'))
        return self.gwyitem


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


class Gwyfile_new_gwyitem_object(unittest.TestCase):
    """Tests for Gwyfile.new_gwyitem_object method"""
    def setUp(self):
        self.Gwyfile = Mock(spec=Gwyfile)

        patcher_new_gwyitem = patch.object(Gwyfile, '_new_gwyitem')
        self.mock_new_gwyitem = patcher_new_gwyitem.start()
        self.addCleanup(patcher_new_gwyitem.stop)

        self.item_key = '/key'
        self.value = Mock()
        self.gwyitem = Mock()

    def test_return_value(self):
        """Test return value"""
        self.mock_new_gwyitem.side_effect = self._side_effect
        actual_return = Gwyfile.new_gwyitem_object(self.item_key, self.value)
        self.assertEqual(actual_return,
                         self.gwyitem)

    def _side_effect(self, *args):
        """ Test arguments of gwyfile_item_new_object C func call"""
        self.assertEqual(args[0], lib.gwyfile_item_new_object)
        self.assertEqual(args[1], self.item_key)
        self.assertEqual(args[2], self.value)
        return self.gwyitem


class Gwyfile_get_gwyitem_int32(unittest.TestCase):
    """ Tests for Gwyfile.get_gwyitem_int32 method"""
    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_gwyitem_int32 = Gwyfile.get_gwyitem_int32
        self.item_key = '/0/base/range_type'

    def test_return_None_if_data_item_is_not_found(self):
        """ Return None if data item is not found """
        self.gwyfile._get_gwyitem_value.return_value = None
        actual_return = self.gwyfile.get_gwyitem_int32(self.gwyfile,
                                                       self.item_key)
        self.assertIs(actual_return, None)

    def test_return_int32_value_if_data_item_is_found(self):
        """ Return int32 value if data item is found """
        valuep = ffi.new("int32_t*", 1)
        self.gwyfile._get_gwyitem_value.return_value = valuep[0]
        actual_return = self.gwyfile.get_gwyitem_int32(self.gwyfile,
                                                       self.item_key)
        self.assertEqual(actual_return, 1)

    def test_args_of_get_gwyitem_value_call(self):
        """ Test args of Gwyfile._get_gwyitem_value call"""
        self.gwyfile._get_gwyitem_value.return_value = None
        self.gwyfile.get_gwyitem_int32(self.gwyfile, self.item_key)
        self.gwyfile._get_gwyitem_value.assert_has_calls(
            [call(self.item_key, lib.gwyfile_item_get_int32)])


class Gwyfile_new_gwyitem_int32(unittest.TestCase):
    """Tests for Gwyfile.new_gwyitem_int32 method"""
    def setUp(self):
        self.Gwyfile = Mock(spec=Gwyfile)

        patcher_new_gwyitem = patch.object(Gwyfile, '_new_gwyitem')
        self.mock_new_gwyitem = patcher_new_gwyitem.start()
        self.addCleanup(patcher_new_gwyitem.stop)

        self.item_key = '/key'
        self.value = 42
        self.gwyitem = Mock()

    def test_return_value(self):
        """Test return value"""
        self.mock_new_gwyitem.side_effect = self._side_effect
        actual_return = Gwyfile.new_gwyitem_int32(self.item_key, self.value)
        self.assertEqual(actual_return,
                         self.gwyitem)

    def _side_effect(self, *args):
        """ Test arguments of gwyfile_item_new_int32 C func call"""
        self.assertEqual(args[0], lib.gwyfile_item_new_int32)
        self.assertEqual(args[1], self.item_key)
        self.assertEqual(int(args[2]), self.value)
        return self.gwyitem


class Gwyfile_get_gwyitem_double(unittest.TestCase):
    """ Tests for Gwyfile.get_gwyitem_double method"""
    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.get_gwyitem_double = Gwyfile.get_gwyitem_double
        self.item_key = '/0/base/min'

    def test_return_None_if_data_item_is_not_found(self):
        """ Return None if data item is not found """
        self.gwyfile._get_gwyitem_value.return_value = None
        actual_return = self.gwyfile.get_gwyitem_double(self.gwyfile,
                                                        self.item_key)
        self.assertIs(actual_return, None)

    def test_return_double_value_if_data_item_is_found(self):
        """ Return double value if data item is found """
        valuep = ffi.new("double*", 1.)
        self.gwyfile._get_gwyitem_value.return_value = valuep[0]
        actual_return = self.gwyfile.get_gwyitem_double(self.gwyfile,
                                                        self.item_key)
        self.assertEqual(actual_return, 1.)

    def test_args_of_get_gwyitem_value_call(self):
        """ Test args of Gwyfile._get_gwyitem_value call"""
        self.gwyfile._get_gwyitem_value.return_value = None
        self.gwyfile.get_gwyitem_double(self.gwyfile, self.item_key)
        self.gwyfile._get_gwyitem_value.assert_has_calls(
            [call(self.item_key, lib.gwyfile_item_get_double)])


class Gwyfile_new_gwyitem_double(unittest.TestCase):
    """Tests for Gwyfile.new_gwyitem_double method"""
    def setUp(self):
        self.Gwyfile = Mock(spec=Gwyfile)

        patcher_new_gwyitem = patch.object(Gwyfile, '_new_gwyitem')
        self.mock_new_gwyitem = patcher_new_gwyitem.start()
        self.addCleanup(patcher_new_gwyitem.stop)

        self.item_key = '/key'
        self.value = 3.14
        self.gwyitem = Mock()

    def test_return_value(self):
        """Test return value"""
        self.mock_new_gwyitem.side_effect = self._side_effect
        actual_return = Gwyfile.new_gwyitem_double(self.item_key, self.value)
        self.assertEqual(actual_return,
                         self.gwyitem)

    def _side_effect(self, *args):
        """ Test arguments of gwyfile_item_new_double C func call"""
        self.assertEqual(args[0], lib.gwyfile_item_new_double)
        self.assertEqual(args[1], self.item_key)
        self.assertEqual(float(args[2]), self.value)
        return self.gwyitem


class Func_new_gwycontainer(unittest.TestCase):
    """ Tests for new_gwycontainer function"""

    def setUp(self):
        self.gwycontainer = Mock()

    @patch('pygwyfile.gwyfile.lib', autospec=True)
    def test_args_of_libgwyfile_func_call(self, mock_lib):
        """ Call gwyfile_object_new C func to create empty GwyContainer"""
        mock_lib.gwyfile_object_new.side_effect = self._side_effect
        gwycontainer = new_gwycontainer()
        self.assertEqual(gwycontainer, self.gwycontainer)

    def _side_effect(self, *args):
        """ First arg of lib.gwyfile_object_new is b"GwyContainer"
            Last arg of lib.gwyfile_object_new is ffi.NULL
        """
        self.assertEqual(ffi.string(args[0]), b"GwyContainer")
        self.assertEqual(args[-1], ffi.NULL)
        return self.gwycontainer


class Func_add_gwyitem_to_gwycontainer(unittest.TestCase):
    """ Tests for add_gwyitem_to_gwycontainer function"""
    def setUp(self):
        self.gwycontainer = Mock()
        self.gwyitem = Mock()
        self.is_added = True

    @patch('pygwyfile.gwyfile.lib', autospec=True)
    def test_return_True_if_gwyitem_was_added(self, mock_lib):
        """ Return True if gwyfile_object_add func returned true"""
        self.is_added = True
        mock_lib.gwyfile_object_add.side_effect = self._side_effect
        actual_return = add_gwyitem_to_gwycontainer(self.gwyitem,
                                                    self.gwycontainer)
        self.assertEqual(actual_return, self.is_added)

    @patch('pygwyfile.gwyfile.lib', autospec=True)
    def test_return_False_if_gwyitem_was_not_added(self, mock_lib):
        """ Return False if gwyfile_object_add func returned false"""
        self.is_added = False
        mock_lib.gwyfile_object_add.side_effect = self._side_effect
        actual_return = add_gwyitem_to_gwycontainer(self.gwyitem,
                                                    self.gwycontainer)
        self.assertEqual(actual_return, self.is_added)

    def _side_effect(self, *args):
        """ First arg is a GWY file data object
            Second arg is a Gwy file data item
            Returns true is the item was added to the object
        """
        self.assertEqual(args[0], self.gwycontainer)
        self.assertEqual(args[1], self.gwyitem)
        return ffi.cast("bool", self.is_added)


if __name__ == '__main__':
    unittest.main()
