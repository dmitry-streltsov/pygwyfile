""" Wrapper for GwyfileObject from Libgwyfile C library

    Classes:
        GwyfileError(Exception): Exceptions during operations with gwy files
        GwyfileErrorCMsg(GwyfileError): Libgwyfile C library exceptions
        Gwyfile: representation of GwyfileObject* from Libgwyfile C library

"""
import os.path

from gwydb.gwy._libgwyfile import ffi, lib


class GwyfileError(Exception):
    """
    Exceptions during operations with gwy files
    """

    pass


class GwyfileErrorCMsg(GwyfileError):
    """
    Class for libgwyfile C library exceptions
    """

    def __init__(self, c_error_msg):
        if c_error_msg:
            error_msg = ffi.string(c_error_msg).decode('utf-8')
            super().__init__(error_msg)
        else:
            super().__init__()


class Gwyfile:
    """Wrapper class for GwyfileObject from Libgwyfile C library

    Attributes:
        c_gwyfile (cdata  GwyfileObject*): gwyfile object from
                                           Libgwyfile C library
        filename ('string'): name of the file

    Methods:
        check_gwyobject(key):  Check presence of object in the gwyfile
        get_gwyobject(key):    Get object
    """

    def __init__(self, c_gwyfile, basename):
        """
        Args:
            c_gwyfile (cdata GwyfileOjbect*): gwyfile object from
                                              Libgwyfile C library
            basename (string): name of file without path
                               (e.g. 'sample.gwy' for 'data/sample.gwy')

        The top-level object of the c_gwyfile must be 'GwyContainer'
        """

        if not c_gwyfile:
            raise GwyfileError("c_gwyfile object is empty")

        c_toplevel_object_name = lib.gwyfile_object_name(c_gwyfile)
        if c_toplevel_object_name:
            toplevel_object_name = ffi.string(c_toplevel_object_name)
        else:
            error_msg = 'The top-level object of c_gwyfile is empty'
            raise GwyfileError(error_msg)

        if not toplevel_object_name == b'GwyContainer':
            error_msg = 'The top-level object of c_gwyfile is not ' \
                        ' a GwyContainer'
            raise GwyfileError(error_msg)

        self.c_gwyfile = c_gwyfile
        self.filename = basename

    def check_gwyobject(self, key):
        """Check presence of object in the gwyfile

        Args:
            key(str): object key

        Returns:
            True if object exists, otherwise False

        """

        item = lib.gwyfile_object_get(self.c_gwyfile, key.encode('utf-8'))
        if not item:
            return False
        else:
            return True

    def get_gwyobject(self, key):
        """Get object

        Args:
            key (str): Name of the object, e.g. "/0/data"

        Returns:
            item_object (cdata GwyfileObject*): The value of the object

        """

        item = lib.gwyfile_object_get(self.c_gwyfile, key.encode('utf-8'))
        if not item:
            raise GwyfileError("Cannot find the item \"{}\"".format(key))
        item_object = lib.gwyfile_item_get_object(item)
        if not item_object:
            raise GwyfileError(
                "Cannot find the object value of the item \"{}\"".format(key))
        return item_object

    @staticmethod
    def from_gwy(filename):
        """Create Gwyfile instance from file

        Args:
            filename (string): filename including path

        Returns:
            Gwyfile:
                instnce of Gwyfile class

        """
        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)

        if not os.path.isfile(filename):
            raise OSError("Cannot find file {}".format(filename))

        c_gwyfile = lib.gwyfile_read_file(filename.encode('utf-8'), errorp)

        if not c_gwyfile:
            raise GwyfileErrorCMsg(errorp[0].message)

        basename = os.path.basename(filename)

        gwyfile = Gwyfile(c_gwyfile, basename)
        return gwyfile
