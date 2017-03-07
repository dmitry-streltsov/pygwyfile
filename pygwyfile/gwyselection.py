""" Pythonic representation for gwyddion selections objects

    Classes:
        GwySelection(ABC): abstract base class.
        GwyPointSelection(GwySelection): point selection
        GwyPointerSelection(GwySelection): pointer selection
        GwyLineSelection(GwySelection): line selection
        GwyRectangleSelection(GwySelection): rectange selection
        GwyEllipseSelection(GwySelection): ellipse selection

"""

from abc import ABC, abstractmethod

from pygwyfile._libgwyfile import ffi, lib
from pygwyfile.gwyfile import GwyfileErrorCMsg


class GwySelection(ABC):
    """Base class for GwySelection objects

    Attributes:
        data: list
              list of selection data

    Metods:
        from_gwy(gwyobject): Create GwySelection* object from <GwyfileObject*>
                             Must be redefined in subclass

    """
    # _get_sel_func (C func): Libgwyfile C function to get selection.
    #                         Must be redefined in subclass
    #
    # _npoints (int): Number of points in one selection
    #                 (e.g. 1 for point selection, 2 for line selection)
    _get_sel_func = None
    _npoints = 1

    data = []

    @abstractmethod
    def __init__(self, points):
        """
        Args:
            points: list or tuple of points
                    each point is a tuple of coordinates (x, y)
        """
        pass

    @classmethod
    @abstractmethod
    def from_gwy(cls, gwysel):
        """
        Get points from <GwyfileObject*>

        Args:
            gwysel (GwyfileObject*):
                GwySelection object from Libgwyfile
                e.g. GwySelectionPoint object for point selection

        Returns:
            [(x1, y1), ..., (xN, yN)]: list of tuples with point coordinates
            or None :                  if there are no point selections

        """

        nsel = cls._get_selection_nsel(gwysel)
        points = cls._get_selection_points(gwysel, nsel)
        return points

    @classmethod
    def _get_selection_nsel(cls, gwysel):
        """Get number of selections from the object

        Args:
            gwysel (GwyfileObject*):
                GwySelection object from Libgwyfile
                e.g. GwySelectionPoint object for point selection

        Returns:
            nsel (int):
                number of selections of this type in gwysel
        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)
        nselp = ffi.new("int32_t*")

        if cls._get_sel_func(gwysel,
                             errorp,
                             ffi.new("char[]", b'nsel'),
                             nselp,
                             ffi.NULL):
            nsel = nselp[0]
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

        return nsel

    @classmethod
    def _get_selection_points(cls, gwysel, nsel):
        """Get all points of selection from the gwysel object

        Args:
            gwysel (GwyfileObject*):
                GwySelection object from Libgwyfile
                e.g. GwySelectionPoint object for point selection
            nsel (int):
                number of selections of this type in gwysel

        Returns:
            [(x1, y1), ..., (xN, yN)]: list of tuples with point coordinates
                                       or None if there are no selections

        """

        error = ffi.new("GwyfileError*")
        errorp = ffi.new("GwyfileError**", error)

        if nsel == 0:
            return None
        else:
            data = ffi.new("double[]", 2 * nsel * cls._npoints)
            datap = ffi.new("double**", data)

        if cls._get_sel_func(gwysel,
                             errorp,
                             ffi.new("char[]", b'data'),
                             datap,
                             ffi.NULL):
            data = datap[0]
            points = [(data[i * 2], data[i * 2 + 1])
                      for i in range(nsel * cls._npoints)]
        else:
            raise GwyfileErrorCMsg(errorp[0].message)

        return points

    @staticmethod
    def _combine_points_in_pair(points):
        """ Combine list of points in list of pairs
            [(x1, y1), (x2, y2), ...] -> [((x1, y1), (x2, y2))...]
        """

        pairs = list(zip(tuple(points[::2]),
                         tuple(points[1::2])))
        return pairs

    def __repr__(self):
        return "<{} instance at {}. Selections: {}>".format(
            self.__class__.__name__,
            hex(id(self)),
            len(self.data))


class GwyPointSelection(GwySelection):
    """Class for point selection

    Attributes:
        data: non-empty list of points [(x1, y1), ...]

    Methods:
        from_gwy(gwyobject): Create GwyPointSelection instance from
                             <GwySelectionPoint*> object
    """

    _npoints = 1  # number of points in one point selection
    _get_sel_func = lib.gwyfile_object_selectionpoint_get

    def __init__(self, points):
        """
        Args:
            points: list or tuple of points (x, y)
        """
        if points:
            self.data = list(points)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(cls, gwysel):
        """
        Create GwyPointSelection instance from <GwySelectionPoint*> object

        Args:
            gwysel:
                <GwySelectionPoint*> object from Libgwyfile library

        Returns:
            GwyPointSelection instance initialized by the point selections
            or None if number of points is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            return GwyPointSelection(points)
        else:
            return None


