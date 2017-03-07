import unittest
from unittest.mock import patch, call, Mock

import numpy as np

from pygwyfile._libgwyfile import ffi
from pygwyfile.gwyfile import GwyfileErrorCMsg
from pygwyfile.gwygraph import GwyGraphCurve, GwyGraphModel


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

    @patch('pygwyfile.gwygraph.GwyGraphCurve', autospec=True)
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
        patcher_lib = patch('pygwyfile.gwygraph.lib',
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
        patcher_lib = patch('pygwyfile.gwygraph.lib',
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

    def test_raise_ValueError_if_curves_number_and_ncurves_different(self):
        """Raise ValueError if len(curves) is not equal to meta['ncurves']
        """
        self.assertRaises(ValueError,
                          GwyGraphModel,
                          curves=[Mock(GwyGraphCurve)],  # just one curve
                          meta=self.test_meta)           # meta['ncurves'] = 2


class GwyGraphModel_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyGraphModel class
    """

    @patch('pygwyfile.gwygraph.GwyGraphModel', autospec=True)
    @patch('pygwyfile.gwygraph.GwyGraphCurve', autospec=True)
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

        patcher_lib = patch('pygwyfile.gwygraph.lib',
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

        patcher_lib = patch('pygwyfile.gwygraph.lib',
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

        # first arg is GwyDatafield returned by get_gwyitem_object
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


if __name__ == '__main__':
    unittest.main()
