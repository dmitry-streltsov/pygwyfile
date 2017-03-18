import unittest
from unittest.mock import patch, call, Mock

import numpy as np

from pygwyfile._libgwyfile import ffi
from pygwyfile.gwyfile import GwyfileError
from pygwyfile.gwyfile import Gwyfile
from pygwyfile.gwyselection import (GwyPointSelection,
                                    GwyPointerSelection,
                                    GwyLineSelection,
                                    GwyRectangleSelection,
                                    GwyEllipseSelection)
from pygwyfile.gwychannel import GwyDataField, GwyChannel


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


class GwyChannel_add_title_to_gwy(unittest.TestCase):
    """ Test _add_title_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_title_to_gwy = GwyChannel._add_title_to_gwy
        self.gwychannel.title = 'Title'
        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_raise_TypeError_if_title_is_None(self):
        """ Raise TypeError exception if title attribute is None"""
        self.gwychannel.title = None
        self.assertRaises(TypeError,
                          self.gwychannel._add_title_to_gwy,
                          self.gwychannel,
                          self.gwycontainer,
                          self.channel_id)

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_string')
    def test_create_new_gwyitem(self,
                                mock_new_gwyitem_string,
                                mock_add_gwyitem_to_gwycontainer):
        """Create new string gwyitem with title value"""
        self.gwychannel._add_title_to_gwy(self.gwychannel,
                                          self.gwycontainer,
                                          self.channel_id)
        mock_new_gwyitem_string.assert_has_calls(
            [call("/{:d}/data/title".format(self.channel_id),
                  self.gwychannel.title)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_string')
    def test_add_gwyitem_to_container(self,
                                      mock_new_gwyitem_string,
                                      mock_add_gwyitem_to_gwycontainer):
        """Add created gwyitem to gywcontainer"""
        gwyitem = mock_new_gwyitem_string.return_value
        self.gwychannel._add_title_to_gwy(self.gwychannel,
                                          self.gwycontainer,
                                          self.channel_id)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls(
            [call(gwyitem, self.gwycontainer)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_string')
    def test_return_value(self,
                          mock_new_gwyitem_string,
                          mock_add_gwyitem_to_gwycontainer):
        """Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_title_to_gwy(self.gwychannel,
                                                     self.gwycontainer,
                                                     self.channel_id)
        self.assertIs(is_added, mock_add_gwyitem_to_gwycontainer.return_value)


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


class GwyChannel_add_palette_to_gwy(unittest.TestCase):
    """Test _add_palette_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_palette_to_gwy = GwyChannel._add_palette_to_gwy
        self.gwycontainer = Mock()
        self.channel_id = 0
        self.gwychannel.palette = 'Gold'

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_palette_does_not_set(self,
                                                  mock_add_gwyitem):
        """ If palette attribute is None do not add anything to gwycontainer
            add retrun False
        """
        self.gwychannel.palette = None
        is_added = self.gwychannel._add_palette_to_gwy(self.gwychannel,
                                                       self.gwycontainer,
                                                       self.channel_id)
        self.assertIs(is_added, False)
        mock_add_gwyitem.assert_has_calls([])

    @patch.object(Gwyfile, 'new_gwyitem_string')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_create_new_gwyitem_with_palette_string(self,
                                                    mock_add_gwyitem,
                                                    mock_new_gwyitem_string):
        """Create new gwyitem with palette string """
        self.gwychannel._add_palette_to_gwy(self.gwychannel,
                                            self.gwycontainer,
                                            self.channel_id)
        mock_new_gwyitem_string.assert_has_calls(
            [call("/{:d}/base/palette".format(self.channel_id),
                  self.gwychannel.palette)])

    @patch.object(Gwyfile, 'new_gwyitem_string')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_add_gwyitem_to_container(self,
                                      mock_add_gwyitem,
                                      mock_new_gwyitem_string):
        """ Add created gwyitem to gwycontainer"""
        self.gwychannel._add_palette_to_gwy(self.gwychannel,
                                            self.gwycontainer,
                                            self.channel_id)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_string.return_value,
                  self.gwycontainer)])

    @patch.object(Gwyfile, 'new_gwyitem_string')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_returned_value(self,
                            mock_add_gwyitem,
                            mock_new_gwyitem_string):
        """ Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_palette_to_gwy(self.gwychannel,
                                                       self.gwycontainer,
                                                       self.channel_id)
        self.assertEqual(is_added,
                         mock_add_gwyitem.return_value)


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


class GwyChannel_add_visibility_to_gwy(unittest.TestCase):
    """Test _add_visibility_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_visibility_to_gwy = (
            GwyChannel._add_visibility_to_gwy)
        self.gwycontainer = Mock()
        self.channel_id = 0
        self.gwychannel.visible = True

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_visible_flag_does_not_set(self,
                                                       mock_add_gwyitem):
        """ If visible attribute is None do not add anything to gwycontainer
            add retrun False
        """
        self.gwychannel.visible = None
        is_added = self.gwychannel._add_visibility_to_gwy(self.gwychannel,
                                                          self.gwycontainer,
                                                          self.channel_id)
        self.assertIs(is_added, False)
        mock_add_gwyitem.assert_has_calls([])

    @patch.object(Gwyfile, 'new_gwyitem_bool')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_create_new_gwyitem_with_palette_string(self,
                                                    mock_add_gwyitem,
                                                    mock_new_gwyitem_bool):
        """Create new gwyitem with visible boolean value """
        self.gwychannel._add_visibility_to_gwy(self.gwychannel,
                                               self.gwycontainer,
                                               self.channel_id)
        mock_new_gwyitem_bool.assert_has_calls(
            [call("/{:d}/data/visible".format(self.channel_id),
                  self.gwychannel.visible)])

    @patch.object(Gwyfile, 'new_gwyitem_bool')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_add_gwyitem_to_container(self,
                                      mock_add_gwyitem,
                                      mock_new_gwyitem_bool):
        """ Add created gwyitem to gwycontainer"""
        self.gwychannel._add_visibility_to_gwy(self.gwychannel,
                                               self.gwycontainer,
                                               self.channel_id)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_bool.return_value,
                  self.gwycontainer)])

    @patch.object(Gwyfile, 'new_gwyitem_bool')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_returned_value(self,
                            mock_add_gwyitem,
                            mock_new_gwyitem_bool):
        """ Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_visibility_to_gwy(self.gwychannel,
                                                          self.gwycontainer,
                                                          self.channel_id)
        self.assertEqual(is_added,
                         mock_add_gwyitem.return_value)


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


