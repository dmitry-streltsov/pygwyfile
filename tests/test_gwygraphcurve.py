import unittest
from unittest.mock import patch, call, Mock

import numpy as np

from pygwyfile._libgwyfile import ffi
from pygwyfile.gwyfile import GwyfileErrorCMsg
from pygwyfile.gwygraph import GwyGraphCurve


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

    @patch('pygwyfile.gwygraphcurve.GwyGraphCurve', autospec=True)
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
        patcher_lib = patch('pygwyfile.gwygraphcurve.lib',
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
        patcher_lib = patch('pygwyfile.gwygraphcurve.lib',
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


class GwyGraphCurve_to_gwy(unittest.TestCase):
    """ Tests for to_gwy method of GwyGraphCurve class"""
    def setUp(self):
        self.ndata = 10
        self.data = np.random.rand(2, self.ndata)
        self.curve = GwyGraphCurve(data=self.data)
        self.description = "Curve"
        self.curve.meta['description'] = self.description
        patcher_lib = patch('pygwyfile.gwygraphcurve.lib',
                            autospec=True)
        self.addCleanup(patcher_lib.stop)
        self.mock_lib = patcher_lib.start()
        self.gwycurve = Mock()

    def test_arguments_of_libgwyfile_func(self):
        """ Test arguments of gwyfile_object_new_graphcurvemodel call"""
        self.mock_lib.gwyfile_object_new_graphcurvemodel.side_effect = (
            self._side_effect)
        gwycurve = self.curve.to_gwy()
        self.assertEqual(gwycurve, self.gwycurve)

    def _side_effect(self, *args):
        self.assertEqual(int(args[0]), self.ndata)
        self.assertEqual(ffi.string(args[1]), b"xdata")
        self.assertEqual(args[2], ffi.cast("double*",
                                           self.curve.data[0].ctypes.data))
        self.assertEqual(ffi.string(args[3]), b"ydata")
        self.assertEqual(args[4], ffi.cast("double*",
                                           self.curve.data[1].ctypes.data))
        self.assertEqual(ffi.string(args[5]), b"description")
        self.assertEqual(ffi.string(args[6]), self.description.encode('utf-8'))
        self.assertEqual(ffi.string(args[7]), b"type")
        self.assertEqual(int(args[8]), self.curve.meta['type'])
        self.assertEqual(ffi.string(args[9]), b"point_type")
        self.assertEqual(int(args[10]), self.curve.meta['point_type'])
        self.assertEqual(ffi.string(args[11]), b"line_style")
        self.assertEqual(int(args[12]), self.curve.meta['line_style'])
        self.assertEqual(ffi.string(args[13]), b"point_size")
        self.assertEqual(int(args[14]), self.curve.meta['point_size'])
        self.assertEqual(ffi.string(args[15]), b"line_size")
        self.assertEqual(int(args[16]), self.curve.meta['line_size'])
        self.assertEqual(ffi.string(args[17]), b"color.red")
        self.assertAlmostEqual(float(args[18]), self.curve.meta['color.red'])
        self.assertEqual(ffi.string(args[19]), b"color.green")
        self.assertAlmostEqual(float(args[20]), self.curve.meta['color.green'])
        self.assertEqual(ffi.string(args[21]), b"color.blue")
        self.assertAlmostEqual(float(args[22]), self.curve.meta['color.blue'])
        self.assertEqual(args[-1], ffi.NULL)
        return self.gwycurve


if __name__ == '__main__':
    unittest.main()
