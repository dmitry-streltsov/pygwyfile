import unittest
from unittest.mock import patch, call, ANY, Mock

import numpy as np

from gwydb.gwy.gwyfile import Gwyfile
from gwydb.gwy.gwyfile import GwyfileError, GwyfileErrorCMsg
from gwydb.gwy.gwyfile import (GwySelection, GwyPointSelections,
                               GwyPointerSelections, GwyLineSelections,
                               GwyRectangleSelections, GwyEllipseSelections)
from gwydb.gwy.gwyfile import GwyDataField
from gwydb.gwy.gwyfile import GwyGraphCurve
from gwydb.gwy.gwyfile import GwyGraphModel
from gwydb.gwy.gwyfile import GwyChannel
from gwydb.gwy.gwyfile import GwyContainer
from gwydb.gwy.gwyfile import ffi
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


class GwySelection__get_selection_nsel(unittest.TestCase):
    """Test _get_selection_nsel methods of GwySelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 3
        patcher = patch.object(GwySelection, '_get_sel_func')
        self.get_sel_func = patcher.start()
        self.addCleanup(patcher.stop)

    def test_raise_exception_in_get_selection_nsel(self):
        """Raise GwyfileErrorCMsg in GwySelection._get_selection_nsel

        Raise GwyfileErrorCMsg in GwySelection._get_selection_nsel
        if get_sel_func returns False
        """
        falsep = ffi.new("bool*", False)
        self.get_sel_func.return_value = falsep[0]
        self.assertRaises(GwyfileErrorCMsg,
                          GwySelection._get_selection_nsel,
                          self.gwysel)

    def test_pos_arguments(self):
        """Test positional arguments in gwyfile_object_selectionpoint_get

        First argument must be GwySelectionPoint libgwyfile object
        Second argument must be GwyfileError** libgwyfile object
        Last argument must be NULL
        """

        self.get_sel_func.side_effect = self._test_pos_args_side_effect
        self.gwysel = Mock()
        GwySelection._get_selection_nsel(self.gwysel)

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

    def test_returned_value(self):
        """Test returned value of _get_selection_nsel method
        """
        self.get_sel_func.side_effect = self._test_returned_value
        self.gwysel = Mock()
        returned_value = GwySelection._get_selection_nsel(self.gwysel)
        self.assertEqual(returned_value, self.nsel)

    def _test_returned_value(self, *args):
        """Write self.nsel in 'nsel' and return True
        """
        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['nsel'][0] = self.nsel

        # Function should return True if object looks acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwySelection_get_selection_points(unittest.TestCase):
    """ Test _get_selection_points method of GwySelection class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 2
        self.points = [(0., 0.), (1., 1.)]
        self.cpoints = ffi.new("double[]", [0., 0., 1., 1.])
        patcher = patch.object(GwySelection, '_get_sel_func')
        self.get_sel_func = patcher.start()
        self.addCleanup(patcher.stop)

    def test_raise_exception_in_get_selection_points(self):
        """Raise GwyfileErrorCMsg in GwySelection._get_selection_points

        Raise GwyfileErrorCMsg in GwySelection._get_selection_points
        if get_sel_func returns False
        """
        falsep = ffi.new("bool*", False)
        self.get_sel_func.return_value = falsep[0]
        self.assertRaises(GwyfileErrorCMsg,
                          GwySelection._get_selection_points,
                          self.gwysel,
                          self.nsel)

    def test_return_None_if_nsel_is_zero(self):
        """Return None if number of selections is zero
        """
        nsel = 0
        points = GwySelection._get_selection_points(self.gwysel,
                                                    nsel)
        self.assertIsNone(points)

    def test_return_points_if_nsel_is_not_zero(self):
        """Return list of points if number of selections is not zero
        """
        self.get_sel_func.side_effect = self._get_points_side_effect
        points = GwySelection._get_selection_points(self.gwysel,
                                                    self.nsel)
        self.assertListEqual(self.points, points)

    def _get_points_side_effect(self, *args):
        """ Write self.cpoints in 'data' field  and return True
        """
        # combine fields names and fields pointers in one dictionary
        arg_keys = [ffi.string(key).decode('utf-8') for key in args[2:-1:2]]
        arg_pointers = [pointer for pointer in args[3:-1:2]]
        arg_dict = dict(zip(arg_keys, arg_pointers))

        arg_dict['data'][0] = self.cpoints

        # Function should return True if object looks acceptable
        truep = ffi.new("bool*", True)
        return truep[0]


class GwySelection__combine_points_in_pairs(unittest.TestCase):
    """Test _combine_points_in_pair method of GwySelection
    """

    def test__combine_ponts_in_pairs_non_empty_arg(self):
        """Combine points in pairs if points list is not empty
        """
        points = [(0., 0.), (1., 1.), (2., 2.), (3., 3.)]
        pairs = GwySelection._combine_points_in_pair(points)
        self.assertListEqual(pairs, [((0., 0.), (1., 1.)),
                                     ((2., 2.), (3., 3.))])

    def test__combine_ponts_in_pairs_empty_arg(self):
        """Return empty list if points list is empty
        """
        points = []
        pairs = GwySelection._combine_points_in_pair(points)
        self.assertListEqual(pairs, [])