class GwyChannel_add_range_type_to_gwy(unittest.TestCase):
    """Test _add_range_type_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_range_type_to_gwy = (
            GwyChannel._add_range_type_to_gwy)
        self.gwycontainer = Mock()
        self.channel_id = 0
        self.gwychannel.range_type = 1

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_range_type_is_unset(self,
                                                 mock_add_gwyitem):
        """ If range_type attribute is None do not add anything to gwycontainer
            add retrun False
        """
        self.gwychannel.range_type = None
        is_added = self.gwychannel._add_range_type_to_gwy(self.gwychannel,
                                                          self.gwycontainer,
                                                          self.channel_id)
        self.assertIs(is_added, False)
        mock_add_gwyitem.assert_has_calls([])

    @patch.object(Gwyfile, 'new_gwyitem_int32')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_create_new_gwyitem_with_palette_string(self,
                                                    mock_add_gwyitem,
                                                    mock_new_gwyitem_int32):
        """Create new gwyitem with range_type value"""
        self.gwychannel._add_range_type_to_gwy(self.gwychannel,
                                               self.gwycontainer,
                                               self.channel_id)
        mock_new_gwyitem_int32.assert_has_calls(
            [call("/{:d}/base/range-type".format(self.channel_id),
                  self.gwychannel.range_type)])

    @patch.object(Gwyfile, 'new_gwyitem_int32')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_add_gwyitem_to_container(self,
                                      mock_add_gwyitem,
                                      mock_new_gwyitem_int32):
        """ Add created gwyitem to gwycontainer"""
        self.gwychannel._add_range_type_to_gwy(self.gwychannel,
                                               self.gwycontainer,
                                               self.channel_id)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_int32.return_value,
                  self.gwycontainer)])

    @patch.object(Gwyfile, 'new_gwyitem_int32')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_returned_value(self,
                            mock_add_gwyitem,
                            mock_new_gwyitem_int32):
        """ Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_range_type_to_gwy(self.gwychannel,
                                                          self.gwycontainer,
                                                          self.channel_id)
        self.assertEqual(is_added,
                         mock_add_gwyitem.return_value)


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


class GwyChannel_add_range_min_to_gwy(unittest.TestCase):
    """Test _add_range_min_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_range_min_to_gwy = (
            GwyChannel._add_range_min_to_gwy)
        self.gwycontainer = Mock()
        self.channel_id = 0
        self.gwychannel.range_min = 0.

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_range_min_is_unset(self,
                                                mock_add_gwyitem):
        """ If range_min attribute is None do not add anything to gwycontainer
            add retrun False
        """
        self.gwychannel.range_min = None
        is_added = self.gwychannel._add_range_min_to_gwy(self.gwychannel,
                                                         self.gwycontainer,
                                                         self.channel_id)
        self.assertIs(is_added, False)
        mock_add_gwyitem.assert_has_calls([])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_create_new_gwyitem_with_range_min_value(self,
                                                     mock_add_gwyitem,
                                                     mock_new_gwyitem_double):
        """Create new gwyitem with range_min value"""
        self.gwychannel._add_range_min_to_gwy(self.gwychannel,
                                              self.gwycontainer,
                                              self.channel_id)
        mock_new_gwyitem_double.assert_has_calls(
            [call("/{:d}/base/min".format(self.channel_id),
                  self.gwychannel.range_min)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_add_gwyitem_to_container(self,
                                      mock_add_gwyitem,
                                      mock_new_gwyitem_double):
        """ Add created gwyitem to gwycontainer"""
        self.gwychannel._add_range_min_to_gwy(self.gwychannel,
                                              self.gwycontainer,
                                              self.channel_id)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_double.return_value,
                  self.gwycontainer)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_returned_value(self,
                            mock_add_gwyitem,
                            mock_new_gwyitem_double):
        """ Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_range_min_to_gwy(self.gwychannel,
                                                         self.gwycontainer,
                                                         self.channel_id)
        self.assertEqual(is_added,
                         mock_add_gwyitem.return_value)


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


