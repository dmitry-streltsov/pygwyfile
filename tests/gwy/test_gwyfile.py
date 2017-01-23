import unittest
from unittest.mock import Mock, patch, ANY

from gwydb.gwy.gwyfile import read_gwyfile


class Func_read_gwy_TestCase(unittest.TestCase):
    """Test read_gwyfile function in gwydb.gwy.gwyfile"""

    @patch('gwydb.gwy.gwyfile.os')
    def test_raise_exception_if_file_doesnt_exist(self, mock_os):
        """Raise OSError exception if file
           does not exist
        """

        filename = 'test.gwy'
        mock_os.path.isfile.return_value = False
        self.assertRaises(OSError, read_gwyfile, filename)

    @patch('gwydb.gwy.gwyfile.os')
    @patch('gwydb.gwy.gwyfile.lib')
    def test_passing_of_function_args(self,
                                      mock_libgwyfile,
                                      mock_os):
        """If file exists call gwyfile_read_file function.
           Check arguments passed to this function
        """

        filename = 'test.gwy'
        mock_os.path.isfile.return_value = True
        mock_libgwyfile.gwyfile_read_file = Mock(spec=True)
        read_gwyfile(filename)
        mock_libgwyfile.gwyfile_read_file.assert_called_once_with(
            filename.encode('utf-8'), ANY)


if __name__ == '__main__':
    unittest.main()