class GwyPointSelections_init(unittest.TestCase):
    """Test constructor of GwyPointSelection class
    """

    def test_arg_is_list_of_points(self):
        """GwyPointSelections.__init__ arg is a list
        """
        points = [(1, 2), (3, 4)]
        point_sel = GwyPointSelections(points)
        self.assertListEqual(point_sel.data, points)

    def test_arg_is_tuple_of_points(self):
        """GwyPointSelections.__init__ arg is a tuple
        """
        points = ((1, 2), (3, 4))
        point_sel = GwyPointSelections(points)
        self.assertListEqual(point_sel.data, [(1, 2), (3, 4)])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyPointSelections.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyPointSelections,
                          points)


class GwyPointSelections_from_gwy(unittest.TestCase):
    """Test from_gwy method of  GwyPointSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 3
        self.points = [(1., 1.), (2., 2.), (3., 3.)]

        patcher_nsel = patch.object(GwyPointSelections, '_get_selection_nsel')
        self.get_nsel = patcher_nsel.start()
        self.addCleanup(patcher_nsel.stop)

        patcher_points = patch.object(GwyPointSelections,
                                      '_get_selection_points')
        self.get_points = patcher_points.start()
        self.addCleanup(patcher_points.stop)

    def test_getting_number_of_selections(self):
        """Get number of selections from gwysel
        """
        GwyPointSelections.from_gwy(self.gwysel)
        self.get_nsel.assert_has_calls([call(self.gwysel)])

    def test_getting_points_of_selections(self):
        """Get points of selections from gwysel
        """
        self.get_nsel.return_value = self.nsel
        GwyPointSelections.from_gwy(self.gwysel)
        self.get_points.assert_has_calls([call(self.gwysel, self.nsel)])

    def test_returned_value(self):
        """Return GwyPointSelections initiated by points from gwysel
        """
        self.get_points.return_value = self.points
        point_sel = GwyPointSelections.from_gwy(self.gwysel)
        self.assertListEqual(point_sel.data, self.points)

    def test_return_None_if_there_are_no_points_in_sel(self):
        self.get_points.return_value = None
        point_sel = GwyPointSelections.from_gwy(self.gwysel)
        self.assertIsNone(point_sel)


class GwyPointerSelections_init(unittest.TestCase):
    """Test constructor of GwyPointerSelection class
    """

    def test_arg_is_list_of_points(self):
        """GwyPointerSelections.__init__ arg is a list
        """
        points = [(1, 2), (3, 4)]
        pointer_sel = GwyPointerSelections(points)
        self.assertListEqual(pointer_sel.data, points)

    def test_arg_is_tuple_of_points(self):
        """GwyPointerSelections.__init__ arg is a tuple
        """
        points = ((1, 2), (3, 4))
        pointer_sel = GwyPointSelections(points)
        self.assertListEqual(pointer_sel.data, [(1, 2), (3, 4)])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyPointerSelections.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyPointerSelections,
                          points)


class GwyPointerSelections_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyPointerSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 3
        self.points = [(1., 1.), (2., 2.), (3., 3.)]

        patcher = patch.object(GwySelection,
                               'from_gwy')
        self.from_gwy_parent = patcher.start()
        self.addCleanup(patcher.stop)

    def test_arg_of_parent_from_gwy_method(self):
        """Get selection points
        """
        GwyPointerSelections.from_gwy(self.gwysel)
        self.from_gwy_parent.assert_has_calls([call(self.gwysel)])

    def test_returned_value(self):
        """Return GwyPointSelections initiated by points from gwysel
        """
        self.from_gwy_parent.return_value = self.points
        pointer_sel = GwyPointerSelections.from_gwy(self.gwysel)
        self.assertListEqual(pointer_sel.data, self.points)

    def test_return_None_if_there_are_no_points_in_sel(self):
        """Return None if there are no points in the selection
        """
        self.from_gwy_parent.return_value = None
        pointer_sel = GwyPointerSelections.from_gwy(self.gwysel)
        self.assertIsNone(pointer_sel)


class GwyLineSelections_init(unittest.TestCase):
    """Test constructor of GwyLineSelections class
    """

    def test_arg_is_list_of_point_pairs(self):
        """GwyLineSelections.__init__ arg is a list
        """
        point_pairs = [((0, 0), (1, 1)),
                       ((2, 2), (3, 3))]
        line_sel = GwyLineSelections(point_pairs)
        self.assertListEqual(line_sel.data, point_pairs)

    def test_arg_is_tuple_of_points(self):
        """GwyLineSelections.__init__ arg is a tuple
        """
        point_pairs = (((0, 0), (1, 1)),
                       ((2, 2), (3, 3)))
        line_sel = GwyLineSelections(point_pairs)
        self.assertListEqual(line_sel.data,
                             [((0, 0), (1, 1)),
                              ((2, 2), (3, 3))])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyLineSelections.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyLineSelections,
                          points)


class GwyLineSelections_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyLineSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.points = [(0, 0), (1, 1), (2, 2), (3, 3)]
        self.point_pairs = [((0, 0), (1, 1)),
                            ((2, 2), (3, 3))]

        patcher = patch.object(GwySelection,
                               'from_gwy')
        self.from_gwy_parent = patcher.start()
        self.addCleanup(patcher.stop)

    def test_arg_of_parent_from_gwy_method(self):
        """Get selection points
        """
        self.from_gwy_parent.return_value = self.points
        GwyLineSelections.from_gwy(self.gwysel)
        self.from_gwy_parent.assert_has_calls([call(self.gwysel)])

    def test_returned_value(self):
        """Return GwyLineSelections initiated by point pairs from gwysel
        """
        self.from_gwy_parent.return_value = self.points
        line_sel = GwyLineSelections.from_gwy(self.gwysel)
        self.assertListEqual(line_sel.data, self.point_pairs)

    def test_return_None_if_there_are_no_points_in_sel(self):
        """Return None if there are no points in the selection
        """
        self.from_gwy_parent.return_value = None
        line_sel = GwyLineSelections.from_gwy(self.gwysel)
        self.assertIsNone(line_sel)


class GwyRectangleSelections_init(unittest.TestCase):
    """Test constructor of GwyRectangleSelections class
    """

    def test_arg_is_list_of_point_pairs(self):
        """GwyRectangleSelections.__init__ arg is a list
        """
        point_pairs = [((0, 0), (1, 1)),
                       ((2, 2), (3, 3))]
        rectangle_sel = GwyRectangleSelections(point_pairs)
        self.assertListEqual(rectangle_sel.data, point_pairs)

    def test_arg_is_tuple_of_points(self):
        """GwyRectangleSelections.__init__ arg is a tuple
        """
        point_pairs = (((0, 0), (1, 1)),
                       ((2, 2), (3, 3)))
        rectangle_sel = GwyRectangleSelections(point_pairs)
        self.assertListEqual(rectangle_sel.data,
                             [((0, 0), (1, 1)),
                              ((2, 2), (3, 3))])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyRectangleSelections.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyRectangleSelections,
                          points)


class GwyRectangleSelections_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyRectangleSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.points = [(0, 0), (1, 1), (2, 2), (3, 3)]
        self.point_pairs = [((0, 0), (1, 1)),
                            ((2, 2), (3, 3))]

        patcher = patch.object(GwySelection,
                               'from_gwy')
        self.from_gwy_parent = patcher.start()
        self.addCleanup(patcher.stop)

    def test_arg_of_parent_from_gwy_method(self):
        """Get selection points
        """
        self.from_gwy_parent.return_value = self.points
        GwyRectangleSelections.from_gwy(self.gwysel)
        self.from_gwy_parent.assert_has_calls([call(self.gwysel)])

    def test_returned_value(self):
        """Return GwyRectangleSelections initiated by point pairs from gwysel
        """
        self.from_gwy_parent.return_value = self.points
        rectangle_sel = GwyRectangleSelections.from_gwy(self.gwysel)
        self.assertListEqual(rectangle_sel.data, self.point_pairs)

    def test_return_None_if_there_are_no_points_in_sel(self):
        """Return None if there are no points in the selection
        """
        self.from_gwy_parent.return_value = None
        rectangle_sel = GwyRectangleSelections.from_gwy(self.gwysel)
        self.assertIsNone(rectangle_sel)


class GwyEllipseSelections_init(unittest.TestCase):
    """Test constructor of GwyEllipseSelections class
    """

    def test_arg_is_list_of_point_pairs(self):
        """GwyEllipseSelections.__init__ arg is a list
        """
        point_pairs = [((0, 0), (1, 1)),
                       ((2, 2), (3, 3))]
        ellipse_sel = GwyEllipseSelections(point_pairs)
        self.assertListEqual(ellipse_sel.data, point_pairs)

    def test_arg_is_tuple_of_points(self):
        """GwyEllipseSelections.__init__ arg is a tuple
        """
        point_pairs = (((0, 0), (1, 1)),
                       ((2, 2), (3, 3)))
        ellipse_sel = GwyEllipseSelections(point_pairs)
        self.assertListEqual(ellipse_sel.data,
                             [((0, 0), (1, 1)),
                              ((2, 2), (3, 3))])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyEllipseSelections.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyEllipseSelections,
                          points)


class GwyEllipseSelections_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyEllipseSelections class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.points = [(0, 0), (1, 1), (2, 2), (3, 3)]
        self.point_pairs = [((0, 0), (1, 1)),
                            ((2, 2), (3, 3))]

        patcher = patch.object(GwySelection,
                               'from_gwy')
        self.from_gwy_parent = patcher.start()
        self.addCleanup(patcher.stop)

    def test_arg_of_parent_from_gwy_method(self):
        """Get selection points
        """
        self.from_gwy_parent.return_value = self.points
        GwyEllipseSelections.from_gwy(self.gwysel)
        self.from_gwy_parent.assert_has_calls([call(self.gwysel)])

    def test_returned_value(self):
        """Return GwyEllipseSelections initiated by point pairs from gwysel
        """
        self.from_gwy_parent.return_value = self.points
        ellipse_sel = GwyEllipseSelections.from_gwy(self.gwysel)
        self.assertListEqual(ellipse_sel.data, self.point_pairs)

    def test_return_None_if_there_are_no_points_in_sel(self):
        """Return None if there are no points in the selection
        """
        self.from_gwy_parent.return_value = None
        ellipse_sel = GwyEllipseSelections.from_gwy(self.gwysel)
        self.assertIsNone(ellipse_sel)


class GwyDataField_init(unittest.TestCase):
    """Test constructor of GwyDataField class
    """
    def setUp(self):
        self.test_data = np.random.rand(256, 256)
        self.test_meta = {'xres': 256,
                          'yres': 256,
                          'xreal': 1e-6,
                          'yreal': 1e-6,
                          'xoff': 0.,
                          'yoff': 0.,
                          'si_unit_xy': 'm',
                          'si_unit_z': 'A'}

    def test_init_with_test_data(self):
        """Test __init__ with data and meta args
        """
        gwydf = GwyDataField(data=self.test_data, meta=self.test_meta)
        np.testing.assert_almost_equal(gwydf.data, self.test_data)
        self.assertDictEqual(self.test_meta, gwydf.meta)

    def test_init_with_empty_meta(self):
        """Test __init__ with empty meta arg
        """
        gwydf = GwyDataField(data=self.test_data)
        np.testing.assert_almost_equal(gwydf.data, self.test_data)
        self.assertDictEqual(gwydf.meta,
                             {'xres': 256,
                              'yres': 256,
                              'xreal': 1.,
                              'yreal': 1.,
                              'xoff': 0.,
                              'yoff': 0.,
                              'si_unit_xy': '',
                              'si_unit_z': ''})

    def test_raise_ValueError_if_mismatched_data_shape_and_xres_yres(self):
        """Raise ValueError if data.shape is not equal meta['xres'], meta['yres']
        """
        test_meta = {'xres': 128,
                     'yres': 128}  # self.test_data.shape = 256, 256
        self.assertRaises(ValueError,
                          GwyDataField,
                          data=self.test_data,
                          meta=test_meta)


class GwyDataField_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyDataField class
    """
    @patch('gwydb.gwy.gwyfile.GwyDataField', autospec=True)
    @patch.object(GwyDataField, '_get_data')
    @patch.object(GwyDataField, '_get_meta')
    def test_GwyDataField_from_gwy(self,
                                   mock_get_meta,
                                   mock_get_data,
                                   mock_GwyDataField):
        """ Get metadata and data from <GwyDatafield*> object, init GwyDatafield
            and return the latter
        """
        cgwydf = Mock()
        test_meta = {'xres': 256,
                     'yres': 256,
                     'xreal': 1e-6,
                     'yreal': 1e-6,
                     'xoff': 0.,
                     'yoff': 0.,
                     'si_unit_xy': 'm',
                     'si_unit_z': 'A'}
        test_data = np.random.rand(256, 256)
        mock_get_meta.return_value = test_meta
        mock_get_data.return_value = test_data
        gwydf = GwyDataField.from_gwy(cgwydf)
        mock_get_meta.assert_has_calls(
            [call(cgwydf)])
        mock_get_data.assert_has_calls(
            [call(cgwydf, test_meta['xres'], test_meta['yres'])])
        mock_GwyDataField.assert_has_calls(
            [call(data=test_data, meta=test_meta)])
        self.assertEqual(gwydf, mock_GwyDataField(data=test_data,
                                                  meta=test_meta))