class GwyChannel_add_range_max_to_gwy(unittest.TestCase):
    """Test _add_range_max_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_range_max_to_gwy = (
            GwyChannel._add_range_max_to_gwy)
        self.gwycontainer = Mock()
        self.channel_id = 0
        self.gwychannel.range_max = 1.

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_range_max_is_unset(self,
                                                mock_add_gwyitem):
        """ If range_max attribute is None do not add anything to gwycontainer
            add retrun False
        """
        self.gwychannel.range_max = None
        is_added = self.gwychannel._add_range_max_to_gwy(self.gwychannel,
                                                         self.gwycontainer,
                                                         self.channel_id)
        self.assertIs(is_added, False)
        mock_add_gwyitem.assert_has_calls([])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_create_new_gwyitem_with_range_max_value(self,
                                                     mock_add_gwyitem,
                                                     mock_new_gwyitem_double):
        """Create new gwyitem with range_max value"""
        self.gwychannel._add_range_max_to_gwy(self.gwychannel,
                                              self.gwycontainer,
                                              self.channel_id)
        mock_new_gwyitem_double.assert_has_calls(
            [call("/{:d}/base/max".format(self.channel_id),
                  self.gwychannel.range_max)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_add_gwyitem_to_container(self,
                                      mock_add_gwyitem,
                                      mock_new_gwyitem_double):
        """ Add created gwyitem to gwycontainer"""
        self.gwychannel._add_range_max_to_gwy(self.gwychannel,
                                              self.gwycontainer,
                                              self.channel_id)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_double.return_value,
                  self.gwycontainer)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_returned_value(self,
                            mock_add_gwyitem,
                            mock_new_gwyitem_double):
        """ Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_range_max_to_gwy(self.gwychannel,
                                                         self.gwycontainer,
                                                         self.channel_id)
        self.assertEqual(is_added,
                         mock_add_gwyitem.return_value)


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


class GwyChannel_add_mask_red_to_gwy(unittest.TestCase):
    """Test _add_mask_red_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_mask_red_to_gwy = GwyChannel._add_mask_red_to_gwy
        self.gwycontainer = Mock()
        self.channel_id = 0
        self.gwychannel.mask_red = 1.

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_mask_red_is_unset(self, mock_add_gwyitem):
        """ If mask_red attribute is None do not add anything to gwycontainer
            add return False
        """
        self.gwychannel.mask_red = None
        is_added = self.gwychannel._add_mask_red_to_gwy(self.gwychannel,
                                                        self.gwycontainer,
                                                        self.channel_id)
        self.assertIs(is_added, False)
        mock_add_gwyitem.assert_has_calls([])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_create_new_gwyitem_with_mask_red_value(self,
                                                    mock_add_gwyitem,
                                                    mock_new_gwyitem_double):
        """Create new gwyitem with mask_red value"""
        self.gwychannel._add_mask_red_to_gwy(self.gwychannel,
                                             self.gwycontainer,
                                             self.channel_id)
        mock_new_gwyitem_double.assert_has_calls(
            [call("/{:d}/mask/red".format(self.channel_id),
                  self.gwychannel.mask_red)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_add_gwyitem_to_container(self,
                                      mock_add_gwyitem,
                                      mock_new_gwyitem_double):
        """ Add created gwyitem to gwycontainer"""
        self.gwychannel._add_mask_red_to_gwy(self.gwychannel,
                                             self.gwycontainer,
                                             self.channel_id)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_double.return_value,
                  self.gwycontainer)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_returned_value(self,
                            mock_add_gwyitem,
                            mock_new_gwyitem_double):
        """ Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_mask_red_to_gwy(self.gwychannel,
                                                        self.gwycontainer,
                                                        self.channel_id)
        self.assertEqual(is_added,
                         mock_add_gwyitem.return_value)


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


class GwyChannel_add_mask_green_to_gwy(unittest.TestCase):
    """Test _add_mask_green_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_mask_green_to_gwy = (
            GwyChannel._add_mask_green_to_gwy)
        self.gwycontainer = Mock()
        self.channel_id = 0
        self.gwychannel.mask_green = 0.

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_mask_green_is_unset(self, mock_add_gwyitem):
        """ If mask_green attribute is None do not add anything to gwycontainer
            add return False
        """
        self.gwychannel.mask_green = None
        is_added = self.gwychannel._add_mask_green_to_gwy(self.gwychannel,
                                                          self.gwycontainer,
                                                          self.channel_id)
        self.assertIs(is_added, False)
        mock_add_gwyitem.assert_has_calls([])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_create_new_gwyitem_with_mask_green_value(self,
                                                      mock_add_gwyitem,
                                                      mock_new_gwyitem_double):
        """Create new gwyitem with mask_green value"""
        self.gwychannel._add_mask_green_to_gwy(self.gwychannel,
                                               self.gwycontainer,
                                               self.channel_id)
        mock_new_gwyitem_double.assert_has_calls(
            [call("/{:d}/mask/green".format(self.channel_id),
                  self.gwychannel.mask_green)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_add_gwyitem_to_container(self,
                                      mock_add_gwyitem,
                                      mock_new_gwyitem_double):
        """ Add created gwyitem to gwycontainer"""
        self.gwychannel._add_mask_green_to_gwy(self.gwychannel,
                                               self.gwycontainer,
                                               self.channel_id)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_double.return_value,
                  self.gwycontainer)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_returned_value(self,
                            mock_add_gwyitem,
                            mock_new_gwyitem_double):
        """ Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_mask_green_to_gwy(self.gwychannel,
                                                          self.gwycontainer,
                                                          self.channel_id)
        self.assertEqual(is_added,
                         mock_add_gwyitem.return_value)


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


