import unittest
from unittest.mock import patch, call, Mock

from gwydb.gwy._libgwyfile import ffi
from gwydb.gwy.gwyfile import GwyfileErrorCMsg
from gwydb.gwy.gwyselection import (GwySelection,
                                    GwyPointSelection,
                                    GwyPointerSelection,
                                    GwyLineSelection,
                                    GwyRectangleSelection,
                                    GwyEllipseSelection)


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


class GwyPointSelection_init(unittest.TestCase):
    """Test constructor of GwyPointSelection class
    """

    def test_arg_is_list_of_points(self):
        """GwyPointSelection.__init__ arg is a list
        """
        points = [(1, 2), (3, 4)]
        point_sel = GwyPointSelection(points)
        self.assertListEqual(point_sel.data, points)

    def test_arg_is_tuple_of_points(self):
        """GwyPointSelection.__init__ arg is a tuple
        """
        points = ((1, 2), (3, 4))
        point_sel = GwyPointSelection(points)
        self.assertListEqual(point_sel.data, [(1, 2), (3, 4)])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyPointSelection.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyPointSelection,
                          points)


class GwyPointSelection_from_gwy(unittest.TestCase):
    """Test from_gwy method of  GwyPointSelection class
    """

    def setUp(self):
        self.gwysel = Mock()
        self.nsel = 3
        self.points = [(1., 1.), (2., 2.), (3., 3.)]

        patcher_nsel = patch.object(GwyPointSelection, '_get_selection_nsel')
        self.get_nsel = patcher_nsel.start()
        self.addCleanup(patcher_nsel.stop)

        patcher_points = patch.object(GwyPointSelection,
                                      '_get_selection_points')
        self.get_points = patcher_points.start()
        self.addCleanup(patcher_points.stop)

    def test_getting_number_of_selections(self):
        """Get number of selections from gwysel
        """
        GwyPointSelection.from_gwy(self.gwysel)
        self.get_nsel.assert_has_calls([call(self.gwysel)])

    def test_getting_points_of_selections(self):
        """Get points of selections from gwysel
        """
        self.get_nsel.return_value = self.nsel
        GwyPointSelection.from_gwy(self.gwysel)
        self.get_points.assert_has_calls([call(self.gwysel, self.nsel)])

    def test_returned_value(self):
        """Return GwyPointSelections initiated by points from gwysel
        """
        self.get_points.return_value = self.points
        point_sel = GwyPointSelection.from_gwy(self.gwysel)
        self.assertListEqual(point_sel.data, self.points)

    def test_return_None_if_there_are_no_points_in_sel(self):
        self.get_points.return_value = None
        point_sel = GwyPointSelection.from_gwy(self.gwysel)
        self.assertIsNone(point_sel)


class GwyPointerSelection_init(unittest.TestCase):
    """Test constructor of GwyPointerSelection class
    """

    def test_arg_is_list_of_points(self):
        """GwyPointerSelection.__init__ arg is a list
        """
        points = [(1, 2), (3, 4)]
        pointer_sel = GwyPointerSelection(points)
        self.assertListEqual(pointer_sel.data, points)

    def test_arg_is_tuple_of_points(self):
        """GwyPointerSelection.__init__ arg is a tuple
        """
        points = ((1, 2), (3, 4))
        pointer_sel = GwyPointSelection(points)
        self.assertListEqual(pointer_sel.data, [(1, 2), (3, 4)])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyPointerSelection.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyPointerSelection,
                          points)


class GwyPointerSelection_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyPointerSelection class
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
        GwyPointerSelection.from_gwy(self.gwysel)
        self.from_gwy_parent.assert_has_calls([call(self.gwysel)])

    def test_returned_value(self):
        """Return GwyPointSelection initiated by points from gwysel
        """
        self.from_gwy_parent.return_value = self.points
        pointer_sel = GwyPointerSelection.from_gwy(self.gwysel)
        self.assertListEqual(pointer_sel.data, self.points)

    def test_return_None_if_there_are_no_points_in_sel(self):
        """Return None if there are no points in the selection
        """
        self.from_gwy_parent.return_value = None
        pointer_sel = GwyPointerSelection.from_gwy(self.gwysel)
        self.assertIsNone(pointer_sel)


class GwyLineSelections_init(unittest.TestCase):
    """Test constructor of GwyLineSelection class
    """

    def test_arg_is_list_of_point_pairs(self):
        """GwyLineSelection.__init__ arg is a list
        """
        point_pairs = [((0, 0), (1, 1)),
                       ((2, 2), (3, 3))]
        line_sel = GwyLineSelection(point_pairs)
        self.assertListEqual(line_sel.data, point_pairs)

    def test_arg_is_tuple_of_points(self):
        """GwyLineSelection.__init__ arg is a tuple
        """
        point_pairs = (((0, 0), (1, 1)),
                       ((2, 2), (3, 3)))
        line_sel = GwyLineSelection(point_pairs)
        self.assertListEqual(line_sel.data,
                             [((0, 0), (1, 1)),
                              ((2, 2), (3, 3))])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyLineSelection.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyLineSelection,
                          points)


