import unittest
from unittest.mock import Mock, patch, call

import numpy as np

from gwydb.gwy.gwy import GwyDatafield
from gwydb.gwy.gwy import GwyChannel
from gwydb.gwy.gwy import GwyContainer
from gwydb.gwy.gwy import get_channel
from gwydb.gwy.gwy import get_container
from gwydb.gwy.gwyfile import Gwyfile

class GwyDatafield_init(unittest.TestCase):
    """Test constructor of GwyDatafield class"""

    def setUp(self):
        self.xres = 256
        self.yres = 128
        self.data = np.random.rand(self.xres, self.yres)

    def test_init_via_dict(self):
        """Test initialization via python dictionary"""
        
        metadata = {'xres': self.xres, 'yres': self.yres}
        datafield = GwyDatafield(self.data, metadata)
        np.testing.assert_equal(datafield.data, self.data)
        self.assertEqual(datafield.xres, self.xres)
        self.assertEqual(datafield.yres, self.yres)

    def test_init_via_kwargs(self):
        """Test initialization via keyword arguments"""

        datafield = GwyDatafield(self.data,
                                 xres=self.xres,
                                 yres=self.yres)
        np.testing.assert_equal(datafield.data, self.data)
        self.assertEqual(datafield.xres, self.xres)
        self.assertEqual(datafield.yres, self.yres)

    def test_raise_ValueError_if_data_is_not_ndarray(self):
        """Raise ValueError if data is not a numpy array"""

        self.assertRaises(TypeError,
                          GwyDatafield,
                          data=[],
                          xres=self.xres,
                          yres=self.yres)

    def test_raise_ValueError_if_no_obligatory_args(self):
        """Raise AttributeError if there is no xres or yres args"""

        self.assertRaises(ValueError,
                          GwyDatafield,
                          data=self.data,
                          xres=self.xres)
        self.assertRaises(ValueError,
                          GwyDatafield,
                          data=self.data,
                          yres=self.yres)
        self.assertRaises(ValueError,
                          GwyDatafield,
                          data=self.data)

    def test_raise_ValueError_if_data_shape_is_wrong(self):
        """Raise ValueError if data.shape is not (xres, yres)"""

        self.xres = 128 # not 256
        self.assertRaises(ValueError,
                          GwyDatafield,
                          data=self.data,
                          xres=self.xres,
                          yres=self.yres)


class GwyChannel_init(unittest.TestCase):
    """Test constructor of GwyChannel class"""

    def setUp(self):
        self.title = "Title"
        self.datafield = Mock(spec=GwyDatafield)
        self.mask = Mock(spec=GwyDatafield)
        self.presentation = Mock(spec=GwyDatafield)

    def test_raise_TypeError_if_wrong_datafields_type(self):
        """Raise TypeError if any datafield is of wrong type"""

        self.assertRaises(TypeError,
                          GwyChannel,
                          title=self.title,
                          datafield=None,
                          mask=self.mask,
                          presentation=self.mask)
        
        wrong_mask = np.array([1, 0, 1], dtype=np.float64)
        self.assertRaises(TypeError,
                          GwyChannel,
                          title=self.title,
                          datafield=self.datafield,
                          mask=wrong_mask,
                          presentation=self.presentation)

        wrong_presentation = np.array([1, 0, 1], dtype=np.float64)
        self.assertRaises(TypeError,
                          GwyChannel,
                          title=self.title,
                          datafield=self.datafield,
                          presentation=wrong_presentation)

    def test_if_all_datafields_are_exist(self):
        """datafield, mask and presentation are not None"""

        gwychannel = GwyChannel(title=self.title,
                                datafield=self.datafield,
                                mask=self.mask,
                                presentation=self.presentation)
        self.assertEqual(gwychannel.title, self.title)
        self.assertEqual(gwychannel.datafield, self.datafield)
        self.assertEqual(gwychannel.mask, self.mask)
        self.assertEqual(gwychannel.presentation, self.presentation)

    def test_if_mask_is_none(self):
        """datafield and presentation are not None, but mask is None"""

        gwychannel = GwyChannel(title=self.title,
                                datafield=self.datafield,
                                mask=None,
                                presentation=self.presentation)
        self.assertEqual(gwychannel.title, self.title)
        self.assertEqual(gwychannel.datafield, self.datafield)
        self.assertEqual(gwychannel.presentation, self.presentation)
        self.assertIsNone(gwychannel.mask)

    def test_if_presentation_is_none(self):
        """datafield and mask are not None, but presentation is None"""

        gwychannel = GwyChannel(title=self.title,
                                datafield=self.datafield,
                                mask=self.mask,
                                presentation=None)
        self.assertEqual(gwychannel.title, self.title)
        self.assertEqual(gwychannel.datafield, self.datafield)
        self.assertEqual(gwychannel.mask, self.mask)
        self.assertIsNone(gwychannel.presentation)

    def test_if_mask_and_presentation_are_none(self):
        """datafield and mask are both None"""

        gwychannel = GwyChannel(title=self.title,
                                datafield=self.datafield,
                                mask=None,
                                presentation=None)
        self.assertEqual(gwychannel.title, self.title)
        self.assertEqual(gwychannel.datafield, self.datafield)
        self.assertIsNone(gwychannel.mask)
        self.assertIsNone(gwychannel.presentation)

    def test_default_args(self):
        """Test behavior with default arguments"""

        gwychannel = GwyChannel(title=self.title,
                                datafield=self.datafield)
        self.assertEqual(gwychannel.title, self.title)
        self.assertEqual(gwychannel.datafield, self.datafield)
        self.assertIsNone(gwychannel.mask)
        self.assertIsNone(gwychannel.presentation)