class GwyDataField_get_meta(unittest.TestCase):
    """Test _get_meta method of GwyDataFieldself
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
    """Test constructor of GwyGraphCurve
    """
    def setUp(self):
        self.test_meta = {'ndata': 256,
                          'description': "Curve label",
                          'type': 1,
                          'point_type': 1,
                          'line_style': 0,
                          'point_size': 5,
                          'line_size': 1,
                          'color.red': 0.,
                          'color.green': 0.,
                          'color.blue': 0.}
        self.test_data = np.random.rand(2, 256)

    def test_init_with_test_data(self):
        """Test __init__ with data and meta args
        """
        gwycurve = GwyGraphCurve(data=self.test_data, meta=self.test_meta)
        np.testing.assert_almost_equal(gwycurve.data, self.test_data)
        self.assertDictEqual(gwycurve.meta, self.test_meta)

    def test_init_with_empty_meta(self):
        """Test __init__ with empty meta arg
        """
        gwycurve = GwyGraphCurve(data=self.test_data)
        np.testing.assert_almost_equal(gwycurve.data, self.test_data)
        self.assertDictEqual(gwycurve.meta,
                             {'ndata': 256,
                              'description': '',
                              'type': 1,
                              'point_type': 2,
                              'line_style': 0,
                              'point_size': 1,
                              'line_size': 1,
                              'color.red': 0.,
                              'color.green': 0.,
                              'color.blue': 0.})

    def test_raise_ValueError_if_wrong_number_of_data_points(self):
        """Raise ValueError if data.shape is not equal (2, meta['ndata'])
        """
        test_meta = {'ndata': 128}  # self.test_data.shape = 256, 256
        self.assertRaises(ValueError,
                          GwyGraphCurve,
                          data=self.test_data,
                          meta=test_meta)

    def test_raise_ValueError_if_wrong_shape_of_data_array(self):
        """Raise ValueError if data.shape is not equal (2, ndata)
        """
        test_data = np.random.rand(256)
        self.assertRaises(ValueError,
                          GwyGraphCurve,
                          data=test_data)

        test_data = np.random.rand(3, 256)
        self.assertRaises(ValueError,
                          GwyGraphCurve,
                          data=test_data)


class GwyGraphCurve_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyGraphCurve class
    """

    @patch('gwydb.gwy.gwyfile.GwyGraphCurve', autospec=True)
    @patch.object(GwyGraphCurve, '_get_data')
    @patch.object(GwyGraphCurve, '_get_meta')
    def test_GwyGraphCurve_init(self,
                                mock_get_meta,
                                mock_get_data,
                                mock_GwyGraphCurve):
        cgwycurve = Mock()
        test_meta = {'ndata': 256,
                     'description': "Curve label",
                     'type': 1}
        test_data = np.random.rand(2, 256)
        mock_get_meta.return_value = test_meta
        mock_get_data.return_value = test_data
        gwycurve = GwyGraphCurve.from_gwy(cgwycurve)
        mock_get_meta.assert_has_calls(
            [call(cgwycurve)])
        mock_get_data.assert_has_calls(
            [call(cgwycurve, test_meta['ndata'])])
        self.assertEqual(gwycurve, mock_GwyGraphCurve(data=test_data,
                                                      meta=test_meta))


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