class GwyChannel_add_mask_blue_to_gwy(unittest.TestCase):
    """Test _add_mask_blue_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_mask_blue_to_gwy = (
            GwyChannel._add_mask_blue_to_gwy)
        self.gwycontainer = Mock()
        self.channel_id = 0
        self.gwychannel.mask_blue = 0.

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_mask_blue_is_unset(self, mock_add_gwyitem):
        """ If mask_blue attribute is None do not add anything to gwycontainer
            add return False
        """
        self.gwychannel.mask_blue = None
        is_added = self.gwychannel._add_mask_blue_to_gwy(self.gwychannel,
                                                         self.gwycontainer,
                                                         self.channel_id)
        self.assertIs(is_added, False)
        mock_add_gwyitem.assert_has_calls([])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_create_new_gwyitem_with_mask_blue_value(self,
                                                     mock_add_gwyitem,
                                                     mock_new_gwyitem_double):
        """Create new gwyitem with mask_blue value"""
        self.gwychannel._add_mask_blue_to_gwy(self.gwychannel,
                                              self.gwycontainer,
                                              self.channel_id)
        mock_new_gwyitem_double.assert_has_calls(
            [call("/{:d}/mask/blue".format(self.channel_id),
                  self.gwychannel.mask_blue)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_add_gwyitem_to_container(self,
                                      mock_add_gwyitem,
                                      mock_new_gwyitem_double):
        """ Add created gwyitem to gwycontainer"""
        self.gwychannel._add_mask_blue_to_gwy(self.gwychannel,
                                              self.gwycontainer,
                                              self.channel_id)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_double.return_value,
                  self.gwycontainer)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_returned_value(self,
                            mock_add_gwyitem,
                            mock_new_gwyitem_double):
        """ Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_mask_blue_to_gwy(self.gwychannel,
                                                         self.gwycontainer,
                                                         self.channel_id)
        self.assertEqual(is_added,
                         mock_add_gwyitem.return_value)


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


class GwyChannel_add_mask_alpha_to_gwy(unittest.TestCase):
    """Test _add_mask_alpha_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_mask_alpha_to_gwy = (
            GwyChannel._add_mask_alpha_to_gwy)
        self.gwycontainer = Mock()
        self.channel_id = 0
        self.gwychannel.mask_alpha = 1.

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_mask_alpha_is_unset(self, mock_add_gwyitem):
        """ If mask_alpha attribute is None do not add anything to gwycontainer
            add return False
        """
        self.gwychannel.mask_alpha = None
        is_added = self.gwychannel._add_mask_alpha_to_gwy(self.gwychannel,
                                                          self.gwycontainer,
                                                          self.channel_id)
        self.assertIs(is_added, False)
        mock_add_gwyitem.assert_has_calls([])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_create_new_gwyitem_with_mask_alpha_value(self,
                                                      mock_add_gwyitem,
                                                      mock_new_gwyitem_double):
        """Create new gwyitem with mask_alpha value"""
        self.gwychannel._add_mask_alpha_to_gwy(self.gwychannel,
                                               self.gwycontainer,
                                               self.channel_id)
        mock_new_gwyitem_double.assert_has_calls(
            [call("/{:d}/mask/alpha".format(self.channel_id),
                  self.gwychannel.mask_alpha)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_add_gwyitem_to_container(self,
                                      mock_add_gwyitem,
                                      mock_new_gwyitem_double):
        """ Add created gwyitem to gwycontainer"""
        self.gwychannel._add_mask_alpha_to_gwy(self.gwychannel,
                                               self.gwycontainer,
                                               self.channel_id)
        mock_add_gwyitem.assert_has_calls(
            [call(mock_new_gwyitem_double.return_value,
                  self.gwycontainer)])

    @patch.object(Gwyfile, 'new_gwyitem_double')
    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_returned_value(self,
                            mock_add_gwyitem,
                            mock_new_gwyitem_double):
        """ Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_mask_alpha_to_gwy(self.gwychannel,
                                                          self.gwycontainer,
                                                          self.channel_id)
        self.assertEqual(is_added,
                         mock_add_gwyitem.return_value)