class GwyContainer_init(unittest.TestCase):
    """Test constructor of GwyContainer"""

    def setUp(self):
        channel1 = Mock(spec=GwyChannel)
        channel2 = Mock(spec=GwyChannel)
        channel3 = Mock(spec=GwyChannel)
        self.channels = [channel1, channel2, channel3]


    def test_check_initialization_with_list(self):
        """Test initialization with list of GwyChannel instances"""
        
        container = GwyContainer(self.channels)
        self.assertEqual(container.channels, self.channels)

    def test_raise_TypeError_if_wrong_type_of_args(self):
        """Raise TypeError if not all elements of list are GwyChannel"""
        
        self.channels.append(Mock(spec=GwyDatafield))
        self.assertRaises(TypeError,
                          GwyContainer,
                          self.channels)

    def test_raise_TypeError_if_arg_is_not_iterable(self):
        """Raise TypeError if trying initialize with non-iterable object"""
        
        self.assertRaises(TypeError,
                          GwyContainer,
                          None)


class Func_get_channel(unittest.TestCase):
    """Test get_channel function"""

    def setUp(self):
        self.gwyfile = Mock(spec=Gwyfile)
        self.channel_id = 0
        self.title = 'Height'
        self.metadata = {'xres': 256,
                         'yres': 256,
                         'xreal': 1e-6,
                         'yreal': 1e-6,
                         'xoff': 0,
                         'yoff': 0,
                         'si_unit_xy': 'm',
                         'si_unit_z': 'm'}
        self.data = np.random.rand(self.metadata['xres'],
                                   self.metadata['yres'])
        
        self.is_mask_exists = False
        self.is_show_exists = False

        self.mask_metadata = {'xres': 256,
                              'yres': 256}
        self.mask_data = np.random.rand(self.mask_metadata['xres'],
                                        self.mask_metadata['yres'])

        self.show_metadata = {'xres': 256,
                              'yres': 256}
        self.show_data = np.random.rand(self.show_metadata['xres'],
                                        self.show_metadata['yres'])
        
        self.gwyfile.get_title.return_value = self.title
        self.gwyfile.get_metadata.return_value = self.metadata
        self.gwyfile.get_data.return_value = self.data
        self.gwyfile._gwyobject_check.side_effect = self._gwyobject_check

    def test_raise_TypeError_if_gwyfile_is_not_a_Gwyfile_instance(self):
        """Raise TypeError exception if gwyfile is not a Gwyfile instance"""

        self.assertRaises(TypeError,
                          get_channel,
                          gwyfile=None,
                          channel_id=self.channel_id)
                          
        
    def test_only_datafield_exists(self):
        """No mask or presentation datafields in the channel"""

        result = get_channel(self.gwyfile, self.channel_id)

        self.assertEqual(result.title, self.title)
        np.testing.assert_almost_equal(result.datafield.data,
                                       self.data)
        for key in self.metadata:
            self.assertEqual(self.metadata[key],
                             getattr(result.datafield, key))

        self.assertIsNone(result.mask)
        self.assertIsNone(result.presentation)

    def test_datafield_and_mask_exist(self):
        """There is datafield and mask in the channel"""
        
        self.is_mask_exists = True
        self.gwyfile.get_mask_metadata.return_value = self.mask_metadata
        self.gwyfile.get_mask_data.return_value = self.mask_data

        result = get_channel(self.gwyfile, self.channel_id)

        # Check datafield
        self.assertEqual(result.title, self.title)
        np.testing.assert_almost_equal(result.datafield.data,
                                       self.data)
        for key in self.metadata:
            self.assertEqual(self.metadata[key],
                             getattr(result.datafield, key))

        # Check mask datafield
        np.testing.assert_equal(result.mask.data, self.mask_data)
        for key in self.mask_metadata:
            self.assertEqual(getattr(result.mask, key),
                             self.mask_metadata[key])

        self.assertIsNone(result.presentation)

    def test_datafield_and_presentation_exist(self):
        """There are datafield and presentation in the channel"""
        
        self.is_show_exists = True
        self.gwyfile.get_presentation_metadata.return_value = self.show_metadata
        self.gwyfile.get_presentation_data.return_value = self.show_data

        result = get_channel(self.gwyfile, self.channel_id)

        # Check datafield
        self.assertEqual(result.title, self.title)
        np.testing.assert_almost_equal(result.datafield.data,
                                       self.data)
        for key in self.metadata:
            self.assertEqual(self.metadata[key],
                             getattr(result.datafield, key))

        # Check presentation datafield
        np.testing.assert_equal(result.presentation.data,
                                self.show_data)
        for key in self.show_metadata:
            self.assertEqual(getattr(result.presentation, key),
                             self.show_metadata[key])

        self.assertIsNone(result.mask)

    def test_datafield_mask_presentation_exist(self):
        """There are datafield, mask and presentation in the channel"""
        
        self.is_show_exists = True
        self.is_mask_exists = True
        self.gwyfile.get_mask_metadata.return_value = self.mask_metadata
        self.gwyfile.get_mask_data.return_value = self.mask_data
        self.gwyfile.get_presentation_metadata.return_value = self.show_metadata
        self.gwyfile.get_presentation_data.return_value = self.show_data

        result = get_channel(self.gwyfile, self.channel_id)

        # Check datafield
        self.assertEqual(result.title, self.title)
        np.testing.assert_almost_equal(result.datafield.data,
                                       self.data)
        for key in self.metadata:
            self.assertEqual(self.metadata[key],
                             getattr(result.datafield, key))

        # Check mask datafield
        np.testing.assert_equal(result.mask.data, self.mask_data)
        for key in self.mask_metadata:
            self.assertEqual(getattr(result.mask, key),
                             self.mask_metadata[key])

        # Check presentation datafield
        np.testing.assert_equal(result.presentation.data,
                                self.show_data)
        for key in self.show_metadata:
            self.assertEqual(getattr(result.presentation, key),
                             self.show_metadata[key])


    def _gwyobject_check(self, key):
        """Return if the Mask or Presentation datafield exists"""
        
        # Datafield always exists in the channel
        if key == "/{:d}/data".format(self.channel_id):
            return True
        # Mask can exist in the channel or not
        if key == "/{:d}/mask".format(self.channel_id):
            return self.is_mask_exists
        # Presentation can exist in the channel or not
        if key == "/{:d}/show".format(self.channel_id):
            return self.is_show_exists
        # Assume that there is no other datafields
        return False


class Func_get_container(unittest.TestCase):
    """Test get_container function"""

    def test_raise_TypeError_if_arg_not_Gwyfile_instance(self):
        """Raise TypeError if arg is not Gwyfile instance """
        
        self.assertRaises(TypeError,
                          get_container,
                          None)
        
    @patch('gwydb.gwy.gwy.get_channel', autospec=True)
    @patch('gwydb.gwy.gwy.GwyContainer', autospec=True)
    def test_args_of_gwycontainer_init(self,
                                       mock_GwyContainer,
                                       mock_get_channel):
        """Returns GwyContainer containing all datafields"""

        # Create list of GwyChannel objects
        ids = [0, 1, 2]
        channels = [Mock(spec=GwyChannel) for i in ids]
        
        gwyfile = Mock(spec=Gwyfile)
        gwyfile.get_channels_ids.return_value = ids
        mock_get_channel.side_effect = channels

        expected_container = mock_GwyContainer.return_value
        result_container = get_container(gwyfile)
        
        mock_GwyContainer.assert_has_calls(
            [call(channels)])
        self.assertEqual(expected_container, result_container)