class GwyGraphModel_init(unittest.TestCase):
    """Test constructor of GwyGraphModel class
    """

    def setUp(self):
        self.test_meta = {'ncurves': 2,
                          'title': 'Plot',
                          'top_label': 'Top label',
                          'left_label': 'Left label',
                          'right_label': 'Right label',
                          'bottom_label': 'Bottom label',
                          'x_unit': 'm',
                          'y_unit': 'm',
                          'x_min': 0.,
                          'x_min_set': True,
                          'x_max': 1.,
                          'x_max_set': True,
                          'y_min': None,
                          'y_min_set': False,
                          'y_max': None,
                          'y_max_set': False,
                          'x_is_logarithmic': False,
                          'y_is_logarithmic': False,
                          'label.visible': True,
                          'label.has_frame': True,
                          'label.reverse': False,
                          'label.frame_thickness': 1,
                          'label.position': 0,
                          'grid-type': 1}
        self.test_curves = [Mock(spec=GwyGraphCurve),
                            Mock(spec=GwyGraphCurve)]

    def test_init_with_curves_and_meta(self):
        """Test GwyGraphModel constructor if meta is defined
        """
        graph = GwyGraphModel(curves=self.test_curves,
                              meta=self.test_meta)
        self.assertEqual(graph.curves, self.test_curves)
        self.assertDictEqual(graph.meta, self.test_meta)

    def test_init_with_curves_without_meta(self):
        """Test GwyGraphModel constructor with default meta
        """
        graph = GwyGraphModel(curves=self.test_curves)
        self.assertEqual(graph.curves, self.test_curves)
        self.assertDictEqual(graph.meta,
                             {'ncurves': 2,
                              'title': '',
                              'top_label': '',
                              'left_label': '',
                              'right_label': '',
                              'bottom_label': '',
                              'x_unit': '',
                              'y_unit': '',
                              'x_min': None,
                              'x_min_set': False,
                              'x_max': None,
                              'x_max_set': False,
                              'y_min': None,
                              'y_min_set': False,
                              'y_max': None,
                              'y_max_set': False,
                              'x_is_logarithmic': False,
                              'y_is_logarithmic': False,
                              'label.visible': True,
                              'label.has_frame': True,
                              'label.reverse': False,
                              'label.frame_thickness': 1,
                              'label.position': 0,
                              'grid-type': 1})

    def test_raise_TypeError_if_curve_is_not_GwyGraphCurve(self):
        """Raise TypeError exception if curve is not GwyGraphCurve
        instance
        """
        self.assertRaises(TypeError,
                          GwyGraphModel,
                          curves=np.random.rand(10))

    def test_raise_ValueError_if_number_of_curves_and_ncurves_different(self):
        """Raise ValueError if len(curves) is not equal to meta['ncurves']
        """
        self.assertRaises(ValueError,
                          GwyGraphModel,
                          curves=[Mock(GwyGraphCurve)],  # just one curve
                          meta=self.test_meta)           # meta['ncurves'] = 2