class GwyChannel_get_data(unittest.TestCase):
    """Test _get_data method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('pygwyfile.gwychannel.GwyDataField',
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


class GwyChannel_add_data_to_gwy(unittest.TestCase):
    """ Test _add_data_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_data_to_gwy = GwyChannel._add_data_to_gwy
        self.gwychannel.data = Mock(spec=GwyDataField)
        self.gwydf = Mock()
        self.gwychannel.data.to_gwy.return_value = self.gwydf
        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_raise_TypeError_if_data_is_not_GwyDataField(self):
        """ Raise TypeError exception if data is not GwyDataField"""
        self.gwychannel.data = 'Wrong data'
        self.assertRaises(TypeError,
                          self.gwychannel._add_data_to_gwy,
                          self.gwychannel,
                          self.gwycontainer,
                          self.channel_id)

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_create_new_gwyitem(self,
                                mock_new_gwyitem_object,
                                mock_add_gwyitem_to_gwycontainer):
        """Create new object gwyitem with data"""
        self.gwychannel._add_data_to_gwy(self.gwychannel,
                                         self.gwycontainer,
                                         self.channel_id)
        mock_new_gwyitem_object.assert_has_calls(
            [call("/{:d}/data".format(self.channel_id),
                  self.gwydf)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_add_gwyitem_to_container(self,
                                      mock_new_gwyitem_object,
                                      mock_add_gwyitem_to_gwycontainer):
        """Add created gwyitem to gywcontainer"""
        gwyitem = mock_new_gwyitem_object.return_value
        self.gwychannel._add_data_to_gwy(self.gwychannel,
                                         self.gwycontainer,
                                         self.channel_id)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls(
            [call(gwyitem, self.gwycontainer)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_return_value(self,
                          mock_new_gwyitem_object,
                          mock_add_gwyitem_to_gwycontainer):
        """Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_data_to_gwy(self.gwychannel,
                                                    self.gwycontainer,
                                                    self.channel_id)
        self.assertIs(is_added, mock_add_gwyitem_to_gwycontainer.return_value)


class GwyChannel_get_mask(unittest.TestCase):
    """Test _get_mask method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('pygwyfile.gwychannel.GwyDataField',
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


class GwyChannel_add_mask_to_gwy(unittest.TestCase):
    """ Test _add_mask_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_mask_to_gwy = GwyChannel._add_mask_to_gwy
        self.gwychannel.mask = Mock(spec=GwyDataField)
        self.gwydf = Mock()
        self.gwychannel.mask.to_gwy.return_value = self.gwydf
        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_raise_TypeError_if_data_is_not_GwyDataField_or_None(self):
        """ Raise TypeError exception if mask is not GwyDataField or None"""
        self.gwychannel.mask = 'Wrong mask'
        self.assertRaises(TypeError,
                          self.gwychannel._add_mask_to_gwy,
                          self.gwychannel,
                          self.gwycontainer,
                          self.channel_id)

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_mask_is_None(self,
                                          mock_add_gwyitem_to_gwycontainer):
        """Return False if mask is None and add nothing to gwycontainer"""
        self.gwychannel.mask = None
        actual_return = self.gwychannel._add_mask_to_gwy(self.gwychannel,
                                                         self.gwycontainer,
                                                         self.channel_id)
        self.assertIs(actual_return, False)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls([])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_create_new_gwyitem(self,
                                mock_new_gwyitem_object,
                                mock_add_gwyitem_to_gwycontainer):
        """Create new object gwyitem with mask data"""
        self.gwychannel._add_mask_to_gwy(self.gwychannel,
                                         self.gwycontainer,
                                         self.channel_id)
        mock_new_gwyitem_object.assert_has_calls(
            [call("/{:d}/mask".format(self.channel_id),
                  self.gwydf)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_add_gwyitem_to_container(self,
                                      mock_new_gwyitem_object,
                                      mock_add_gwyitem_to_gwycontainer):
        """Add created gwyitem to gywcontainer"""
        gwyitem = mock_new_gwyitem_object.return_value
        self.gwychannel._add_mask_to_gwy(self.gwychannel,
                                         self.gwycontainer,
                                         self.channel_id)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls(
            [call(gwyitem, self.gwycontainer)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_return_value(self,
                          mock_new_gwyitem_object,
                          mock_add_gwyitem_to_gwycontainer):
        """Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_mask_to_gwy(self.gwychannel,
                                                    self.gwycontainer,
                                                    self.channel_id)
        self.assertIs(is_added, mock_add_gwyitem_to_gwycontainer.return_value)


class GwyChannel_get_show(unittest.TestCase):
    """Test _get_show method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('pygwyfile.gwychannel.GwyDataField',
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


class GwyChannel_add_show_to_gwy(unittest.TestCase):
    """ Test _add_show_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_show_to_gwy = GwyChannel._add_show_to_gwy
        self.gwychannel.show = Mock(spec=GwyDataField)
        self.gwydf = Mock()
        self.gwychannel.show.to_gwy.return_value = self.gwydf
        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_raise_TypeError_if_show_is_not_GwyDataField_or_None(self):
        """ Raise TypeError exception if show is not GwyDataField or None"""
        self.gwychannel.show = 'Wrong presentation'
        self.assertRaises(TypeError,
                          self.gwychannel._add_show_to_gwy,
                          self.gwychannel,
                          self.gwycontainer,
                          self.channel_id)

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_show_is_None(self,
                                          mock_add_gwyitem_to_gwycontainer):
        """Return False if show is None and add nothing to gwycontainer"""
        self.gwychannel.show = None
        actual_return = self.gwychannel._add_show_to_gwy(self.gwychannel,
                                                         self.gwycontainer,
                                                         self.channel_id)
        self.assertIs(actual_return, False)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls([])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_create_new_gwyitem(self,
                                mock_new_gwyitem_object,
                                mock_add_gwyitem_to_gwycontainer):
        """Create new object gwyitem with show data"""
        self.gwychannel._add_show_to_gwy(self.gwychannel,
                                         self.gwycontainer,
                                         self.channel_id)
        mock_new_gwyitem_object.assert_has_calls(
            [call("/{:d}/show".format(self.channel_id),
                  self.gwydf)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_add_gwyitem_to_container(self,
                                      mock_new_gwyitem_object,
                                      mock_add_gwyitem_to_gwycontainer):
        """Add created gwyitem to gywcontainer"""
        gwyitem = mock_new_gwyitem_object.return_value
        self.gwychannel._add_show_to_gwy(self.gwychannel,
                                         self.gwycontainer,
                                         self.channel_id)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls(
            [call(gwyitem, self.gwycontainer)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_return_value(self,
                          mock_new_gwyitem_object,
                          mock_add_gwyitem_to_gwycontainer):
        """Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_show_to_gwy(self.gwychannel,
                                                    self.gwycontainer,
                                                    self.channel_id)
        self.assertIs(is_added, mock_add_gwyitem_to_gwycontainer.return_value)


class GwyChannel_get_point_sel(unittest.TestCase):
    """Test _get_point_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('pygwyfile.gwychannel.GwyPointSelection',
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


class GwyChannel_add_point_sel_to_gwy(unittest.TestCase):
    """ Test _add_point_sel_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_point_sel_to_gwy = (
            GwyChannel._add_point_sel_to_gwy)
        self.gwychannel.point_selections = Mock(spec=GwyPointSelection)
        self.gwysel = Mock()
        self.gwychannel.point_selections.to_gwy.return_value = self.gwysel
        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_raise_TypeError_if_point_sel_is_not_GwyDataField_or_None(self):
        """ Raise TypeError exception if point_selections is not GwyDataField
            or None
        """
        self.gwychannel.point_selections = 'Wrong type'
        self.assertRaises(TypeError,
                          self.gwychannel._add_point_sel_to_gwy,
                          self.gwychannel,
                          self.gwycontainer,
                          self.channel_id)

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_point_selections_is_None(
            self,
            mock_add_gwyitem_to_gwycontainer):
        """Return False if point_selections is None and
           add nothing to gwycontainer
        """
        self.gwychannel.point_selections = None
        actual_return = self.gwychannel._add_point_sel_to_gwy(
            self.gwychannel,
            self.gwycontainer,
            self.channel_id)
        self.assertIs(actual_return, False)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls([])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_create_new_gwyitem(self,
                                mock_new_gwyitem_object,
                                mock_add_gwyitem_to_gwycontainer):
        """Create new object gwyitem with point_selections data"""
        self.gwychannel._add_point_sel_to_gwy(self.gwychannel,
                                              self.gwycontainer,
                                              self.channel_id)
        mock_new_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/point".format(self.channel_id),
                  self.gwysel)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_add_gwyitem_to_container(self,
                                      mock_new_gwyitem_object,
                                      mock_add_gwyitem_to_gwycontainer):
        """Add created gwyitem to gywcontainer"""
        gwyitem = mock_new_gwyitem_object.return_value
        self.gwychannel._add_point_sel_to_gwy(self.gwychannel,
                                              self.gwycontainer,
                                              self.channel_id)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls(
            [call(gwyitem, self.gwycontainer)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_return_value(self,
                          mock_new_gwyitem_object,
                          mock_add_gwyitem_to_gwycontainer):
        """Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_point_sel_to_gwy(self.gwychannel,
                                                         self.gwycontainer,
                                                         self.channel_id)
        self.assertIs(is_added, mock_add_gwyitem_to_gwycontainer.return_value)


class GwyChannel_get_pointer_sel(unittest.TestCase):
    """Test _get_pointer_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('pygwyfile.gwychannel.GwyPointerSelection',
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


class GwyChannel_add_pointer_sel_to_gwy(unittest.TestCase):
    """ Test _add_pointer_sel_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_pointer_sel_to_gwy = (
            GwyChannel._add_pointer_sel_to_gwy)
        self.gwychannel.pointer_selections = Mock(spec=GwyPointerSelection)
        self.gwysel = Mock()
        self.gwychannel.pointer_selections.to_gwy.return_value = self.gwysel
        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_raise_TypeError_if_pointer_sel_is_not_GwyDataField_or_None(self):
        """ Raise TypeError exception if pointer_selections is not GwyDataField
            or None
        """
        self.gwychannel.pointer_selections = 'Wrong type'
        self.assertRaises(TypeError,
                          self.gwychannel._add_pointer_sel_to_gwy,
                          self.gwychannel,
                          self.gwycontainer,
                          self.channel_id)

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_pointer_selections_is_None(
            self,
            mock_add_gwyitem_to_gwycontainer):
        """Return False if pointer_selections is None and
           add nothing to gwycontainer
        """
        self.gwychannel.pointer_selections = None
        actual_return = self.gwychannel._add_pointer_sel_to_gwy(
            self.gwychannel,
            self.gwycontainer,
            self.channel_id)
        self.assertIs(actual_return, False)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls([])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_create_new_gwyitem(self,
                                mock_new_gwyitem_object,
                                mock_add_gwyitem_to_gwycontainer):
        """Create new object gwyitem with point_selections data"""
        self.gwychannel._add_pointer_sel_to_gwy(self.gwychannel,
                                                self.gwycontainer,
                                                self.channel_id)
        mock_new_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/pointer".format(self.channel_id),
                  self.gwysel)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_add_gwyitem_to_container(self,
                                      mock_new_gwyitem_object,
                                      mock_add_gwyitem_to_gwycontainer):
        """Add created gwyitem to gywcontainer"""
        gwyitem = mock_new_gwyitem_object.return_value
        self.gwychannel._add_pointer_sel_to_gwy(self.gwychannel,
                                                self.gwycontainer,
                                                self.channel_id)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls(
            [call(gwyitem, self.gwycontainer)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_return_value(self,
                          mock_new_gwyitem_object,
                          mock_add_gwyitem_to_gwycontainer):
        """Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_pointer_sel_to_gwy(self.gwychannel,
                                                           self.gwycontainer,
                                                           self.channel_id)
        self.assertIs(is_added, mock_add_gwyitem_to_gwycontainer.return_value)


class GwyChannel_get_line_sel(unittest.TestCase):
    """Test _get_line_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('pygwyfile.gwychannel.GwyLineSelection',
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


class GwyChannel_add_line_sel_to_gwy(unittest.TestCase):
    """ Test _add_line_sel_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_line_sel_to_gwy = GwyChannel._add_line_sel_to_gwy
        self.gwychannel.line_selections = Mock(spec=GwyLineSelection)
        self.gwysel = Mock()
        self.gwychannel.line_selections.to_gwy.return_value = self.gwysel
        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_raise_TypeError_if_line_sel_is_not_GwyDataField_or_None(self):
        """ Raise TypeError exception if line_selections is not GwyDataField
            or None
        """
        self.gwychannel.line_selections = 'Wrong type'
        self.assertRaises(TypeError,
                          self.gwychannel._add_line_sel_to_gwy,
                          self.gwychannel,
                          self.gwycontainer,
                          self.channel_id)

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_line_selections_is_None(
            self,
            mock_add_gwyitem_to_gwycontainer):
        """Return False if line_selections is None and
           add nothing to gwycontainer
        """
        self.gwychannel.line_selections = None
        actual_return = self.gwychannel._add_line_sel_to_gwy(
            self.gwychannel,
            self.gwycontainer,
            self.channel_id)
        self.assertIs(actual_return, False)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls([])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_create_new_gwyitem(self,
                                mock_new_gwyitem_object,
                                mock_add_gwyitem_to_gwycontainer):
        """Create new object gwyitem with line_selections data"""
        self.gwychannel._add_line_sel_to_gwy(self.gwychannel,
                                             self.gwycontainer,
                                             self.channel_id)
        mock_new_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/line".format(self.channel_id),
                  self.gwysel)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_add_gwyitem_to_container(self,
                                      mock_new_gwyitem_object,
                                      mock_add_gwyitem_to_gwycontainer):
        """Add created gwyitem to gywcontainer"""
        gwyitem = mock_new_gwyitem_object.return_value
        self.gwychannel._add_line_sel_to_gwy(self.gwychannel,
                                             self.gwycontainer,
                                             self.channel_id)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls(
            [call(gwyitem, self.gwycontainer)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_return_value(self,
                          mock_new_gwyitem_object,
                          mock_add_gwyitem_to_gwycontainer):
        """Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_line_sel_to_gwy(self.gwychannel,
                                                        self.gwycontainer,
                                                        self.channel_id)
        self.assertIs(is_added, mock_add_gwyitem_to_gwycontainer.return_value)


class GwyChannel_get_rectangle_sel(unittest.TestCase):
    """Test _get_rectangle_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('pygwyfile.gwychannel.GwyRectangleSelection',
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


class GwyChannel_add_rectangle_sel_to_gwy(unittest.TestCase):
    """ Test _add_rectangle_sel_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_rectangle_sel_to_gwy = (
            GwyChannel._add_rectangle_sel_to_gwy)
        self.gwychannel.rectangle_selections = Mock(spec=GwyRectangleSelection)
        self.gwysel = Mock()
        self.gwychannel.rectangle_selections.to_gwy.return_value = self.gwysel
        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_raise_TypeError_if_rectangle_sel_is_not_GwyDataField(self):
        """ Raise TypeError exception if rectangle_selections is not GwyDataField
            or None
        """
        self.gwychannel.rectangle_selections = 'Wrong type'
        self.assertRaises(TypeError,
                          self.gwychannel._add_rectangle_sel_to_gwy,
                          self.gwychannel,
                          self.gwycontainer,
                          self.channel_id)

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_rectangle_selections_is_None(
            self,
            mock_add_gwyitem_to_gwycontainer):
        """Return False if ractangle_selections is None and
           add nothing to gwycontainer
        """
        self.gwychannel.rectangle_selections = None
        actual_return = self.gwychannel._add_rectangle_sel_to_gwy(
            self.gwychannel,
            self.gwycontainer,
            self.channel_id)
        self.assertIs(actual_return, False)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls([])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_create_new_gwyitem(self,
                                mock_new_gwyitem_object,
                                mock_add_gwyitem_to_gwycontainer):
        """Create new object gwyitem with rectangle_selections data"""
        self.gwychannel._add_rectangle_sel_to_gwy(self.gwychannel,
                                                  self.gwycontainer,
                                                  self.channel_id)
        mock_new_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/rectangle".format(self.channel_id),
                  self.gwysel)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_add_gwyitem_to_container(self,
                                      mock_new_gwyitem_object,
                                      mock_add_gwyitem_to_gwycontainer):
        """Add created gwyitem to gywcontainer"""
        gwyitem = mock_new_gwyitem_object.return_value
        self.gwychannel._add_rectangle_sel_to_gwy(self.gwychannel,
                                                  self.gwycontainer,
                                                  self.channel_id)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls(
            [call(gwyitem, self.gwycontainer)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_return_value(self,
                          mock_new_gwyitem_object,
                          mock_add_gwyitem_to_gwycontainer):
        """Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_rectangle_sel_to_gwy(self.gwychannel,
                                                             self.gwycontainer,
                                                             self.channel_id)
        self.assertIs(is_added, mock_add_gwyitem_to_gwycontainer.return_value)


class GwyChannel_get_ellipse_sel(unittest.TestCase):
    """Test _get_ellipse_sel method of GwyChannel class
    """

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        patcher = patch('pygwyfile.gwychannel.GwyEllipseSelection',
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


class GwyChannel_add_ellipse_sel_to_gwy(unittest.TestCase):
    """ Test _add_ellipse_sel_to_gwy method of GwyChannel class"""

    def setUp(self):
        self.gwychannel = Mock(spec=GwyChannel)
        self.gwychannel._add_ellipse_sel_to_gwy = (
            GwyChannel._add_ellipse_sel_to_gwy)
        self.gwychannel.ellipse_selections = Mock(spec=GwyEllipseSelection)
        self.gwysel = Mock()
        self.gwychannel.ellipse_selections.to_gwy.return_value = self.gwysel
        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_raise_TypeError_if_ellipse_sel_is_not_GwyDataField_or_None(self):
        """ Raise TypeError exception if ellipse_selections is not GwyDataField
            or None
        """
        self.gwychannel.ellipse_selections = 'Wrong type'
        self.assertRaises(TypeError,
                          self.gwychannel._add_ellipse_sel_to_gwy,
                          self.gwychannel,
                          self.gwycontainer,
                          self.channel_id)

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    def test_return_False_if_ellipse_selections_is_None(
            self,
            mock_add_gwyitem_to_gwycontainer):
        """Return False if ellipse_selections is None and
           add nothing to gwycontainer
        """
        self.gwychannel.ellipse_selections = None
        actual_return = self.gwychannel._add_ellipse_sel_to_gwy(
            self.gwychannel,
            self.gwycontainer,
            self.channel_id)
        self.assertIs(actual_return, False)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls([])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_create_new_gwyitem(self,
                                mock_new_gwyitem_object,
                                mock_add_gwyitem_to_gwycontainer):
        """Create new object gwyitem with ellipse_selections data"""
        self.gwychannel._add_ellipse_sel_to_gwy(self.gwychannel,
                                                self.gwycontainer,
                                                self.channel_id)
        mock_new_gwyitem_object.assert_has_calls(
            [call("/{:d}/select/ellipse".format(self.channel_id),
                  self.gwysel)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_add_gwyitem_to_container(self,
                                      mock_new_gwyitem_object,
                                      mock_add_gwyitem_to_gwycontainer):
        """Add created gwyitem to gywcontainer"""
        gwyitem = mock_new_gwyitem_object.return_value
        self.gwychannel._add_ellipse_sel_to_gwy(self.gwychannel,
                                                self.gwycontainer,
                                                self.channel_id)
        mock_add_gwyitem_to_gwycontainer.assert_has_calls(
            [call(gwyitem, self.gwycontainer)])

    @patch('pygwyfile.gwychannel.add_gwyitem_to_gwycontainer', autospec=True)
    @patch.object(Gwyfile, 'new_gwyitem_object')
    def test_return_value(self,
                          mock_new_gwyitem_object,
                          mock_add_gwyitem_to_gwycontainer):
        """Return result of add_gwyitem_to_gwycontainer call"""
        is_added = self.gwychannel._add_ellipse_sel_to_gwy(self.gwychannel,
                                                           self.gwycontainer,
                                                           self.channel_id)
        self.assertIs(is_added, mock_add_gwyitem_to_gwycontainer.return_value)


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

    @patch('pygwyfile.gwychannel.GwyChannel', autospec=True)
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


class GwyChannel_to_gwy(unittest.TestCase):
    """ Tests for to_gwy method of GwyChannel class"""
    def setUp(self):
        self.channel = Mock(spec=GwyChannel)
        self.channel.to_gwy = GwyChannel.to_gwy
        self.channel._add_title_to_gwy = Mock(autospec=True)
        self.channel._add_data_to_gwy = Mock(autospec=True)
        self.channel._add_visibility_to_gwy = Mock(autospec=True)
        self.channel._add_palette_to_gwy = Mock(autospec=True)
        self.channel._add_range_type_to_gwy = Mock(autospec=True)
        self.channel._add_range_min_to_gwy = Mock(autospec=True)
        self.channel._add_range_max_to_gwy = Mock(autospec=True)
        self.channel._add_mask_to_gwy = Mock(autospec=True)
        self.channel._add_mask_red_to_gwy = Mock(autospec=True)
        self.channel._add_mask_green_to_gwy = Mock(autospec=True)
        self.channel._add_mask_blue_to_gwy = Mock(autospec=True)
        self.channel._add_mask_alpha_to_gwy = Mock(autospec=True)
        self.channel._add_show_to_gwy = Mock(autospec=True)
        self.channel._add_point_sel_to_gwy = Mock(autospec=True)
        self.channel._add_pointer_sel_to_gwy = Mock(autospec=True)
        self.channel._add_line_sel_to_gwy = Mock(autospec=True)
        self.channel._add_rectangle_sel_to_gwy = Mock(autospec=True)
        self.channel._add_ellipse_sel_to_gwy = Mock(autspec=True)

        self.gwycontainer = Mock()
        self.channel_id = 0

    def test_add_title_to_gwy(self):
        """ Add title item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_title_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_data_to_gwy(self):
        """ Add data item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_data_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_visibility_to_gwy(self):
        """ Add visible item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_visibility_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_palette_to_gwy(self):
        """ Add palette item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_palette_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_range_type_to_gwy(self):
        """ Add range-type item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_range_type_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_range_min_to_gwy(self):
        """ Add range-min item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_range_min_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_range_max_to_gwy(self):
        """ Add range-max item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_range_max_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_mask_to_gwy(self):
        """ Add mask datafield item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_mask_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_mask_red_to_gwy(self):
        """ Add red component of the mask to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_mask_red_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_mask_green_to_gwy(self):
        """ Add green component of the mask to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_mask_green_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_mask_blue_to_gwy(self):
        """ Add blue component of the mask to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_mask_blue_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_mask_alpha_to_gwy(self):
        """ Add alpha (opacity) component to the mask to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_mask_alpha_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_show_to_gwy(self):
        """ Add presentation datafield to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_show_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_point_sel_to_gwy(self):
        """ Add point selection item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_point_sel_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_pointer_sel_to_gwy(self):
        """ Add pointer selection item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_pointer_sel_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_line_sel_to_gwy(self):
        """ Add line selection item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_line_sel_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_rectangle_sel_to_gwy(self):
        """ Add rectangle selection item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_rectangle_sel_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])

    def test_add_ellipse_sel_to_gwy(self):
        """ Add ellipse selection item to GwyContainer"""
        self.channel.to_gwy(self.channel, self.gwycontainer, self.channel_id)
        self.channel._add_ellipse_sel_to_gwy.assert_has_calls(
            [call(self.gwycontainer, self.channel_id)])


if __name__ == '__main__':
    unittest.main()