class GwyLineSelection_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyLineSelection class
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
        GwyLineSelection.from_gwy(self.gwysel)
        self.from_gwy_parent.assert_has_calls([call(self.gwysel)])

    def test_returned_value(self):
        """Return GwyLineSelection initiated by point pairs from gwysel
        """
        self.from_gwy_parent.return_value = self.points
        line_sel = GwyLineSelection.from_gwy(self.gwysel)
        self.assertListEqual(line_sel.data, self.point_pairs)

    def test_return_None_if_there_are_no_points_in_sel(self):
        """Return None if there are no points in the selection
        """
        self.from_gwy_parent.return_value = None
        line_sel = GwyLineSelection.from_gwy(self.gwysel)
        self.assertIsNone(line_sel)


class GwyRectangleSelection_init(unittest.TestCase):
    """Test constructor of GwyRectangleSelection class
    """

    def test_arg_is_list_of_point_pairs(self):
        """GwyRectangleSelections.__init__ arg is a list
        """
        point_pairs = [((0, 0), (1, 1)),
                       ((2, 2), (3, 3))]
        rectangle_sel = GwyRectangleSelection(point_pairs)
        self.assertListEqual(rectangle_sel.data, point_pairs)

    def test_arg_is_tuple_of_points(self):
        """GwyRectangleSelection.__init__ arg is a tuple
        """
        point_pairs = (((0, 0), (1, 1)),
                       ((2, 2), (3, 3)))
        rectangle_sel = GwyRectangleSelection(point_pairs)
        self.assertListEqual(rectangle_sel.data,
                             [((0, 0), (1, 1)),
                              ((2, 2), (3, 3))])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyRectangleSelection.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyRectangleSelection,
                          points)


class GwyRectangleSelection_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyRectangleSelection class
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
        GwyRectangleSelection.from_gwy(self.gwysel)
        self.from_gwy_parent.assert_has_calls([call(self.gwysel)])

    def test_returned_value(self):
        """Return GwyRectangleSelection initiated by point pairs from gwysel
        """
        self.from_gwy_parent.return_value = self.points
        rectangle_sel = GwyRectangleSelection.from_gwy(self.gwysel)
        self.assertListEqual(rectangle_sel.data, self.point_pairs)

    def test_return_None_if_there_are_no_points_in_sel(self):
        """Return None if there are no points in the selection
        """
        self.from_gwy_parent.return_value = None
        rectangle_sel = GwyRectangleSelection.from_gwy(self.gwysel)
        self.assertIsNone(rectangle_sel)


class GwyEllipseSelection_init(unittest.TestCase):
    """Test constructor of GwyEllipseSelection class
    """

    def test_arg_is_list_of_point_pairs(self):
        """GwyEllipseSelections.__init__ arg is a list
        """
        point_pairs = [((0, 0), (1, 1)),
                       ((2, 2), (3, 3))]
        ellipse_sel = GwyEllipseSelection(point_pairs)
        self.assertListEqual(ellipse_sel.data, point_pairs)

    def test_arg_is_tuple_of_points(self):
        """GwyEllipseSelections.__init__ arg is a tuple
        """
        point_pairs = (((0, 0), (1, 1)),
                       ((2, 2), (3, 3)))
        ellipse_sel = GwyEllipseSelection(point_pairs)
        self.assertListEqual(ellipse_sel.data,
                             [((0, 0), (1, 1)),
                              ((2, 2), (3, 3))])

    def test_arg_is_an_empty_list(self):
        """Raise ValueError if GwyEllipseSelection.__init__ arg is empty
        """
        points = []
        self.assertRaises(ValueError,
                          GwyEllipseSelection,
                          points)


class GwyEllipseSelection_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyEllipseSelection class
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
        GwyEllipseSelection.from_gwy(self.gwysel)
        self.from_gwy_parent.assert_has_calls([call(self.gwysel)])

    def test_returned_value(self):
        """Return GwyEllipseSelections initiated by point pairs from gwysel
        """
        self.from_gwy_parent.return_value = self.points
        ellipse_sel = GwyEllipseSelection.from_gwy(self.gwysel)
        self.assertListEqual(ellipse_sel.data, self.point_pairs)

    def test_return_None_if_there_are_no_points_in_sel(self):
        """Return None if there are no points in the selection
        """
        self.from_gwy_parent.return_value = None
        ellipse_sel = GwyEllipseSelection.from_gwy(self.gwysel)
        self.assertIsNone(ellipse_sel)
