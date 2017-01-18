# -*- coding: utf-8 -*-
""" CFFI interface for interacting with Libgwyfile library
"""

from cffi import FFI
ffibuilder = FFI()

ffibuilder.set_source("_gwyio",
                     r"""
                     #include "gwyfilelib/gwyfile.h"
                     """,
                     sources=["gwyfilelib/gwyfile.c"])


ffibuilder.cdef("""
    typedef ... GwyfileObject;
    typedef ... GwyfileItem;
    typedef struct {
        ...;
        char* message;
    } GwyfileError;
    
    GwyfileObject* gwyfile_read_file(const char*  filename, GwyfileError**  error);
    const char* gwyfile_object_name(const GwyfileObject* object);
    const char* gwyfile_item_name(const GwyfileItem* item);
    int* gwyfile_object_container_enumerate_channels(const GwyfileObject* object, unsigned int* nchannels);
    GwyfileItem* gwyfile_object_get(const GwyfileObject* object, const char* name);
    GwyfileObject* gwyfile_item_get_object(const GwyfileItem* item);
    bool gwyfile_object_datafield_get(const GwyfileObject* object, GwyfileError** error, ...);
""")


if __name__ == "__main__":
    ffibuilder.compile(verbose=True)