class GwyPointerSelection(GwySelection):
    """Class for pointer selection

    Attributes:
        data: list of points [(x1, y1), ...]

    Methods:
        from_gwy(gwyobject): Create GwyPointerSelection from
                             <GwySelectionPointer*> object
    """

    _npoints = 1  # number of points in one pointer selection
    _get_sel_func = lib.gwyfile_object_selectionpoint_get

    def __init__(self, points):
        if points:
            self.data = list(points)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(cls, gwysel):
        """
        Create GwyPointerSelection instance from <GwySelectionPointer*> object

        Args:
            gwysel:
                <GwySelectionPointer*> object from Libgwyfile library

        Returns:
            GwyPointerSelection instance initialized by the pointer selections
            or None if number of pointers is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            return GwyPointerSelection(points)
        else:
            return None


class GwyLineSelection(GwySelection):
    """Class for line selections

    Attributes:
        data: list of point pairs [((x1, y1), (x2, y2))...]
              (two points for one line selection)

    Methods:
        from_gwy(gwyobject): Create GwyLineSelection instance from
                             <GwySelectionLine*> object
    """

    _npoints = 2  # number of points in one line selection
    _get_sel_func = lib.gwyfile_object_selectionline_get

    def __init__(self, point_pairs):
        if point_pairs:
            self.data = list(point_pairs)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(self, gwysel):
        """
        Create GwyLineSelection instance from <GwySelectionLine*> object

        Args:
            gwysel:
                <GwySelectionLine*> object from Libgwyfile library

        Returns:
            GwyLineSelection instance initialized by the line selections
            or None if number of points is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            point_pairs = super()._combine_points_in_pair(points)
            return GwyLineSelection(point_pairs)
        else:
            return None


class GwyRectangleSelection(GwySelection):
    """Class for rectange selections

    Attributes:
        data: list of point pairs [((x1, y1), (x2, y2))...]
              (two points for one rectangle selection)

    Methods:
        from_gwy(gwyobject): Create GwyRectangleSelection instance from
                             <GwySelectionRectangle*> object
    """

    _npoints = 2  # number of points in one rectangle selection
    _get_sel_func = lib.gwyfile_object_selectionrectangle_get

    def __init__(self, point_pairs):
        if point_pairs:
            self.data = list(point_pairs)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(self, gwysel):
        """
        Create GwyRectangleSelection instance from
        <GwySelectionRectangle*> object

        Args:
            gwysel:
                <GwySelectionRectangle*> object from Libgwyfile library

        Returns:
            GwyRectangleSelection instance initialized by the rectangle sel.
            or None if number of points is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            point_pairs = super()._combine_points_in_pair(points)
            return GwyRectangleSelection(point_pairs)
        else:
            return None


class GwyEllipseSelection(GwySelection):
    """Class for ellipse selections

    Attributes:
        data: list of point pairs [((x1, y1), (x2, y2))...]
              (two points for one ellipse selection)

    Methods:
        from_gwy(gwyobject): Create GwyEllipseSelection from
                             <GwySelectionEllipse*> object

    """

    _npoints = 2  # number of points in one ellipse selection
    _get_sel_func = lib.gwyfile_object_selectionellipse_get

    def __init__(self, point_pairs):
        if point_pairs:
            self.data = list(point_pairs)
        else:
            raise ValueError("points list is empty")

    @classmethod
    def from_gwy(self, gwysel):
        """
        Create GwyEllipseSelection instance from <GwySelectionEllipse*> object

        Args:
            gwysel:
                <GwySelectionEllipse*> object from Libgwyfile library

        Returns:
            GwyEllipseSelection instance initialized by the ellipse selections
            or None if number of points is zero
        """
        points = super().from_gwy(gwysel)
        if points is not None:
            point_pairs = super()._combine_points_in_pair(points)
            return GwyEllipseSelection(point_pairs)
        else:
            return None