class GwyGraphModel_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyGraphModel class
    """

    @patch('gwydb.gwy.gwyfile.GwyGraphModel', autospec=True)
    @patch('gwydb.gwy.gwyfile.GwyGraphCurve', autospec=True)
    @patch.object(GwyGraphModel, '_get_curves')
    @patch.object(GwyGraphModel, '_get_meta')
    def test_arg_passing_to_other_methods(self,
                                          mock_get_meta,
                                          mock_get_curves,
                                          mock_GwyGraphCurve,
                                          mock_GwyGraphModel):
        """
        """
        gwygraphmodel = Mock()
        test_meta = {'ncurves': 2}
        test_gwycurves = [Mock(), Mock()]
        mock_get_meta.return_value = test_meta
        mock_get_curves.return_value = test_gwycurves
        graphmodel = Mock(spec=GwyGraphModel)
        mock_GwyGraphModel.return_value = graphmodel

        graph = GwyGraphModel.from_gwy(gwygraphmodel)

        # get meta data from <GwyGraphModel*> object
        mock_get_meta.assert_has_calls(
            [call(gwygraphmodel)])

        # get list of <GwyGraphModelCurve*> objects
        mock_get_curves.assert_has_calls(
            [call(gwygraphmodel, test_meta['ncurves'])])

        # create list of GwyGraphCurves instances
        mock_GwyGraphCurve.from_gwy.assert_has_calls(
            [call(gwycurve) for gwycurve in test_gwycurves])

        # create GwyGraphModel instance
        mock_GwyGraphModel.assert_has_calls(
            [call(curves=[mock_GwyGraphCurve.from_gwy.return_value
                          for gwycurve in test_gwycurves],
                  meta=test_meta)])

        # return GwyGraphModel instance
        self.assertEqual(graph, graphmodel)


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
                          GwyGraphModel.from_gwy,
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

        # first arg is GwyDatafield returned by get_gwyobject
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


# class GwyGraphModel_init(unittest.TestCase):
#     """Test __init__ method of GwyGraphModel class
#     """
#     @patch.object(GwyGraphModel, '__init__')
#     @patch.object(GwyGraphCurve, 'from_gwy')
#     @patch.object(GwyGraphModel, '_get_curves')
#     @patch.object(GwyGraphModel, '_get_meta')
#     def test_GwyGraphModel_init(self,
#                                 mock_get_meta,
#                                 mock_get_curves,
#                                 mock_from_gwy,
#                                 mock_GwyGraphModel):
#         cgwygraphmodel = Mock()
#         test_meta = {'ncurves': 3,
#                      'title': 'Profiles',
#                      'x_unit': 'm',
#                      'y_unit': 'm'}
#         cgwycurves_array = ffi.new("GwyfileObject*[]", test_meta['ncurves'])
#         mock_get_meta.return_value = test_meta
#         mock_get_curves.return_value = cgwycurves_array
#         mock_GwyGraphModel.return_value = None

