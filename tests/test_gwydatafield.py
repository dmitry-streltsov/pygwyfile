import unittest
from unittest.mock import patch, call, Mock

import numpy as np

from pygwyfile._libgwyfile import ffi
from pygwyfile.gwyfile import GwyfileErrorCMsg
from pygwyfile.gwydatafield import GwyDataField


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
    @patch('pygwyfile.gwydatafield.GwyDataField', autospec=True)
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

        patcher_lib = patch('pygwyfile.gwydatafield.lib',
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

        patcher_lib = patch('pygwyfile.gwydatafield.lib',
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


if __name__ == '__main__':
    unittest.main()
