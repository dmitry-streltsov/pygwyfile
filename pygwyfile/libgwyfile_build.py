""" CFFI interface for interacting with Libgwyfile library
"""

from cffi import FFI


ffibuilder = FFI()

ffibuilder.set_source("pygwyfile._libgwyfile",
                      r"""
                      #include "gwyfile.h"
                      """,
                      include_dirs=["pygwyfile/libgwyfile"],
                      sources=["pygwyfile/libgwyfile/gwyfile.c"])

ffibuilder.cdef("""
    typedef ... GwyfileObject;
    typedef ... GwyfileItem;
    typedef struct {
        ...;
        char* message;
    } GwyfileError;

    GwyfileObject* gwyfile_read_file(const char*  filename,
                                     GwyfileError**  error);
    const char* gwyfile_object_name(const GwyfileObject* object);
    int* gwyfile_object_container_enumerate_channels(const GwyfileObject* object,
                                                     unsigned int* nchannels);
    int* gwyfile_object_container_enumerate_graphs(const GwyfileObject* object,
                                                   unsigned int* ngraphs);
    GwyfileItem* gwyfile_object_get(const GwyfileObject* object,
                                    const char* name);
    GwyfileObject* gwyfile_item_get_object(const GwyfileItem* item);
    bool gwyfile_object_datafield_get(const GwyfileObject* object,
                                      GwyfileError** error,
                                      ...);
    bool gwyfile_object_selectionpoint_get(const GwyfileObject* object,
                                           const GwyfileError** error,
                                           ...);
    bool gwyfile_object_selectionline_get(const GwyfileObject* object,
                                          GwyfileError** error,
                                          ...);
    bool gwyfile_object_selectionrectangle_get(const GwyfileObject* object,
                                               GwyfileError** error,
                                               ...);
    bool gwyfile_object_selectionellipse_get(const GwyfileObject* object,
                                             GwyfileError** error,
                                             ...);
    bool gwyfile_object_graphmodel_get(const GwyfileObject* object,
                                       GwyfileError** error,
                                       ...);
    bool gwyfile_object_graphcurvemodel_get(const GwyfileObject* object,
                                            GwyfileError** error,
                                            ...);
    bool gwyfile_item_get_bool(const GwyfileItem* item);
    double gwyfile_item_get_double(const GwyfileItem* item);
    const char* gwyfile_item_get_string(const GwyfileItem* item);
    int32_t gwyfile_item_get_int32(const GwyfileItem* item);
    GwyfileObject* gwyfile_object_new_selectionpoint(int nsel, ...);
    GwyfileObject* gwyfile_object_new_selectionline(int nsel, ...);
    GwyfileObject* gwyfile_object_new_selectionrectangle(int nsel, ...);
    GwyfileObject* gwyfile_object_new_selectionellipse(int nsel, ...);
    GwyfileObject* gwyfile_object_new_graphcurvemodel(int ndata, ...);
    GwyfileObject* gwyfile_object_new_graphmodel(int ncurves, ...);
""")


if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
