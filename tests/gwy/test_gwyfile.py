import unittest
from unittest.mock import Mock, patch, ANY

from gwydb.gwy.gwyfile import read_gwyfile


class Read_gwyTestCase(unittest.TestCase):
    """Test read_gwyfile function"""

    @patch('gwydb.gwy.gwyfile.os')
    def test_raising_exception(self,
                               mock_os):
        """Test that OSError exception raises
           if gwy file does not exists
        """

        filename = 'test.gwy'
        mock_os.path.isfile.return_value = False
        self.assertRaises(OSError, read_gwyfile, filename)

    @patch('gwydb.gwy.gwyfile.os')
    @patch('gwydb.gwy.gwyfile.lib')
    def test_transfer_of_function_args(self,
                                       mock_libgwyfile,
                                       mock_os):
        """Test arguments transfer to gwyfile_read_file function"""

        filename = 'test.gwy'
        mock_os.path.isfile.return_value = True

        # To prevent real reading of the 'test.gwy' file
        mock_libgwyfile.gwyfile_read_file = Mock(spec=True)

        read_gwyfile(filename)

        mock_libgwyfile.gwyfile_read_file.assert_called_once_with(
            filename.encode('utf-8'), ANY)


if __name__ == '__main__':
    unittest.main()
