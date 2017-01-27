import unittest
from unittest.mock import Mock

import numpy as np

from gwydb.gwy.gwy import get_channel
from gwydb.gwy.gwyfile import Gwyfile


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

        self.gwyfile.get_title.return_value = self.title
        self.gwyfile.get_metadata.return_value = self.metadata
        self.gwyfile.get_data.return_value = self.data
        self.gwyfile._gwyobject_check.side_effect = self.side_effect

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

    def side_effect(self, key):
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