#         graphmodel = GwyGraphModel.from_gwy(cgwygraphmodel)
#         self.assertDictEqual(test_meta, graphmodel.meta)
#         mock_gwygraphcurve.assert_has_calls(
#             [call(curve) for curve in cgwycurves_array])
#         self.assertEqual(graphmodel.curves, graphmodel._curves)


class GwyChannel_get_title(unittest.TestCase):
    """Test _get_title method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        self.gwyfile.get_gwyobject.return_value = (
            ffi.new("char[]", b"Title"))

    def test_raise_exception_if_gwyobject_does_not_exist(self):
        """Raise GwyFileError is title gwyobject does not exist
        """
        self.gwyfile.check_gwyobject.return_value = False
        self.assertRaises(GwyfileError,
                          GwyChannel._get_title,
                          self.gwyfile,
                          self.channel_id)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyobject method
        """

        GwyChannel._get_title(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyobject.assert_has_calls(
            [call("/{:d}/data/title".format(self.channel_id))])

    def test_returned_value(self):
        """
        Check returned value of get_title method
        """

        title = GwyChannel._get_title(self.gwyfile, self.channel_id)
        self.assertEqual(title, 'Title')


class GwyChannel_get_data(unittest.TestCase):
    """Test _get_data method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwyfile.GwyDataField',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyDataField = patcher.start()

    def test_raise_exception_if_gwydatafield_does_not_exist(self):
        """Raise GwyFileError is <GwyDataField*>  object does not exist
        """
        self.gwyfile.check_gwyobject.return_value = False
        self.assertRaises(GwyfileError,
                          GwyChannel._get_data,
                          self.gwyfile,
                          self.channel_id)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyobject method
        """

        GwyChannel._get_data(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyobject.assert_has_calls(
            [call("/{:d}/data".format(self.channel_id))])

    def test_call_GwyDataField_constructor(self):
        """
        Pass gwydatafield object to GwyDataField constructor
        """

        gwydatafield = self.gwyfile.get_gwyobject.return_value
        GwyChannel._get_data(self.gwyfile, self.channel_id)
        self.mock_GwyDataField.from_gwy.assert_has_calls(
            [call(gwydatafield)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyDataField constructor
        """

        expected_return = self.mock_GwyDataField.from_gwy.return_value
        actual_return = GwyChannel._get_data(self.gwyfile, self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_mask(unittest.TestCase):
    """Test _get_mask method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwyfile.GwyDataField',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyDataField = patcher.start()

    def test_check_existence_of_mask_datafield(self):
        """Check that mask <GwyDataField*> exists
        """
        GwyChannel._get_mask(self.gwyfile, self.channel_id)
        self.gwyfile.check_gwyobject.assert_has_calls(
            [call("/{:d}/mask".format(self.channel_id))])

    def test_return_None_if_mask_datafield_does_not_exist(self):
        """Return None if mask <GwyDataField*> does not exist
        """
        self.gwyfile.check_gwyobject.return_value = False
        actual_return = GwyChannel._get_mask(self.gwyfile,
                                             self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyobject method
        """

        GwyChannel._get_mask(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyobject.assert_has_calls(
            [call("/{:d}/mask".format(self.channel_id))])

    def test_call_GwyDataField_constructor(self):
        """
        Pass gwydatafield object to GwyDataField constructor
        """

        gwydatafield = self.gwyfile.get_gwyobject.return_value
        GwyChannel._get_mask(self.gwyfile, self.channel_id)
        self.mock_GwyDataField.from_gwy.assert_has_calls(
            [call(gwydatafield)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyDataField constructor
        """

        expected_return = self.mock_GwyDataField.from_gwy.return_value
        actual_return = GwyChannel._get_mask(self.gwyfile, self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_show(unittest.TestCase):
    """Test _get_show method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwyfile.GwyDataField',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyDataField = patcher.start()

    def test_check_existence_of_show_datafield(self):
        """Check that presentation <GwyDataField*> exists
        """
        GwyChannel._get_show(self.gwyfile, self.channel_id)
        self.gwyfile.check_gwyobject.assert_has_calls(
            [call("/{:d}/show".format(self.channel_id))])

    def test_return_None_if_show_datafield_does_not_exist(self):
        """Return None if presentation <GwyDataField*> does not exist
        """
        self.gwyfile.check_gwyobject.return_value = False
        actual_return = GwyChannel._get_show(self.gwyfile,
                                             self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyobject method
        """

        GwyChannel._get_show(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyobject.assert_has_calls(
            [call("/{:d}/show".format(self.channel_id))])

    def test_call_GwyDataField_constructor(self):
        """
        Pass gwydatafield object to GwyDataField constructor
        """

        gwydatafield = self.gwyfile.get_gwyobject.return_value
        GwyChannel._get_show(self.gwyfile, self.channel_id)
        self.mock_GwyDataField.from_gwy.assert_has_calls(
            [call(gwydatafield)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyDataField constructor
        """

        expected_return = self.mock_GwyDataField.from_gwy.return_value
        actual_return = GwyChannel._get_show(self.gwyfile, self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_point_sel(unittest.TestCase):
    """Test _get_point_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwyfile.GwyPointSelections',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyPointSelections = patcher.start()

    def test_check_existence_of_point_selections(self):
        """Check that point selections exists in the channel
        """
        GwyChannel._get_point_sel(self.gwyfile, self.channel_id)
        self.gwyfile.check_gwyobject.assert_has_calls(
            [call("/{:d}/select/point".format(self.channel_id))])

    def test_return_None_if_point_selections_do_not_exist(self):
        """Return None if point selections do not exist
        """
        self.gwyfile.check_gwyobject.return_value = False
        actual_return = GwyChannel._get_point_sel(self.gwyfile,
                                                  self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyobject method
        """

        GwyChannel._get_point_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyobject.assert_has_calls(
            [call("/{:d}/select/point".format(self.channel_id))])

    def test_call_GwyPointSelections_constructor(self):
        """
        Pass gwypointselection object to GwyPointSelections.from_gwy method
        """

        gwypointsel = self.gwyfile.get_gwyobject.return_value
        GwyChannel._get_point_sel(self.gwyfile, self.channel_id)
        self.mock_GwyPointSelections.from_gwy.assert_has_calls(
            [call(gwypointsel)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyPointSelections constructor
        """

        expected_return = self.mock_GwyPointSelections.from_gwy.return_value
        actual_return = GwyChannel._get_point_sel(self.gwyfile,
                                                  self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_pointer_sel(unittest.TestCase):
    """Test _get_pointer_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwyfile.GwyPointerSelections',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyPointerSelections = patcher.start()

    def test_check_existence_of_pointer_selections(self):
        """Check that pointer selections exists in the channel
        """
        GwyChannel._get_pointer_sel(self.gwyfile, self.channel_id)
        self.gwyfile.check_gwyobject.assert_has_calls(
            [call("/{:d}/select/pointer".format(self.channel_id))])

    def test_return_None_if_pointer_selections_do_not_exist(self):
        """Return None if pointer selections do not exist
        """
        self.gwyfile.check_gwyobject.return_value = False
        actual_return = GwyChannel._get_pointer_sel(self.gwyfile,
                                                    self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyobject method
        """

        GwyChannel._get_pointer_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyobject.assert_has_calls(
            [call("/{:d}/select/pointer".format(self.channel_id))])

    def test_call_GwyPointSelections_constructor(self):
        """
        Pass gwypointselection object to GwyPointerSelections constructor
        """

        gwypointersel = self.gwyfile.get_gwyobject.return_value
        GwyChannel._get_pointer_sel(self.gwyfile, self.channel_id)
        self.mock_GwyPointerSelections.from_gwy.assert_has_calls(
            [call(gwypointersel)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyPointerSelections constructor
        """

        expected_return = self.mock_GwyPointerSelections.from_gwy.return_value
        actual_return = GwyChannel._get_pointer_sel(self.gwyfile,
                                                    self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_line_sel(unittest.TestCase):
    """Test _get_line_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwyfile.GwyLineSelections',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyLineSelections = patcher.start()

    def test_check_existence_of_line_selections(self):
        """Check that line selections exists in the channel
        """
        GwyChannel._get_line_sel(self.gwyfile, self.channel_id)
        self.gwyfile.check_gwyobject.assert_has_calls(
            [call("/{:d}/select/line".format(self.channel_id))])

    def test_return_None_if_line_selections_do_not_exist(self):
        """Return None if line selections do not exist
        """
        self.gwyfile.check_gwyobject.return_value = False
        actual_return = GwyChannel._get_line_sel(self.gwyfile,
                                                 self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyobject method
        """

        GwyChannel._get_line_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyobject.assert_has_calls(
            [call("/{:d}/select/line".format(self.channel_id))])

    def test_call_GwyLineSelections_constructor(self):
        """
        Pass gwylineselection object to GwyLineSelections constructor
        """

        gwylinesel = self.gwyfile.get_gwyobject.return_value
        GwyChannel._get_line_sel(self.gwyfile, self.channel_id)
        self.mock_GwyLineSelections.from_gwy.assert_has_calls(
            [call(gwylinesel)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyLineSelections constructor
        """

        expected_return = self.mock_GwyLineSelections.from_gwy.return_value
        actual_return = GwyChannel._get_line_sel(self.gwyfile,
                                                 self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_rectangle_sel(unittest.TestCase):
    """Test _get_rectangle_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwyfile.GwyRectangleSelections',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyRectangleSelections = patcher.start()

    def test_check_existence_of_rectangle_selections(self):
        """Check that rectangle selections exists in the channel
        """
        GwyChannel._get_rectangle_sel(self.gwyfile, self.channel_id)
        self.gwyfile.check_gwyobject.assert_has_calls(
            [call("/{:d}/select/rectangle".format(self.channel_id))])

    def test_return_None_if_rectangle_selections_do_not_exist(self):
        """Return None if rectangle selections do not exist
        """
        self.gwyfile.check_gwyobject.return_value = False
        actual_return = GwyChannel._get_rectangle_sel(self.gwyfile,
                                                      self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyobject method
        """

        GwyChannel._get_rectangle_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyobject.assert_has_calls(
            [call("/{:d}/select/rectangle".format(self.channel_id))])

    def test_call_GwyRectangleSelections_constructor(self):
        """
        Pass gwyrectangleselection object to GwyRectangleSelections constructor
        """

        gwyrectsel = self.gwyfile.get_gwyobject.return_value
        GwyChannel._get_rectangle_sel(self.gwyfile, self.channel_id)
        self.mock_GwyRectangleSelections.from_gwy.assert_has_calls(
            [call(gwyrectsel)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyRectangleSelections constructor
        """

        expected_return = (
            self.mock_GwyRectangleSelections.from_gwy.return_value)
        actual_return = GwyChannel._get_rectangle_sel(self.gwyfile,
                                                      self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_ellipse_sel(unittest.TestCase):
    """Test _get_ellipse_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwyfile.GwyEllipseSelections',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyEllipseSelections = patcher.start()

    def test_check_existence_of_ellipse_selections(self):
        """Check that ellipse selections exists in the channel
        """
        GwyChannel._get_ellipse_sel(self.gwyfile, self.channel_id)
        self.gwyfile.check_gwyobject.assert_has_calls(
            [call("/{:d}/select/ellipse".format(self.channel_id))])

    def test_return_None_if_ellipse_selections_do_not_exist(self):
        """Return None if ellipse selections do not exist
        """
        self.gwyfile.check_gwyobject.return_value = False
        actual_return = GwyChannel._get_ellipse_sel(self.gwyfile,
                                                    self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyobject method
        """

        GwyChannel._get_ellipse_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyobject.assert_has_calls(
            [call("/{:d}/select/ellipse".format(self.channel_id))])

    def test_call_GwyEllipseSelections_constructor(self):
        """
        Pass gwyellipseselection object to GwyEllipseSelections constructor
        """

        gwyellipsesel = self.gwyfile.get_gwyobject.return_value
        GwyChannel._get_ellipse_sel(self.gwyfile, self.channel_id)
        self.mock_GwyEllipseSelections.from_gwy.assert_has_calls(
            [call(gwyellipsesel)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyEllipseSelections constructor
        """

        expected_return = self.mock_GwyEllipseSelections.from_gwy.return_value
        actual_return = GwyChannel._get_ellipse_sel(self.gwyfile,
                                                    self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_init(unittest.TestCase):
    """Test __init__ method of GwyChannel class
    """

    @patch.object(GwyChannel, '_get_title')
    @patch.object(GwyChannel, '_get_data')
    @patch.object(GwyChannel, '_get_mask')
    @patch.object(GwyChannel, '_get_show')
    @patch.object(GwyChannel, '_get_point_sel')
    @patch.object(GwyChannel, '_get_pointer_sel')
    @patch.object(GwyChannel, '_get_line_sel')
    @patch.object(GwyChannel, '_get_rectangle_sel')
    @patch.object(GwyChannel, '_get_ellipse_sel')
    def test_GwyGraphModel_init(self,
                                mock_get_ellipse_sel,
                                mock_get_rectangle_sel,
                                mock_get_line_sel,
                                mock_get_pointer_sel,
                                mock_get_point_sel,
                                mock_get_show,
                                mock_get_mask,
                                mock_get_data,
                                mock_get_title):
        gwyfile = Mock(spec=Gwyfile)
        channel_id = 0
        channel = GwyChannel(gwyfile, channel_id)
        self.assertEqual(channel.title, mock_get_title.return_value)
        self.assertEqual(channel.data, mock_get_data.return_value)
        self.assertEqual(channel.mask, mock_get_mask.return_value)
        self.assertEqual(channel.show, mock_get_show.return_value)
        self.assertEqual(channel.point_selections,
                         mock_get_point_sel.return_value)
        self.assertEqual(channel.pointer_selections,
                         mock_get_pointer_sel.return_value)
        self.assertEqual(channel.line_selections,
                         mock_get_line_sel.return_value)
        self.assertEqual(channel.rectangle_selections,
                         mock_get_rectangle_sel.return_value)
        self.assertEqual(channel.ellipse_selections,
                         mock_get_ellipse_sel.return_value)


class GwyContainer_get_channel_ids_TestCase(unittest.TestCase):
    """
    Test _get_channel_ids method in GwyContainer class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.gwyfile.c_gwyfile = Mock()

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
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

        patcher_lib = patch('gwydb.gwy.gwyfile.lib', autospec=True)
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

    @patch('gwydb.gwy.gwyfile.GwyChannel', autospec=True)
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
                             [mock_GwyChannel(gwyfile, channel_id)
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
    @patch('gwydb.gwy.gwyfile.GwyGraphModel', autospec=True)
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


class GwyContainer_init(unittest.TestCase):
    """Test __init__ method of GwyContainer
    """

    @patch.object(GwyContainer, '_dump_graphs')
    @patch.object(GwyContainer, '_dump_channels')
    def test_init_method_of_GwyContainer(self,
                                         mock_dump_channels,
                                         mock_dump_graphs):
        gwyfile = Mock(spec=Gwyfile)
        channels = Mock(spec=list)
        graphs = Mock(spec=list)
        mock_dump_channels.return_value = channels
        mock_dump_graphs.return_value = graphs
        container = GwyContainer(gwyfile)
        self.assertEqual(container.channels, channels)
        self.assertEqual(container.graphs, graphs)


if __name__ == '__main__':
    unittest.main()
