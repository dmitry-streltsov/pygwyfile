import unittest
from unittest.mock import patch, call, Mock

import numpy as np

from gwydb.gwy._libgwyfile import ffi
from gwydb.gwy.gwyfile import GwyfileError, GwyfileErrorCMsg
from gwydb.gwy.gwyfile import Gwyfile
from gwydb.gwy.gwyselection import (GwyPointSelection,
                                    GwyPointerSelection,
                                    GwyLineSelection,
                                    GwyRectangleSelection,
                                    GwyEllipseSelection)
from gwydb.gwy.gwychannel import GwyDataField, GwyChannel


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
    @patch('gwydb.gwy.gwychannel.GwyDataField', autospec=True)
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

        patcher_lib = patch('gwydb.gwy.gwychannel.lib',
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

        patcher_lib = patch('gwydb.gwy.gwychannel.lib',
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


class GwyChannel_get_title(unittest.TestCase):
    """Test _get_title method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_string(self):
        """Get string value of "/0/data/title" item"""
        GwyChannel._get_title(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_string.assert_has_calls(
            [call("/{:d}/data/title".format(self.channel_id))])

    def test_returned_value(self):
        """ Return this string"""
        actual_return = GwyChannel._get_title(self.gwyfile,
                                              self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_string.return_value)


class GwyChannel_get_palette(unittest.TestCase):
    """Test _get_palette method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_string(self):
        """Get string value of "/0/base/palette" item"""
        GwyChannel._get_palette(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_string.assert_has_calls(
            [call("/{:d}/base/palette".format(self.channel_id))])

    def test_returned_value(self):
        """Return this string"""
        actual_return = GwyChannel._get_palette(self.gwyfile,
                                                self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_string.return_value)


class GwyChannel_get_visibility(unittest.TestCase):
    """Test _get_visibility method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_bool(self):
        """Get boolean value of "/0/data/visible" item"""
        GwyChannel._get_visibility(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_bool.assert_has_calls(
            [call("/{:d}/data/visible".format(self.channel_id))])

    def test_returned_value(self):
        """Return this string"""
        actual_return = GwyChannel._get_visibility(self.gwyfile,
                                                   self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_bool.return_value)


class GwyChannel_get_range_type(unittest.TestCase):
    """Tests for _get_range_type method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_int32(self):
        """Get int32 value of "/0/base/range-type" """
        GwyChannel._get_range_type(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_int32.assert_has_calls(
            [call("/{:d}/base/range-type".format(self.channel_id))])

    def test_returned_value(self):
        """ Return this value"""
        actual_return = GwyChannel._get_range_type(self.gwyfile,
                                                   self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_int32.return_value)


class GwyChannel_get_range_min(unittest.TestCase):
    """Tests for _get_range_min method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_double(self):
        """Get double value of "/0/base/min" """
        GwyChannel._get_range_min(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_double.assert_has_calls(
            [call("/{:d}/base/min".format(self.channel_id))])

    def test_returned_value(self):
        """ Return this value"""
        actual_return = GwyChannel._get_range_min(self.gwyfile,
                                                  self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_double.return_value)


class GwyChannel_get_range_max(unittest.TestCase):
    """Tests for _get_range_max method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_double(self):
        """Get double value of "/0/base/max" """
        GwyChannel._get_range_max(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_double.assert_has_calls(
            [call("/{:d}/base/max".format(self.channel_id))])

    def test_returned_value(self):
        """ Return this value"""
        actual_return = GwyChannel._get_range_max(self.gwyfile,
                                                  self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_double.return_value)


class GwyChannel_get_mask_red(unittest.TestCase):
    """Tests for _get_mask_red method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_double(self):
        """Get double value of "/0/mask/red" """
        GwyChannel._get_mask_red(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_double.assert_has_calls(
            [call("/{:d}/mask/red".format(self.channel_id))])

    def test_returned_value(self):
        """ Return this value"""
        actual_return = GwyChannel._get_mask_red(self.gwyfile,
                                                 self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_double.return_value)


class GwyChannel_get_mask_green(unittest.TestCase):
    """Tests for _get_mask_green method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_green(self):
        """Get double value of "/0/mask/green" """
        GwyChannel._get_mask_green(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_double.assert_has_calls(
            [call("/{:d}/mask/green".format(self.channel_id))])

    def test_returned_value(self):
        """ Return this value"""
        actual_return = GwyChannel._get_mask_green(self.gwyfile,
                                                   self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_double.return_value)


class GwyChannel_get_mask_blue(unittest.TestCase):
    """Tests for _get_mask_blue method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_double(self):
        """Get double value of "/0/mask/blue" """
        GwyChannel._get_mask_blue(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_double.assert_has_calls(
            [call("/{:d}/mask/blue".format(self.channel_id))])

    def test_returned_value(self):
        """ Return this value"""
        actual_return = GwyChannel._get_mask_blue(self.gwyfile,
                                                  self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_double.return_value)


class GwyChannel_get_mask_alpha(unittest.TestCase):
    """Tests for _get_mask_alpha method of GwyChannel class"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0

    def test_arg_passing_to_get_gwyitem_double(self):
        """Get double value of "/0/mask/alpha" """
        GwyChannel._get_mask_alpha(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_double.assert_has_calls(
            [call("/{:d}/mask/alpha".format(self.channel_id))])

    def test_returned_value(self):
        """ Return this value"""
        actual_return = GwyChannel._get_mask_alpha(self.gwyfile,
                                                   self.channel_id)
        self.assertEqual(actual_return,
                         self.gwyfile.get_gwyitem_double.return_value)


class GwyChannel_get_data(unittest.TestCase):
    """Test _get_data method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwychannel.GwyDataField',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyDataField = patcher.start()

    def test_raise_exception_if_gwydatafield_does_not_exist(self):
        """Raise GwyFileError is <GwyDataField*>  object does not exist
        """
        self.gwyfile.get_gwyitem_object.return_value = None
        self.assertRaises(GwyfileError,
                          GwyChannel._get_data,
                          self.gwyfile,
                          self.channel_id)

    def test_check_args_passing_to_get_gwyitem_object(self):
        """Check args passing to Gwyfile.get_gwyitem_object method"""
        GwyChannel._get_data(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_object.assert_has_calls(
            [call("/{:d}/data".format(self.channel_id))])

    def test_call_GwyDataField_constructor(self):
        """
        Pass gwydatafield object to GwyDataField constructor
        """

        gwydatafield = self.gwyfile.get_gwyitem_object.return_value
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
        patcher = patch('gwydb.gwy.gwychannel.GwyDataField',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyDataField = patcher.start()

    def test_return_None_if_mask_datafield_does_not_exist(self):
        """Return None if mask <GwyDataField*> does not exist
        """
        self.gwyfile.get_gwyitem_object.return_value = None
        actual_return = GwyChannel._get_mask(self.gwyfile,
                                             self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyitem_object(self):
        """
        Check args passing to Gwyfile.get_gwyitem_object method
        """

        GwyChannel._get_mask(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_object.assert_has_calls(
            [call("/{:d}/mask".format(self.channel_id))])

    def test_call_GwyDataField_constructor(self):
        """
        Pass gwydatafield object to GwyDataField constructor
        """

        gwydatafield = self.gwyfile.get_gwyitem_object.return_value
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
        patcher = patch('gwydb.gwy.gwychannel.GwyDataField',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyDataField = patcher.start()

    def test_return_None_if_show_datafield_does_not_exist(self):
        """Return None if presentation <GwyDataField*> does not exist
        """
        self.gwyfile.get_gwyitem_object.return_value = False
        actual_return = GwyChannel._get_show(self.gwyfile,
                                             self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyobject(self):
        """
        Check args passing to Gwyfile.get_gwyitem_object method
        """

        GwyChannel._get_show(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_object.assert_has_calls(
            [call("/{:d}/show".format(self.channel_id))])

    def test_call_GwyDataField_constructor(self):
        """
        Pass gwydatafield object to GwyDataField constructor
        """

        gwydatafield = self.gwyfile.get_gwyitem_object.return_value
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
        patcher = patch('gwydb.gwy.gwychannel.GwyPointSelection',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyPointSelection = patcher.start()

    def test_return_None_if_point_selections_do_not_exist(self):
        """Return None if point selections do not exist
        """
        self.gwyfile.get_gwyitem_object.return_value = False
        actual_return = GwyChannel._get_point_sel(self.gwyfile,
                                                  self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyitem_object(self):
        """
        Check args passing to Gwyfile.get_gwyitem_object method
        """

        GwyChannel._get_point_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/point".format(self.channel_id))])

    def test_call_GwyPointSelections_constructor(self):
        """
        Pass gwypointselection object to GwyPointSelection.from_gwy method
        """

        gwypointsel = self.gwyfile.get_gwyitem_object.return_value
        GwyChannel._get_point_sel(self.gwyfile, self.channel_id)
        self.mock_GwyPointSelection.from_gwy.assert_has_calls(
            [call(gwypointsel)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyPointSelection constructor
        """

        expected_return = self.mock_GwyPointSelection.from_gwy.return_value
        actual_return = GwyChannel._get_point_sel(self.gwyfile,
                                                  self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_pointer_sel(unittest.TestCase):
    """Test _get_pointer_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwychannel.GwyPointerSelection',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyPointerSelection = patcher.start()

    def test_return_None_if_pointer_selections_do_not_exist(self):
        """Return None if pointer selections do not exist
        """
        self.gwyfile.get_gwyitem_object.return_value = False
        actual_return = GwyChannel._get_pointer_sel(self.gwyfile,
                                                    self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyitem_object(self):
        """
        Check args passing to Gwyfile.get_gwyitem_object method
        """

        GwyChannel._get_pointer_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/pointer".format(self.channel_id))])

    def test_call_GwyPointSelection_constructor(self):
        """
        Pass gwypointselection object to GwyPointerSelection constructor
        """

        gwypointersel = self.gwyfile.get_gwyitem_object.return_value
        GwyChannel._get_pointer_sel(self.gwyfile, self.channel_id)
        self.mock_GwyPointerSelection.from_gwy.assert_has_calls(
            [call(gwypointersel)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyPointerSelection constructor
        """

        expected_return = self.mock_GwyPointerSelection.from_gwy.return_value
        actual_return = GwyChannel._get_pointer_sel(self.gwyfile,
                                                    self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_line_sel(unittest.TestCase):
    """Test _get_line_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwychannel.GwyLineSelection',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyLineSelection = patcher.start()

    def test_return_None_if_line_selections_do_not_exist(self):
        """Return None if line selections do not exist
        """
        self.gwyfile.get_gwyitem_object.return_value = None
        actual_return = GwyChannel._get_line_sel(self.gwyfile,
                                                 self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyitem_object(self):
        """
        Check args passing to Gwyfile.get_gwyitem_object method
        """

        GwyChannel._get_line_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/line".format(self.channel_id))])

    def test_call_GwyLineSelection_constructor(self):
        """
        Pass gwylineselection object to GwyLineSelection constructor
        """

        gwylinesel = self.gwyfile.get_gwyitem_object.return_value
        GwyChannel._get_line_sel(self.gwyfile, self.channel_id)
        self.mock_GwyLineSelection.from_gwy.assert_has_calls(
            [call(gwylinesel)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyLineSelection constructor
        """

        expected_return = self.mock_GwyLineSelection.from_gwy.return_value
        actual_return = GwyChannel._get_line_sel(self.gwyfile,
                                                 self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_rectangle_sel(unittest.TestCase):
    """Test _get_rectangle_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwychannel.GwyRectangleSelection',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyRectangleSelection = patcher.start()

    def test_return_None_if_rectangle_selections_do_not_exist(self):
        """Return None if rectangle selections do not exist
        """
        self.gwyfile.get_gwyitem_object.return_value = None
        actual_return = GwyChannel._get_rectangle_sel(self.gwyfile,
                                                      self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyitem_object(self):
        """
        Check args passing to Gwyfile.get_gwyitem_object method
        """

        GwyChannel._get_rectangle_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/rectangle".format(self.channel_id))])

    def test_call_GwyRectangleSelections_constructor(self):
        """
        Pass gwyrectangleselection object to GwyRectangleSelection constructor
        """

        gwyrectsel = self.gwyfile.get_gwyitem_object.return_value
        GwyChannel._get_rectangle_sel(self.gwyfile, self.channel_id)
        self.mock_GwyRectangleSelection.from_gwy.assert_has_calls(
            [call(gwyrectsel)])

    def test_check_returned_value(self):
        """
        Return object returned by GwyRectangleSelection constructor
        """

        expected_return = (
            self.mock_GwyRectangleSelection.from_gwy.return_value)
        actual_return = GwyChannel._get_rectangle_sel(self.gwyfile,
                                                      self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_get_ellipse_sel(unittest.TestCase):
    """Test _get_ellipse_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('gwydb.gwy.gwychannel.GwyEllipseSelection',
                        autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_GwyEllipseSelection = patcher.start()

    def test_return_None_if_ellipse_selections_do_not_exist(self):
        """Return None if ellipse selections do not exist
        """
        self.gwyfile.get_gwyitem_object.return_value = False
        actual_return = GwyChannel._get_ellipse_sel(self.gwyfile,
                                                    self.channel_id)
        self.assertIsNone(actual_return)

    def test_check_args_passing_to_get_gwyitem_object(self):
        """Check args passing to Gwyfile.get_gwyitem_object method
        """

        GwyChannel._get_ellipse_sel(self.gwyfile, self.channel_id)
        self.gwyfile.get_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/ellipse".format(self.channel_id))])

    def test_call_GwyEllipseSelection_constructor(self):
        """Pass gwyellipseselection object to GwyEllipseSelection constructor
        """

        gwyellipsesel = self.gwyfile.get_gwyitem_object.return_value
        GwyChannel._get_ellipse_sel(self.gwyfile, self.channel_id)
        self.mock_GwyEllipseSelection.from_gwy.assert_has_calls(
             [call(gwyellipsesel)])

    def test_check_returned_value(self):
        """Return object returned by GwyEllipseSelections constructor
        """

        expected_return = self.mock_GwyEllipseSelection.from_gwy.return_value
        actual_return = GwyChannel._get_ellipse_sel(self.gwyfile,
                                                    self.channel_id)
        self.assertIs(expected_return, actual_return)


class GwyChannel_init(unittest.TestCase):
    """Test init method of GwyChannel class
    """

    def test_raise_TypeError_if_data_is_not_GwyDataField(self):
        """Raise TypeError exception if data is not GwyDataField instance
        """
        data = np.zeros(10)
        self.assertRaises(TypeError,
                          GwyChannel,
                          title='Title',
                          data=data)

    def test_raise_TypeError_if_mask_is_not_GwyDataField_or_None(self):
        """Raise TypeError exception if mask is not GwyDataField instance or None
        """
        data = Mock(spec=GwyDataField)
        mask = np.zeros(10)
        self.assertRaises(TypeError,
                          GwyChannel,
                          title='Title',
                          data=data,
                          mask=mask)

    def test_raise_TypeError_if_show_is_not_GwyDataField_or_None(self):
        """Raise TypeError exception if show is not GwyDataField instance or None
        """
        data = Mock(spec=GwyDataField)
        show = np.zeros(10)
        self.assertRaises(TypeError,
                          GwyChannel,
                          title='Title',
                          data=data,
                          show=show)

    def test_raise_TypeError_if_point_sel_is_not_GwyPointSelection(self):
        """Raise TypeError exception if point_sel is not GwyPointSelection
        instance or None
        """
        data = Mock(spec=GwyDataField)
        point_sel = (0., 0.)
        self.assertRaises(TypeError,
                          GwyChannel,
                          title='Title',
                          data=data,
                          point_sel=point_sel)

    def test_raise_TypeError_if_pointer_sel_is_not_GwyPointerSelection(self):
        """Raise TypeError exception if pointer_sel is not GwyPointerSelection
        instance or None
        """
        data = Mock(spec=GwyDataField)
        pointer_sel = (0., 0.)
        self.assertRaises(TypeError,
                          GwyChannel,
                          title='Title',
                          data=data,
                          pointer_sel=pointer_sel)

    def test_raise_TypeError_if_line_sel_is_not_GwyLineSelection(self):
        """Raise TypeError exception if line_sel is not GwyLineSelection
        instance or None
        """
        data = Mock(spec=GwyDataField)
        line_sel = ((0., 0.), (1., 1.))
        self.assertRaises(TypeError,
                          GwyChannel,
                          title='Title',
                          data=data,
                          line_sel=line_sel)

    def test_raise_TypeError_if_rectangle_sel_is_of_wrong_type(self):
        """Raise TypeError exception if rectangle_sel is not GwyRectangleSelection
        instance or None
        """
        data = Mock(spec=GwyDataField)
        rectangle_sel = ((0., 0.), (1., 1.))
        self.assertRaises(TypeError,
                          GwyChannel,
                          title='Title',
                          data=data,
                          rectangle_sel=rectangle_sel)

    def test_raise_TypeError_if_ellipse_sel_is_not_GwyEllipseSelection(self):
        """Raise TypeError exception if ellipse_sel is not GwyEllipseSelection
        instance or None
        """
        data = Mock(spec=GwyDataField)
        ellipse_sel = ((0., 0.), (1., 1.))
        self.assertRaises(TypeError,
                          GwyChannel,
                          title='Title',
                          data=data,
                          ellipse_sel=ellipse_sel)

    def test_title_data_attributes(self):
        """Check title and data attributes of GwyChannel
        """
        data = Mock(spec=GwyDataField)
        title = 'Title'
        channel = GwyChannel(title=title, data=data)
        self.assertEqual(channel.title, title)
        self.assertEqual(channel.data, data)

    def test_mask_show_attribute(self):
        """Check mask and show attributes of GwyChannel
        """
        data = Mock(spec=GwyDataField)
        title = 'Title'
        mask = Mock(spec=GwyDataField)
        show = Mock(spec=GwyDataField)
        channel = GwyChannel(title=title, data=data,
                             mask=mask, show=show)
        self.assertEqual(channel.mask, mask)
        self.assertEqual(channel.show, show)

    def test_selections_attributes(self):
        """Check *_selections attributes
        """
        data = Mock(spec=GwyDataField)
        title = 'Title'
        point_sel = Mock(spec=GwyPointSelection)
        pointer_sel = Mock(spec=GwyPointerSelection)
        line_sel = Mock(spec=GwyLineSelection)
        rectangle_sel = Mock(spec=GwyRectangleSelection)
        ellipse_sel = Mock(spec=GwyEllipseSelection)

        channel = GwyChannel(title=title, data=data,
                             point_sel=point_sel,
                             pointer_sel=pointer_sel,
                             line_sel=line_sel,
                             rectangle_sel=rectangle_sel,
                             ellipse_sel=ellipse_sel)
        self.assertEqual(channel.point_selections,
                         point_sel)
        self.assertEqual(channel.pointer_selections,
                         pointer_sel)
        self.assertEqual(channel.line_selections,
                         line_sel)
        self.assertEqual(channel.rectangle_selections,
                         rectangle_sel)
        self.assertEqual(channel.ellipse_selections,
                         ellipse_sel)


class GwyChannel_from_gwy(unittest.TestCase):
    """Test from_gwy method of GwyChannel class """

    def test_raise_TypeError_if_gwyfile_is_of_wrong_type(self):
        """Raise TypeError exception if gwyfile is not Gwyfile instance """
        self.assertRaises(TypeError, GwyChannel.from_gwy, 'test_string',
                          0)

    @patch('gwydb.gwy.gwychannel.GwyChannel', autospec=True)
    @patch.object(GwyChannel, '_get_title')
    @patch.object(GwyChannel, '_get_data')
    @patch.object(GwyChannel, '_get_mask')
    @patch.object(GwyChannel, '_get_show')
    @patch.object(GwyChannel, '_get_point_sel')
    @patch.object(GwyChannel, '_get_pointer_sel')
    @patch.object(GwyChannel, '_get_line_sel')
    @patch.object(GwyChannel, '_get_rectangle_sel')
    @patch.object(GwyChannel, '_get_ellipse_sel')
    @patch.object(GwyChannel, '_get_visibility')
    @patch.object(GwyChannel, '_get_palette')
    @patch.object(GwyChannel, '_get_range_type')
    @patch.object(GwyChannel, '_get_range_min')
    @patch.object(GwyChannel, '_get_range_max')
    @patch.object(GwyChannel, '_get_mask_red')
    @patch.object(GwyChannel, '_get_mask_green')
    @patch.object(GwyChannel, '_get_mask_blue')
    @patch.object(GwyChannel, '_get_mask_alpha')
    def test_args_of_other_calls(self,
                                 mock_get_mask_alpha,
                                 mock_get_mask_blue,
                                 mock_get_mask_green,
                                 mock_get_mask_red,
                                 mock_get_range_max,
                                 mock_get_range_min,
                                 mock_get_range_type,
                                 mock_get_palette,
                                 mock_get_visibility,
                                 mock_get_ellipse_sel,
                                 mock_get_rectangle_sel,
                                 mock_get_line_sel,
                                 mock_get_pointer_sel,
                                 mock_get_point_sel,
                                 mock_get_show,
                                 mock_get_mask,
                                 mock_get_data,
                                 mock_get_title,
                                 mock_GwyChannel):
        gwyfile = Mock(spec=Gwyfile)
        channel_id = 0

        title = 'Title'
        mock_get_title.return_value = title

        data = Mock(spec=GwyDataField)
        mock_get_data.return_value = data

        visible = True
        visiblep = ffi.new("bool*", visible)
        mock_get_visibility.return_value = visiblep[0]

        palette = 'Gold'
        mock_get_palette.return_value = palette

        range_type = 1
        mock_get_range_type.return_value = range_type

        range_min = 0.
        mock_get_range_min.return_value = range_min

        range_max = 1e-8
        mock_get_range_max.return_value = range_max

        mask = Mock(spec=GwyDataField)
        mock_get_mask.return_value = mask

        mask_red = 1.0
        mock_get_mask_red.return_value = mask_red

        mask_green = 0.
        mock_get_mask_green.return_value = mask_green

        mask_blue = 0.
        mock_get_mask_blue.return_value = mask_blue

        mask_alpha = 0.5
        mock_get_mask_alpha.return_value = mask_alpha

        show = Mock(spec=GwyDataField)
        mock_get_show.return_value = show

        point_sel = Mock(spec=GwyPointSelection)
        mock_get_point_sel.return_value = point_sel

        pointer_sel = Mock(spec=GwyPointerSelection)
        mock_get_pointer_sel.return_value = pointer_sel

        line_sel = Mock(spec=GwyLineSelection)
        mock_get_line_sel.return_value = line_sel

        rectangle_sel = Mock(spec=GwyRectangleSelection)
        mock_get_rectangle_sel.return_value = rectangle_sel

        ellipse_sel = Mock(spec=GwyEllipseSelection)
        mock_get_ellipse_sel.return_value = ellipse_sel

        channel = GwyChannel.from_gwy(gwyfile, channel_id)

        mock_get_title.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_data.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_mask.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_visibility.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_palette.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_range_type.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_range_min.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_range_max.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_point_sel.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_pointer_sel.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_line_sel.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_rectangle_sel.assert_has_calls(
            [call(gwyfile, channel_id)])

        mock_get_ellipse_sel.assert_has_calls(
            [call(gwyfile, channel_id)])

        self.assertEqual(channel, mock_GwyChannel.return_value)

        mock_GwyChannel.assert_has_calls(
            [call(title=title,
                  data=data,
                  visible=visible,
                  palette=palette,
                  range_type=range_type,
                  range_min=range_min,
                  range_max=range_max,
                  mask=mask,
                  mask_red=mask_red,
                  mask_green=mask_green,
                  mask_blue=mask_blue,
                  mask_alpha=mask_alpha,
                  show=show,
                  point_sel=point_sel,
                  pointer_sel=pointer_sel,
                  line_sel=line_sel,
                  rectangle_sel=rectangle_sel,
                  ellipse_sel=ellipse_sel)])
