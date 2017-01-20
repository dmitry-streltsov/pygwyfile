/*
 * $Id: gwyfile.c 283 2016-04-27 20:48:28Z yeti-dn $
 *
 * Copyright © 2014-2016, David Nečas (Yeti) <yeti@gwyddion.net>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the “Software”), to
 * deal in the Software without restriction, including without limitation the
 * rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
 * sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#else
/* XXX: If you are embedding the library and do not have config.h, (un)define
 * the following to match your configuration. */

/* Define WORDS_BIGENDIAN to 1 if your processor stores words with the most
   significant byte first (like Motorola and SPARC, unlike Intel). */
#undef WORDS_BIGENDIAN
#endif

/* Define HAVE_UNISTD_H for a POSIX system.  An educated guess is provided
 * that should catch common Unix-like systems so you might not have to. */
#ifdef _WIN32
#include <sys/types.h>
#include <sys/stat.h>
#include <io.h>
#elif (defined(HAVE_UNISTD_H) || defined(__unix__) || defined(__unix) || (defined(__APPLE__) && defined(__MACH__)))
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

/* Maximum object/item nesting depth before we give up and report an error.
 * Technically, GWY files have no limit but too deep nesting can result in a
 * stack overflow which is often difficult to handle.  This value should be
 * sufficient for all realistic purposes and still safe in normal environments.
 */
#define GWYFILE_MAX_DEPTH 200

#define GWYFILE_PATH_ABBREVIATION_LIMIT 64

#define GWYFILE_MAX_ERROR_MESSAGE_LENGTH 260

/* End of things that might need to be adjusted. */

#include "gwyfile.h"
#include <math.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <float.h>
#include <assert.h>

#ifndef SIZE_MAX
#define SIZE_MAX ((size_t)-1)
#endif

#define GWYFILE_MAGIC_HEADER2 "GWYP"
#define GWYFILE_MAGIC_LEN 4

#define gwyfile_strequal(a,b) (!strcmp((a),(b)))
#define gwyfile_max(a,b) ((a) < (b) ? (b) : (a))
#define gwyfile_min(a,b) ((a) > (b) ? (b) : (a))

enum {
    BYTESWAP_BLOCK_SIZE = 1024*1024,
    BYTESWAP_STATIC_BUF_SIZE = 4*8,
};

#ifndef DOXYGEN_SHOULD_SKIP_THIS

struct _GwyfileItem {
    GwyfileItemType type;
    uint32_t array_length;
    char *name;
    unsigned int name_len;
    bool data_owned;
    GwyfileObject *owner;
    size_t data_size;
    union {
        /* Atomic types, no length. */
        bool b;
        char c;
        int32_t i;
        int64_t q;
        double d;
        /* Allocated types, no length. */
        char *s;
        GwyfileObject *o;
        /* Atomic arrays, have length. */
        char *ca;
        int32_t *ia;
        int64_t *qa;
        double *da;
        /* Allocated type arrays, have length. */
        char **sa;
        GwyfileObject **oa;
    } v;
};

struct _GwyfileObject {
    GwyfileItem *owner;
    char *name;
    uint32_t name_len;
    unsigned int nitems;
    unsigned int nallocitems;
    GwyfileItem **items;

    size_t data_size;
};

typedef struct {
    size_t alloc_size;
    size_t len;
    int *ids;
} GwyfileIdList;

#define GWYFILE_ID_LIST_INIT { 0, 0, NULL }

typedef union
{
  double v_double;
  struct {
#ifdef WORDS_BIGENDIAN
    unsigned int sign : 1;
    unsigned int biased_exponent : 11;
    unsigned int mantissa_high : 20;
    unsigned int mantissa_low : 32;
#else
    unsigned int mantissa_low : 32;
    unsigned int mantissa_high : 20;
    unsigned int biased_exponent : 11;
    unsigned int sign : 1;
#endif
  } mpn;
} GwyfileDouble;

#endif

static GwyfileItem*   gwyfile_item_fread_internal           (FILE *stream,
                                                             size_t max_size,
                                                             uint32_t depth,
                                                             GwyfileObject *owner,
                                                             GwyfileError **error);
static GwyfileObject* gwyfile_object_new_internal           (const char *name,
                                                             bool consume_name);
static GwyfileItem*   gwyfile_item_new_internal_bool        (const char *name,
                                                             bool consume_name,
                                                             bool value);
static GwyfileItem*   gwyfile_item_new_internal_char        (const char *name,
                                                             bool consume_name,
                                                             char value);
static GwyfileItem*   gwyfile_item_new_internal_int32       (const char *name,
                                                             bool consume_name,
                                                             int32_t value);
static GwyfileItem*   gwyfile_item_new_internal_int64       (const char *name,
                                                             bool consume_name,
                                                             int64_t value);
static GwyfileItem*   gwyfile_item_new_internal_double      (const char *name,
                                                             bool consume_name,
                                                             double value);
static GwyfileItem*   gwyfile_item_new_internal_string      (const char *name,
                                                             bool consume_name,
                                                             char *value);
static GwyfileItem*   gwyfile_item_new_internal_string_copy (const char *name,
                                                             bool consume_name,
                                                             const char *value);
static GwyfileItem*   gwyfile_item_new_internal_object      (const char *name,
                                                             bool consume_name,
                                                             GwyfileObject *object);
static GwyfileItem*   gwyfile_item_new_internal_char_array  (const char *name,
                                                             bool consume_name,
                                                             char *value,
                                                             uint32_t array_length);
static GwyfileItem*   gwyfile_item_new_internal_int32_array (const char *name,
                                                             bool consume_name,
                                                             int32_t *value,
                                                             uint32_t array_length);
static GwyfileItem*   gwyfile_item_new_internal_int64_array (const char *name,
                                                             bool consume_name,
                                                             int64_t *value,
                                                             uint32_t array_length);
static GwyfileItem*   gwyfile_item_new_internal_double_array(const char *name,
                                                             bool consume_name,
                                                             double *value,
                                                             uint32_t array_length);
static GwyfileItem*   gwyfile_item_new_internal_string_array(const char *name,
                                                             bool consume_name,
                                                             char **value,
                                                             uint32_t array_length);
static GwyfileItem*   gwyfile_item_new_internal_object_array(const char *name,
                                                             bool consume_name,
                                                             GwyfileObject **value,
                                                             uint32_t array_length);
static GwyfileItem*   gwyfile_item_new_internal             (GwyfileItemType type,
                                                             const char *name,
                                                             bool consume_name);
static void           gwyfile_item_notify_size_change       (GwyfileItem *item,
                                                             size_t oldsize);
static void           gwyfile_item_propagate_size_change    (GwyfileItem *item,
                                                             size_t size_change,
                                                             bool increase);
static void           gwyfile_object_propagate_size_change  (GwyfileObject *object,
                                                             size_t size_change,
                                                             bool increase);
static void           gwyfile_object_remove_last            (GwyfileObject *object,
                                                             bool freeitem);
static void           gwyfile_object_append                 (GwyfileObject *object,
                                                             GwyfileItem *item);
static const char*    gwyfile_object_find_duplicate_item    (GwyfileObject *object);
static inline bool    gwyfile_item_type_is_valid            (GwyfileItemType type);
static inline bool    gwyfile_item_type_is_array            (GwyfileItemType type);
static bool           gwyfile_is_valid_utf8                 (const char *s);
static bool           gwyfile_is_valid_identifier           (const char *s);
static inline char*   gwyfile_strdup                        (const char *s);
static inline void*   gwyfile_memdup                        (const void *p,
                                                             size_t size);
static char*          gwyfile_fread_string                  (FILE *stream,
                                                             size_t *max_size,
                                                             GwyfileError **error,
                                                             const char *what);
static bool           gwyfile_fwrite_le                     (const void *p0,
                                                             unsigned int itemsize,
                                                             size_t nitems,
                                                             FILE *stream);
static bool           gwyfile_fread_le                      (void *p0,
                                                             unsigned int itemsize,
                                                             size_t nitems,
                                                             FILE *stream);
static bool           gwyfile_check_size                    (size_t *max_size,
                                                             size_t size,
                                                             GwyfileError **error,
                                                             const char *what);
static void*          gwyfile_alloc_check                   (size_t nbytes,
                                                             GwyfileError **error);
static void           gwyfile_set_error_overrun             (GwyfileError **error,
                                                             const char *what);
static void           gwyfile_set_error                     (GwyfileError **error,
                                                             GwyfileErrorDomain domain,
                                                             GwyfileErrorCode code,
                                                             const char *format,
                                                             ...);
static void           gwyfile_set_error_errno               (GwyfileError **error);
static void           gwyfile_set_error_fread               (GwyfileError **error,
                                                             FILE *stream,
                                                             const char *what);
static bool           gwyfile_check_object_internal         (const GwyfileObject *object,
                                                             unsigned int flags,
                                                             GwyfileErrorList *errlist,
                                                             size_t *nalloc);
static bool           gwyfile_check_item_internal           (const GwyfileItem *item,
                                                             unsigned int flags,
                                                             GwyfileErrorList *errlist,
                                                             size_t *nalloc);
static void           gwyfile_error_list_append             (GwyfileErrorList *errlist,
                                                             GwyfileError *err,
                                                             size_t *nalloc);
static char*          gwyfile_format_path                   (const GwyfileObject *leaf_object,
                                                             const GwyfileItem *leaf_item);

/*!\fn bool gwyfile_write_file(GwyfileObject *object, const char *filename, GwyfileError **error)
 * \brief Writes a GWY file to a named file.
 *
 * The file will be overwritten if it exists.
 *
 * This function handles opening and closing of the file for you, otherwise
 * it is very similar to gwyfile_fwrite().
 *
 * If an I/O error occurs during writing the partially written file is kept,
 * i.e. it is not removed.
 *
 * The file name is passed to the system fopen() function as given.  You may
 * want to consider using gwyfile_read_wfile() or opening the file yourself
 * and using gwyfile_fread() on MS Windows.
 *
 * \param object The top-level GWY file data object for the file.  Normally
 *               it is a GwyContainer.
 * \param filename Name of the file to write the GWY file to.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \return \c true if the writing succeeded.
 */
bool
gwyfile_write_file(GwyfileObject *object,
                   const char *filename,
                   GwyfileError **error)
{
    FILE *stream;

    assert(object);
    assert(filename);

#ifndef _WIN32
    if (!(stream = fopen(filename, "wb"))) {
        gwyfile_set_error_errno(error);
        return false;
    }
#else
    if (fopen_s(&stream, filename, "wb") != 0) {
        gwyfile_set_error_errno(error);
        return false;
    }
#endif

    if (!gwyfile_fwrite(object, stream, error)) {
        fclose(stream);
        return false;
    }

    if (!fclose(stream))
        return true;

    gwyfile_set_error_errno(error);
    return false;
}

static size_t
gwyfile_file_size_upper_estimate(FILE *stream)
{
    int fd;
#if defined(_WIN32)
    long length;

    assert(stream);
    fd = _fileno(stream);
    length = _filelength(fd);
    if (length < 0)
        return SIZE_MAX;

    return (size_t)length;
#elif defined(_POSIX_VERSION)
    struct stat buf;

    assert(stream);
    fd = fileno(stream);
    if (fstat(fd, &buf) || !S_ISREG(buf.st_mode))
        return SIZE_MAX;

    return buf.st_size;
#else
    return SIZE_MAX;
#endif
}

/*!\fn GwyfileObject* gwyfile_read_file(const char *filename, GwyfileError **error)
 * \brief Reads a GWY file from a named file and returns its top-level object.
 *
 * This function handles opening and closing of the file for you, otherwise
 * it is very similar to gwyfile_fread().
 *
 * The file name is passed to the system fopen() function as given.  You may
 * want to consider using gwyfile_read_wfile() or opening the file yourself
 * and using gwyfile_fread() on MS Windows.
 *
 * \param filename Name of the file to write the GWY file to.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \return The reconstructed top-level data object, or \c NULL if the reading
 *         or reconstruction fails.
 */
GwyfileObject*
gwyfile_read_file(const char *filename,
                  GwyfileError **error)
{
    GwyfileObject *object;
    size_t max_size;
    FILE *stream;

    assert(filename);

#ifndef _WIN32
    if (!(stream = fopen(filename, "rb"))) {
        gwyfile_set_error_errno(error);
        return false;
    }
#else
    if (fopen_s(&stream, filename, "rb") != 0) {
        gwyfile_set_error_errno(error);
        return false;
    }
#endif

    max_size = gwyfile_file_size_upper_estimate(stream);
    object = gwyfile_fread(stream, max_size, error);
    fclose(stream);

    return object;
}

#ifdef _WIN32
/*!\fn bool gwyfile_write_wfile(GwyfileObject *object, const wchar_t *filename, GwyfileError **error)
 * \brief Writes a GWY file to a named file
 *        (wide-character variant).
 * \note This function is available only on MS Windows.
 *
 * This function is completely identical to gwyfile_write_file() aside from
 * using _wfopen() to open the file instead of fopen().  There is no difference
 * in handling of the file data itself.
 *
 * \param object The top-level GWY file data object for the file.  Normally
 *               it is a GwyContainer.
 * \param filename Name of the file to write the GWY file to.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \return \c true if the writing succeeded.
 */
bool
gwyfile_write_wfile(GwyfileObject *object,
                    const wchar_t *filename,
                    GwyfileError **error)
{
    static const wchar_t mode[] = { 'w', 'b', 0 };
    FILE *stream;

    assert(object);
    assert(filename);

    if (!(stream = _wfopen(filename, mode))) {
        gwyfile_set_error_errno(error);
        return false;
    }

    if (!gwyfile_fwrite(object, stream, error)) {
        fclose(stream);
        return false;
    }

    if (fclose(stream) == 0)
        return true;

    gwyfile_set_error_errno(error);
    return false;
}

/*!\fn GwyfileObject* gwyfile_read_wfile(const wchar_t *filename, GwyfileError **error)
 * \brief Reads a GWY file from a named file and returns its top-level object
 *        (wide-character variant).
 * \note This function is available only on MS Windows.
 *
 * This function is completely identical to gwyfile_read_file() aside from
 * using _wfopen() to open the file instead of fopen().  There is no difference
 * in handling of the file data itself.
 *
 * \param filename Name of the file to write the GWY file to.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \return The reconstructed top-level data object, or \c NULL if the reading
 *         or reconstruction fails.
 */
GwyfileObject*
gwyfile_read_wfile(const wchar_t *filename,
                   GwyfileError **error)
{
    static const wchar_t mode[] = { 'r', 'b', 0 };
    GwyfileObject *object;
    size_t max_size;
    FILE *stream;

    assert(filename);

    if (!(stream = _wfopen(filename, mode))) {
        gwyfile_set_error_errno(error);
        return NULL;
    }
    max_size = gwyfile_file_size_upper_estimate(stream);
    object = gwyfile_fread(stream, max_size, error);
    fclose(stream);

    return object;
}
#endif

/*!\fn bool gwyfile_fwrite(GwyfileObject *object, FILE *stream, GwyfileError **error)
 * \brief Writes a GWY file to a stdio stream.
 *
 * This function differs from gwyfile_object_fwrite() only by adding the
 * magic file header that preceeds the top-level object in a GWY file.
 *
 * The stream does not have to be seekable.  This makes the function useful
 * for writing GWY files to pipes and the standard output.  Otherwise it is
 * usually easier to use gwyfile_write_file().
 *
 * \param object The top-level GWY file data object for the file.  Normally
 *               it is a GwyContainer.
 * \param stream C stdio stream to write the GWY file to.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \return \c true if the writing succeeded.
 */
bool
gwyfile_fwrite(GwyfileObject *object,
               FILE *stream,
               GwyfileError **error)
{
    unsigned int len = GWYFILE_MAGIC_LEN;

    assert(stream);
    if (fwrite(GWYFILE_MAGIC_HEADER2, 1, len, stream) != len) {
        gwyfile_set_error_errno(error);
        return false;
    }

    /* Don't care about object here, let gwyfile_object_fwrite() care. */
    return gwyfile_object_fwrite(object, stream, error);
}

/*!\fn GwyfileObject* gwyfile_fread(FILE *stream, size_t max_size, GwyfileError **error)
 * \brief Reads a GWY file from a stdio stream and returns the top-level object.
 *
 * This function differs from gwyfile_object_fread() only by reading and
 * checking the magic file header that preceeds the top-level object in a GWY
 * file.
 *
 * The stream does not have to be seekable.  This makes the function useful
 * for reading GWY files from pipes and the standard input.  Otherwise it is
 * usually easier to use gwyfile_read_file().
 *
 * On success, the position indicator in \p stream will be pointed after the
 * end of the top-level object.
 *
 * On failure, the position indicator state in \p stream is undefined.
 *
 * The maximum number of bytes to read is given by \p max_size which is of type
 * <tt>size_t</tt>, however, be aware that sizes in GWY files are only 32bit.
 * So any value that does not fit into a 32bit integer means the same as
 * <tt>SIZE_MAX</tt>.
 *
 * If reading more than \p max_size bytes would be required to reconstruct the
 * top-level object, the function fails with
 * GwyfileErrorCode::GWYFILE_ERROR_CONFINEMENT error in the
 * GwyfileErrorDomain::GWYFILE_ERROR_DOMAIN_DATA domain.
 *
 * \param stream C stdio stream to read the GWY file from.
 * \param max_size Maximum number of bytes to read.  Pass \c SIZE_MAX for
 *                 unconstrained reading.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \return The reconstructed top-level data object, or \c NULL if the reading
 *         or reconstruction fails.
 */
GwyfileObject*
gwyfile_fread(FILE *stream,
              size_t max_size,
              GwyfileError **error)
{
    char magic[GWYFILE_MAGIC_LEN];

    assert(stream);
    if (!gwyfile_check_size(&max_size, GWYFILE_MAGIC_LEN, error,
                            "magic file header"))
        return NULL;

    if (fread(magic, 1, GWYFILE_MAGIC_LEN, stream) != GWYFILE_MAGIC_LEN) {
        gwyfile_set_error_fread(error, stream, "magic file header");
        return NULL;
    }
    if (memcmp(magic, GWYFILE_MAGIC_HEADER2, GWYFILE_MAGIC_LEN)) {
        gwyfile_set_error(error, GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_MAGIC,
                          "Wrong magic file header "
                          "0x%02x 0x%02x 0x%02x 0x%02x.",
                          magic[0], magic[1], magic[2], magic[3]);
        return NULL;
    }

    return gwyfile_object_fread(stream, max_size, error);
}

/*!\fn GwyfileObject* gwyfile_object_new(const char *name, ...)
 * \brief Creates a new GWY file object.
 *
 * The object type name must be a valid identifier formed from ASCII letters,
 * digits and underscores.  Usually, it is the name of a serialisable Gwyddion
 * object such as <tt>"GwyDataField"</tt>.  However, if you use GWY files to
 * store other hierarchical data (not intended for Gwyddion) this does not have
 * to hold.
 *
 * Each item must have a unique name.
 *
 * The created object will consume all the items and will take care of freeing
 * them.  You must not touch them any more after this function returns.
 *
 * \param name Object type name.  It determines what data items are expected
 *             inside.
 * \param ... A <tt>NULL</tt>-terminated list of items to add to the object.
 * \return The newly created GWY file object.
 * \sa gwyfile_object_newv
 */
GwyfileObject*
gwyfile_object_new(const char *name,
                   ...)
{
    GwyfileObject *object = gwyfile_object_new_internal(name, false);
    va_list ap;
    GwyfileItem *item;
    bool unique;

    assert(object);

    va_start(ap, name);
    while ((item = va_arg(ap, GwyfileItem*))) {
        assert(item);
        gwyfile_object_append(object, item);
    }
    va_end(ap);

    unique = !gwyfile_object_find_duplicate_item(object);
    assert(unique);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_newv(const char *name, GwyfileItem **items, unsigned int nitems)
 * \brief Creates a new GWY file object.
 *
 * The object type name must be a valid identifier formed from ASCII letters,
 * digits and underscores.  Usually, it is the name of a serialisable Gwyddion
 * object such as <tt>"GwyDataField"</tt>.  However, if you use GWY files to
 * store other hierarchical data (not intended for Gwyddion) this does not have
 * to hold.
 *
 * Each item must have a unique name.
 *
 * The created object will consume all the items and will take care of freeing
 * them.  You must not touch them any more after this function returns.
 *
 * The array \p items, however, remains owned by the caller.
 *
 * \param name Object type name.
 * \param items Array of items to add to the object.
 * \param nitems Number of items in \p items.
 * \return The newly created GWY file object.
 * \sa gwyfile_object_new
 */
GwyfileObject*
gwyfile_object_newv(const char *name,
                    GwyfileItem **items,
                    unsigned int nitems)
{
    GwyfileObject *object = gwyfile_object_new_internal(name, false);
    unsigned int i;
    bool unique;

    assert(object);

    for (i = 0; i < nitems; i++) {
        assert(items[i]);
        gwyfile_object_append(object, items[i]);
    }

    unique = !gwyfile_object_find_duplicate_item(object);
    assert(unique);

    return object;
}

/* If you pass zero @n it means this is allowed and we consume the arguments
 * but do not create any data item.  Return value indicates whether we consumed
 * argument, not whether an item was added. */
static bool
gwyfile_object_new_handle_data_items(GwyfileObject *object,
                                     const char *name,
                                     const char *basename, uint32_t n,
                                     va_list *ap)
{
    unsigned int blen = strlen(basename);
    unsigned int len = strlen(name);
    GwyfileItem *item;
    bool added;

    if (len < blen || strncmp(name, basename, blen))
        return false;

    if (len == blen) {
        double *data = va_arg(*ap, double*);
        if (!n)
            return true;
        item = gwyfile_item_new_double_array(basename, data, n);
    }
    else if (gwyfile_strequal(name + blen, "(copy)")) {
        const double *data = va_arg(*ap, const double*);
        if (!n)
            return true;
        item = gwyfile_item_new_double_array_copy(basename, data, n);
    }
    else if (gwyfile_strequal(name + blen, "(const)")) {
        const double *data = va_arg(*ap, const double*);
        if (!n)
            return true;
        item = gwyfile_item_new_double_array_const(basename, data, n);
    }
    else
        return false;

    added = gwyfile_object_add(object, item);
    assert(added);
    return true;
}

/*!\fn GwyfileObject* gwyfile_object_new_datafield(int xres, int yres, double xreal, double yreal, ...)
 * \brief Creates a new GWY file \c GwyDataField object.
 *
 * A \c GwyDataField must also have an item <tt>"data"</tt> containing the data
 * that you must add explicitly, depending on how you want to handle the
 * memory.  It can be added by passing one of the additional items listed
 * below.  Additional items can be also added using the standard function
 * gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size \p xres × \p yres.  It will
 * be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size \p xres × \p yres.  It
 * will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size \p xres × \p yres.
 * It will be just used the object.  You must ensure the array exists during
 * the entire lifetime of the created object.
 *
 * \arg <tt>"xoff"</tt> – double.  Horizontal offset of the top-left corner in
 * physical units.
 *
 * \arg <tt>"yoff"</tt> – double.  Vertical offset of the top-left corner in
 * physical units.
 *
 * \arg <tt>"si_unit_xy"</tt> – string.  Physical units of lateral dimensions,
 * base SI units, e.g. <tt>"m"</tt>.  It will be used to create a
 * contained \c GwySIUnit object item.
 *
 * \arg <tt>"si_unit_z"</tt> – string.  Physical units of field values, base
 * SI units, e.g.  <tt>"A"</tt>.  It will be used to create a contained
 * \c GwySIUnit object item.
 *
 * \param xres Horizontal dimension in pixels (positive integer).
 * \param yres Vertical dimension in pixels (positive integer).
 * \param xreal Horizontal size in physical units (positive number).
 * \param yreal Vertical size in physical units (positive number).
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_datafield(int xres,
                             int yres,
                             double xreal,
                             double yreal,
                             ...)
{
    GwyfileObject *object;
    int n = xres*yres;
    const char *name;
    va_list ap;

    assert(xres > 0);
    assert(yres > 0);
    object = gwyfile_object_new("GwyDataField",
                                gwyfile_item_new_int32("xres", xres),
                                gwyfile_item_new_int32("yres", yres),
                                gwyfile_item_new_double("xreal", xreal),
                                gwyfile_item_new_double("yreal", yreal),
                                NULL);

    va_start(ap, yreal);
    while ((name = va_arg(ap, const char*))) {
        GwyfileItem *item = NULL;
        bool added;

        if (gwyfile_object_new_handle_data_items(object, name, "data", n, &ap))
            continue;

        if (gwyfile_strequal(name, "si_unit_xy")
            || gwyfile_strequal(name, "si_unit_z")) {
            const char *unitstr = va_arg(ap, const char*);
            item = gwyfile_item_new_object(name,
                                           gwyfile_object_new_siunit(unitstr));
        }
        else if (gwyfile_strequal(name, "xoff")
                 || gwyfile_strequal(name, "yoff")) {
            double offset = va_arg(ap, double);
            item = gwyfile_item_new_double(name, offset);
        }
        else {
            /* We might want to just ignore unknown additional items but it
             * messes up our stack. */
            assert(!"Reached");
            break;
        }

        added = gwyfile_object_add(object, item);
        assert(added);
    }
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_dataline(int res, double real, ...)
 * \brief Creates a new GWY file \c GwyDataLine object.
 *
 * A \c GwyDataLine must also have an item <tt>"data"</tt> containing the data
 * that you must add explicitly, depending on how you want to handle the
 * memory.  It can be added by passing one of the additional items listed
 * below.  Additional items can be also added using the standard function
 * gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size \p res.  It will
 * be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size \p res.  It
 * will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size \p res.  It
 * will be just used the object.  You must ensure the array exists during the
 * entire lifetime of the created object.
 *
 * \arg <tt>"off"</tt> – double.  Offset of the left edge in physical units.
 *
 * \arg <tt>"si_unit_x"</tt> – string.  Physical units of lateral dimensions,
 * base SI units, e.g. <tt>"m"</tt>.  It will be used to create a
 * contained \c GwySIUnit object item.
 *
 * \arg <tt>"si_unit_y"</tt> – string.  Physical units of line values, base
 * SI units, e.g.  <tt>"A"</tt>.  It will be used to create a contained
 * \c GwySIUnit object item.
 *
 * \param res Dimension in pixels (positive integer).
 * \param real Size in physical units (positive number).
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_dataline(int res,
                            double real,
                            ...)
{
    GwyfileObject *object;
    const char *name;
    va_list ap;

    assert(res > 0);
    object = gwyfile_object_new("GwyDataLine",
                                gwyfile_item_new_int32("res", res),
                                gwyfile_item_new_double("real", real),
                                NULL);

    va_start(ap, real);
    while ((name = va_arg(ap, const char*))) {
        GwyfileItem *item = NULL;
        bool added;

        if (gwyfile_object_new_handle_data_items(object, name, "data", res,
                                                 &ap))
            continue;

        if (gwyfile_strequal(name, "si_unit_x")
            || gwyfile_strequal(name, "si_unit_y")) {
            const char *unitstr = va_arg(ap, const char*);
            item = gwyfile_item_new_object(name,
                                           gwyfile_object_new_siunit(unitstr));
        }
        else if (gwyfile_strequal(name, "off")) {
            double offset = va_arg(ap, double);
            item = gwyfile_item_new_double(name, offset);
        }
        else {
            /* We might want to just ignore unknown additional items but it
             * messes up our stack. */
            assert(!"Reached");
            break;
        }

        added = gwyfile_object_add(object, item);
        assert(added);
    }
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_brick(int xres, int yres, int zres, double xreal, double yreal, double zreal, ...)
 * \brief Creates a new GWY file \c GwyBrick object.
 *
 * A \c GwyBrick must also have an item <tt>"data"</tt> containing the data
 * that you must add explicitly, depending on how you want to handle the
 * memory.  It can be added by passing one of the additional items listed
 * below.  Additional items can be also added using the standard function
 * gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size \p xres × \p yres × \p zres.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size \p xres × \p yres ×
 * \p zres.  It will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size \p xres × \p yres ×
 * \p zres.  It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * \arg <tt>"xoff"</tt> – double.  Horizontal offset of the top-left upper
 * corner in physical units.
 *
 * \arg <tt>"yoff"</tt> – double.  Vertical offset of the top-left upper corner
 * in physical units.
 *
 * \arg <tt>"zoff"</tt> – double.  Depth-wise offset of the top-left upper
 * corner in physical units.
 *
 * \arg <tt>"si_unit_x"</tt> – string.  Physical units of horizontal
 * dimensions, base SI units, e.g. <tt>"m"</tt>.  It will be used to create a
 * contained \c GwySIUnit object item.
 *
 * \arg <tt>"si_unit_y"</tt> – string.  Physical units of vertical
 * dimensions, base SI units, e.g. <tt>"m"</tt>.  It will be used to create a
 * contained \c GwySIUnit object item.
 *
 * \arg <tt>"si_unit_z"</tt> – string.  Physical units of vertical
 * dimensions, base SI units, e.g. <tt>"m"</tt>.  It will be used to create a
 * contained \c GwySIUnit object item.
 *
 * \arg <tt>"si_unit_w"</tt> – string.  Physical units of brick values, base
 * SI units, e.g.  <tt>"A"</tt>.  It will be used to create a contained
 * \c GwySIUnit object item.
 *
 * \arg <tt>"calibration"</tt> – object of type \c GwyDataLine, with resolution
 * equal to \c zres that represents a non-linear z-axis calibration.  It will
 * be consumed by the created object.
 *
 * \param xres Horizontal dimension in pixels (positive integer).
 * \param yres Vertical dimension in pixels (positive integer).
 * \param zres Depth-wise dimension in pixels (positive integer).
 * \param xreal Horizontal size in physical units (positive number).
 * \param yreal Vertical size in physical units (positive number).
 * \param zreal Depth-wise size in physical units (positive number).
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_brick(int xres,
                         int yres,
                         int zres,
                         double xreal,
                         double yreal,
                         double zreal,
                         ...)
{
    GwyfileObject *object;
    const char *name;
    int n = xres*yres*zres;
    va_list ap;

    assert(xres > 0);
    assert(yres > 0);
    assert(zres > 0);
    object = gwyfile_object_new("GwyBrick",
                                gwyfile_item_new_int32("xres", xres),
                                gwyfile_item_new_int32("yres", yres),
                                gwyfile_item_new_int32("zres", zres),
                                gwyfile_item_new_double("xreal", xreal),
                                gwyfile_item_new_double("yreal", yreal),
                                gwyfile_item_new_double("zreal", zreal),
                                NULL);

    va_start(ap, zreal);
    while ((name = va_arg(ap, const char*))) {
        GwyfileItem *item = NULL;
        bool added;

        if (gwyfile_object_new_handle_data_items(object, name, "data", n, &ap))
            continue;

        if (gwyfile_strequal(name, "si_unit_x")
            || gwyfile_strequal(name, "si_unit_y")
            || gwyfile_strequal(name, "si_unit_z")
            || gwyfile_strequal(name, "si_unit_w")) {
            const char *unitstr = va_arg(ap, const char*);
            item = gwyfile_item_new_object(name,
                                           gwyfile_object_new_siunit(unitstr));
        }
        else if (gwyfile_strequal(name, "xoff")
                 || gwyfile_strequal(name, "yoff")
                 || gwyfile_strequal(name, "zoff")) {
            double offset = va_arg(ap, double);
            item = gwyfile_item_new_double(name, offset);
        }
        else if (gwyfile_strequal(name, "calibration")) {
            GwyfileObject *calobj = va_arg(ap, GwyfileObject*);
            item = gwyfile_item_new_object(name, calobj);
        }
        else {
            /* We might want to just ignore unknown additional items but it
             * messes up our stack. */
            assert(!"Reached");
            break;
        }

        added = gwyfile_object_add(object, item);
        assert(added);
    }
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_surface(int n, ...)
 * \brief Creates a new GWY file \c GwySurface object.
 *
 * A \c GwySurface must also have an item <tt>"data"</tt> containing the data
 * that you must add explicitly, depending on how you want to handle the
 * memory.  It can be added by passing one of the additional items listed
 * below.  Additional items can be also added using the standard function
 * gwyfile_object_add().
 *
 * The size of the data is three times the number of points.  The data consits
 * of triplets (x, y, z) representing the coordinates of individual data
 * points, concatenated to a single continuous block of doubles.
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size 3 × \p n.  It will
 * be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size 3 × \p n.  It
 * will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size 3 × \p n.
 * It will be just used the object.  You must ensure the array exists during
 * the entire lifetime of the created object.
 *
 * \arg <tt>"si_unit_xy"</tt> – string.  Physical units of X and Y coordinates,
 * base SI units, e.g. <tt>"m"</tt>.  It will be used to create a
 * contained \c GwySIUnit object item.
 *
 * \arg <tt>"si_unit_z"</tt> – string.  Physical units of Z values, base
 * SI units, e.g.  <tt>"A"</tt>.  It will be used to create a contained
 * \c GwySIUnit object item.
 *
 * \param n The number of points in the XYZ surface.
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 * \since 1.2
 */
GwyfileObject*
gwyfile_object_new_surface(int n,
                           ...)
{
    GwyfileObject *object;
    const char *name;
    va_list ap;

    assert(n > 0);
    object = gwyfile_object_new("GwySurface", NULL);

    va_start(ap, n);
    while ((name = va_arg(ap, const char*))) {
        GwyfileItem *item = NULL;
        bool added;

        if (gwyfile_object_new_handle_data_items(object, name, "data", 3*n,
                                                 &ap))
            continue;

        if (gwyfile_strequal(name, "si_unit_xy")
            || gwyfile_strequal(name, "si_unit_z")) {
            const char *unitstr = va_arg(ap, const char*);
            item = gwyfile_item_new_object(name,
                                           gwyfile_object_new_siunit(unitstr));
        }
        else {
            /* We might want to just ignore unknown additional items but it
             * messes up our stack. */
            assert(!"Reached");
            break;
        }

        added = gwyfile_object_add(object, item);
        assert(added);
    }
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_spectra(int ncurves, GwyfileObject **curves, ...)
 * \brief Creates a new GWY file \c GwySpectra object.
 *
 * A \c GwySpectra must also have an item <tt>"coords"</tt> containing the real
 * spectra coordinates that you must add explicitly, depending on how you want
 * to handle the memory.  It can be added by passing one of the additional
 * items listed below.  Additional items can be also added using the standard
 * function gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"coords"</tt> – array of doubles of size 2\p ncurves.  It will
 * be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"coords(copy)"</tt> – array of doubles of size 2\p ncurves.  It
 * will be copied by the object.
 *
 * \arg <tt>"coords(const)"</tt> – array of doubles of size 2\p ncurves.  It
 * will be just used the object.  You must ensure the array exists during the
 * entire lifetime of the created object.
 *
 * \arg <tt>"title"</tt> – string.  Title of the spectra.  It will be copied by
 * the object.
 *
 * \arg <tt>"spec_xlabel"</tt> – string.  Label of the spectra curve abscissae.
 * It will be copied by the object.
 *
 * \arg <tt>"spec_ylabel"</tt> – string.  Label of the spectra curve ordinates.
 * It will be copied by the object.
 *
 * \arg <tt>"si_unit_xy"</tt> – string.  Physical units of lateral dimensions,
 * base SI units, e.g. <tt>"m"</tt>.  It will be used to create a
 * contained \c GwySIUnit object item.
 *
 * \arg <tt>"selected"</tt> – array of 32bit integers with
 * ceil(<tt>ncurves</tt>/32) elements describing which spectra are currently
 * selected.  A set (one) bit means selected spectrum, unset (zero) means the
 * spectrum is not selected.  The array will be copied by the object.
 *
 * \param ncurves Number of spectra curves (positive integer).
 * \param curves Array of \p ncurves <tt>GwySpectra</tt> objects.  Both the
 *               array and the objects within will be consumed by the function
 *               that will take care of freeing them later.
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_spectra(int ncurves,
                           GwyfileObject **curves,
                           ...)
{
    GwyfileObject *object;
    const char *name;
    va_list ap;

    assert(ncurves > 0);
    assert(curves);
    object = gwyfile_object_new("GwySpectra",
                                gwyfile_item_new_object_array("data",
                                                              curves, ncurves),
                                NULL);

    va_start(ap, curves);
    while ((name = va_arg(ap, const char*))) {
        GwyfileItem *item = NULL;
        bool added;

        if (gwyfile_object_new_handle_data_items(object, name,
                                                 "coords", 2*ncurves, &ap))
            continue;

        if (gwyfile_strequal(name, "si_unit_xy")) {
            const char *unitstr = va_arg(ap, const char*);
            item = gwyfile_item_new_object(name,
                                           gwyfile_object_new_siunit(unitstr));
        }
        else if (gwyfile_strequal(name, "title")
                 || gwyfile_strequal(name, "spec_xlabel")
                 || gwyfile_strequal(name, "spec_ylabel")) {
            const char *str = va_arg(ap, const char*);
            item = gwyfile_item_new_string_copy(name, str);
        }
        else if (gwyfile_strequal(name, "selected")) {
            const int32_t *selected = va_arg(ap, const int32_t*);
            item = gwyfile_item_new_int32_array_copy(name, selected,
                                                     (ncurves + 31)/32);
        }
        else {
            /* We might want to just ignore unknown additional items but it
             * messes up our stack. */
            assert(!"Reached");
            break;
        }

        added = gwyfile_object_add(object, item);
        assert(added);
    }
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_graphcurvemodel(int ndata, ...)
 * \brief Creates a new GWY file \c GwyGraphCurveModel object.
 *
 * A \c GwyGraphCurveModel must also have items <tt>"xdata"</tt> and
 * <tt>"ydata"</tt> containing the data that you must add explicitly, depending
 * on how you want to handle the memory.  They can be added by passing one of
 * the additional items listed below.  Additional items can be also added using
 * the standard function gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"xdata"</tt> – array of doubles of size \p ndata.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"xdata(copy)"</tt> – array of doubles of size \p ndata.
 * It will be copied by the object.
 *
 * \arg <tt>"xdata(const)"</tt> – array of doubles of size \p ndata.
 * It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * \arg <tt>"ydata"</tt> – array of doubles of size \p ndata.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"ydata(copy)"</tt> – array of doubles of size \p ndata.
 * It will be copied by the object.
 *
 * \arg <tt>"ydata(const)"</tt> – array of doubles of size \p ndata.
 * It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * \arg <tt>"description"</tt> – string.  Curve label.  It will be copied by
 * the object.
 *
 * \arg <tt>"type"</tt> – 32bit integer.  See \c GwyGraphCurveType in
 * Gwyddion API documentation for the list of curve modes.
 *
 * \arg <tt>"point_type"</tt> – 32bit integer.  See \c GwyGraphPointType in
 * Gwyddion API documentation for the list of point types.
 *
 * \arg <tt>"line_style"</tt> – 32bit integer.  See \c GdkLineStyle in
 * Gtk+ 2 API documentation for the list of line styles.
 *
 * \arg <tt>"point_size"</tt> – 32bit integer.  Point size.
 *
 * \arg <tt>"line_size"</tt> – 32bit integer.  Line width.
 *
 * \arg <tt>"color.red"</tt> – double.  Red colour component from the
 * interval [0, 1].
 *
 * \arg <tt>"color.green"</tt> – double.  Green colour component from the
 * interval [0, 1].
 *
 * \arg <tt>"color.blue"</tt> – double.  Blue colour component from the
 * interval [0, 1].
 *
 * \param ndata Number of data points (positive integer).
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_graphcurvemodel(int ndata, ...)
{
    GwyfileObject *object;
    const char *name;
    va_list ap;

    assert(ndata > 0);
    object = gwyfile_object_new("GwyGraphCurveModel", NULL);

    va_start(ap, ndata);
    while ((name = va_arg(ap, const char*))) {
        GwyfileItem *item = NULL;
        bool added;

        if (gwyfile_object_new_handle_data_items(object, name, "xdata", ndata,
                                                 &ap))
            continue;
        if (gwyfile_object_new_handle_data_items(object, name, "ydata", ndata,
                                                 &ap))
            continue;

        if (gwyfile_strequal(name, "description")) {
            const char *description = va_arg(ap, const char*);
            item = gwyfile_item_new_string_copy(name, description);
        }
        else if (gwyfile_strequal(name, "type")
                 || gwyfile_strequal(name, "point_type")
                 || gwyfile_strequal(name, "line_style")
                 || gwyfile_strequal(name, "point_size")
                 || gwyfile_strequal(name, "line_size")) {
            int32_t type = va_arg(ap, int32_t);
            item = gwyfile_item_new_int32(name, type);
        }
        else if (gwyfile_strequal(name, "color.red")
                 || gwyfile_strequal(name, "color.green")
                 || gwyfile_strequal(name, "color.blue")) {
            double colorcomp = va_arg(ap, double);
            item = gwyfile_item_new_double(name, colorcomp);
        }
        else {
            /* We might want to just ignore unknown additional items but it
             * messes up our stack. */
            assert(!"Reached");
            break;
        }

        added = gwyfile_object_add(object, item);
        assert(added);
    }
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_graphmodel(int ncurves, ...)
 * \brief Creates a new GWY file \c GwyGraphModel object.
 *
 * A \c GwyGraphModel must also have item <tt>"curves"</tt> containing the data
 * that you must add explicitly.  If you pass \p ncurves as zero, the item
 * is not created at all and you should use gwyfile_object_add() afterward.
 * If you pass non-zero \p ncurves you should also pass an additional
 * <tt>"curves"</tt> item with the specified number of curves.
 *
 * Possible additional items:
 * \arg <tt>"curves"</tt> – ::_GwyfileObject* array with \c ncurves items.  May
 * only be passed if \p ncurves is non-zero.  Both the array and the objects
 * inside become owned by the newly created object as with
 * gwyfile_item_new_object_array().
 *
 * \arg <tt>"title"</tt> – string.  Graph title.  It will be copied by the
 * object.
 *
 * \arg <tt>"top_label"</tt> – string.  Top axis label.  It will be copied by
 * the object.
 *
 * \arg <tt>"left_label"</tt> – string.  Left axis label.  It will be copied by
 * the object.
 *
 * \arg <tt>"right_label"</tt> – string.  Right axis label.  It will be copied
 * by the object.
 *
 * \arg <tt>"bottom_label"</tt> – string.  Bottom axis label.  It will be
 * copied by the object.
 *
 * \arg <tt>"x_unit"</tt> – string.  Physical units of abscissa, in base SI
 * units, e.g. <tt>"m"</tt>.  It will be used to create a contained \c
 * GwySIUnit object item.
 *
 * \arg <tt>"y_unit"</tt> – string.  Physical units of ordinate, in base SI
 * units, e.g.  <tt>"A"</tt>.  It will be used to create a contained \c
 * GwySIUnit object item.
 *
 * \arg <tt>"x_min"</tt> – double.  Minimum value of abscissa.  Effective
 * if <tt>"x_min_set"</tt> is <tt>true</tt>.
 *
 * \arg <tt>"x_min_set"</tt> – boolean.  Whether the minimum value of abscissa
 * is set explicitly (i.e. user-requested).
 *
 * \arg <tt>"x_max"</tt> – double.  Maximum value of abscissa.  Effective
 * if <tt>"x_max_set"</tt> is <tt>true</tt>.
 *
 * \arg <tt>"x_max_set"</tt> – boolean.  Whether the maximum value of abscissa
 * is set explicitly (i.e. user-requested).
 *
 * \arg <tt>"y_min"</tt> – double.  Minimum value of ordinate.  Effective
 * if <tt>"y_min_set"</tt> is <tt>true</tt>.
 *
 * \arg <tt>"y_min_set"</tt> – boolean.  Whether the minimum value of ordinate
 * is set explicitly (i.e. user-requested).
 *
 * \arg <tt>"y_max"</tt> – double.  Maximum value of ordinate.  Effective
 * if <tt>"y_max_set"</tt> is <tt>true</tt>.
 *
 * \arg <tt>"y_max_set"</tt> – boolean.  Whether the maximum value of ordinate
 * is set explicitly (i.e. user-requested).
 *
 * \arg <tt>"x_is_logarithmic"</tt> – boolean.  Whether abscissa is displayed
 * in logaritmic scale.
 *
 * \arg <tt>"y_is_logarithmic"</tt> – boolean.  Whether ordinate is displayed
 * in logaritmic scale.
 *
 * \arg <tt>"label.visible"</tt> – boolean.  Whether the graph key is visible.
 *
 * \arg <tt>"label.has_frame"</tt> – boolean.  Whether the graph key has a
 * frame.
 *
 * \arg <tt>"label.reverse"</tt> – boolean.  Whether the graph key should be
 * displayed with a reversed layout.
 *
 * \arg <tt>"label.frame_thickness"</tt> – 32bit integer.  Thickness of the
 * graph key frame.
 *
 * \arg <tt>"label.position"</tt> – 32bit integer.  See \c
 * GwyGraphLabelPosition in Gwyddion API documentation for the list of graph
 * label position types.
 *
 * \arg <tt>"grid-type"</tt> – 32bit integer.  See \c GwyGraphGridType in
 * Gwyddion API documentation for the list of graph grid types.  Note this
 * property has never been actually implemented in Gwyddion.
 *
 * \param ncurves Number of curves (non-negative integer).  If you pass zero
 *                you must not pass any <tt>"curves"</tt> additional item to
 *                this function.
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_graphmodel(int ncurves, ...)
{
    GwyfileObject *object;
    const char *name;
    va_list ap;

    assert(ncurves >= 0);
    object = gwyfile_object_new("GwyGraphModel", NULL);

    va_start(ap, ncurves);
    while ((name = va_arg(ap, const char*))) {
        GwyfileItem *item = NULL;
        bool added;

        if (gwyfile_strequal(name, "title")
            || gwyfile_strequal(name, "top_label")
            || gwyfile_strequal(name, "bottom_label")
            || gwyfile_strequal(name, "left_label")
            || gwyfile_strequal(name, "right_label")) {
            const char *label = va_arg(ap, const char*);
            item = gwyfile_item_new_string_copy(name, label);
        }
        else if (gwyfile_strequal(name, "x_is_logarithmic")
                 || gwyfile_strequal(name, "y_is_logarithmic")
                 || gwyfile_strequal(name, "x_min_set")
                 || gwyfile_strequal(name, "y_min_set")
                 || gwyfile_strequal(name, "x_max_set")
                 || gwyfile_strequal(name, "y_max_set")
                 || gwyfile_strequal(name, "label.reverse")
                 || gwyfile_strequal(name, "label.visible")
                 || gwyfile_strequal(name, "label.has_frame")) {
            bool setting = va_arg(ap, int);   /* Promotion */
            item = gwyfile_item_new_bool(name, setting);
        }
        else if (gwyfile_strequal(name, "x_min")
                 || gwyfile_strequal(name, "x_max")
                 || gwyfile_strequal(name, "y_min")
                 || gwyfile_strequal(name, "y_max")) {
            double value = va_arg(ap, double);
            item = gwyfile_item_new_double(name, value);
        }
        else if (gwyfile_strequal(name, "label.frame_thickness")
                 || gwyfile_strequal(name, "label.position")
                 || gwyfile_strequal(name, "grid-type")) {
            int32_t value = va_arg(ap, int);
            item = gwyfile_item_new_int32(name, value);
        }
        else if (gwyfile_strequal(name, "x_unit")
            || gwyfile_strequal(name, "y_unit")) {
            const char *unitstr = va_arg(ap, const char*);
            item = gwyfile_item_new_object(name,
                                           gwyfile_object_new_siunit(unitstr));
        }
        else if (gwyfile_strequal(name, "curves")) {
            GwyfileObject **curves = va_arg(ap, GwyfileObject**);
            item = gwyfile_item_new_object_array(name, curves, ncurves);
        }
        else {
            /* We might want to just ignore unknown additional items but it
             * messes up our stack. */
            assert(!"Reached");
            break;
        }

        added = gwyfile_object_add(object, item);
        assert(added);
    }
    va_end(ap);

    return object;
}

static GwyfileObject*
gwyfile_object_new_selection(const char *name, int nsel, int ncoord,
                             va_list *ap)
{
    GwyfileObject *object;
    GwyfileItem *item = NULL;
    bool added;
    int n = ncoord*nsel;

    assert(nsel >= 0);
    object = gwyfile_object_new(name, NULL);

    while ((name = va_arg(*ap, const char*))) {
        if (gwyfile_object_new_handle_data_items(object, name, "data", n, ap))
            continue;

        /* We might want to just ignore unknown additional items but it
         * messes up our stack. */
        assert(!"Reached");
    }

    item = gwyfile_item_new_int32("max", nsel);
    added = gwyfile_object_add(object, item);
    assert(added);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_selectionpoint(int nsel, ...)
 * \brief Creates a new GWY file \c GwySelectionPoint object.
 *
 * A non-empty \c GwySelectionPoint must also have item <tt>"data"</tt>
 * containing the coordinates that you must add explicitly, depending on how
 * you want to handle the memory.  They can be added by passing one of the
 * additional items listed below.  Additional items can be also added using the
 * standard function gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size 2 × \p nsel.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size 2 × \p nsel.
 * It will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size 2 × \p nsel.
 * It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * This constructor creates automatically a 32bit integer <tt>"max"</tt> item
 * with the same value as \p nsel.  This item specifies the maximum number of
 * shapes in the selection.  However, this number is usually changed to some
 * suitable value by Gwyddion tools.  Hence it is only created to ensure the
 * maximum number is at least the actual number of shapes.
 *
 * \param nsel Number of points in the selection.
 *             Zero is allowed, any data item is ignored then.
 *             Note that the number of coordinates is 2 × \p nsel.
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_selectionpoint(int nsel, ...)
{
    GwyfileObject *object;
    va_list ap;

    va_start(ap, nsel);
    object = gwyfile_object_new_selection("GwySelectionPoint", nsel, 2, &ap);
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_selectionline(int nsel, ...)
 * \brief Creates a new GWY file \c GwySelectionLine object.
 *
 * A non-empty \c GwySelectionLine must also have item <tt>"data"</tt>
 * containing the coordinates that you must add explicitly, depending on how
 * you want to handle the memory.  They can be added by passing one of the
 * additional items listed below.  Additional items can be also added using the
 * standard function gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size 4 × \p nsel.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size 4 × \p nsel.
 * It will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size 4 × \p nsel.
 * It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * This constructor creates automatically a 32bit integer <tt>"max"</tt> item
 * with the same value as \p nsel.  This item specifies the maximum number of
 * shapes in the selection.  However, this number is usually changed to some
 * suitable value by Gwyddion tools.  Hence it is only created to ensure the
 * maximum number is at least the actual number of shapes.
 *
 * \param nsel Number of lines in the selection.
 *             Zero is allowed, any data item is ignored then.
 *             Note that the number of coordinates is 4 × \p nsel.
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_selectionline(int nsel, ...)
{
    GwyfileObject *object;
    va_list ap;

    va_start(ap, nsel);
    object = gwyfile_object_new_selection("GwySelectionLine", nsel, 4, &ap);
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_selectionrectangle(int nsel, ...)
 * \brief Creates a new GWY file \c GwySelectionRectangle object.
 *
 * A non-empty \c GwySelectionRectangle must also have item <tt>"data"</tt>
 * containing the coordinates that you must add explicitly, depending on how
 * you want to handle the memory.  They can be added by passing one of the
 * additional items listed below.  Additional items can be also added using the
 * standard function gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size 4 × \p nsel.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size 4 × \p nsel.
 * It will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size 4 × \p nsel.
 * It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * This constructor creates automatically a 32bit integer <tt>"max"</tt> item
 * with the same value as \p nsel.  This item specifies the maximum number of
 * shapes in the selection.  However, this number is usually changed to some
 * suitable value by Gwyddion tools.  Hence it is only created to ensure the
 * maximum number is at least the actual number of shapes.
 *
 * \param nsel Number of rectangles in the selection.
 *             Zero is allowed, any data item is ignored then.
 *             Note that the number of coordinates is 4 × \p nsel.
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_selectionrectangle(int nsel, ...)
{
    GwyfileObject *object;
    va_list ap;

    va_start(ap, nsel);
    object = gwyfile_object_new_selection("GwySelectionRectangle", nsel, 4,
                                          &ap);
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_selectionellipse(int nsel, ...)
 * \brief Creates a new GWY file \c GwySelectionEllipse object.
 *
 * A non-empty \c GwySelectionEllipse must also have item <tt>"data"</tt>
 * containing the coordinates that you must add explicitly, depending on how
 * you want to handle the memory.  They can be added by passing one of the
 * additional items listed below.  Additional items can be also added using the
 * standard function gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size 4 × \p nsel.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size 4 × \p nsel.
 * It will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size 4 × \p nsel.
 * It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * This constructor creates automatically a 32bit integer <tt>"max"</tt> item
 * with the same value as \p nsel.  This item specifies the maximum number of
 * shapes in the selection.  However, this number is usually changed to some
 * suitable value by Gwyddion tools.  Hence it is only created to ensure the
 * maximum number is at least the actual number of shapes.
 *
 * \param nsel Number of ellipses in the selection.
 *             Zero is allowed, any data item is ignored then.
 *             Note that the number of coordinates is 4 × \p nsel.
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_selectionellipse(int nsel, ...)
{
    GwyfileObject *object;
    va_list ap;

    va_start(ap, nsel);
    object = gwyfile_object_new_selection("GwySelectionEllipse", nsel, 4, &ap);
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_selectionlattice(int nsel, ...)
 * \brief Creates a new GWY file \c GwySelectionLattice object.
 *
 * A non-empty \c GwySelectionLattice must also have item <tt>"data"</tt>
 * containing the coordinates that you must add explicitly, depending on how
 * you want to handle the memory.  They can be added by passing one of the
 * additional items listed below.  Additional items can be also added using the
 * standard function gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size 4 × \p nsel.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size 4 × \p nsel.
 * It will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size 4 × \p nsel.
 * It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * This constructor creates automatically a 32bit integer <tt>"max"</tt> item
 * with the same value as \p nsel.  This item specifies the maximum number of
 * shapes in the selection.  However, this number is usually changed to some
 * suitable value by Gwyddion tools.  Hence it is only created to ensure the
 * maximum number is at least the actual number of shapes.
 *
 * \param nsel Number of lattices in the selection.
 *             Zero is allowed, any data item is ignored then.
 *             Note that the number of coordinates is 4 × \p nsel.
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_selectionlattice(int nsel, ...)
{
    GwyfileObject *object;
    va_list ap;

    va_start(ap, nsel);
    object = gwyfile_object_new_selection("GwySelectionLattice", nsel, 4, &ap);
    va_end(ap);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_selectionaxis(int nsel, int orientation, ...)
 * \brief Creates a new GWY file \c GwySelectionAxis object.
 *
 * A non-empty \c GwySelectionAxis must also have item <tt>"data"</tt>
 * containing the coordinates that you must add explicitly, depending on how
 * you want to handle the memory.  They can be added by passing one of the
 * additional items listed below.  Additional items can be also added using the
 * standard function gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size \p nsel.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size \p nsel.
 * It will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size \p nsel.
 * It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * This constructor creates automatically a 32bit integer <tt>"max"</tt> item
 * with the same value as \p nsel.  This item specifies the maximum number of
 * shapes in the selection.  However, this number is usually changed to some
 * suitable value by Gwyddion tools.  Hence it is only created to ensure the
 * maximum number is at least the actual number of shapes.
 *
 * \param nsel Number of axes in the selection.
 *             Zero is allowed, any data item is ignored then.
 * \param orientation Axis orientation.  See \c GwyOrientation in
 *                    Gwyddion API documentation for description.
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 */
GwyfileObject*
gwyfile_object_new_selectionaxis(int nsel, int orientation, ...)
{
    GwyfileObject *object;
    GwyfileItem *item;
    bool added;
    va_list ap;

    va_start(ap, orientation);
    object = gwyfile_object_new_selection("GwySelectionAxis", nsel, 1, &ap);
    va_end(ap);

    item = gwyfile_item_new_int32("orientation", orientation);
    added = gwyfile_object_add(object, item);
    assert(added);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_selectionpath(int nsel, double slackness, bool closed, ...)
 * \brief Creates a new GWY file \c GwySelectionPath object.
 *
 * A non-empty \c GwySelectionPath must also have item <tt>"data"</tt>
 * containing the coordinates that you must add explicitly, depending on how
 * you want to handle the memory.  They can be added by passing one of the
 * additional items listed below.  Additional items can be also added using the
 * standard function gwyfile_object_add().
 *
 * Possible additional items:
 * \arg <tt>"data"</tt> – array of doubles of size 2 × \p nsel.
 * It will be consumed by the object which will take care of freeing it later.
 *
 * \arg <tt>"data(copy)"</tt> – array of doubles of size 2 × \p nsel.
 * It will be copied by the object.
 *
 * \arg <tt>"data(const)"</tt> – array of doubles of size 2 × \p nsel.
 * It will be just used the object.  You must ensure the array exists
 * during the entire lifetime of the created object.
 *
 * This constructor creates automatically a 32bit integer <tt>"max"</tt> item
 * with the same value as \p nsel.  This item specifies the maximum number of
 * shapes in the selection.  However, this number is usually changed to some
 * suitable value by Gwyddion tools.  Hence it is only created to ensure the
 * maximum number is at least the actual number of shapes.
 *
 * \param nsel Number of points in the selection.
 *             Zero is allowed, any data item is ignored then.
 * \param slackness Spline path slackness (number between 0 and √2).  See
 *                  \c GwySelectionPath in Gwyddion API documentation for
 *                  description.
 * \param closed Whether the path is closed (<tt>true</tt>) or open
 *               (<tt>false</tt>).
 * \param ... Additional data items specified as name, value pairs.
 *            Terminated by \c NULL.
 * \return The newly created GWY file data object.
 * \since 1.2
 */
GwyfileObject*
gwyfile_object_new_selectionpath(int nsel,
                                 double slackness,
                                 bool closed,
                                 ...)
{
    GwyfileObject *object;
    GwyfileItem *item;
    bool added;
    va_list ap;

    va_start(ap, closed);
    object = gwyfile_object_new_selection("GwySelectionPath", nsel, 2, &ap);
    va_end(ap);

    item = gwyfile_item_new_double("slackness", slackness);
    added = gwyfile_object_add(object, item);
    assert(added);

    item = gwyfile_item_new_bool("closed", closed);
    added = gwyfile_object_add(object, item);
    assert(added);

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_new_siunit(const char *unitstr)
 * \brief Creates a new GWY file \c GwySIUnit object.
 *
 * The unit string should represent an unprefixed SI unit such as
 * <tt>"m"</tt>, <tt>"A"</tt> or <tt>"N/m"</tt>.
 *
 * \param unitstr String representation of the SI unit (to be copied).
 * \return The newly created GWY file data object or <tt>NULL</tt>.
 */
GwyfileObject*
gwyfile_object_new_siunit(const char *unitstr)
{
    GwyfileObject *object;

    object = gwyfile_object_new("GwySIUnit",
                                gwyfile_item_new_string_copy("unitstr",
                                                             unitstr),
                                NULL);

    return object;
}

static bool
gwyfile_object_check_type(const GwyfileObject *object,
                          const char *objname,
                          GwyfileError **error)
{
    assert(object);
    assert(object->name);
    assert(objname);

    if (gwyfile_strequal(object->name, objname))
        return true;

    if (error) {
        char *path = gwyfile_format_path(object, NULL);
        gwyfile_set_error(error,
                          GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_OBJECT_NAME,
                          "Type of %s is not %s.", path, objname);
        free(path);
    }

    return false;
}

static GwyfileItem*
gwyfile_object_check_item(const GwyfileObject *object,
                          const char *name,
                          GwyfileItemType type,
                          GwyfileError **error)
{
    GwyfileItem *item;

    assert(object);
    assert(name);

    item = gwyfile_object_get_with_type(object, name, type);
    if (item)
        return item;

    if (error) {
        char *path = gwyfile_format_path(object, NULL);
        gwyfile_set_error(error,
                          GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_MISSING_ITEM,
                          "Object %s does not contain "
                          "mandatory item %s of type %d.",
                          path, name, type);
        free(path);
    }

    return NULL;
}

/* The name arguments may seem a bit strange.  We just don't want to do any
 * run-time string juggling when everything is known compile-time. */
static inline bool
gwyfile_object_get_handle_data_items(const GwyfileObject *object,
                                     const char *name,
                                     const char *getname,
                                     const char *takename,
                                     va_list *ap)
{
    GwyfileItem *item;

    if (gwyfile_strequal(name, getname)) {
        item = gwyfile_object_get_with_type(object, getname,
                                            GWYFILE_ITEM_DOUBLE_ARRAY);
        const double **value = va_arg(*ap, const double**);
        assert(value);
        *value = item ? gwyfile_item_get_double_array(item) : NULL;
        return true;
    }

    if (gwyfile_strequal(name, takename)) {
        item = gwyfile_object_get_with_type(object, getname,
                                            GWYFILE_ITEM_DOUBLE_ARRAY);
        double **value = va_arg(*ap, double**);
        assert(value);
        *value = item ? gwyfile_item_take_double_array(item) : NULL;
        return true;
    }

    return false;
}

static inline void
gwyfile_object_fill_int32(const GwyfileObject *object,
                          const char *name,
                          va_list *ap,
                          int32_t default_value)
{
    GwyfileItem *item = gwyfile_object_get_with_type(object, name,
                                                     GWYFILE_ITEM_INT32);
    int32_t *value = va_arg(*ap, int32_t*);

    assert(value);
    *value = item ? gwyfile_item_get_int32(item) : default_value;
}

static inline void
gwyfile_object_fill_bool(const GwyfileObject *object,
                         const char *name,
                         va_list *ap,
                         bool default_value)
{
    GwyfileItem *item = gwyfile_object_get_with_type(object, name,
                                                     GWYFILE_ITEM_BOOL);
    bool *value = va_arg(*ap, bool*);

    assert(value);
    *value = item ? gwyfile_item_get_bool(item) : default_value;
}

static inline void
gwyfile_object_fill_double(const GwyfileObject *object,
                           const char *name,
                           va_list *ap,
                           double default_value,
                           double min_value,
                           double max_value)
{
    GwyfileItem *item = gwyfile_object_get_with_type(object, name,
                                                     GWYFILE_ITEM_DOUBLE);
    double *value = va_arg(*ap, double*);

    assert(value);
    assert(default_value >= min_value);
    assert(default_value <= max_value);
    *value = item ? gwyfile_item_get_double(item) : default_value;
    if (!(*value >= min_value) || !(*value <= max_value))
        *value = default_value;
}

static inline void
gwyfile_object_fill_string(const GwyfileObject *object,
                           const char *name,
                           va_list *ap,
                           const char *default_value)
{
    GwyfileItem *item = gwyfile_object_get_with_type(object, name,
                                                     GWYFILE_ITEM_STRING);
    char **value = va_arg(*ap, char**);

    assert(value);
    *value = gwyfile_strdup(item
                            ? gwyfile_item_get_string(item)
                            : default_value);
}

static inline void
gwyfile_object_fill_siunit(const GwyfileObject *object,
                           const char *name,
                           va_list *ap)
{
    GwyfileItem *item;
    char **value = va_arg(*ap, char**);
    const char *unitstr = "";

    assert(value);
    if ((item = gwyfile_object_get_with_type(object, name,
                                             GWYFILE_ITEM_OBJECT))
        && (object = gwyfile_item_get_object(item))
        && gwyfile_strequal(object->name, "GwySIUnit")
        && (item = gwyfile_object_get_with_type(object, "unitstr",
                                                GWYFILE_ITEM_STRING))) {
        unitstr = gwyfile_item_get_string(item);
    }
    *value = gwyfile_strdup(unitstr);
}

static bool
gwyfile_object_datafield_check(const GwyfileObject *object,
                               GwyfileError **error)
{
    GwyfileItem *xres_item, *yres_item, *data_item;
    int xres, yres;
    uint32_t ndata;

    if (!gwyfile_object_check_type(object, "GwyDataField", error))
        return false;

    if (!(xres_item = gwyfile_object_check_item(object, "xres",
                                                GWYFILE_ITEM_INT32,
                                                error))
        || !(yres_item = gwyfile_object_check_item(object, "yres",
                                                   GWYFILE_ITEM_INT32,
                                                   error))
        || !(data_item = gwyfile_object_check_item(object, "data",
                                                   GWYFILE_ITEM_DOUBLE_ARRAY,
                                                   error)))
        return false;

    xres = gwyfile_item_get_int32(xres_item);
    yres = gwyfile_item_get_int32(yres_item);
    ndata = gwyfile_item_array_length(data_item);
    if (xres > 0
        && yres > 0
        && (uint32_t)xres == ndata/yres
        && (uint32_t)yres == ndata/xres
        && (uint32_t)xres * (uint32_t)yres == ndata)
        return true;

    if (error) {
        char *path = gwyfile_format_path(object, NULL);
        gwyfile_set_error(error,
                          GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_ARRAY_SIZE,
                          "Data array length %u of %s "
                          "does not match pixel dimensions %dx%d.",
                          ndata, path, xres, yres);
        free(path);
    }

    return false;
}

/*!\fn bool gwyfile_object_datafield_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file \c GwyDataField
 *        object.
 *
 * The function checks if the object type is actually <tt>"GwyDataField"</tt>
 * and if it contains sane data items.  Every \c GwyDataField must contain at
 * least the pixel resolutions <tt>"xres"</tt> and <tt>"yres"</tt> and a
 * matching array of doubles <tt>"data"</tt> of the corresponding size.
 *
 * If \p object does not seem to represent a valid \c GwyDataField object the
 * function fails, does not fill any output arguments (beside the error) and
 * returns <tt>false</tt>.
 *
 * All other items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value (e.g. NaN physical dimension).  Unknown additional items are simply
 * ignored.  The function does not fail in these cases and returns
 * <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"data"</tt> – array of doubles of size \p xres × \p yres.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size \p xres × \p yres.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \arg <tt>"xres"</tt> – 32bit integer.  Horizontal dimension in pixels.
 *
 * \arg <tt>"yres"</tt> – 32bit integer.  Vertical dimension in pixels.
 *
 * \arg <tt>"xreal"</tt> – double.  Horizontal size in physical units.
 *
 * \arg <tt>"yreal"</tt> – double.  Vertical size in physical units.
 *
 * \arg <tt>"xoff"</tt> – double.  Horizontal offset of the top-left corner in
 * physical units.
 *
 * \arg <tt>"yoff"</tt> – double.  Vertical offset of the top-left corner in
 * physical units.
 *
 * \arg <tt>"si_unit_xy"</tt> – string.  Physical units of lateral dimensions,
 * base SI units, e.g. <tt>"m"</tt>.  The returned string is newly allocated
 * and the caller must free it with free().
 *
 * \arg <tt>"si_unit_z"</tt> – string.  Physical units of field values, base SI
 * units, e.g.  <tt>"A"</tt>.  The returned string is newly allocated and the
 * caller must free it with free().
 *
 * \param object A GWY file data object, presumably a <tt>GwyDataField</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_datafield_get(const GwyfileObject *object,
                             GwyfileError **error,
                             ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_datafield_check(object, error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;

        if (gwyfile_strequal(name, "xres") || gwyfile_strequal(name, "yres"))
            gwyfile_object_fill_int32(object, name, &ap, 0);
        else if (gwyfile_strequal(name, "xreal")
                 || gwyfile_strequal(name, "yreal"))
            gwyfile_object_fill_double(object, name, &ap,
                                       1.0, DBL_MIN, DBL_MAX);
        else if (gwyfile_strequal(name, "xoff")
                 || gwyfile_strequal(name, "yoff"))
            gwyfile_object_fill_double(object, name, &ap,
                                       0.0, -DBL_MAX, DBL_MAX);
        else if (gwyfile_strequal(name, "si_unit_xy")
                 || gwyfile_strequal(name, "si_unit_z"))
            gwyfile_object_fill_siunit(object, name, &ap);
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

static bool
gwyfile_object_dataline_check(const GwyfileObject *object,
                              GwyfileError **error)
{
    GwyfileItem *res_item, *data_item;
    int res;
    uint32_t ndata;

    if (!gwyfile_object_check_type(object, "GwyDataLine", error))
        return false;

    if (!(res_item = gwyfile_object_check_item(object, "res",
                                               GWYFILE_ITEM_INT32,
                                               error))
        || !(data_item = gwyfile_object_check_item(object, "data",
                                                   GWYFILE_ITEM_DOUBLE_ARRAY,
                                                   error)))
        return false;

    res = gwyfile_item_get_int32(res_item);
    ndata = gwyfile_item_array_length(data_item);
    if (res > 0 && (uint32_t)res == ndata)
        return true;

    if (error) {
        char *path = gwyfile_format_path(object, NULL);
        gwyfile_set_error(error,
                          GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_ARRAY_SIZE,
                          "Data array length %u of %s "
                          "does not match pixel dimension %d.",
                          ndata, path, res);
        free(path);
    }

    return false;
}

/*!\fn bool gwyfile_object_dataline_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file \c GwyDataLine
 *        object.
 *
 * The function checks if the object type is actually <tt>"GwyDataLine"</tt>
 * and if it contains sane data items.  Every \c GwyDataLine must contain at
 * least the pixel resolution <tt>"res"</tt> and a matching array of doubles
 * <tt>"data"</tt> of the corresponding size.
 *
 * If \p object does not seem to represent a valid \c GwyDataLine object the
 * function fails, does not fill any output arguments (beside the error) and
 * returns <tt>false</tt>.
 *
 * All other items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value (e.g. NaN physical dimension).  Unknown additional items are simply
 * ignored.  The function does not fail in these cases and returns
 * <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"data"</tt> – array of doubles of size \p res.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size \p res.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \arg <tt>"res"</tt> – 32bit integer.  Dimension in pixels.
 *
 * \arg <tt>"real"</tt> – double.  Dimension in physical units.
 *
 * \arg <tt>"off"</tt> – double.  Offset of the left edge in physical units.
 *
 * \arg <tt>"si_unit_x"</tt> – string.  Physical units of the abscissa,
 * base SI units, e.g. <tt>"m"</tt>.  The returned string is newly allocated
 * and the caller must free it with free().
 *
 * \arg <tt>"si_unit_y"</tt> – string.  Physical units of values, base SI
 * units, e.g.  <tt>"A"</tt>.  The returned string is newly allocated and the
 * caller must free it with free().
 *
 * \param object A GWY file data object, presumably a <tt>GwyDataLine</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_dataline_get(const GwyfileObject *object,
                            GwyfileError **error,
                            ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_dataline_check(object, error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;

        if (gwyfile_strequal(name, "res"))
            gwyfile_object_fill_int32(object, name, &ap, 0);
        else if (gwyfile_strequal(name, "real"))
            gwyfile_object_fill_double(object, name, &ap,
                                       1.0, DBL_MIN, DBL_MAX);
        else if (gwyfile_strequal(name, "off"))
            gwyfile_object_fill_double(object, name, &ap,
                                       0.0, -DBL_MAX, DBL_MAX);
        else if (gwyfile_strequal(name, "si_unit_x")
                 || gwyfile_strequal(name, "si_unit_y"))
            gwyfile_object_fill_siunit(object, name, &ap);
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

static bool
gwyfile_object_brick_check(const GwyfileObject *object,
                           GwyfileError **error)
{
    GwyfileItem *xres_item, *yres_item, *zres_item, *data_item;
    int xres, yres, zres;
    uint32_t ndata;

    if (!gwyfile_object_check_type(object, "GwyBrick", error))
        return false;

    if (!(xres_item = gwyfile_object_check_item(object, "xres",
                                                GWYFILE_ITEM_INT32,
                                                error))
        || !(yres_item = gwyfile_object_check_item(object, "yres",
                                                   GWYFILE_ITEM_INT32,
                                                   error))
        || !(zres_item = gwyfile_object_check_item(object, "zres",
                                                   GWYFILE_ITEM_INT32,
                                                   error))
        || !(data_item = gwyfile_object_check_item(object, "data",
                                                   GWYFILE_ITEM_DOUBLE_ARRAY,
                                                   error)))
        return false;

    xres = gwyfile_item_get_int32(xres_item);
    yres = gwyfile_item_get_int32(yres_item);
    zres = gwyfile_item_get_int32(zres_item);
    ndata = gwyfile_item_array_length(data_item);
    if (xres > 0
        && yres > 0
        && zres > 0
        && (uint32_t)xres == ndata/yres/zres
        && (uint32_t)yres == ndata/xres/zres
        && (uint32_t)zres == ndata/xres/yres
        && (uint32_t)xres * (uint32_t)yres * (uint32_t)zres == ndata)
        return true;

    if (error) {
        char *path = gwyfile_format_path(object, NULL);
        gwyfile_set_error(error,
                          GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_ARRAY_SIZE,
                          "Data array length %u of %s "
                          "does not match pixel dimension %dx%dx%d.",
                          ndata, path, xres, yres, zres);
        free(path);
    }

    return false;
}

/*!\fn bool gwyfile_object_brick_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file \c GwyBrick
 *        object.
 *
 * The function checks if the object type is actually <tt>"GwyBrick"</tt> and
 * if it contains sane data items.  Every \c GwyBrick must contain at least the
 * pixel resolutions <tt>"xres"</tt>, <tt>"yres"</tt> and <tt>"zres"></tt> and
 * a matching array of doubles <tt>"data"</tt> of the corresponding size.
 *
 * If \p object does not seem to represent a valid \c GwyBrick object the
 * function fails, does not fill any output arguments (beside the error) and
 * returns <tt>false</tt>.
 *
 * All other items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value (e.g. NaN physical dimension).  Unknown additional items are simply
 * ignored.  The function does not fail in these cases and returns
 * <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"data"</tt> – array of doubles of size \p xres × \p yres × \p zres.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size \p xres × \p yres × \p
 * zres.  The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \arg <tt>"xres"</tt> – 32bit integer.  Horizontal dimension in pixels.
 *
 * \arg <tt>"yres"</tt> – 32bit integer.  Vertical dimension in pixels.
 *
 * \arg <tt>"zres"</tt> – 32bit integer.  Depth-wise dimension in pixels.
 *
 * \arg <tt>"xreal"</tt> – double.  Horizontal size in physical units.
 *
 * \arg <tt>"yreal"</tt> – double.  Vertical size in physical units.
 *
 * \arg <tt>"zreal"</tt> – double.  Depth-wise size in physical units.
 *
 * \arg <tt>"xoff"</tt> – double.  Horizontal offset of the top-left upper
 * corner in physical units.
 *
 * \arg <tt>"yoff"</tt> – double.  Vertical offset of the top-left upper corner
 * in physical units.
 *
 * \arg <tt>"zoff"</tt> – double.  Depth-wise offset of the top-left upper
 * corner in physical units.
 *
 * \arg <tt>"si_unit_x"</tt> – string.  Physical units of horizontal
 * dimensions, base SI units, e.g. <tt>"m"</tt>.  The returned string is newly
 * allocated and the caller must free it with free().
 *
 * \arg <tt>"si_unit_y"</tt> – string.  Physical units of vertical dimensions,
 * base SI units, e.g. <tt>"m"</tt>.  The returned string is newly allocated
 * and the caller must free it with free().
 *
 * \arg <tt>"si_unit_z"</tt> – string.  Physical units of depth dimensions,
 * base SI units, e.g. <tt>"m"</tt>.  The returned string is newly allocated
 * and the caller must free it with free().
 *
 * \arg <tt>"si_unit_w"</tt> – string.  Physical units of brick values, base SI
 * units, e.g.  <tt>"A"</tt>.  The returned string is newly allocated and the
 * caller must free it with free().
 *
 * \param object A GWY file data object, presumably a <tt>GwyBrick</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_brick_get(const GwyfileObject *object,
                         GwyfileError **error,
                         ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_brick_check(object, error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;

        if (gwyfile_strequal(name, "xres")
            || gwyfile_strequal(name, "yres")
            || gwyfile_strequal(name, "zres"))
            gwyfile_object_fill_int32(object, name, &ap, 0);
        else if (gwyfile_strequal(name, "xreal")
                 || gwyfile_strequal(name, "yreal")
                 || gwyfile_strequal(name, "zreal"))
            gwyfile_object_fill_double(object, name, &ap,
                                       1.0, DBL_MIN, DBL_MAX);
        else if (gwyfile_strequal(name, "xoff")
                 || gwyfile_strequal(name, "yoff")
                 || gwyfile_strequal(name, "zoff"))
            gwyfile_object_fill_double(object, name, &ap,
                                       0.0, -DBL_MAX, DBL_MAX);
        else if (gwyfile_strequal(name, "si_unit_x")
                 || gwyfile_strequal(name, "si_unit_y")
                 || gwyfile_strequal(name, "si_unit_z")
                 || gwyfile_strequal(name, "si_unit_w"))
            gwyfile_object_fill_siunit(object, name, &ap);
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

static bool
gwyfile_object_surface_check(const GwyfileObject *object,
                             GwyfileError **error)
{
    GwyfileItem *data_item;
    uint32_t ndata;

    if (!gwyfile_object_check_type(object, "GwySurface", error))
        return false;

    if (!(data_item = gwyfile_object_check_item(object, "data",
                                                GWYFILE_ITEM_DOUBLE_ARRAY,
                                                error)))
        return false;

    ndata = gwyfile_item_array_length(data_item);
    if (ndata % 3 == 0)
        return true;

    if (error) {
        char *path = gwyfile_format_path(object, NULL);
        gwyfile_set_error(error,
                          GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_ARRAY_SIZE,
                          "Data array length %u of %s is not multiple of %d.",
                          ndata, path, 3);
        free(path);
    }

    return false;
}

/*!\fn bool gwyfile_object_surface_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file \c GwySurface
 *        object.
 *
 * The function checks if the object type is actually <tt>"GwySurface"</tt>
 * and if it contains sane data items.  Every \c GwySurface must contain at
 * least an array of doubles <tt>"data"</tt> of size that is a multiple of 3.
 *
 * If \p object does not seem to represent a valid \c GwySurface object the
 * function fails, does not fill any output arguments (beside the error) and
 * returns <tt>false</tt>.
 *
 * All other items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value.  Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"data"</tt> – array of doubles of size 3 × \p n.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size 3 × \p n.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \arg <tt>"n"</tt> – 32bit integer.  Number of points.  Note that the
 * number values in the data array is three times the number of points.
 *
 * \arg <tt>"si_unit_xy"</tt> – string.  Physical units of X and Y coordinates,
 * base SI units, e.g. <tt>"m"</tt>.  The returned string is newly allocated
 * and the caller must free it with free().
 *
 * \arg <tt>"si_unit_z"</tt> – string.  Physical units of Z values, base SI
 * units, e.g.  <tt>"A"</tt>.  The returned string is newly allocated and the
 * caller must free it with free().
 *
 * \param object A GWY file data object, presumably a <tt>GwySurface</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 * \since 1.2
 */
bool
gwyfile_object_surface_get(const GwyfileObject *object,
                           GwyfileError **error,
                           ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_surface_check(object, error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;

        if (gwyfile_strequal(name, "n")) {
            int32_t *value = va_arg(ap, int32_t*);
            GwyfileItem *data_item;

            assert(value);
            data_item = gwyfile_object_get_with_type(object, "data",
                                                     GWYFILE_ITEM_DOUBLE_ARRAY);
            *value = gwyfile_item_array_length(data_item)/3;
        }
        else if (gwyfile_strequal(name, "si_unit_xy")
                 || gwyfile_strequal(name, "si_unit_z"))
            gwyfile_object_fill_siunit(object, name, &ap);
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

static bool
gwyfile_object_graphcurvemodel_check(const GwyfileObject *object,
                                     uint32_t *ndata,
                                     GwyfileError **error)
{
    GwyfileItem *xdata_item, *ydata_item;
    uint32_t nxdata, nydata;

    if (!gwyfile_object_check_type(object, "GwyGraphCurveModel", error))
        return false;

    if (!(xdata_item = gwyfile_object_check_item(object, "xdata",
                                                 GWYFILE_ITEM_DOUBLE_ARRAY,
                                                 error))
        || !(ydata_item = gwyfile_object_check_item(object, "ydata",
                                                    GWYFILE_ITEM_DOUBLE_ARRAY,
                                                    error)))
        return false;

    nxdata = gwyfile_item_array_length(xdata_item);
    nydata = gwyfile_item_array_length(ydata_item);
    if (nxdata > 0 && nydata > 0 && nxdata == nydata) {
        *ndata = nxdata;
        return true;
    }

    if (error) {
        char *path = gwyfile_format_path(object, NULL);
        gwyfile_set_error(error,
                          GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_ARRAY_SIZE,
                          "X and Y data array lengths %u and %u of %s "
                          "do not match.",
                          nxdata, nydata, path);
        free(path);
    }

    return false;
}

/*!\fn bool gwyfile_object_graphcurvemodel_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file \c GwyGraphCurveModel
 *        object.
 *
 * The function checks if the object type is actually
 * <tt>"GwyGraphCurveModel"</tt> and if it contains sane data items.  Every \c
 * GwyGraphCurveModel must contain at least the abscissa and ordinate data
 * <tt>"xdata"</tt> and <tt>"ydata"</tt> of the same size.
 *
 * If \p object does not seem to represent a valid \c GwyGraphCurveModel object
 * the function fails, does not fill any output arguments (beside the error)
 * and returns <tt>false</tt>.
 *
 * All other items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value (e.g. colour component outisde [0, 1]).  Unknown additional items are
 * simply ignored.  The function does not fail in these cases and returns
 * <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"ndata"</tt> – 32bit integer.  The number of points in the curve,
 * equal to the length of both <tt>"xdata"</tt> and <tt>"ydata"</tt> arrays.
 *
 * \arg <tt>"xdata"</tt> – array of doubles of size \p ndata.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"xdata(take)"</tt> – array of doubles of size \p ndata.  The array
 * ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"xdata"</tt> repeatedly but
 * <tt>"xdata(take)"</tt> may be requested from each object at most once.
 *
 * \arg <tt>"ydata"</tt> – array of doubles of size \p ndata.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"ydata(take)"</tt> – array of doubles of size \p ndata.  The array
 * ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"ydata"</tt> repeatedly but
 * <tt>"ydata(take)"</tt> may be requested from each object at most once.
 *
 * \arg <tt>"description"</tt> – string.  Curve label.  The returned string is
 * newly allocated and the caller must free it with free().
 *
 * \arg <tt>"type"</tt> – 32bit integer.  See \c GwyGraphCurveType in
 * Gwyddion API documentation for the list of curve modes.
 *
 * \arg <tt>"point_type"</tt> – 32bit integer.  See \c GwyGraphPointType in
 * Gwyddion API documentation for the list of point types.
 *
 * \arg <tt>"line_style"</tt> – 32bit integer.  See \c GdkLineStyle in
 * Gtk+ 2 API documentation for the list of line styles.
 *
 * \arg <tt>"point_size"</tt> – 32bit integer.  Point size.
 *
 * \arg <tt>"line_size"</tt> – 32bit integer.  Line width.
 *
 * \arg <tt>"color.red"</tt> – double.  Red colour component from the
 * interval [0, 1].
 *
 * \arg <tt>"color.green"</tt> – double.  Green colour component from the
 * interval [0, 1].
 *
 * \arg <tt>"color.blue"</tt> – double.  Blue colour component from the
 * interval [0, 1].
 *
 * \param object A GWY file data object, presumably a
 *               <tt>GwyGraphCurveModel</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_graphcurvemodel_get(const GwyfileObject *object,
                                   GwyfileError **error,
                                   ...)
{
    const char *name;
    uint32_t ndata;
    va_list ap;

    assert(object);
    if (!gwyfile_object_graphcurvemodel_check(object, &ndata, error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "xdata", "xdata(take)",
                                                 &ap)
            ||gwyfile_object_get_handle_data_items(object, name,
                                                   "ydata", "ydata(take)",
                                                   &ap))
            continue;

        if (gwyfile_strequal(name, "ndata")) {
            int32_t *value = va_arg(ap, int32_t*);
            assert(value);
            *value = ndata;
        }
        else if (gwyfile_strequal(name, "description"))
            gwyfile_object_fill_string(object, name, &ap, "");
        else if (gwyfile_strequal(name, "type")
                 || gwyfile_strequal(name, "line_size"))
            gwyfile_object_fill_int32(object, name, &ap, 1);
        else if (gwyfile_strequal(name, "point_type")
                 || gwyfile_strequal(name, "line_style"))
            gwyfile_object_fill_int32(object, name, &ap, 0);
        else if (gwyfile_strequal(name, "point_size"))
            gwyfile_object_fill_int32(object, name, &ap, 5);
        else if (gwyfile_strequal(name, "color.red")
                 || gwyfile_strequal(name, "color.green")
                 || gwyfile_strequal(name, "color.blue"))
            gwyfile_object_fill_double(object, name, &ap, 0.0, 0.0, 1.0);
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

static bool
gwyfile_object_graphmodel_check(const GwyfileObject *object,
                                uint32_t *ncurves,
                                GwyfileError **error)
{
    GwyfileItem *curves_item;

    if (!gwyfile_object_check_type(object, "GwyGraphModel", error))
        return false;

    /* Item "curves" is optional so it is OK when it fails to check. */
    if (!(curves_item = gwyfile_object_check_item(object, "curves",
                                                  GWYFILE_ITEM_OBJECT_ARRAY,
                                                  NULL))) {
        *ncurves = 0;
        return true;
    }

    *ncurves = gwyfile_item_array_length(curves_item);
    return true;
}

/*!\fn bool gwyfile_object_graphmodel_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file \c GwyGraphModel
 *        object.
 *
 * The function checks if the object type is actually
 * <tt>"GwyGraphModel"</tt> and if it contains sane data items.  Every \c
 * GwyGraphModel must contain at least the abscissa and ordinate data
 * <tt>"xdata"</tt> and <tt>"ydata"</tt> of the same size.
 *
 * If \p object does not seem to represent a valid \c GwyGraphModel object
 * the function fails, does not fill any output arguments (beside the error)
 * and returns <tt>false</tt>.
 *
 * All other items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value.  Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"ncurves"</tt> – 32bit integer.  The number of curves in the graph,
 * equal to the length of <tt>"curves"</tt> array.  It may be zero.
 *
 * \arg <tt>"curves"</tt> – array of ::_GwyfileObject pointers of size
 * \p ncurves.  Both the array and objects inside remain to be owned by the
 * item.  The pointer will be filled with \c NULL when there are no curves.
 *
 * \arg <tt>"title"</tt> – string.  Graph title.  The returned string is newly
 * allocated and the caller must free it with free().
 *
 * \arg <tt>"top_label"</tt> – string.  Top axis label.  The returned string is
 * newly allocated and the caller must free it with free().
 *
 * \arg <tt>"left_label"</tt> – string.  Left axis label.  The returned string
 * is newly allocated and the caller must free it with free().
 *
 * \arg <tt>"right_label"</tt> – string.  Right axis label.  The returned
 * string is newly allocated and the caller must free it with free().
 *
 * \arg <tt>"bottom_label"</tt> – string.  Bottom axis label.  The returned
 * string is newly allocated and the caller must free it with free().
 *
 * \arg <tt>"x_unit"</tt> – string.  Physical units of abscissa, in base SI
 * units, e.g. <tt>"m"</tt>.  The returned string is newly allocated and the
 * caller must free it with free().
 *
 * \arg <tt>"y_unit"</tt> – string.  Physical units of ordinate, in base SI
 * units, e.g.  <tt>"A"</tt>.  The returned string is newly allocated and the
 * caller must free it with free().
 *
 * \arg <tt>"x_min"</tt> – double.  Minimum value of abscissa.  Effective
 * if <tt>"x_min_set"</tt> is <tt>true</tt>.
 *
 * \arg <tt>"x_min_set"</tt> – boolean.  Whether the minimum value of abscissa
 * is set explicitly (i.e. user-requested).
 *
 * \arg <tt>"x_max"</tt> – double.  Maximum value of abscissa.  Effective
 * if <tt>"x_max_set"</tt> is <tt>true</tt>.
 *
 * \arg <tt>"x_max_set"</tt> – boolean.  Whether the maximum value of abscissa
 * is set explicitly (i.e. user-requested).
 *
 * \arg <tt>"y_min"</tt> – double.  Minimum value of ordinate.  Effective
 * if <tt>"y_min_set"</tt> is <tt>true</tt>.
 *
 * \arg <tt>"y_min_set"</tt> – boolean.  Whether the minimum value of ordinate
 * is set explicitly (i.e. user-requested).
 *
 * \arg <tt>"y_max"</tt> – double.  Maximum value of ordinate.  Effective
 * if <tt>"y_max_set"</tt> is <tt>true</tt>.
 *
 * \arg <tt>"y_max_set"</tt> – boolean.  Whether the maximum value of ordinate
 * is set explicitly (i.e. user-requested).
 *
 * \arg <tt>"x_is_logarithmic"</tt> – boolean.  Whether abscissa is displayed
 * in logaritmic scale.
 *
 * \arg <tt>"y_is_logarithmic"</tt> – boolean.  Whether ordinate is displayed
 * in logaritmic scale.
 *
 * \arg <tt>"label.visible"</tt> – boolean.  Whether the graph key is visible.
 *
 * \arg <tt>"label.has_frame"</tt> – boolean.  Whether the graph key has a
 * frame.
 *
 * \arg <tt>"label.reverse"</tt> – boolean.  Whether the graph key should be
 * displayed with a reversed layout.
 *
 * \arg <tt>"label.frame_thickness"</tt> – 32bit integer.  Thickness of the
 * graph key frame.
 *
 * \arg <tt>"label.position"</tt> – 32bit integer.  See \c
 * GwyGraphLabelPosition in Gwyddion API documentation for the list of graph
 * label position types.
 *
 * \arg <tt>"grid-type"</tt> – 32bit integer.  See \c GwyGraphGridType in
 * Gwyddion API documentation for the list of graph grid types.  Note this
 * property has never been actually implemented in Gwyddion.
 *
 * \param object A GWY file data object, presumably a
 *               <tt>GwyGraphModel</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_graphmodel_get(const GwyfileObject *object,
                              GwyfileError **error,
                              ...)
{
    const char *name;
    uint32_t ncurves;
    va_list ap;

    assert(object);
    if (!gwyfile_object_graphmodel_check(object, &ncurves, error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_strequal(name, "ncurves")) {
            int32_t *value = va_arg(ap, int32_t*);
            assert(value);
            *value = ncurves;
        }
        else if (gwyfile_strequal(name, "curves")) {
            GwyfileItem *item = gwyfile_object_get_with_type(object, name,
                                                             GWYFILE_ITEM_OBJECT_ARRAY);
            GwyfileObject *const **value = va_arg(ap, GwyfileObject* const**);
            assert(value);
            *value = item ? gwyfile_item_get_object_array(item) : NULL;
        }
        else if (gwyfile_strequal(name, "x_unit")
                 || gwyfile_strequal(name, "y_unit"))
            gwyfile_object_fill_siunit(object, name, &ap);
        else if (gwyfile_strequal(name, "title")
                 || gwyfile_strequal(name, "top_label")
                 || gwyfile_strequal(name, "left_label")
                 || gwyfile_strequal(name, "right_label")
                 || gwyfile_strequal(name, "bottom_label"))
            gwyfile_object_fill_string(object, name, &ap, "");
        else if (gwyfile_strequal(name, "x_min")
                 || gwyfile_strequal(name, "y_min"))
            gwyfile_object_fill_double(object, name, &ap,
                                       0.0, -DBL_MAX, DBL_MAX);
        else if (gwyfile_strequal(name, "x_max")
                 || gwyfile_strequal(name, "y_max"))
            gwyfile_object_fill_double(object, name, &ap,
                                       1.0, -DBL_MAX, DBL_MAX);
        else if (gwyfile_strequal(name, "x_min_set")
                 || gwyfile_strequal(name, "x_max_set")
                 || gwyfile_strequal(name, "y_min_set")
                 || gwyfile_strequal(name, "y_max_set")
                 || gwyfile_strequal(name, "x_is_logarithmic")
                 || gwyfile_strequal(name, "y_is_logarithmic")
                 || gwyfile_strequal(name, "label.reversed"))
            gwyfile_object_fill_bool(object, name, &ap, false);
        else if (gwyfile_strequal(name, "label.visible")
                 || gwyfile_strequal(name, "label.has_frame"))
            gwyfile_object_fill_bool(object, name, &ap, true);
        else if (gwyfile_strequal(name, "label.frame_thickness")
                 || gwyfile_strequal(name, "grid-type"))
            gwyfile_object_fill_int32(object, name, &ap, 1);
        else if (gwyfile_strequal(name, "label.position"))
            gwyfile_object_fill_int32(object, name, &ap, 0);
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

static bool
gwyfile_object_spectra_check(const GwyfileObject *object,
                             uint32_t *ndata,
                             GwyfileError **error)
{
    GwyfileItem *data_item, *coords_item, *selected_item;
    GwyfileObject* const* curves;
    uint32_t ncurves, ncoords, i;

    if (!gwyfile_object_check_type(object, "GwySpectra", error))
        return false;

    if (!(data_item = gwyfile_object_check_item(object, "data",
                                                GWYFILE_ITEM_OBJECT_ARRAY,
                                                error))
        || !(coords_item = gwyfile_object_check_item(object, "coords",
                                                     GWYFILE_ITEM_DOUBLE_ARRAY,
                                                     error)))
        return false;

    ncurves = gwyfile_item_array_length(data_item);
    ncoords = gwyfile_item_array_length(coords_item);
    if (ncoords != 2*ncurves) {
        if (error) {
            char *path = gwyfile_format_path(object, NULL);
            gwyfile_set_error(error,
                              GWYFILE_ERROR_DOMAIN_DATA,
                              GWYFILE_ERROR_ARRAY_SIZE,
                              "Data and coords array lengths %u and %u "
                              "of %s do not match.",
                              ncurves, ncoords, path);
            free(path);
        }
        return false;
    }

    curves = gwyfile_item_get_object_array(data_item);
    for (i = 0; i < ncurves; i++) {
        if (!gwyfile_object_dataline_check(curves[i], error))
            return false;
    }

    if ((selected_item = gwyfile_object_get_with_type(object, "selected",
                                                      GWYFILE_ITEM_INT32_ARRAY))) {
        uint32_t nsel = gwyfile_item_array_length(selected_item);
        if (nsel != (ncurves + 31)/32) {
            if (error) {
                char *path = gwyfile_format_path(object, NULL);
                gwyfile_set_error(error,
                                  GWYFILE_ERROR_DOMAIN_DATA,
                                  GWYFILE_ERROR_ARRAY_SIZE,
                                  "Data and selected array lengths %u and %u "
                                  "of %s do not match.",
                                  ncurves, nsel, path);
                free(path);
            }
            return false;
        }
    }

    *ndata = ncurves;
    return true;
}

/*!\fn bool gwyfile_object_spectra_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file \c GwySpectra
 *        object.
 *
 * The function checks if the object type is actually
 * <tt>"GwySpectra"</tt> and if it contains sane data items.  Every \c
 * GwySpectra must contain at least the curves <tt>"data"</tt> and their
 * coordinates <tt>"coords"</tt> of the corresponding sizes.
 *
 * If \p object does not seem to represent a valid \c GwySpectra object
 * the function fails, does not fill any output arguments (beside the error)
 * and returns <tt>false</tt>.
 *
 * All other items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value.  Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"ndata"</tt> – 32bit integer.  The number of curves in the spectra,
 * equal to the length of <tt>"data"</tt> array.  It may be zero.
 *
 * \arg <tt>"data"</tt> – array of ::_GwyfileObject pointers of size
 * \p ndata.  Both the array and objects inside remain to be owned by the
 * item.  The pointer will be filled with \c NULL when there are no spectra
 * curves.
 *
 * \arg <tt>"coords"</tt> – array of doubles of size 2<tt>ndata</tt>.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"coords(take)"</tt> – array of doubles of size 2<tt>ndata</tt>.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the coords is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"coords"</tt> repeatedly but
 * <tt>"coords(take)"</tt> may be requested from each object at most once.
 *
 * \arg <tt>"title"</tt> – string.  Spectra title.  The returned string is
 * newly allocated and the caller must free it with free().
 *
 * \arg <tt>"spec_xlabel"</tt> – string.  Spectra abscissa label.  The returned
 * string is newly allocated and the caller must free it with free().
 *
 * \arg <tt>"spec_ylabel"</tt> – string.  Spectra ordinate label.  The returned
 * string is newly allocated and the caller must free it with free().
 *
 * \arg <tt>"si_unit_xy"</tt> – string.  Physical units of ordinate, in base SI
 * units, e.g.  <tt>"m"</tt>.  The returned string is newly allocated and the
 * caller must free it with free().
 *
 * \arg <tt>"selected"</tt> – array of 32bit integers with
 * ceil(<tt>ndata</tt>/32) elements describing which spectra are currently
 * selected.  The returned array is newly allocated and the caller must free it
 * with free().  It will be filled with \c NULL if the item is not present or
 * there are no curves.
 *
 * \param object A GWY file data object, presumably a <tt>GwySpectra</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_spectra_get(const GwyfileObject *object,
                           GwyfileError **error,
                           ...)
{
    const char *name;
    uint32_t ndata;
    va_list ap;

    assert(object);
    if (!gwyfile_object_spectra_check(object, &ndata, error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "coords", "coords(take)",
                                                 &ap))
            continue;

        if (gwyfile_strequal(name, "ndata")) {
            int32_t *value = va_arg(ap, int32_t*);
            assert(value);
            *value = ndata;
        }
        else if (gwyfile_strequal(name, "data")) {
            GwyfileItem *item = gwyfile_object_get_with_type(object, name,
                                                             GWYFILE_ITEM_OBJECT_ARRAY);
            GwyfileObject *const **value = va_arg(ap, GwyfileObject* const**);
            assert(value);
            *value = item ? gwyfile_item_get_object_array(item) : NULL;
        }
        else if (gwyfile_strequal(name, "si_unit_xy"))
            gwyfile_object_fill_siunit(object, name, &ap);
        else if (gwyfile_strequal(name, "si_unit_xy"))
            gwyfile_object_fill_siunit(object, name, &ap);
        else if (gwyfile_strequal(name, "title")
                 || gwyfile_strequal(name, "spec_xlabel")
                 || gwyfile_strequal(name, "spec_ylabel"))
            gwyfile_object_fill_string(object, name, &ap, "");
        else if (gwyfile_strequal(name, "selected")) {
            int32_t **value = va_arg(ap, int32_t**);
            GwyfileItem *item = gwyfile_object_get_with_type(object, name,
                                                             GWYFILE_ITEM_INT32_ARRAY);
            const int32_t *selected = NULL;

            assert(value);
            if (item && ndata)
                selected = gwyfile_item_get_int32_array(item);
            *value = (int32_t*)gwyfile_memdup(selected, (ndata + 31)/32);
        }
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

static bool
gwyfile_object_selection_check(const GwyfileObject *object,
                               const char *name, int ncoord,
                               GwyfileError **error)
{
    GwyfileItem *data_item;
    uint32_t ndata;

    if (!gwyfile_object_check_type(object, name, error))
        return false;

    data_item = gwyfile_object_check_item(object, "data",
                                          GWYFILE_ITEM_DOUBLE_ARRAY,
                                          error);
    if (!data_item)
        return true;

    ndata = gwyfile_item_array_length(data_item);
    if (ndata % ncoord == 0)
        return true;

    if (error) {
        char *path = gwyfile_format_path(object, NULL);
        gwyfile_set_error(error,
                          GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_ARRAY_SIZE,
                          "Data array length %u of %s is not multiple of %d.",
                          ndata, path, ncoord);
        free(path);
    }
    return false;
}

static bool
gwyfile_object_get_handle_nsel(const GwyfileObject *object,
                               const char *name, int ncoord,
                               va_list *ap)
{
    GwyfileItem *item;
    int32_t *value;

    if (!gwyfile_strequal(name, "nsel"))
        return false;

    value = va_arg(*ap, int32_t*);
    assert(value);
    item = gwyfile_object_get_with_type(object, "data",
                                        GWYFILE_ITEM_DOUBLE_ARRAY);
    *value = item ? gwyfile_item_array_length(item)/ncoord : 0;
    return true;
}

/*!\fn bool gwyfile_object_selectionpoint_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file \c GwySelectionPoint
 *        object.
 *
 * The function checks if the object type is actually
 * <tt>"GwySelectionPoint"</tt> and if it contains sane data items.
 *
 * If \p object does not seem to represent a valid \c GwySelectionPoint object
 * the function fails, does not fill any output arguments (beside the error)
 * and returns <tt>false</tt>.
 *
 * All items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value.  Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"nsel"</tt> – 32bit integer.  The number of points in the
 * selection (not the number of double values).
 *
 * \arg <tt>"data"</tt> – array of doubles of size 2×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size 2×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \param object A GWY file data object, presumably a
 *               <tt>GwySelectionPoint</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_selectionpoint_get(const GwyfileObject *object,
                                  GwyfileError **error,
                                  ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_selection_check(object, "GwySelectionPoint", 2,
                                        error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;
        if (gwyfile_object_get_handle_nsel(object, name, 2, &ap))
            continue;
        /* We have a pointer in the arg list so we could try just skipping
         * it, but the caller is likely going to crash if we don't put
         * anything there anyway... */
        assert(!"Reached");
    }
    va_end(ap);

    return true;
}

/*!\fn bool gwyfile_object_selectionrectangle_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file
 *        \c GwySelectionRectangle object.
 *
 * The function checks if the object type is actually
 * <tt>"GwySelectionRectangle"</tt> and if it contains sane data items.
 *
 * If \p object does not seem to represent a valid \c GwySelectionRectangle
 * object the function fails, does not fill any output arguments (beside the
 * error) and returns <tt>false</tt>.
 *
 * All items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value.  Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"nsel"</tt> – 32bit integer.  The number of rectangles in the
 * selection (not the number of double values).
 *
 * \arg <tt>"data"</tt> – array of doubles of size 4×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size 4×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \param object A GWY file data object, presumably a
 *               <tt>GwySelectionRectangle</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_selectionrectangle_get(const GwyfileObject *object,
                                      GwyfileError **error,
                                      ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_selection_check(object, "GwySelectionRectangle", 4,
                                        error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;
        if (gwyfile_object_get_handle_nsel(object, name, 4, &ap))
            continue;
        /* We have a pointer in the arg list so we could try just skipping
         * it, but the caller is likely going to crash if we don't put
         * anything there anyway... */
        assert(!"Reached");
    }
    va_end(ap);

    return true;
}

/*!\fn bool gwyfile_object_selectionellipse_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file
 *        \c GwySelectionEllipse object.
 *
 * The function checks if the object type is actually
 * <tt>"GwySelectionEllipse"</tt> and if it contains sane data items.
 *
 * If \p object does not seem to represent a valid \c GwySelectionEllipse
 * object the function fails, does not fill any output arguments (beside the
 * error) and returns <tt>false</tt>.
 *
 * All items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value.  Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"nsel"</tt> – 32bit integer.  The number of ellipses in the
 * selection (not the number of double values).
 *
 * \arg <tt>"data"</tt> – array of doubles of size 4×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size 4×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \param object A GWY file data object, presumably a
 *               <tt>GwySelectionEllipse</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_selectionellipse_get(const GwyfileObject *object,
                                    GwyfileError **error,
                                    ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_selection_check(object, "GwySelectionEllipse", 4,
                                        error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;
        if (gwyfile_object_get_handle_nsel(object, name, 4, &ap))
            continue;
        /* We have a pointer in the arg list so we could try just skipping
         * it, but the caller is likely going to crash if we don't put
         * anything there anyway... */
        assert(!"Reached");
    }
    va_end(ap);

    return true;
}

/*!\fn bool gwyfile_object_selectionline_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file
 *        \c GwySelectionLine object.
 *
 * The function checks if the object type is actually
 * <tt>"GwySelectionLine"</tt> and if it contains sane data items.
 *
 * If \p object does not seem to represent a valid \c GwySelectionLine
 * object the function fails, does not fill any output arguments (beside the
 * error) and returns <tt>false</tt>.
 *
 * All items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value. Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"nsel"</tt> – 32bit integer.  The number of lines in the
 * selection (not the number of double values).
 *
 * \arg <tt>"data"</tt> – array of doubles of size 4×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size 4×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \param object A GWY file data object, presumably a
 *               <tt>GwySelectionLine</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_selectionline_get(const GwyfileObject *object,
                                 GwyfileError **error,
                                 ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_selection_check(object, "GwySelectionLine", 4,
                                        error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;
        if (gwyfile_object_get_handle_nsel(object, name, 4, &ap))
            continue;
        /* We have a pointer in the arg list so we could try just skipping
         * it, but the caller is likely going to crash if we don't put
         * anything there anyway... */
        assert(!"Reached");
    }
    va_end(ap);

    return true;
}

/*!\fn bool gwyfile_object_selectionlattice_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file
 *        \c GwySelectionLattice object.
 *
 * The function checks if the object type is actually
 * <tt>"GwySelectionLattice"</tt> and if it contains sane data items.
 *
 * If \p object does not seem to represent a valid \c GwySelectionLattice
 * object the function fails, does not fill any output arguments (beside the
 * error) and returns <tt>false</tt>.
 *
 * All items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value. Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"nsel"</tt> – 32bit integer.  The number of lattices in the
 * selection (not the number of double values).
 *
 * \arg <tt>"data"</tt> – array of doubles of size 4×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size 4×\p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \param object A GWY file data object, presumably a
 *               <tt>GwySelectionLattice</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_selectionlattice_get(const GwyfileObject *object,
                                    GwyfileError **error,
                                    ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_selection_check(object, "GwySelectionLattice", 4,
                                        error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;
        if (gwyfile_object_get_handle_nsel(object, name, 4, &ap))
            continue;
        /* We have a pointer in the arg list so we could try just skipping
         * it, but the caller is likely going to crash if we don't put
         * anything there anyway... */
        assert(!"Reached");
    }
    va_end(ap);

    return true;
}

/*!\fn bool gwyfile_object_selectionaxis_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file
 *        \c GwySelectionAxis object.
 *
 * The function checks if the object type is actually
 * <tt>"GwySelectionAxis"</tt> and if it contains sane data items.
 *
 * If \p object does not seem to represent a valid \c GwySelectionAxis
 * object the function fails, does not fill any output arguments (beside the
 * error) and returns <tt>false</tt>.
 *
 * All items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value. Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"nsel"</tt> – 32bit integer.  The number of axes in the
 * selection (not the number of double values).
 *
 * \arg <tt>"orientation"</tt> – 32bit integer from the GwyOrientation enum.
 * The axis orientation.
 *
 * \arg <tt>"data"</tt> – array of doubles of size \p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size \p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \param object A GWY file data object, presumably a
 *               <tt>GwySelectionAxis</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_selectionaxis_get(const GwyfileObject *object,
                                 GwyfileError **error,
                                 ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_selection_check(object, "GwySelectionAxis", 1,
                                        error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;
        if (gwyfile_object_get_handle_nsel(object, name, 1, &ap))
            continue;

        if (gwyfile_strequal(name, "orientation"))
            gwyfile_object_fill_int32(object, name, &ap, 0);
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

/*!\fn bool gwyfile_object_selectionpath_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file
 *        \c GwySelectionPath object.
 *
 * The function checks if the object type is actually
 * <tt>"GwySelectionPath"</tt> and if it contains sane data items.
 *
 * If \p object does not seem to represent a valid \c GwySelectionPath
 * object the function fails, does not fill any output arguments (beside the
 * error) and returns <tt>false</tt>.
 *
 * All items have default values that will be returned if the
 * corresponding item is not found, is of the wrong type or has an invalid
 * value. Unknown additional items are simply ignored.  The function does not
 * fail in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"nsel"</tt> – 32bit integer.  The number of points in the
 * selection (not the number of double values).
 *
 * \arg <tt>"slackness"</tt> – double.  Spline path slackness.
 *
 * \arg <tt>"closed"</tt> – boolean.  Whether the path is closed.
 *
 * \arg <tt>"data"</tt> – array of doubles of size \p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership does not change (as if gwyfile_item_get_double_array()
 * was used).
 *
 * \arg <tt>"data(take)"</tt> – array of doubles of size \p nsel.
 * It will be returned as \p NULL for empty selections.
 * The array ownership is transferred to the caller (as if
 * gwyfile_item_take_double_array() was used) who has to free it with free()
 * later.  Taking the data is not permitted if they are not owned by the data
 * item.  Hence you may requested <tt>"data"</tt> repeatedly but
 * <tt>"data(take)"</tt> may be requested from each object at most once.
 *
 * \param object A GWY file data object, presumably a
 *               <tt>GwySelectionPath</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 * \since 1.2
 */
bool
gwyfile_object_selectionpath_get(const GwyfileObject *object,
                                 GwyfileError **error,
                                 ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_selection_check(object, "GwySelectionPath", 2,
                                        error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_object_get_handle_data_items(object, name,
                                                 "data", "data(take)",
                                                 &ap))
            continue;
        if (gwyfile_object_get_handle_nsel(object, name, 2, &ap))
            continue;

        if (gwyfile_strequal(name, "slackness")) {
            gwyfile_object_fill_double(object, name, &ap,
                                       sqrt(0.5), 0.0, sqrt(2.0));
        }
        else if (gwyfile_strequal(name, "closed"))
            gwyfile_object_fill_bool(object, name, &ap, false);
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

static bool
gwyfile_object_siunit_check(const GwyfileObject *object,
                            GwyfileError **error)
{
    GwyfileItem *unitstr_item;

    if (!gwyfile_object_check_type(object, "GwySIUnit", error))
        return false;

    if (!(unitstr_item = gwyfile_object_check_item(object, "unitstr",
                                                   GWYFILE_ITEM_STRING,
                                                   error)))
        return false;

    return true;
}

/*!\fn bool gwyfile_object_siunit_get(const GwyfileObject *object, GwyfileError **error, ...)
 * \brief Obtains information and/or data from a GWY file \c GwySIUnit object.
 *
 * The function checks if the object type is actually <tt>"GwySIUnit"</tt> and
 * if it contains sane data items.  Note functions for specific Gwyddion data
 * objects, such as gwyfile_object_datafield_get(), can extract the unit
 * strings directly, saving you dealing explicitly with the unit object.
 *
 * If \p object does not seem to represent a valid \c GwySIUnit object the
 * function fails, does not fill any output arguments (beside the error) and
 * returns <tt>false</tt>.
 *
 * Every \c GwySIUnit object must contain at least the <tt>"unitstr"</tt> item.
 * Unknown additional items are simply ignored.  The function does not fail
 * in these cases and returns <tt>true</tt>.
 *
 * Possible items to request:
 * \arg <tt>"unitstr"</tt> – string.  Physical units, in base SI units, e.g.
 * <tt>"m"</tt>.  The returned string is newly allocated and the caller must
 * free it with free().
 *
 * \param object A GWY file data object, presumably a <tt>GwySIUnit</tt>.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param ... Requested data items specified as name, pointer-to-value pairs.
 *            Terminated by \c NULL.
 * \return \c true if the object looks acceptable and the item values were
 *         filled.
 */
bool
gwyfile_object_siunit_get(const GwyfileObject *object,
                          GwyfileError **error,
                          ...)
{
    const char *name;
    va_list ap;

    assert(object);
    if (!gwyfile_object_siunit_check(object, error))
        return false;

    va_start(ap, error);
    while ((name = va_arg(ap, const char*))) {
        if (gwyfile_strequal(name, "unitstr"))
            gwyfile_object_fill_string(object, name, &ap, "");
        else {
            /* We have a pointer in the arg list so we could try just skipping
             * it, but the caller is likely going to crash if we don't put
             * anything there anyway... */
            assert(!"Reached");
        }
    }
    va_end(ap);

    return true;
}

static void
gwyfile_id_list_add(GwyfileIdList *idlist, int id)
{
    if (idlist->len == idlist->alloc_size) {
        size_t alloc_size = idlist->alloc_size;
        int *ids = idlist->ids;

        idlist->alloc_size = alloc_size ? 2*alloc_size : 16;
        idlist->ids = (int*)realloc(ids, idlist->alloc_size*sizeof(int));
        /* We are in a deep shit if the realloc fails.  There is no reasonable
         * way to report an error.  Just stop adding items to the list.  */
        if (!idlist->ids) {
            idlist->alloc_size = alloc_size;
            idlist->ids = ids;
            errno = ENOMEM;
            return;
        }
    }
    idlist->ids[idlist->len++] = id;
}

static int
gwyfile_extract_id(const char *s, const char *template)
{
    const char *p = strstr(template, "%d");
    char *end;
    int id;

    if (!p)
        return -1;

    if (strncmp(s, template, p-template))
        return -1;

    id = strtol(s + (p - template), &end, 10);
    if ((const char*)end == s + (p - template))
        return -1;

    if (strcmp(end, p + 2))
        return -1;

    return id;
}

static int
gwyfile_compare_int(const void *pa, const void *pb)
{
    int a = *(const int*)pa;
    int b = *(const int*)pb;

    if (a < b)
        return -1;
    if (a > b)
        return 1;
    return 0;
}

static void
gwyfile_add_channel_id(const GwyfileItem *item, void *user_data)
{
    GwyfileObject *object;
    const char *name;
    int id, xres, yres;

    if (item->type != GWYFILE_ITEM_OBJECT)
        return;

    object = gwyfile_item_get_object(item);
    if (!gwyfile_object_datafield_get(object, NULL,
                                      "xres", &xres,
                                      "yres", &yres,
                                      NULL))
        return;

    name = item->name;
    if ((id = gwyfile_extract_id(name, "/%d/data")) >= 0) {
        GwyfileIdList *idlist = (GwyfileIdList*)user_data;
        gwyfile_id_list_add(idlist, id);
    }
}

/*!\fn int* gwyfile_object_container_enumerate_channels(const GwyfileObject *object, unsigned int *nchannels)
 * \brief Enumerates channels in a Gwyddion GWY file.
 *
 * A channel is considered valid and returned in the list if its primary data
 * field exists.  The presence of auxiliary channel data (masks, presentations,
 * selections, colour mapping settings, etc.) is not checked.
 *
 * \param object A GWY file data object, presumably the main
 *               <tt>GwyContainer</tt>.
 * \param nchannels Return location for the number of channels.
 * \return A newly allocated array with channel numbers.  It has to be freed
 *         later by the caller using free().  \c NULL is returned when the
 *         number of channels found is zero (this does not require any
 *         exception in the freeing rule though).
 */
int*
gwyfile_object_container_enumerate_channels(const GwyfileObject *object,
                                            unsigned int *nchannels)
{
    GwyfileIdList idlist = GWYFILE_ID_LIST_INIT;

    assert(object);
    assert(nchannels);

    if (!gwyfile_strequal(object->name, "GwyContainer")) {
        *nchannels = 0;
        return NULL;
    }

    gwyfile_object_foreach(object, gwyfile_add_channel_id, &idlist);
    qsort(idlist.ids, idlist.len, sizeof(int), &gwyfile_compare_int);

    *nchannels = idlist.len;
    return idlist.ids;
}

static void
gwyfile_add_volume_id(const GwyfileItem *item, void *user_data)
{
    GwyfileObject *object;
    const char *name;
    int id, xres, yres, zres;

    if (item->type != GWYFILE_ITEM_OBJECT)
        return;

    object = gwyfile_item_get_object(item);
    if (!gwyfile_object_brick_get(object, NULL,
                                  "xres", &xres,
                                  "yres", &yres,
                                  "zres", &zres,
                                  NULL))
        return;

    name = item->name;
    if ((id = gwyfile_extract_id(name, "/brick/%d")) >= 0) {
        GwyfileIdList *idlist = (GwyfileIdList*)user_data;
        gwyfile_id_list_add(idlist, id);
    }
}

/*!\fn int* gwyfile_object_container_enumerate_volume(const GwyfileObject *object, unsigned int *nvolume)
 * \brief Enumerates volume data in a Gwyddion GWY file.
 *
 * Volume data are considered valid and returned in the list if the data brick
 * exists.  The presence of auxiliary data is not checked.
 *
 * \param object A GWY file data object, presumably the main
 *               <tt>GwyContainer</tt>.
 * \param nvolume Return location for the number of volume data.
 * \return A newly allocated array with volume data numbers.  It has to be
 *         freed later by the caller using free().  \c NULL is returned when
 *         the number of volume data found is zero (this does not require any
 *         exception in the freeing rule though).
 */
int*
gwyfile_object_container_enumerate_volume(const GwyfileObject *object,
                                          unsigned int *nvolume)
{
    GwyfileIdList idlist = GWYFILE_ID_LIST_INIT;

    assert(object);
    assert(nvolume);

    if (!gwyfile_strequal(object->name, "GwyContainer")) {
        *nvolume = 0;
        return NULL;
    }

    gwyfile_object_foreach(object, gwyfile_add_volume_id, &idlist);
    qsort(idlist.ids, idlist.len, sizeof(int), &gwyfile_compare_int);

    *nvolume = idlist.len;
    return idlist.ids;
}

static void
gwyfile_add_graph_id(const GwyfileItem *item, void *user_data)
{
    GwyfileObject *object;
    GwyfileObject *const *curves;
    const char *name;
    int id, ncurves;

    if (item->type != GWYFILE_ITEM_OBJECT)
        return;

    object = gwyfile_item_get_object(item);
    if (!gwyfile_object_graphmodel_get(object, NULL,
                                       "ncurves", &ncurves,
                                       "curves", &curves,
                                       NULL))
        return;

    name = item->name;
    if ((id = gwyfile_extract_id(name, "/0/graph/graph/%d")) >= 1) {
        GwyfileIdList *idlist = (GwyfileIdList*)user_data;
        gwyfile_id_list_add(idlist, id);
    }
}

/*!\fn int* gwyfile_object_container_enumerate_graphs(const GwyfileObject *object, unsigned int *ngraphs)
 * \brief Enumerates graphs in a Gwyddion GWY file.
 *
 * Graphs are considered valid and returned in the list if the graph model
 * object exists.  The presence of auxiliary data is not checked.
 *
 * \param object A GWY file data object, presumably the main
 *               <tt>GwyContainer</tt>.
 * \param ngraphs Return location for the number of graphs.
 * \return A newly allocated array with graph numbers.  It has to be
 *         freed later by the caller using free().  \c NULL is returned when
 *         the number of graphs found is zero (this does not require any
 *         exception in the freeing rule though).
 */
int*
gwyfile_object_container_enumerate_graphs(const GwyfileObject *object,
                                          unsigned int *ngraphs)
{
    GwyfileIdList idlist = GWYFILE_ID_LIST_INIT;

    assert(object);
    assert(ngraphs);

    if (!gwyfile_strequal(object->name, "GwyContainer")) {
        *ngraphs = 0;
        return NULL;
    }

    gwyfile_object_foreach(object, gwyfile_add_graph_id, &idlist);
    qsort(idlist.ids, idlist.len, sizeof(int), &gwyfile_compare_int);

    *ngraphs = idlist.len;
    return idlist.ids;
}

static void
gwyfile_add_xyz_id(const GwyfileItem *item, void *user_data)
{
    GwyfileObject *object;
    const char *name;
    int id, n;

    if (item->type != GWYFILE_ITEM_OBJECT)
        return;

    object = gwyfile_item_get_object(item);
    if (!gwyfile_object_datafield_get(object, NULL, "n", &n, NULL))
        return;

    name = item->name;
    if ((id = gwyfile_extract_id(name, "/xyz/%d")) >= 0) {
        GwyfileIdList *idlist = (GwyfileIdList*)user_data;
        gwyfile_id_list_add(idlist, id);
    }
}

/*!\fn int* gwyfile_object_container_enumerate_xyz(const GwyfileObject *object, unsigned int *nxyz)
 * \brief Enumerates XYZ data in a Gwyddion GWY file.
 *
 * XYZ data are considered valid and returned in the list if its primary
 * surface object exists.  The presence of auxiliary data is not checked.
 *
 * \param object A GWY file data object, presumably the main
 *               <tt>GwyContainer</tt>.
 * \param nxyz Return location for the number of XYZ data.
 * \return A newly allocated array with XYZ data numbers.  It has to be freed
 *         later by the caller using free().  \c NULL is returned when the
 *         number of XYZ data found is zero (this does not require any
 *         exception in the freeing rule though).
 * \since 1.2
 */
int*
gwyfile_object_container_enumerate_xyz(const GwyfileObject *object,
                                       unsigned int *nxyz)
{
    GwyfileIdList idlist = GWYFILE_ID_LIST_INIT;

    assert(object);
    assert(nxyz);

    if (!gwyfile_strequal(object->name, "GwyContainer")) {
        *nxyz = 0;
        return NULL;
    }

    gwyfile_object_foreach(object, gwyfile_add_xyz_id, &idlist);
    qsort(idlist.ids, idlist.len, sizeof(int), &gwyfile_compare_int);

    *nxyz = idlist.len;
    return idlist.ids;
}

static void
gwyfile_add_spectra_id(const GwyfileItem *item, void *user_data)
{
    GwyfileObject *object, *data;
    const char *name;
    const double *coords;
    uint32_t ndata;
    int id;

    if (item->type != GWYFILE_ITEM_OBJECT)
        return;

    object = gwyfile_item_get_object(item);
    if (!gwyfile_object_spectra_get(object, NULL,
                                    "ndata", &ndata,
                                    "data", &data,
                                    "coords", &coords,
                                    NULL))
        return;

    name = item->name;
    if ((id = gwyfile_extract_id(name, "/sps/%d")) >= 0) {
        GwyfileIdList *idlist = (GwyfileIdList*)user_data;
        gwyfile_id_list_add(idlist, id);
    }
}

/*!\fn int* gwyfile_object_container_enumerate_spectra(const GwyfileObject *object, unsigned int *nspectra)
 * \brief Enumerates spectra in a Gwyddion GWY file.
 *
 * A spectra object is considered valid and returned in the list if it looks
 * sane.  The presence of auxiliary spectra data is not checked.
 *
 * \param object A GWY file data object, presumably the main
 *               <tt>GwyContainer</tt>.
 * \param nspectra Return location for the number of spectra.
 * \return A newly allocated array with spectra numbers.  It has to be freed
 *         later by the caller using free().  \c NULL is returned when the
 *         number of spectra found is zero (this does not require any
 *         exception in the freeing rule though).
 */
int*
gwyfile_object_container_enumerate_spectra(const GwyfileObject *object,
                                           unsigned int *nspectra)
{
    GwyfileIdList idlist = GWYFILE_ID_LIST_INIT;

    assert(object);
    assert(nspectra);

    if (!gwyfile_strequal(object->name, "GwyContainer")) {
        *nspectra = 0;
        return NULL;
    }

    gwyfile_object_foreach(object, gwyfile_add_spectra_id, &idlist);
    qsort(idlist.ids, idlist.len, sizeof(int), &gwyfile_compare_int);

    *nspectra = idlist.len;
    return idlist.ids;
}

/*!\fn void gwyfile_object_free(GwyfileObject *object)
 * \brief Frees a GWY file data object.
 *
 * All items contained in the object are freed recursively.  It is not
 * permitted to free an object present in a data item.
 *
 * You can pass \c NULL as \p object.  The function is then no-op.
 *
 * \param object A GWY file data object.
 */
void
gwyfile_object_free(GwyfileObject *object)
{
    if (!object)
        return;

    assert(!object->owner);

    while (object->nitems)
        gwyfile_object_remove_last(object, true);

    free(object->name);
    free(object->items);
    free(object);
}

/*!\fn const char* gwyfile_object_name(const GwyfileObject *object)
 * \brief Obtains the name of a GWY file data object.
 *
 * \param object A GWY file data object.
 * \return The object type name.  The returned string is owned by \p object
 *         and must not be modified or freed.
 */
const char*
gwyfile_object_name(const GwyfileObject *object)
{
    assert(object);
    return object->name;
}

/*!\fn size_t gwyfile_object_size(const GwyfileObject *object)
 * \brief Obtains the size of a GWY file data object.
 *
 * The size includes the size of object name and the size field itself.  See
 * gwyfile_object_data_size() for the size of just object data.
 *
 * \param object A GWY file data object.
 * \return The object size, in bytes.
 */
size_t
gwyfile_object_size(const GwyfileObject *object)
{
    assert(object);
    return object->name_len+1 + sizeof(uint32_t) + object->data_size;
}

/*!\fn size_t gwyfile_object_data_size(const GwyfileObject *object)
 * \brief Obtains the data size of a GWY file data object.
 *
 * This is the size value stored in GWY files size and does not include the
 * size of object name and the size field itself.
 *
 * \param object A GWY file data object.
 * \return The object data size, in bytes.
 */
size_t
gwyfile_object_data_size(const GwyfileObject *object)
{
    assert(object);
    return object->data_size;
}

/*!\fn bool gwyfile_object_add(GwyfileObject *object, GwyfileItem *item)
 * \brief Adds an data item to a GWY file data object.
 *
 * If no item of the same name exists in this object, the item will be consumed
 * by the object that will take care of freeing it later.  Generally, you
 * should not access the item after passing it to this function as there is no
 * guarantee when it will be freed.
 *
 * If an item of the same name already exists in this object, the function
 * will return \c false and keep the existing item.  Note this means the \p
 * item may be leaked if you do not check the return value.
 *
 * \param object A GWY file data object.
 * \param item A GWY file data item that is not present in any object.
 * \return \c true if the item was actually added.
 */
bool
gwyfile_object_add(GwyfileObject *object, GwyfileItem *item)
{
    GwyfileItem **items;
    unsigned int i, nitems;

    assert(object);
    assert(item);
    assert(!item->owner);

    nitems = object->nitems;
    items = object->items;
    for (i = 0; i < nitems; i++) {
        /* Fail is there is an existing item of the same name. */
        if (gwyfile_strequal(items[i]->name, item->name))
            return false;
    }

    gwyfile_object_append(object, item);
    return true;
}

static unsigned int
gwyfile_object_find(const GwyfileObject *object, const char *name)
{
    GwyfileItem **items = object->items;
    unsigned int i, nitems;

    nitems = object->nitems;
    for (i = 0; i < nitems; i++) {
        if (gwyfile_strequal(items[i]->name, name))
            return i;
    }

    return nitems;
}

static unsigned int
gwyfile_object_find_with_type(const GwyfileObject *object,
                              const char *name, GwyfileItemType type)
{
    GwyfileItem **items = object->items;
    unsigned int i, nitems;

    nitems = object->nitems;
    for (i = 0; i < nitems; i++) {
        if (items[i]->type == type && gwyfile_strequal(items[i]->name, name))
            return i;
    }

    return nitems;
}

/*!\fn bool gwyfile_object_remove(GwyfileObject *object, const char *name)
 * \brief Removes an item from a GWY file data object and frees it.
 *
 * \param object A GWY file data object.
 * \param name Name of data item to remove.
 * \return Whether such item was present and was removed.
 */
bool
gwyfile_object_remove(GwyfileObject *object,
                      const char *name)
{
    unsigned int i, nitems;

    assert(object);
    assert(name);

    nitems = object->nitems;
    if ((i = gwyfile_object_find(object, name)) < nitems) {
        GwyfileItem **items = object->items;
        if (i < nitems-1) {
            GwyfileItem *item = items[i];
            items[i] = items[nitems-1];
            items[nitems-1] = item;
        }
        gwyfile_object_remove_last(object, true);
        return true;
    }

    return false;
}

/*!\fn GwyfileItem* gwyfile_object_get(const GwyfileObject *object, const char *name)
 * \brief Finds a data item in a GWY file object.
 *
 * This function looks up the item by name.  If you want to ensure the item is
 * also of a specified type, use gwyfile_object_get_with_type().
 *
 * \param object A GWY file data object.
 * \param name Name of data item to find.
 * \return The item, if found.  Otherwise \c NULL is returned.
 */
GwyfileItem*
gwyfile_object_get(const GwyfileObject *object,
                   const char *name)
{
    unsigned int i, nitems;

    assert(object);
    assert(name);

    nitems = object->nitems;
    if ((i = gwyfile_object_find(object, name)) < nitems)
        return object->items[i];

    return NULL;
}

/*!\fn GwyfileItem* gwyfile_object_take(GwyfileObject *object, const char *name)
 * \brief Takes an item from a GWY file data object.
 *
 * The caller becomes the owner of the returned item and is responsible for
 * freeing it later.
 *
 * \param object A GWY file data object.
 * \param name Name of data item to take.
 * \return The item, if found.  Otherwise \c NULL is returned.
 */
GwyfileItem*
gwyfile_object_take(GwyfileObject *object,
                    const char *name)
{
    unsigned int i, nitems;

    assert(object);
    assert(name);

    nitems = object->nitems;
    if ((i = gwyfile_object_find(object, name)) < nitems) {
        GwyfileItem **items = object->items;
        GwyfileItem *item = items[i];
        if (i < nitems-1) {
            items[i] = items[nitems-1];
            items[nitems-1] = item;
        }
        gwyfile_object_remove_last(object, false);
        return item;
    }

    return NULL;
}

/*!\fn GwyfileItem* gwyfile_object_get_with_type(const GwyfileObject *object, const char *name, GwyfileItemType type)
 * \brief Finds a data item in a GWY file object, ensuring its type.
 *
 * This function returns an item only if both its name and type match the
 * arguments.
 *
 * \param object A GWY file data object.
 * \param name Name of data item to find.
 * \param type Type of the item to find.
 * \return The item, if found.  Otherwise \c NULL is returned.
 * \sa gwyfile_object_take_with_type
 */
GwyfileItem*
gwyfile_object_get_with_type(const GwyfileObject *object,
                             const char *name,
                             GwyfileItemType type)
{
    unsigned int i, nitems;

    assert(object);
    assert(name);

    nitems = object->nitems;
    if ((i = gwyfile_object_find_with_type(object, name, type)) < nitems)
        return object->items[i];

    return NULL;
}

/*!\fn GwyfileItem* gwyfile_object_take_with_type(GwyfileObject *object, const char *name, GwyfileItemType type)
 * \brief Takes a data item from a GWY file object, ensuring its type.
 *
 * This function returns an item only if both its name and type match the
 * arguments.
 *
 * The caller becomes the owner of the returned item and is responsible for
 * freeing it later.
 *
 * \param object A GWY file data object.
 * \param name Name of data item to find.
 * \param type Type of the item to find.
 * \return The item, if found.  Otherwise \c NULL is returned.
 * \sa gwyfile_object_get_with_type
 */
GwyfileItem*
gwyfile_object_take_with_type(GwyfileObject *object,
                              const char *name,
                              GwyfileItemType type)
{
    unsigned int i, nitems;

    assert(object);
    assert(name);

    nitems = object->nitems;
    if ((i = gwyfile_object_find_with_type(object, name, type)) < nitems) {
        GwyfileItem **items = object->items;
        GwyfileItem *item = items[i];
        if (i < nitems-1) {
            items[i] = items[nitems-1];
            items[nitems-1] = item;
        }
        gwyfile_object_remove_last(object, false);
        return item;
    }

    return NULL;
}

/*!\fn void gwyfile_object_foreach(const GwyfileObject *object, GwyfileObjectForeachFunc function, void *user_data)
 * \param object A GWY file data object.
 * \param function Function to call for each item in the object.
 * \param user_data Data passed to the function.
 * \brief Calls a function for each item contained in a GWY file data object.
 *
 * The function must not add items to \p object and it must not remove items
 * either.  And, of course, it must not cause \p object to be freed.
 */
void
gwyfile_object_foreach(const GwyfileObject *object,
                       GwyfileObjectForeachFunc function,
                       void *user_data)
{
    GwyfileItem **items;
    unsigned int i, nitems;

    assert(object);
    assert(function);

    nitems = object->nitems;
    items = object->items;
    for (i = 0; i < nitems; i++)
        function(items[i], user_data);
}

/*!\fn unsigned int gwyfile_object_nitems(const GwyfileObject *object)
 * \param object A GWY file data object.
 * \brief Obtains the number of items in a GWY file data object.
 *
 * This function is intended to be used in conjunction with
 * gwyfile_object_item_names() or possibly gwyfile_object_foreach().
 *
 * \return The number of items in \p object.
 */
unsigned int
gwyfile_object_nitems(const GwyfileObject *object)
{
    assert(object);
    return object->nitems;
}

/*!\fn const char** gwyfile_object_item_names(const GwyfileObject *object)
 * \param object A GWY file data object.
 * \brief Constructs the list of names of all items in a GWY file data object.
 *
 * Note the called must free the array with free() when no longer needed, but
 * the strings within remain owned by \p object and are generally only
 * guaranteed to be valid until \p object is changed.
 *
 * \return A newly allocated array with names of all items in \p object.
 *         When there are no items \c NULL is returned.
 *         Upon memory allocation failure \c NULL is returned and \c errno is
 *         set to <tt>ENOMEM</tt>.
 */
const char**
gwyfile_object_item_names(const GwyfileObject *object)
{
    const char **names;
    unsigned int i;

    assert(object);
    if (!object->nitems)
        return NULL;

    names = malloc(object->nitems*sizeof(const char**));
    if (!names) {
        errno = ENOMEM;   /* Generally not guaranteed by OS. */
        return NULL;
    }
    for (i = 0; i < object->nitems; i++)
        names[i] = object->items[i]->name;

    return names;
}

/*!\fn bool gwyfile_object_fwrite(GwyfileObject *object, FILE *stream, GwyfileError **error)
 * \brief Writes a GWY file data object to a stdio stream.
 *
 * The stream does not have to be seekable.
 *
 * On success, the position indicator in \p stream will be pointed after the
 * end of the written object.
 *
 * On failure, the position indicator state in \p stream is undefined.
 *
 * \param object A GWY file data object.
 * \param stream C stdio stream to write the object to.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \return \c true if the writing succeeded.
 */
bool
gwyfile_object_fwrite(GwyfileObject *object,
                      FILE *stream,
                      GwyfileError **error)
{
    GwyfileItem **items;
    unsigned int i, nitems, name_len;

    assert(object);
    assert(stream);
    name_len = object->name_len;

    if (object->data_size > (size_t)0xffffffffu - sizeof(uint32_t) - name_len) {
        if (error) {
            char *path = gwyfile_format_path(object, NULL);
            gwyfile_set_error(error,
                              GWYFILE_ERROR_DOMAIN_DATA,
                              GWYFILE_ERROR_OBJECT_SIZE,
                              "Object %s size does not fit into 32bit integer.",
                              path);
            free(path);
        }
        return false;
    }

    if (fwrite(object->name, 1, name_len+1, stream) != name_len+1) {
        gwyfile_set_error_errno(error);
        return false;
    }

    if (!gwyfile_fwrite_le(&object->data_size, sizeof(int32_t), 1, stream)) {
        gwyfile_set_error_errno(error);
        return false;
    }

    nitems = object->nitems;
    items = object->items;
    for (i = 0; i < nitems; i++) {
        if (!gwyfile_item_fwrite(items[i], stream, error))
            return false;
    }

    return true;
}

static GwyfileObject*
gwyfile_object_fread_internal(FILE *stream,
                              size_t max_size,
                              uint32_t depth,
                              GwyfileObject *owner,
                              GwyfileError **error)
{
    GwyfileObject *object;
    const char *dupname;
    char *name;
    uint32_t data_size;

    assert(stream);
    if (depth >= GWYFILE_MAX_DEPTH) {
        if (error) {
            char *path = gwyfile_format_path(owner, NULL);
            gwyfile_set_error(error,
                              GWYFILE_ERROR_DOMAIN_DATA,
                              GWYFILE_ERROR_TOO_DEEP_NESTING,
                              "Too deep object/item nesting in %s.",
                              path);
            free(path);
        }
        return NULL;
    }

    if (!(name = gwyfile_fread_string(stream, &max_size, error, "object name")))
        return NULL;

    if (!gwyfile_check_size(&max_size, sizeof(uint32_t), error, "size field")) {
        free(name);
        return NULL;
    }

    if (!gwyfile_fread_le(&data_size, sizeof(uint32_t), 1, stream)) {
        gwyfile_set_error_fread(error, stream, "size field");
        free(name);
        return NULL;
    }
    if (max_size < data_size) {
        gwyfile_set_error_overrun(error, "object data");
        free(name);
        return NULL;
    }
    /* We can actually have an empty object.  Unlike empty arrays, this is
     * silly but permitted.  So do not fail immediately when max_size == 0. */

    object = gwyfile_object_new_internal(name, true);

    /* NB: We do not count bytes read from the file.  The reconstruction should
     * be sufficiently strict so that we either can write byte-for-byte copy
     * of the file content; or we report failure.  This means things like
     * duplicate or unknown items cannot be tolerated though if could skip
     * the item or its object.  */
    while (object->data_size < data_size) {
        uint32_t remaining_size = data_size - object->data_size;
        GwyfileItem *item = gwyfile_item_fread_internal(stream, remaining_size,
                                                        depth+1, object, error);
        if (!item) {
            gwyfile_object_free(object);
            return NULL;
        }
        gwyfile_object_append(object, item);
    }
    assert(object->data_size == data_size);

    if ((dupname = gwyfile_object_find_duplicate_item(object))) {
        if (error) {
            unsigned int i = gwyfile_object_find(object, dupname);
            GwyfileItem *item = object->items[i];
            char *path, *ipath;

            /* The ownership tree is not set up yet.  Try to produce
             * a meaningful error message despite. */
            path = gwyfile_format_path(owner, NULL);
            item->owner = NULL;
            ipath = gwyfile_format_path(NULL, item);
            item->owner = object;

            gwyfile_set_error(error,
                              GWYFILE_ERROR_DOMAIN_DATA,
                              GWYFILE_ERROR_DUPLICATE_NAME,
                              "Duplicate item %s in %s.",
                              ipath, path);
            free(ipath);
            free(path);
        }
        gwyfile_object_free(object);
        return NULL;
    }

    return object;
}

/*!\fn GwyfileObject* gwyfile_object_fread(FILE *stream, size_t max_size, GwyfileError **error)
 * \brief Reads a GWY file data object from a stdio stream.
 *
 * The stream does not have to be seekable.
 *
 * On success, the position indicator in \p stream will be pointed after the
 * end of the object.
 *
 * On failure, the position indicator state in \p stream is undefined.
 *
 * The maximum number of bytes to read is given by \p max_size which is of type
 * <tt>size_t</tt>, however, be aware that sizes in GWY files are only 32bit.
 * So any value that does not fit into a 32bit integer means the same as
 * <tt>SIZE_MAX</tt>.
 *
 * If reading more than \p max_size bytes would be required to reconstruct the
 * top-level object, the function fails with
 * GwyfileErrorCode::GWYFILE_ERROR_CONFINEMENT error in the
 * GwyfileErrorDomain::GWYFILE_ERROR_DOMAIN_DATA domain.
 *
 * \param stream C stdio stream to read the GWY file from.
 * \param max_size Maximum number of bytes to read.  Pass \c SIZE_MAX for
 *                 unconstrained reading.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \return The reconstructed data object, or \c NULL if the reading or
 *         reconstruction fails.
 */
GwyfileObject*
gwyfile_object_fread(FILE *stream,
                     size_t max_size,
                     GwyfileError **error)
{
    return gwyfile_object_fread_internal(stream, max_size, 0, NULL, error);
}

/*!\fn GwyfileItem* gwyfile_item_new_bool(const char *name, bool value)
 * \brief Creates a new boolean GWY file item.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value.
 * \return The newly created GWY file data item.
 */
GwyfileItem*
gwyfile_item_new_bool(const char *name,
                      bool value)
{
    assert(name);
    return gwyfile_item_new_internal_bool(name, false, value);
}

/*!\fn void gwyfile_item_set_bool(GwyfileItem *item, bool value)
 * \brief Sets the value of a boolean GWY file item.
 *
 * The item must be of the boolean type.
 *
 * \param item A boolean GWY file data item.
 * \param value New value for the item.
 */
void
gwyfile_item_set_bool(GwyfileItem *item,
                      bool value)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_BOOL);
    item->v.b = value;
}

/*!\fn bool gwyfile_item_get_bool(const GwyfileItem *item)
 * \brief Gets the boolean value contained in a GWY file data item.
 *
 * The item must be of the boolean type.  Use gwyfile_item_type() to check item
 * type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A boolean GWY file data item.
 * \return The boolean value of \p item.
 */
bool
gwyfile_item_get_bool(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_BOOL);
    return item->v.b;
}

/*!\fn GwyfileItem* gwyfile_item_new_char(const char *name, char value)
 * \brief Creates a new character GWY file item.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value.
 * \return The newly created GWY file data item.
 */
GwyfileItem*
gwyfile_item_new_char(const char *name,
                      char value)
{
    assert(name);
    return gwyfile_item_new_internal_char(name, false, value);
}

/*!\fn void gwyfile_item_set_char(GwyfileItem *item, char value)
 * \brief Sets the value of a character GWY file item.
 *
 * The item must be of the character type.
 *
 * \param item A character GWY file data item.
 * \param value New value for the item.
 */
void
gwyfile_item_set_char(GwyfileItem *item,
                      char value)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_CHAR);
    item->v.c = value;
}

/*!\fn char gwyfile_item_get_char(const GwyfileItem *item)
 * \brief Gets the character value contained in a GWY file data item.
 *
 * The item must be of the character type.  Use gwyfile_item_type() to check
 * item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A character GWY file data item.
 * \return The character value of \p item.
 */
char
gwyfile_item_get_char(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_CHAR);
    return item->v.c;
}

/*!\fn GwyfileItem* gwyfile_item_new_int32(const char *name, int32_t value)
 * \brief Creates a new 32bit integer GWY file item.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value.
 * \return The newly created GWY file data item.
 */
GwyfileItem*
gwyfile_item_new_int32(const char *name,
                       int32_t value)
{
    assert(name);
    return gwyfile_item_new_internal_int32(name, false, value);
}

/*!\fn void gwyfile_item_set_int32(GwyfileItem *item, int32_t value)
 * \brief Sets the value of a 32bit integer GWY file item.
 *
 * The item must be of the 32bit integer type.
 *
 * \param item A 32bit integer GWY file data item.
 * \param value New value for the item.
 */
void
gwyfile_item_set_int32(GwyfileItem *item,
                       int32_t value)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_INT32);
    item->v.i = value;
}

/*!\fn int32_t gwyfile_item_get_int32(const GwyfileItem *item)
 * \brief Gets the 32bit integer value contained in a GWY file data item.
 *
 * The item must be of the 32bit integer type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A 32bit integer GWY file data item.
 * \return The 32bit integer value of \p item.
 */
int32_t
gwyfile_item_get_int32(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_INT32);
    return item->v.i;
}

/*!\fn GwyfileItem* gwyfile_item_new_int64(const char *name, int64_t value)
 * \brief Creates a new 64bit integer GWY file item.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value.
 * \return The newly created GWY file data item.
 */
GwyfileItem*
gwyfile_item_new_int64(const char *name,
                       int64_t value)
{
    assert(name);
    return gwyfile_item_new_internal_int64(name, false, value);
}

/*!\fn void gwyfile_item_set_int64(GwyfileItem *item, int64_t value)
 * \brief Sets the value of a 64bit integer GWY file item.
 *
 * The item must be of the 64bit integer type.
 *
 * \param item A 64bit integer GWY file data item.
 * \param value New value for the item.
 */
void
gwyfile_item_set_int64(GwyfileItem *item,
                       int64_t value)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_INT64);
    item->v.q = value;
}

/*!\fn int64_t gwyfile_item_get_int64(const GwyfileItem *item)
 * \brief Gets the 64bit integer value contained in a GWY file data item.
 *
 * The item must be of the 64bit integer type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A 64bit integer GWY file data item.
 * \return The 64bit integer value of \p item.
 */
int64_t
gwyfile_item_get_int64(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_INT64);
    return item->v.q;
}

/*!\fn GwyfileItem* gwyfile_item_new_double(const char *name, double value)
 * \brief Creates a new double GWY file item.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value.
 * \return The newly created GWY file data item.
 */
GwyfileItem*
gwyfile_item_new_double(const char *name,
                        double value)
{
    assert(name);
    return gwyfile_item_new_internal_double(name, false, value);
}

/*!\fn void gwyfile_item_set_double(GwyfileItem *item, double value)
 * \brief Sets the value of a double GWY file item.
 *
 * The item must be of the double type.
 *
 * \param item A double GWY file data item.
 * \param value New value for the item.
 */
void
gwyfile_item_set_double(GwyfileItem *item,
                        double value)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_DOUBLE);
    item->v.d = value;
}

/*!\fn double gwyfile_item_get_double(const GwyfileItem *item)
 * \brief Gets the double value contained in a GWY file data item.
 *
 * The item must be of the double type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A double GWY file data item.
 * \return The double value of \p item.
 */
double
gwyfile_item_get_double(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_DOUBLE);
    return item->v.d;
}

/*!\fn GwyfileItem* gwyfile_item_new_string(const char *name, char *value)
 * \brief Creates a new string GWY file item.
 *
 * The item consumes the provided string and takes care of freeing it later.
 * You must not touch the string any more; it can be already freed when this
 * function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be consumed).  It must be a UTF-8-encoded
 *              string.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_string_copy gwyfile_item_new_string_const
 */
GwyfileItem*
gwyfile_item_new_string(const char *name,
                        char *value)
{
    assert(name);
    assert(value);
    return gwyfile_item_new_internal_string(name, false, value);
}

/*!\fn void gwyfile_item_set_string(GwyfileItem *item, char *value)
 * \brief Sets the value of a string GWY file item.
 *
 * The item must be of the string type.
 *
 * The item consumes the provided string and takes care of freeing it later.
 * You must not touch the string any more; it can be already freed when this
 * function returns.
 *
 * \param item A string GWY file data item.
 * \param value New value for the item (to be consumed).
 * \sa gwyfile_item_set_string_copy gwyfile_item_set_string_const
 */
void
gwyfile_item_set_string(GwyfileItem *item,
                        char *value)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING);
    assert(value);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.s);
    item->data_size = strlen(value) + 1;
    item->v.s = value;
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_string_copy(const char *name, const char *value)
 * \brief Creates a new string GWY file item.
 *
 * This function makes a copy the provided string.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be copied).  It must be a UTF-8-encoded string.
 * \return The newly created GWY file data item.
 *         Upon memory allocation failure \c NULL is returned and \c errno is
 *         set to <tt>ENOMEM</tt>.
 * \sa gwyfile_item_new_string gwyfile_item_new_string_const
 */
GwyfileItem*
gwyfile_item_new_string_copy(const char *name,
                             const char *value)
{
    assert(name);
    assert(value);
    return gwyfile_item_new_internal_string_copy(name, false, value);
}

/*!\fn void gwyfile_item_set_string_copy(GwyfileItem *item, const char *value)
 * \brief Sets the value of a string GWY file item.
 *
 * The item must be of the string type.
 *
 * This function makes a copy the provided string.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param item A string GWY file data item.
 * \param value New value for the item (to be copied).
 * \sa gwyfile_item_set_string gwyfile_item_set_string_const
 */
void
gwyfile_item_set_string_copy(GwyfileItem *item,
                             const char *value)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING);
    assert(value);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.s);
    item->data_size = strlen(value) + 1;
    item->v.s = gwyfile_memdup(value, item->data_size);
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_string_const(const char *name, const char *value)
 * \brief Creates a new string GWY file item.
 *
 * The string must exist for the entire lifetime of the item and its length
 * must not change.  Hence this function is best for actual constant strings,
 * however, it can be also used with other strings whose lifetime is
 * guaranteed.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be used as-is).  It must be a UTF-8-encoded
 *              string.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_string gwyfile_item_new_string_copy
 */
GwyfileItem*
gwyfile_item_new_string_const(const char *name,
                              const char *value)
{
    assert(name);
    assert(value);
    GwyfileItem *item = gwyfile_item_new_internal_string(name, false,
                                                         (char*)value);
    item->data_owned = false;
    return item;
}

/*!\fn void gwyfile_item_set_string_const(GwyfileItem *item, const char *value)
 * \brief Sets the value of a string GWY file item.
 *
 * The item must be of the string type.
 *
 * The string must exist for the entire lifetime of the item and its length
 * must not change.  Hence this function is best for actual constant strings,
 * however, it can be also used with other strings whose lifetime is
 * guaranteed.
 *
 * \param item A string GWY file data item.
 * \param value New value for the item (to be used as-is).
 * \sa gwyfile_item_set_string gwyfile_item_set_string_copy
 */
void
gwyfile_item_set_string_const(GwyfileItem *item,
                              const char *value)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING);
    assert(value);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.s);
    item->data_size = strlen(value) + 1;
    item->v.s = (char*)value;
    item->data_owned = false;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn const char* gwyfile_item_get_string(const GwyfileItem *item)
 * \brief Gets the string value contained in a GWY file data item.
 *
 * The item must be of the string type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A string GWY file data item.
 * \return The string value of \p item.  The string ownership does not change.
 * \sa gwyfile_item_take_string
 */
const char*
gwyfile_item_get_string(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING);
    return item->v.s;
}

/*!\fn char* gwyfile_item_take_string(GwyfileItem *item)
 * \brief Takes the string value contained in a GWY file data item.
 *
 * The item must own the string when this function is called.  The ownership is
 * transferred to the caller who becomes responsible to freeing it later.  The
 * string can still be obtained with gwyfile_item_get_string() but,
 * obviously, it cannot be taken again.
 *
 * The item must be of the string type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A string GWY file data item.
 * \return The string value of \p item.  The string becomes owned by the
 *         caller.
 * \sa gwyfile_item_get_string
 */
char*
gwyfile_item_take_string(GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING);
    assert(item->data_owned);
    item->data_owned = false;
    return item->v.s;
}

/*!\fn GwyfileItem* gwyfile_item_new_object(const char *name, GwyfileObject *object)
 * \brief Creates a new object GWY file item.
 *
 * The item consumes the provied object and will take care of freeing it later.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be consumed).  The object must not be placed
 *              in any item yet.
 * \return The newly created GWY file data item.
 */
GwyfileItem*
gwyfile_item_new_object(const char *name,
                        GwyfileObject *value)
{
    assert(name);
    assert(value);
    assert(!value->owner);
    return gwyfile_item_new_internal_object(name, false, value);
}

/*!\fn void gwyfile_item_set_object(GwyfileItem *item, GwyfileObject *value)
 * \brief Sets the value of an object GWY file item.
 *
 * The item must be of the object type.
 *
 * The item consumes the provied object and will take care of freeing it later.
 * It is not permitted to pass an object already present in another item.
 *
 * \param item An object GWY file data item.
 * \param value New value for the item (to be consumed).
 */
void
gwyfile_item_set_object(GwyfileItem *item,
                        GwyfileObject *value)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_OBJECT);
    assert(value);
    assert(!value->owner);
    oldsize = item->data_size;
    gwyfile_object_free(item->v.o);
    item->data_size = gwyfile_object_size(value);
    item->v.o = value;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileObject* gwyfile_item_get_object(const GwyfileItem *item)
 * \brief Gets the object value contained in a GWY file data item.
 *
 * The item must be of the object type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item An object GWY file data item.
 * \return The object value of \p item.  The object remains owned by \p item.
 */
GwyfileObject*
gwyfile_item_get_object(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_OBJECT);
    return item->v.o;
}

/*!\fn GwyfileObject* gwyfile_item_release_object(GwyfileItem *item)
 * \brief Releases the object contained in a GWY file data item and frees
 *        the item.
 *
 * The item must be of the object type.   It must be also a root, i.e. not be
 * contained in any object.  The object is released from the item, becoming a
 * new root object, and the item is freed.
 *
 * \param item A root object GWY file data item.
 * \return The object value of \p item.
 * \sa gwyfile_item_free gwyfile_item_get_object gwyfile_object_take
 */
GwyfileObject*
gwyfile_item_release_object(GwyfileItem *item)
{
    GwyfileObject *object;
    assert(item);
    assert(item->type == GWYFILE_ITEM_OBJECT);
    assert(!item->owner);
    object = item->v.o;
    object->owner = NULL;
    item->data_owned = false;
    gwyfile_item_free(item);
    return object;
}

/*!\fn GwyfileItem* gwyfile_item_new_char_array(const char *name, char *value, uint32_t array_length)
 * \brief Creates a new character array GWY file item.
 *
 * The item consumes the provided array and takes care of freeing it later.
 * You must not touch the array any more; it can be already freed when this
 * function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_char_array_copy gwyfile_item_new_char_array_const
 */
GwyfileItem*
gwyfile_item_new_char_array(const char *name,
                            char *value,
                            uint32_t array_length)
{
    assert(name);
    assert(value);
    assert(array_length);
    return gwyfile_item_new_internal_char_array(name, false,
                                                value, array_length);
}

/*!\fn void gwyfile_item_set_char_array(GwyfileItem *item, char *value, uint32_t array_length)
 * \brief Sets the value of a character array GWY file item.
 *
 * The item must be of the character array type.
 *
 * The item consumes the provided character array and takes care of freeing it
 * later.  You must not touch the array any more; it can be already freed when
 * this function returns.
 *
 * \param item A character array GWY file data item.
 * \param value New value for the item (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_char_array_copy gwyfile_item_set_char_array_const
 */
void
gwyfile_item_set_char_array(GwyfileItem *item,
                            char *value,
                            uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_CHAR_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.ca);
    item->data_size = sizeof(uint32_t) + array_length;
    item->array_length = array_length;
    item->v.ca = value;
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_char_array_copy(const char *name, const char *value, uint32_t array_length)
 * \brief Creates a new character array GWY file item.
 *
 * This function makes a copy the provided array.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 *         Upon memory allocation failure \c NULL is returned and \c errno is
 *         set to <tt>ENOMEM</tt>.
 * \sa gwyfile_item_new_char_array gwyfile_item_new_char_array_const
 */
GwyfileItem*
gwyfile_item_new_char_array_copy(const char *name,
                                 const char *value,
                                 uint32_t array_length)
{
    char *valuecopy;

    assert(name);
    assert(value);
    assert(array_length);
    valuecopy = gwyfile_memdup(value, array_length*sizeof(char));
    if (!valuecopy)
        return NULL;
    return gwyfile_item_new_internal_char_array(name, false,
                                                valuecopy, array_length);
}

/*!\fn void gwyfile_item_set_char_array_copy(GwyfileItem *item, const char *value, uint32_t array_length)
 * \brief Sets the value of a character array GWY file item.
 *
 * The item must be of the character array type.
 *
 * This function makes a copy the provided array.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param item A character array GWY file data item.
 * \param value New value for the item (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_char_array gwyfile_item_set_char_array_const
 */
void
gwyfile_item_set_char_array_copy(GwyfileItem *item,
                                 const char *value,
                                 uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_CHAR_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.ca);
    item->data_size = sizeof(uint32_t) + array_length;
    item->array_length = array_length;
    item->v.ca = gwyfile_memdup(value, array_length);
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_char_array_const(const char *name, const char *value, uint32_t array_length)
 * \brief Creates a new character array GWY file item.
 *
 * The array must exist for the entire lifetime of the item.  Hence this
 * function is best for actual constant arrays, however, it can be also used
 * with other arrays whose lifetime is guaranteed.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_char_array gwyfile_item_new_char_array_copy
 */
GwyfileItem*
gwyfile_item_new_char_array_const(const char *name,
                                  const char *value,
                                  uint32_t array_length)
{
    GwyfileItem *item;

    assert(name);
    assert(value);
    assert(array_length);
    item = gwyfile_item_new_internal_char_array(name, false,
                                                (char*)value, array_length);
    item->data_owned = false;
    return item;
}

/*!\fn void gwyfile_item_set_char_array_const(GwyfileItem *item, const char *value, uint32_t array_length)
 * \brief Sets the value of a character array GWY file item.
 *
 * The item must be of the character array type.
 *
 * The array must exist for the entire lifetime of the item.  Hence this
 * function is best for actual constant arrays, however, it can be also used
 * with other arrays whose lifetime is guaranteed.
 *
 * \param item A character array GWY file data item.
 * \param value New value for the item (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_char_array gwyfile_item_set_char_array_copy
 */
void
gwyfile_item_set_char_array_const(GwyfileItem *item,
                                  const char *value,
                                  uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_CHAR_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.ca);
    item->data_size = sizeof(uint32_t) + array_length;
    item->array_length = array_length;
    item->v.ca = (char*)value;
    item->data_owned = false;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn const char* gwyfile_item_get_char_array(const GwyfileItem *item)
 * \brief Gets the character array value contained in a GWY file data item.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the character array type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A character array GWY file data item.
 * \return The character array value of \p item.  The array ownership does not
 *         change.
 * \sa gwyfile_item_take_char_array
 */
const char*
gwyfile_item_get_char_array(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_CHAR_ARRAY);
    return item->v.ca;
}

/*!\fn char* gwyfile_item_take_char_array(GwyfileItem *item)
 * \brief Takes the character array value contained in a GWY file data item.
 *
 * The item must own the array when this function is called.  The ownership is
 * transferred to the caller who becomes responsible to freeing it later.  The
 * array can still be obtained with gwyfile_item_get_char_array() but,
 * obviously, it cannot be taken again.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the character array type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A character array GWY file data item.
 * \return The character array value of \p item.  The array becomes owned by
 *         the caller.
 * \sa gwyfile_item_get_char_array
 */
char*
gwyfile_item_take_char_array(GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_CHAR_ARRAY);
    assert(item->data_owned);
    item->data_owned = false;
    return item->v.ca;
}

/*!\fn GwyfileItem* gwyfile_item_new_int32_array(const char *name, int32_t *value, uint32_t array_length)
 * \brief Creates a new 32bit integer array GWY file item.
 *
 * The item consumes the provided array and takes care of freeing it later.
 * You must not touch the array any more; it can be already freed when this
 * function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_int32_array_copy
 */
GwyfileItem*
gwyfile_item_new_int32_array(const char *name,
                             int32_t *value,
                             uint32_t array_length)
{
    assert(name);
    assert(value);
    assert(array_length);
    return gwyfile_item_new_internal_int32_array(name, false,
                                                 value, array_length);
}

/*!\fn void gwyfile_item_set_int32_array(GwyfileItem *item, int32_t *value, uint32_t array_length)
 * \brief Sets the value of a 32bit integer array GWY file item.
 *
 * The item must be of the 32bit integer array type.
 *
 * The item consumes the provided 32bit integer array and takes care of freeing
 * it later.  You must not touch the array any more; it can be already freed
 * when this function returns.
 *
 * \param item A 32bit integer array GWY file data item.
 * \param value New value for the item (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_int32_array_copy
 */
void
gwyfile_item_set_int32_array(GwyfileItem *item,
                             int32_t *value,
                             uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_INT32_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.ia);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(int32_t);
    item->array_length = array_length;
    item->v.ia = value;
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_int32_array_copy(const char *name, const int32_t *value, uint32_t array_length)
 * \brief Creates a new 32bit integer array GWY file item.
 *
 * This function makes a copy the provided array.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 *         Upon memory allocation failure \c NULL is returned and \c errno is
 *         set to <tt>ENOMEM</tt>.
 * \sa gwyfile_item_new_int32_array
 */
GwyfileItem*
gwyfile_item_new_int32_array_copy(const char *name,
                                  const int32_t *value,
                                  uint32_t array_length)
{
    int32_t *valuecopy;

    assert(name);
    assert(value);
    assert(array_length);
    valuecopy = gwyfile_memdup(value, array_length*sizeof(int32_t));
    if (!valuecopy)
        return NULL;
    return gwyfile_item_new_internal_int32_array(name, false,
                                                 valuecopy, array_length);
}

/*!\fn void gwyfile_item_set_int32_array_copy(GwyfileItem *item, const int32_t *value, uint32_t array_length)
 * \brief Sets the value of a 32bit integer array GWY file item.
 *
 * The item must be of the 32bit integer array type.
 *
 * This function makes a copy the provided array.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param item A 32bit integer array GWY file data item.
 * \param value New value for the item (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_int32_array
 */
void
gwyfile_item_set_int32_array_copy(GwyfileItem *item,
                                  const int32_t *value,
                                  uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_INT32_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.ia);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(int32_t);
    item->array_length = array_length;
    item->v.ia = gwyfile_memdup(value, array_length*sizeof(int32_t));
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_int32_array_const(const char *name, const int32_t *value, uint32_t array_length)
 * \brief Creates a new 32bit integer array GWY file item.
 *
 * The array must exist for the entire lifetime of the item.  Hence this
 * function is best for actual constant arrays, however, it can be also used
 * with other arrays whose lifetime is guaranteed.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_int32_array gwyfile_item_new_int32_array_copy
 */
GwyfileItem*
gwyfile_item_new_int32_array_const(const char *name,
                                   const int32_t *value,
                                   uint32_t array_length)
{
    GwyfileItem *item;

    assert(name);
    assert(value);
    assert(array_length);
    item = gwyfile_item_new_internal_int32_array(name, false,
                                                 (int32_t*)value, array_length);
    item->data_owned = false;
    return item;
}

/*!\fn void gwyfile_item_set_int32_array_const(GwyfileItem *item, const int32_t *value, uint32_t array_length)
 * \brief Sets the value of a 32bit integer array GWY file item.
 *
 * The item must be of the 32bit integer array type.
 *
 * The array must exist for the entire lifetime of the item.  Hence this
 * function is best for actual constant arrays, however, it can be also used
 * with other arrays whose lifetime is guaranteed.
 *
 * \param item A 32bit integer array GWY file data item.
 * \param value New value for the item (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_int32_array gwyfile_item_set_int32_array_copy
 */
void
gwyfile_item_set_int32_array_const(GwyfileItem *item,
                                   const int32_t *value,
                                   uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_INT32_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.ia);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(int32_t);
    item->array_length = array_length;
    item->v.ia = (int32_t*)value;
    item->data_owned = false;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn const int32_t* gwyfile_item_get_int32_array(const GwyfileItem *item)
 * \brief Gets the 32bit integer array value contained in a GWY file data item.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the 32bit integer array type.  Use gwyfile_item_type()
 * to check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A 32bit integer array GWY file data item.
 * \return The 32bit integer array value of \p item.  The array ownership does
 *         not change.
 * \sa gwyfile_item_take_int32_array
 */
const int32_t*
gwyfile_item_get_int32_array(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_INT32_ARRAY);
    return item->v.ia;
}

/*!\fn int32_t* gwyfile_item_take_int32_array(GwyfileItem *item)
 * \brief Takes the 32bit integer array value contained in a GWY file data
 *        item.
 *
 * The item must own the array when this function is called.  The ownership is
 * transferred to the caller who becomes responsible to freeing it later.  The
 * array can still be obtained with gwyfile_item_get_int32_array() but,
 * obviously, it cannot be taken again.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the 32bit integer array type.  Use gwyfile_item_type()
 * to check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A 32bit integer array GWY file data item.
 * \return The 32bit integer array value of \p item.  The array becomes owned
 *         by the caller.
 * \sa gwyfile_item_get_int32_array
 */
int32_t*
gwyfile_item_take_int32_array(GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_INT32_ARRAY);
    assert(item->data_owned);
    item->data_owned = false;
    return item->v.ia;
}

/*!\fn GwyfileItem* gwyfile_item_new_int64_array(const char *name, int64_t *value, uint32_t array_length)
 * \brief Creates a new 64bit integer array GWY file item.
 *
 * The item consumes the provided array and takes care of freeing it later.
 * You must not touch the array any more; it can be already freed when this
 * function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_int64_array_copy
 */
GwyfileItem*
gwyfile_item_new_int64_array(const char *name,
                             int64_t *value,
                             uint32_t array_length)
{
    assert(name);
    assert(value);
    assert(array_length);
    return gwyfile_item_new_internal_int64_array(name, false,
                                                 value, array_length);
}

/*!\fn void gwyfile_item_set_int64_array(GwyfileItem *item, int64_t *value, uint32_t array_length)
 * \brief Sets the value of a 64bit integer array GWY file item.
 *
 * The item must be of the 64bit integer array type.
 *
 * The item consumes the provided 64bit integer array and takes care of freeing
 * it later.  You must not touch the array any more; it can be already freed
 * when this function returns.
 *
 * \param item A 64bit integer array GWY file data item.
 * \param value New value for the item (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_int64_array_copy
 */
void
gwyfile_item_set_int64_array(GwyfileItem *item,
                             int64_t *value,
                             uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_INT64_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.qa);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(int64_t);
    item->array_length = array_length;
    item->v.qa = value;
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_int64_array_copy(const char *name, const int64_t *value, uint32_t array_length)
 * \brief Creates a new 64bit integer array GWY file item.
 *
 * This function makes a copy the provided array.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 *         Upon memory allocation failure \c NULL is returned and \c errno is
 *         set to <tt>ENOMEM</tt>.
 * \sa gwyfile_item_new_int64_array
 */
GwyfileItem*
gwyfile_item_new_int64_array_copy(const char *name,
                                  const int64_t *value,
                                  uint32_t array_length)
{
    int64_t *valuecopy;

    assert(name);
    assert(value);
    assert(array_length);
    valuecopy = gwyfile_memdup(value, array_length*sizeof(int64_t));
    if (!valuecopy)
        return NULL;
    return gwyfile_item_new_internal_int64_array(name, false,
                                                 valuecopy, array_length);
}

/*!\fn void gwyfile_item_set_int64_array_copy(GwyfileItem *item, const int64_t *value, uint32_t array_length)
 * \brief Sets the value of a 64bit integer array GWY file item.
 *
 * The item must be of the 64bit integer array type.
 *
 * This function makes a copy the provided array.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param item A 64bit integer array GWY file data item.
 * \param value New value for the item (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_int64_array
 */
void
gwyfile_item_set_int64_array_copy(GwyfileItem *item,
                                  const int64_t *value,
                                  uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_INT64_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.qa);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(int64_t);
    item->array_length = array_length;
    item->v.qa = gwyfile_memdup(value, array_length*sizeof(int64_t));
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_int64_array_const(const char *name, const int64_t *value, uint32_t array_length)
 * \brief Creates a new 64bit integer array GWY file item.
 *
 * The array must exist for the entire lifetime of the item.  Hence this
 * function is best for actual constant arrays, however, it can be also used
 * with other arrays whose lifetime is guaranteed.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_int64_array gwyfile_item_new_int64_array_copy
 */
GwyfileItem*
gwyfile_item_new_int64_array_const(const char *name,
                                   const int64_t *value,
                                   uint32_t array_length)
{
    GwyfileItem *item;

    assert(name);
    assert(value);
    assert(array_length);
    item = gwyfile_item_new_internal_int64_array(name, false,
                                                 (int64_t*)value, array_length);
    item->data_owned = false;
    return item;
}

/*!\fn void gwyfile_item_set_int64_array_const(GwyfileItem *item, const int64_t *value, uint32_t array_length)
 * \brief Sets the value of a 64bit integer array GWY file item.
 *
 * The item must be of the 64bit integer array type.
 *
 * The array must exist for the entire lifetime of the item.  Hence this
 * function is best for actual constant arrays, however, it can be also used
 * with other arrays whose lifetime is guaranteed.
 *
 * \param item A 64bit integer array GWY file data item.
 * \param value New value for the item (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_int64_array gwyfile_item_set_int64_array_copy
 */
void
gwyfile_item_set_int64_array_const(GwyfileItem *item,
                                   const int64_t *value,
                                   uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_INT64_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.qa);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(int64_t);
    item->array_length = array_length;
    item->v.qa = (int64_t*)value;
    item->data_owned = false;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn const int64_t* gwyfile_item_get_int64_array(const GwyfileItem *item)
 * \brief Gets the 64bit integer array value contained in a GWY file data item.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the 64bit integer array type.  Use gwyfile_item_type()
 * to check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A 64bit integer array GWY file data item.
 * \return The 64bit integer array value of \p item.  The array ownership does
 *         not change.
 * \sa gwyfile_item_take_int64_array
 */
const int64_t*
gwyfile_item_get_int64_array(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_INT64_ARRAY);
    return item->v.qa;
}

/*!\fn int64_t* gwyfile_item_take_int64_array(GwyfileItem *item)
 * \brief Takes the 64bit integer array value contained in a GWY file data
 *        item.
 *
 * The item must own the array when this function is called.  The ownership is
 * transferred to the caller who becomes responsible to freeing it later.  The
 * array can still be obtained with gwyfile_item_get_int64_array() but,
 * obviously, it cannot be taken again.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the 64bit integer array type.  Use gwyfile_item_type()
 * to check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A 64bit integer array GWY file data item.
 * \return The 64bit integer array value of \p item.  The array becomes owned
 *         by the caller.
 * \sa gwyfile_item_get_int64_array
 */
int64_t*
gwyfile_item_take_int64_array(GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_INT64_ARRAY);
    assert(item->data_owned);
    item->data_owned = false;
    return item->v.qa;
}

/*!\fn GwyfileItem* gwyfile_item_new_double_array(const char *name, double *value, uint32_t array_length)
 * \brief Creates a new double array GWY file item.
 *
 * The item consumes the provided array and takes care of freeing it later.
 * You must not touch the array any more; it can be already freed when this
 * function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_double_array_copy gwyfile_item_new_double_array_const
 */
GwyfileItem*
gwyfile_item_new_double_array(const char *name,
                              double *value,
                              uint32_t array_length)
{
    assert(name);
    assert(value);
    assert(array_length);
    return gwyfile_item_new_internal_double_array(name, false,
                                                  value, array_length);
}

/*!\fn void gwyfile_item_set_double_array(GwyfileItem *item, double *value, uint32_t array_length)
 * \brief Sets the value of a double array GWY file item.
 *
 * The item must be of the double array type.
 *
 * The item consumes the provided double array and takes care of freeing
 * it later.  You must not touch the array any more; it can be already freed
 * when this function returns.
 *
 * \param item A double array GWY file data item.
 * \param value New value for the item (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_double_array_copy gwyfile_item_set_double_array_const
 */
void
gwyfile_item_set_double_array(GwyfileItem *item,
                              double *value,
                              uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_DOUBLE_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.da);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(double);
    item->array_length = array_length;
    item->v.da = value;
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_double_array_copy(const char *name, const double *value, uint32_t array_length)
 * \brief Creates a new double array GWY file item.
 *
 * This function makes a copy the provided array.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 *         Upon memory allocation failure \c NULL is returned and \c errno is
 *         set to <tt>ENOMEM</tt>.
 * \sa gwyfile_item_new_double_array gwyfile_item_new_double_array_const
 */
GwyfileItem*
gwyfile_item_new_double_array_copy(const char *name,
                                   const double *value,
                                   uint32_t array_length)
{
    double *valuecopy;

    assert(name);
    assert(value);
    assert(array_length);
    valuecopy = gwyfile_memdup(value, array_length*sizeof(double));
    if (!valuecopy)
        return NULL;
    return gwyfile_item_new_internal_double_array(name, false,
                                                  valuecopy, array_length);
}

/*!\fn void gwyfile_item_set_double_array_copy(GwyfileItem *item, const double *value, uint32_t array_length)
 * \brief Sets the value of a 64bit integer array GWY file item.
 *
 * The item must be of the 64bit integer array type.
 *
 * This function makes a copy the provided array.  You can continue doing
 * whatever you wish with it after the function returns.
 *
 * \param item A 64bit integer array GWY file data item.
 * \param value New value for the item (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_double_array gwyfile_item_set_double_array_const
 */
void
gwyfile_item_set_double_array_copy(GwyfileItem *item,
                                  const double *value,
                                  uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_DOUBLE_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.da);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(double);
    item->array_length = array_length;
    item->v.da = gwyfile_memdup(value, array_length*sizeof(double));
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_double_array_const(const char *name, const double *value, uint32_t array_length)
 * \brief Creates a new double array GWY file item.
 *
 * The array must exist for the entire lifetime of the item.  Hence this
 * function is best for actual constant arrays, however, it can be also used
 * with other arrays whose lifetime is guaranteed.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_double_array gwyfile_item_new_double_array_copy
 */
GwyfileItem*
gwyfile_item_new_double_array_const(const char *name,
                                    const double *value,
                                    uint32_t array_length)
{
    GwyfileItem *item;

    assert(name);
    assert(value);
    assert(array_length);
    item = gwyfile_item_new_internal_double_array(name, false,
                                                 (double*)value, array_length);
    item->data_owned = false;
    return item;
}

/*!\fn void gwyfile_item_set_double_array_const(GwyfileItem *item, const double *value, uint32_t array_length)
 * \brief Sets the value of a double array GWY file item.
 *
 * The item must be of the double array type.
 *
 * The array must exist for the entire lifetime of the item.  Hence this
 * function is best for actual constant arrays, however, it can be also used
 * with other arrays whose lifetime is guaranteed.
 *
 * \param item A double array GWY file data item.
 * \param value New value for the item (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_double_array gwyfile_item_set_double_array_copy
 */
void
gwyfile_item_set_double_array_const(GwyfileItem *item,
                                    const double *value,
                                    uint32_t array_length)
{
    size_t oldsize;

    assert(item);
    assert(item->type == GWYFILE_ITEM_DOUBLE_ARRAY);
    assert(value);
    assert(array_length);
    oldsize = item->data_size;
    if (item->data_owned)
        free(item->v.da);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(double);
    item->array_length = array_length;
    item->v.da = (double*)value;
    item->data_owned = false;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn const double* gwyfile_item_get_double_array(const GwyfileItem *item)
 * \brief Gets the double array value contained in a GWY file data item.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the double array type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A double array GWY file data item.
 * \return The double array value of \p item.  The array ownership does not
 *         change.
 */
const double*
gwyfile_item_get_double_array(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_DOUBLE_ARRAY);
    return item->v.da;
}

/*!\fn double* gwyfile_item_take_double_array(GwyfileItem *item)
 * \brief Takes the double array value contained in a GWY file data item.
 *
 * The item must own the array when this function is called.  The ownership is
 * transferred to the caller who becomes responsible to freeing it later.  The
 * array can still be obtained with gwyfile_item_get_double_array() but,
 * obviously, it cannot be taken again.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the double array type.  Use gwyfile_item_type()
 * to check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A double array GWY file data item.
 * \return The double array value of \p item.  The array becomes owned
 *         by the caller.
 * \sa gwyfile_item_get_double_array
 */
double*
gwyfile_item_take_double_array(GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_DOUBLE_ARRAY);
    assert(item->data_owned);
    item->data_owned = false;
    return item->v.da;
}

/*!\fn GwyfileItem* gwyfile_item_new_string_array(const char *name, char **value, uint32_t array_length)
 * \brief Creates a new string array GWY file item.
 *
 * The item consumes the provided array and the strings inside and takes
 * care of freeing them later.  You must not touch the array any more; it can
 * be already freed when this function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_string_array_copy gwyfile_item_new_string_array_const
 */
GwyfileItem*
gwyfile_item_new_string_array(const char *name,
                              char **value,
                              uint32_t array_length)
{
    uint32_t i;

    assert(name);
    assert(value);
    assert(array_length);
    for (i = 0; i < array_length; i++) {
        assert(value[i]);
    }
    return gwyfile_item_new_internal_string_array(name, false,
                                                  value, array_length);
}

/*!\fn void gwyfile_item_set_string_array(GwyfileItem *item, char **value, uint32_t array_length)
 * \brief Sets the value of a string array GWY file item.
 *
 * The item must be of the string array type.
 *
 * The item consumes the provided array and the strings inside and takes
 * care of freeing them later.  You must not touch the array any more; it can
 * be already freed when this function returns.
 *
 * \param item A string array GWY file data item.
 * \param value New value for the item (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_string_array_copy gwyfile_item_set_string_array_const
 */
void
gwyfile_item_set_string_array(GwyfileItem *item,
                              char **value,
                              uint32_t array_length)
{
    size_t oldsize;
    uint32_t i;

    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING_ARRAY);
    assert(value);
    assert(array_length);
    for (i = 0; i < array_length; i++) {
        assert(value[i]);
    }
    oldsize = item->data_size;
    if (item->data_owned) {
        for (i = 0; i < item->array_length; i++)
            free(item->v.sa[i]);
        free(item->v.sa);
    }
    item->data_size = sizeof(uint32_t);
    for (i = 0; i < array_length; i++)
        item->data_size += strlen(value[i]) + 1;
    item->array_length = array_length;
    item->v.sa = value;
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_string_array_copy(const char *name, const char *const *value, uint32_t array_length)
 * \brief Creates a new string array GWY file item.
 *
 * This function makes copies of both the provided array and the strings
 * inside.  You can continue doing whatever you wish with it after the function
 * returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 *         Upon memory allocation failure \c NULL is returned and \c errno is
 *         set to <tt>ENOMEM</tt>.
 * \sa gwyfile_item_new_string_array gwyfile_item_new_string_array_const
 */
GwyfileItem*
gwyfile_item_new_string_array_copy(const char *name,
                                   const char *const *value,
                                   uint32_t array_length)
{
    char **valuecopy;
    uint32_t i;

    assert(name);
    assert(value);
    assert(array_length);
    for (i = 0; i < array_length; i++) {
        assert(value[i]);
    }
    valuecopy = malloc(array_length*sizeof(char**));
    if (!valuecopy) {
        errno = ENOMEM;   /* Generally not guaranteed by OS. */
        return NULL;
    }
    for (i = 0; i < array_length; i++) {
        valuecopy[i] = gwyfile_strdup(value[i]);
        if (!valuecopy[i]) {
            while (i) {
                i--;
                free(valuecopy[i]);
            }
            free(valuecopy);
            errno = ENOMEM;   /* Generally not guaranteed by OS. */
            return NULL;
        }
    }
    return gwyfile_item_new_internal_string_array(name, false,
                                                  valuecopy, array_length);
}

/*!\fn void gwyfile_item_set_string_array_copy(GwyfileItem *item, const char *const *value, uint32_t array_length)
 * \brief Sets the value of a string array GWY file item.
 *
 * The item must be of the string array type.
 *
 * This function makes copies of both the provided array and the strings
 * inside.  You can continue doing whatever you wish with it after the function
 * returns.
 *
 * \param item A string array GWY file data item.
 * \param value New value for the item (to be copied).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_string_array gwyfile_item_set_string_array_const
 */
void
gwyfile_item_set_string_array_copy(GwyfileItem *item,
                                   const char *const *value,
                                   uint32_t array_length)
{
    size_t oldsize;
    uint32_t i;

    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING_ARRAY);
    assert(value);
    assert(array_length);
    for (i = 0; i < array_length; i++) {
        assert(value[i]);
    }
    oldsize = item->data_size;
    if (item->data_owned) {
        for (i = 0; i < item->array_length; i++)
            free(item->v.sa[i]);
        free(item->v.sa);
    }
    item->data_size = sizeof(uint32_t);
    item->array_length = array_length;
    item->v.sa = gwyfile_memdup(value, array_length*sizeof(char*));
    for (i = 0; i < array_length; i++) {
        size_t len = strlen(value[i]);
        item->data_size += len + 1;
        item->v.sa[i] = gwyfile_memdup(value[i], len + 1);
    }
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn GwyfileItem* gwyfile_item_new_string_array_const(const char *name, const char *const *value, uint32_t array_length)
 * \brief Creates a new string array GWY file item.
 *
 * The array and the strings must exist for the entire lifetime of the item.
 * Furthermore, the number of strings and their lengths may not change.  Hence
 * this function is best for actual constant arrays, however, it can be also
 * used with other arrays whose lifetime and content are guaranteed.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 * \sa gwyfile_item_new_string_array gwyfile_item_new_string_array_copy
 */
GwyfileItem*
gwyfile_item_new_string_array_const(const char *name,
                                    const char *const *value,
                                    uint32_t array_length)
{
    GwyfileItem *item;
    uint32_t i;

    assert(name);
    assert(value);
    assert(array_length);
    for (i = 0; i < array_length; i++) {
        assert(value[i]);
    }
    item = gwyfile_item_new_internal_string_array(name, false,
                                                  (char**)value, array_length);
    item->data_owned = false;
    return item;
}

/*!\fn void gwyfile_item_set_string_array_const(GwyfileItem *item, const char *const *value, uint32_t array_length)
 * \brief Sets the value of a string array GWY file item.
 *
 * The item must be of the string array type.
 *
 * The array and the strings must exist for the entire lifetime of the item.
 * Furthermore, the number of strings and their lengths may not change (more
 * precisely, you must call this function again with the same array to update
 * the item if you change them).  Hence this function is best for actual
 * constant arrays, however, it can be also used with other arrays whose
 * lifetime and content are guaranteed.
 *
 * \param item A string array GWY file data item.
 * \param value New value for the item (to be used as-is).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \sa gwyfile_item_set_string_array gwyfile_item_set_string_array_copy
 */
void
gwyfile_item_set_string_array_const(GwyfileItem *item,
                                    const char *const *value,
                                    uint32_t array_length)
{
    size_t oldsize;
    uint32_t i;

    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING_ARRAY);
    assert(value);
    assert(array_length);
    for (i = 0; i < array_length; i++) {
        assert(value[i]);
    }
    oldsize = item->data_size;
    if (item->data_owned) {
        for (i = 0; i < item->array_length; i++)
            free(item->v.sa[i]);
        free(item->v.sa);
    }
    item->data_size = sizeof(uint32_t);
    for (i = 0; i < array_length; i++)
        item->data_size += strlen(value[i]) + 1;
    item->array_length = array_length;
    item->v.sa = (char**)value;
    item->data_owned = false;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn const char* const* gwyfile_item_get_string_array(const GwyfileItem *item)
 * \brief Gets the string array value contained in a GWY file data item.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the string array type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A string array GWY file data item.
 * \return The string array value of \p item.  The array and the strings inside
 *         remain owned by \p item.
 */
const char* const*
gwyfile_item_get_string_array(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING_ARRAY);
    return (const char* const*)item->v.sa;
}

/*!\fn char** gwyfile_item_take_string_array(GwyfileItem *item)
 * \brief Takes the string array value contained in a GWY file data item.
 *
 * The item must own the array when this function is called.  The ownership of
 * both the array and the strings inside is transferred to the caller who
 * becomes responsible to freeing it later.  The array can still be obtained
 * with gwyfile_item_get_string_array() but, obviously, it cannot be taken
 * again.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the string array type.  Use gwyfile_item_type()
 * to check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item A string array GWY file data item.
 * \return The string array value of \p item.  The array and the strings
 *         become owned by the caller.
 * \sa gwyfile_item_get_string_array
 */
char**
gwyfile_item_take_string_array(GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_STRING_ARRAY);
    assert(item->data_owned);
    item->data_owned = false;
    return item->v.sa;
}

/*!\fn GwyfileItem* gwyfile_item_new_object_array(const char *name, GwyfileObject **value, uint32_t array_length)
 * \brief Creates a new object array GWY file item.
 *
 * The item consumes the provided array and all objects inside and takes
 * care of freeing them later. You must not touch the array any more; it can be
 * already freed when this function returns.
 *
 * \param name Item name.  It must be a non-empty UTF-8-encoded string
 *             (usually, it should be an ASCII string).  A copy of the string
 *             will be made.
 * \param value Item value (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 * \return The newly created GWY file data item.
 */
GwyfileItem*
gwyfile_item_new_object_array(const char *name,
                              GwyfileObject **value,
                              uint32_t array_length)
{
    uint32_t i;

    assert(name);
    assert(value);
    assert(array_length);
    for (i = 0; i < array_length; i++) {
        assert(value[i]);
        assert(!value[i]->owner);
    }
    return gwyfile_item_new_internal_object_array(name, false,
                                                  value, array_length);
}

/*!\fn void gwyfile_item_set_object_array(GwyfileItem *item, GwyfileObject **value, uint32_t array_length)
 * \brief Sets the value of a object array GWY file item.
 *
 * The item must be of the object array type.
 *
 * The item consumes the provided array and the objects inside and takes
 * care of freeing them later.  You must not touch the array any more; it can
 * be already freed when this function returns.
 *
 * \param item A object array GWY file data item.
 * \param value New value for the item (to be consumed).
 * \param array_length Array length.  It must be non-zero as GWY files do not
 *                     permit empty arrays.
 */
void
gwyfile_item_set_object_array(GwyfileItem *item,
                              GwyfileObject **value,
                              uint32_t array_length)
{
    size_t oldsize;
    uint32_t i;

    assert(item);
    assert(item->type == GWYFILE_ITEM_OBJECT_ARRAY);
    assert(value);
    assert(array_length);
    for (i = 0; i < array_length; i++) {
        assert(value[i]);
        assert(!value[i]->owner);
    }
    oldsize = item->data_size;
    /* XXX: Can we have a non-owned object array? */
    if (item->data_owned) {
        for (i = 0; i < item->array_length; i++) {
            item->v.oa[i]->owner = NULL;
            gwyfile_object_free(item->v.oa[i]);
        }
        free(item->v.oa);
    }
    item->data_size = sizeof(uint32_t);
    item->array_length = array_length;
    for (i = 0; i < array_length; i++)
        item->data_size += gwyfile_object_size(value[i]);
    item->v.oa = value;
    item->data_owned = true;
    gwyfile_item_notify_size_change(item, oldsize);
}

/*!\fn void gwyfile_item_free(GwyfileItem *item)
 * \brief Frees a GWY file data item.
 *
 * All item data, including contained arrays, strings and objects, are freed
 * recursively. It is not permitted to free an item present in a data object.
 *
 * You can pass \c NULL as \p item.  The function is then no-op.
 *
 * \param item A GWY file data item.
 * \sa gwyfile_item_release_object
 */
void
gwyfile_item_free(GwyfileItem *item)
{
    if (!item)
        return;

    assert(!item->owner);
    free(item->name);

    if (item->type == GWYFILE_ITEM_STRING) {
        if (item->data_owned)
            free(item->v.s);
    }
    else if (item->type == GWYFILE_ITEM_CHAR_ARRAY) {
        if (item->data_owned)
            free(item->v.ca);
    }
    else if (item->type == GWYFILE_ITEM_INT32_ARRAY) {
        if (item->data_owned)
            free(item->v.ia);
    }
    else if (item->type == GWYFILE_ITEM_INT64_ARRAY) {
        if (item->data_owned)
            free(item->v.qa);
    }
    else if (item->type == GWYFILE_ITEM_DOUBLE_ARRAY) {
        if (item->data_owned)
            free(item->v.da);
    }
    else if (item->type == GWYFILE_ITEM_OBJECT) {
        /* Note the data_owned condition is here for
         * gwyfile_item_release_object().  Objects inside items are always
         * owned otherwise. */
        if (item->data_owned) {
            item->v.o->owner = NULL;
            gwyfile_object_free(item->v.o);
        }
    }
    else if (item->type == GWYFILE_ITEM_STRING_ARRAY) {
        if (item->data_owned) {
            char **sa = item->v.sa;
            unsigned int i;
            for (i = 0; i < item->array_length; i++)
                free(sa[i]);
            free(sa);
        }
    }
    else if (item->type == GWYFILE_ITEM_OBJECT_ARRAY) {
        /* XXX: Can we have a non-owned object array? */
        if (item->data_owned) {
            GwyfileObject **oa = item->v.oa;
            unsigned int i;
            for (i = 0; i < item->array_length; i++) {
                oa[i]->owner = NULL;
                gwyfile_object_free(oa[i]);
            }
            free(oa);
        }
    }

    memset(item, 0, sizeof(GwyfileItem));
    free(item);
}

/*!\fn GwyfileItemType gwyfile_item_type(const GwyfileItem *item)
 * \brief Obtains the type of a GWY file data item.
 *
 * \param item A GWY file data item.
 * \return The item type.
 */
GwyfileItemType
gwyfile_item_type(const GwyfileItem *item)
{
    assert(item);
    return item->type;
}

/*!\fn const char* gwyfile_item_name(const GwyfileItem *item)
 * \brief Obtains the name of a GWY file data item.
 *
 * \param item A GWY file data item.
 * \returns The object type name.  The returned string is owned by \p item and
 *          must not be modified or freed.
 */
const char*
gwyfile_item_name(const GwyfileItem *item)
{
    assert(item);
    return item->name;
}

/*!\fn uint32_t* gwyfile_item_array_length(const GwyfileItem *item)
 * \brief Obtains the array length of a GWY file data item.
 *
 * This function may be called on non-array data items.  Zero is returned as
 * the length in this case.
 *
 * \param item A GWY file data item.
 * \return The number of items of the contained array.
 */
uint32_t
gwyfile_item_array_length(const GwyfileItem *item)
{
    assert(item);
    return item->array_length;
}

/*!\fn size_t gwyfile_item_data_size(const GwyfileItem *item)
 * \brief Obtains the size of a GWY file data item data.
 *
 * The size is the number of bytes the item data would occupy in a GWY file.
 * It includes the size of all contained data, in particular contained objects
 * and object arrays.
 *
 * The returned size does not include the item type and name (see
 * gwyfile_item_size() for that).  It is the pure data size.
 *
 * \param item A GWY file data item.
 * \return The item data size, in bytes.
 */
size_t
gwyfile_item_data_size(const GwyfileItem *item)
{
    if (!item || !item->type)
        return 0;

    return item->data_size;
}

/*!\fn size_t gwyfile_item_size(const GwyfileItem *item)
 * \brief Obtains the total size of a GWY file data item.
 *
 * The size is the number of bytes the data would occupy in a GWY file.
 * It is equal to the value returned by gwyfile_item_data_size() plus
 * the size of item type and name.  For array types, it includes the array
 * length record.
 *
 * \param item A GWY file data item.
 * \return The item size, in bytes.
 */
size_t
gwyfile_item_size(const GwyfileItem *item)
{
    if (!item || !item->type)
        return 0;

    return 1 + item->name_len+1 + item->data_size;
}

/*!\fn bool gwyfile_item_fwrite(const GwyfileItem *item, FILE *stream, GwyfileError **error)
 * \brief Writes a GWY file data item to a stdio stream.
 *
 * The stream does not have to be seekable.
 *
 * \param item A GWY file data item.
 * \param stream C stdio stream to write the item to.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \return \c true if the writing succeeded.
 */
bool
gwyfile_item_fwrite(const GwyfileItem *item, FILE *stream, GwyfileError **error)
{
    GwyfileItemType type;
    uint32_t alen;
    char c;

    errno = 0;
    assert(item);
    assert(stream);

    if (fwrite(item->name, 1, item->name_len+1, stream) != item->name_len+1) {
        gwyfile_set_error_errno(error);
        return false;
    }

    alen = item->array_length;
    type = item->type;
    c = type;
    if (fwrite(&c, 1, 1, stream) != 1) {
        gwyfile_set_error_errno(error);
        return false;
    }

    if (type == GWYFILE_ITEM_BOOL) {
        c = item->v.b;
        if (fwrite(&c, 1, 1, stream) == 1)
            return true;
        gwyfile_set_error_errno(error);
        return false;
    }
    else if (type == GWYFILE_ITEM_CHAR) {
        if (fwrite(&item->v.c, 1, 1, stream) == 1)
            return true;
        gwyfile_set_error_errno(error);
        return false;
    }
    else if (type == GWYFILE_ITEM_INT32) {
        if (gwyfile_fwrite_le(&item->v.i, sizeof(int32_t), 1, stream))
            return true;
        gwyfile_set_error_errno(error);
        return false;
    }
    else if (type == GWYFILE_ITEM_INT64) {
        if (gwyfile_fwrite_le(&item->v.q, sizeof(int64_t), 1, stream))
            return true;
    }
    else if (type == GWYFILE_ITEM_DOUBLE) {
        if (gwyfile_fwrite_le(&item->v.d, sizeof(double), 1, stream))
            return true;
    }
    else if (type == GWYFILE_ITEM_STRING) {
        size_t expected_size = strlen(item->v.s) + 1;
        if (fwrite(item->v.s, 1, expected_size, stream) == expected_size)
            return true;
    }
    else if (type == GWYFILE_ITEM_OBJECT) {
        return gwyfile_object_fwrite(item->v.o, stream, error);
    }
    else if (type == GWYFILE_ITEM_CHAR_ARRAY) {
        if (gwyfile_fwrite_le(&alen, 1, sizeof(uint32_t), stream)
            && fwrite(item->v.ca, 1, alen, stream) == alen)
            return true;
    }
    else if (type == GWYFILE_ITEM_INT32_ARRAY) {
        if (gwyfile_fwrite_le(&alen, 1, sizeof(uint32_t), stream)
            && gwyfile_fwrite_le(item->v.ia, sizeof(int32_t), alen, stream))
            return true;
    }
    else if (type == GWYFILE_ITEM_INT64_ARRAY) {
        if (gwyfile_fwrite_le(&alen, 1, sizeof(uint32_t), stream)
            && gwyfile_fwrite_le(item->v.qa, sizeof(int64_t), alen, stream))
            return true;
    }
    else if (type == GWYFILE_ITEM_DOUBLE_ARRAY) {
        if (gwyfile_fwrite_le(&alen, 1, sizeof(uint32_t), stream)
            && gwyfile_fwrite_le(item->v.da, sizeof(double), alen, stream))
            return true;
    }
    else if (type == GWYFILE_ITEM_STRING_ARRAY) {
        uint32_t i;
        if (!gwyfile_fwrite_le(&alen, 1, sizeof(uint32_t), stream)) {
            gwyfile_set_error_errno(error);
            return false;
        }
        for (i = 0; i < alen; i++) {
            const char *s = item->v.sa[i];
            size_t expected_size = strlen(s) + 1;
            if (fwrite(s, 1, expected_size, stream) != expected_size) {
                gwyfile_set_error_errno(error);
                return false;
            }
        }
        return true;
    }
    else if (type == GWYFILE_ITEM_OBJECT_ARRAY) {
        uint32_t i;
        if (!gwyfile_fwrite_le(&alen, 1, sizeof(uint32_t), stream)) {
            gwyfile_set_error_errno(error);
            return false;
        }
        for (i = 0; i < alen; i++) {
            if (!gwyfile_object_fwrite(item->v.oa[i], stream, error))
                return false;
        }
        return true;
    }
    else {
        assert(!"Reached");
    }

    gwyfile_set_error_errno(error);
    return false;
}

static GwyfileItem*
gwyfile_item_fread_internal(FILE *stream,
                            size_t max_size,
                            uint32_t depth,
                            GwyfileObject *owner,
                            GwyfileError **error)
{
    GwyfileItemType type;
    char *name;
    uint32_t alen = 0, i;
    char c;

    assert(stream);
    if (!(name = gwyfile_fread_string(stream, &max_size, error, "item name")))
        return NULL;

    if (!gwyfile_check_size(&max_size, 1, error, "item type"))
        goto fail;

    /* NB: We cannot use name in error messages because it is not checked until
     * we try create the item. */
    if (fread(&c, 1, 1, stream) != 1) {
        gwyfile_set_error_fread(error, stream, "item type");
        goto fail;
    }
    type = c;
    if (!gwyfile_item_type_is_valid(type)) {
        if (error) {
            char *path = gwyfile_format_path(owner, NULL);
            gwyfile_set_error(error,
                              GWYFILE_ERROR_DOMAIN_DATA,
                              GWYFILE_ERROR_ITEM_TYPE,
                              "Invalid item type %d in %s.",
                              type, path);
            free(path);
        }
        goto fail;
    }

    /* If the item is an array, read the length now. */
    if (gwyfile_item_type_is_array(type)) {
        if (!gwyfile_check_size(&max_size, sizeof(uint32_t),
                                error, "array length"))
            goto fail;
        if (!gwyfile_fread_le(&alen, sizeof(uint32_t), 1, stream)) {
            gwyfile_set_error_fread(error, stream, "array length");
            free(name);
            return NULL;
        }
        if (!alen) {
            if (error) {
                char *path = gwyfile_format_path(owner, NULL);
                gwyfile_set_error(error,
                                  GWYFILE_ERROR_DOMAIN_DATA,
                                  GWYFILE_ERROR_ARRAY_SIZE,
                                  "Item array of type %d "
                                  "has zero length in %s.",
                                  type, path);
                free(path);
            }
            free(name);
            return NULL;
        }
    }

    /* XXX: Who will validate the name and when? */

    /* Duplicating and freeing name is a bit lame.  Note, however, that
     * GwyfileItem appends the type to the name string so we might not be able
     * to use the string as-is anyway. */
    if (type == GWYFILE_ITEM_BOOL) {
        if (!gwyfile_check_size(&max_size, 1, error, "bool item"))
            goto fail;
        if (fread(&c, 1, 1, stream) == 1)
            return gwyfile_item_new_internal_bool(name, true, c);
        gwyfile_set_error_fread(error, stream, "bool item");
    }
    else if (type == GWYFILE_ITEM_CHAR) {
        if (!gwyfile_check_size(&max_size, 1, error, "char item"))
            goto fail;
        if (fread(&c, 1, 1, stream) == 1)
            return gwyfile_item_new_internal_char(name, true, c);
        gwyfile_set_error_fread(error, stream, "char item");
    }
    else if (type == GWYFILE_ITEM_INT32) {
        int32_t i;
        if (!gwyfile_check_size(&max_size, sizeof(int32_t),
                                error, "int32 item"))
            goto fail;
        if (gwyfile_fread_le(&i, sizeof(int32_t), 1, stream))
            return gwyfile_item_new_internal_int32(name, true, i);
        gwyfile_set_error_fread(error, stream, "int32 item");
    }
    else if (type == GWYFILE_ITEM_INT64) {
        int64_t q;
        if (!gwyfile_check_size(&max_size, sizeof(int64_t),
                                error, "int64 item"))
            goto fail;
        if (gwyfile_fread_le(&q, sizeof(int64_t), 1, stream))
            return gwyfile_item_new_internal_int64(name, true, q);
        gwyfile_set_error_fread(error, stream, "int64 item");
    }
    else if (type == GWYFILE_ITEM_DOUBLE) {
        double d;
        if (!gwyfile_check_size(&max_size, sizeof(double),
                                error, "double item"))
            goto fail;
        if (gwyfile_fread_le(&d, sizeof(double), 1, stream))
            return gwyfile_item_new_internal_double(name, true, d);
        gwyfile_set_error_fread(error, stream, "double item");
    }
    else if (type == GWYFILE_ITEM_STRING) {
        char *s;
        if ((s = gwyfile_fread_string(stream, &max_size, error, "string item")))
            return gwyfile_item_new_internal_string(name, true, s);
    }
    else if (type == GWYFILE_ITEM_OBJECT) {
        GwyfileObject *object;
        if ((object = gwyfile_object_fread_internal(stream, max_size, depth,
                                                    owner, error)))
            return gwyfile_item_new_internal_object(name, true, object);
    }
    else if (type == GWYFILE_ITEM_CHAR_ARRAY) {
        char *ca;
        if (!gwyfile_check_size(&max_size, alen, error, "char array item"))
            goto fail;
        if (!(ca = (char*)gwyfile_alloc_check(alen*sizeof(char), error)))
            goto fail;
        if (fread(ca, sizeof(char), alen, stream))
            return gwyfile_item_new_internal_char_array(name, true, ca, alen);
        gwyfile_set_error_fread(error, stream, "char array item");
        free(ca);
    }
    else if (type == GWYFILE_ITEM_INT32_ARRAY) {
        int32_t *ia;
        if (alen > max_size/sizeof(int32_t)) {
            gwyfile_set_error_overrun(error, "int32 array item");
            goto fail;
        }
        max_size -= alen*sizeof(int32_t);
        if (!(ia = (int32_t*)gwyfile_alloc_check(alen*sizeof(int32_t), error)))
            goto fail;
        if (gwyfile_fread_le(ia, sizeof(int32_t), alen, stream))
            return gwyfile_item_new_internal_int32_array(name, true, ia, alen);
        gwyfile_set_error_fread(error, stream, "int32 array item");
        free(ia);
    }
    else if (type == GWYFILE_ITEM_INT64_ARRAY) {
        int64_t *qa;
        if (alen > max_size/sizeof(int64_t)) {
            gwyfile_set_error_overrun(error, "int64 array item");
            goto fail;
        }
        max_size -= alen*sizeof(int64_t);
        if (!(qa = (int64_t*)gwyfile_alloc_check(alen*sizeof(int64_t), error)))
            goto fail;
        if (gwyfile_fread_le(qa, sizeof(int64_t), alen, stream))
            return gwyfile_item_new_internal_int64_array(name, true, qa, alen);
        gwyfile_set_error_fread(error, stream, "int64 array item");
        free(qa);
    }
    else if (type == GWYFILE_ITEM_DOUBLE_ARRAY) {
        double *da;
        if (alen > max_size/sizeof(double)) {
            gwyfile_set_error_overrun(error, "double array item");
            goto fail;
        }
        if (!(da = (double*)gwyfile_alloc_check(alen*sizeof(double), error)))
            goto fail;
        if (gwyfile_fread_le(da, sizeof(double), alen, stream))
            return gwyfile_item_new_internal_double_array(name, true, da, alen);
        gwyfile_set_error_fread(error, stream, "double array item");
        free(da);
    }
    else if (type == GWYFILE_ITEM_STRING_ARRAY) {
        char **sa;
        if (alen > max_size) {
            gwyfile_set_error_overrun(error, "string array item");
            goto fail;
        }
        if (!(sa = (char**)gwyfile_alloc_check(alen*sizeof(char*), error)))
            goto fail;
        for (i = 0; i < alen; i++) {
            if (!(sa[i] = gwyfile_fread_string(stream, &max_size,
                                               error, "string array item"))) {
                while (i--)
                    free(sa[i]);
                free(sa);
                goto fail;
            }
        }
        return gwyfile_item_new_internal_string_array(name, true, sa, alen);
    }
    else if (type == GWYFILE_ITEM_OBJECT_ARRAY) {
        GwyfileObject **oa;
        size_t memsize = alen*sizeof(GwyfileObject*);
        if (alen > max_size/(sizeof(uint32_t) + 1)) {
            gwyfile_set_error_overrun(error, "object array item");
            goto fail;
        }
        if (!(oa = (GwyfileObject**)gwyfile_alloc_check(memsize, error)))
            goto fail;
        for (i = 0; i < alen; i++) {
            size_t object_size;

            if (!(oa[i] = gwyfile_object_fread_internal(stream, max_size, depth,
                                                        owner, error))) {
                while (i--)
                    gwyfile_object_free(oa[i]);
                free(oa);
                goto fail;
            }
            object_size = gwyfile_object_size(oa[i]);
            assert(object_size <= max_size);
            max_size -= object_size;
        }
        return gwyfile_item_new_internal_object_array(name, true, oa, alen);
    }
    else {
        assert(!"Reached");
    }

fail:
    free(name);
    return NULL;
}

/*!\fn GwyfileItem* gwyfile_item_fread(FILE *stream, size_t max_size, GwyfileError **error)
 * \brief Reads a GWY file data item from a stdio stream.
 *
 * The stream does not have to be seekable.
 *
 * On success, the position indicator in \p stream will be pointed after the
 * end of the item.
 *
 * On failure, the position indicator state in \p stream is undefined.
 *
 * The maximum number of bytes to read is given by \p max_size which is of type
 * <tt>size_t</tt>, however, be aware that sizes in GWY files are only 32bit.
 * So any value that does not fit into a 32bit integer means the same as
 * <tt>SIZE_MAX</tt>, i.e. unconstrained reading.
 *
 * If reading more than \p max_size bytes would be required to reconstruct the
 * top-level object, the function fails with
 * GwyfileErrorCode::GWYFILE_ERROR_CONFINEMENT error in the
 * GwyfileErrorDomain::GWYFILE_ERROR_DOMAIN_DATA domain.
 *
 * \param stream C stdio stream to read the GWY file from.
 * \param error Location for the error (or <tt>NULL</tt>).
 * \param max_size Maximum number of bytes to read.  Pass \c SIZE_MAX for
 *                 unconstrained reading.
 * \return The reconstructed data item.  \c NULL is returned upon I/O faulure.
 */
GwyfileItem*
gwyfile_item_fread(FILE *stream, size_t max_size, GwyfileError **error)
{
    return gwyfile_item_fread_internal(stream, max_size, 0, NULL, error);
}

/*!\fn bool gwyfile_item_owns_data(const GwyfileItem *item)
 * \brief Reports if a GWY file item owns its data.
 *
 * It is possible to pass any type of data item to this function.  It returns
 * \c true for data that cannot be taken from the item.
 *
 * You should rarely need this function.
 *
 * \param item A GWY file data item.
 * \return \c true if \p item owns its data.
 */
bool
gwyfile_item_owns_data(const GwyfileItem *item)
{
    assert(item);
    return item->data_owned;
}

/*!\fn GwyfileObject* const* gwyfile_item_get_object_array(const GwyfileItem *item)
 * \brief Gets the object array value contained in a GWY file data item.
 *
 * Use gwyfile_item_array_length() to obtain the array length.
 *
 * The item must be of the object array type.  Use gwyfile_item_type() to
 * check item type if the type may not match the expected type.  Use
 * gwyfile_object_get_with_type() to obtain object items ensuring the type.
 *
 * \param item An object GWY file data item.
 * \return The object array value of \p item.  The array and objects ownership
 *         does not change.
 */
GwyfileObject* const*
gwyfile_item_get_object_array(const GwyfileItem *item)
{
    assert(item);
    assert(item->type == GWYFILE_ITEM_OBJECT_ARRAY);
    return item->v.oa;
}

static GwyfileObject*
gwyfile_object_new_internal(const char *name, bool consume_name)
{
    GwyfileObject *object;
    size_t namelen;
    char *objname;

    assert(name);
    namelen = strlen(name);
    objname = (char*)(consume_name ? name : gwyfile_memdup(name, namelen + 1));
    /* We should only get here with consume_name=false from API calls, not file
     * reading. */
    assert(objname);
    object = (GwyfileObject*)calloc(1, sizeof(GwyfileObject));
    assert(object);
    object->name_len = namelen;
    object->name = objname;

    return object;
}

static GwyfileItem*
gwyfile_item_new_internal_bool(const char *name,
                               bool consume_name,
                               bool value)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_BOOL,
                                                  name, consume_name);
    item->data_size = 1;
    item->v.b = !!value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_char(const char *name,
                               bool consume_name,
                               char value)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_CHAR,
                                                  name, consume_name);
    item->data_size = 1;
    item->v.c = value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_int32(const char *name,
                                bool consume_name,
                                int32_t value)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_INT32,
                                                  name, consume_name);
    item->data_size = sizeof(int32_t);
    item->v.i = value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_int64(const char *name,
                                bool consume_name,
                                int64_t value)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_INT64,
                                                  name, consume_name);
    item->data_size = sizeof(int64_t);
    item->v.q = value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_double(const char *name,
                                 bool consume_name,
                                 double value)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_DOUBLE,
                                                  name, consume_name);
    item->data_size = sizeof(double);
    item->v.d = value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_string(const char *name,
                                 bool consume_name,
                                 char *value)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_STRING,
                                                  name, consume_name);
    item->data_size = strlen(value) + 1;
    item->v.s = value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_string_copy(const char *name,
                                      bool consume_name,
                                      const char *value)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_STRING,
                                                  name, consume_name);
    item->data_size = strlen(value) + 1;
    item->v.s = gwyfile_memdup(value, item->data_size);
    if (!item->v.s) {
        free(item);
        item = NULL;
    }
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_object(const char *name,
                                 bool consume_name,
                                 GwyfileObject *value)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_OBJECT,
                                                  name, consume_name);
    item->data_size = gwyfile_object_size(value);
    item->v.o = value;
    value->owner = item;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_char_array(const char *name,
                                     bool consume_name,
                                     char *value,
                                     uint32_t array_length)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_CHAR_ARRAY,
                                                  name, consume_name);
    item->data_size = sizeof(uint32_t) + array_length;
    item->array_length = array_length;
    item->v.ca = value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_int32_array(const char *name,
                                      bool consume_name,
                                      int32_t *value,
                                      uint32_t array_length)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_INT32_ARRAY,
                                                  name, consume_name);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(int32_t);
    item->array_length = array_length;
    item->v.ia = value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_int64_array(const char *name,
                                      bool consume_name,
                                      int64_t *value,
                                      uint32_t array_length)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_INT64_ARRAY,
                                                  name, consume_name);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(int64_t);
    item->array_length = array_length;
    item->v.qa = value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_double_array(const char *name,
                                       bool consume_name,
                                       double *value,
                                       uint32_t array_length)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_DOUBLE_ARRAY,
                                                  name, consume_name);
    item->data_size = sizeof(uint32_t) + array_length*sizeof(double);
    item->array_length = array_length;
    item->v.da = value;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_string_array(const char *name,
                                       bool consume_name,
                                       char **value,
                                       uint32_t array_length)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_STRING_ARRAY,
                                                  name, consume_name);
    uint32_t i;
    item->data_size = sizeof(uint32_t);
    for (i = 0; i < array_length; i++)
        item->data_size += strlen(value[i]) + 1;
    item->v.sa = value;
    item->array_length = array_length;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal_object_array(const char *name,
                                       bool consume_name,
                                       GwyfileObject **value,
                                       uint32_t array_length)
{
    GwyfileItem *item = gwyfile_item_new_internal(GWYFILE_ITEM_OBJECT_ARRAY,
                                                  name, consume_name);
    uint32_t i;
    item->data_size = sizeof(uint32_t);
    for (i = 0; i < array_length; i++) {
        value[i]->owner = item;
        item->data_size += gwyfile_object_size(value[i]);
    }
    item->v.oa = value;
    item->array_length = array_length;
    return item;
}

static GwyfileItem*
gwyfile_item_new_internal(GwyfileItemType type,
                          const char *name,
                          bool consume_name)
{
    GwyfileItem *item;

    item = (GwyfileItem*)calloc(1, sizeof(GwyfileItem));
    assert(item);
    item->type = type;
    item->name_len = strlen(name);
    item->data_owned = true;
    if (consume_name)
        item->name = (char*)name;
    else {
        item->name = malloc(item->name_len+1);
        assert(item->name);
        memcpy(item->name, name, item->name_len+1);
    }

    return item;
}

static void
gwyfile_item_notify_size_change(GwyfileItem *item, size_t oldsize)
{
    GwyfileObject *owner = item->owner;

    if (!owner)
        return;

    if (item->data_size > oldsize)
        gwyfile_object_propagate_size_change(owner,
                                             item->data_size - oldsize, true);
    else
        gwyfile_object_propagate_size_change(owner,
                                             oldsize - item->data_size, false);
}

static void
gwyfile_item_propagate_size_change(GwyfileItem *item,
                                   size_t size_change,
                                   bool increase)
{
    assert(item->type == GWYFILE_ITEM_OBJECT
           || item->type == GWYFILE_ITEM_OBJECT_ARRAY);

    if (increase) {
        assert(item->data_size + size_change >= item->data_size);
        item->data_size += size_change;
    }
    else {
        assert(size_change <= item->data_size);
        item->data_size -= size_change;
    }

    if (item->owner) {
        gwyfile_object_propagate_size_change(item->owner,
                                             size_change, increase);
    }
}

static void
gwyfile_object_remove_last(GwyfileObject *object, bool freeitem)
{
    GwyfileItem *item;

    assert(object->nitems);
    item = object->items[object->nitems-1];
    assert(item->owner == object);
    gwyfile_object_propagate_size_change(object,
                                         gwyfile_item_size(item), false);
    item->owner = NULL;
    if (freeitem)
        gwyfile_item_free(item);
    object->nitems--;
}

static void
gwyfile_object_append(GwyfileObject *object, GwyfileItem *item)
{
    GwyfileItem **itemsnew;
    size_t newsize;

    if (object->nitems == object->nallocitems) {
        object->nallocitems = gwyfile_max(2*object->nallocitems, 4);
        newsize = object->nallocitems*sizeof(GwyfileItem*);
        itemsnew = (GwyfileItem**)realloc(object->items, newsize);
        /* This is crude.  However, we should not get here while reading a
         * file (XXX though we currently do), only by API calls. */
        assert(itemsnew);
        object->items = itemsnew;
    }

    object->items[object->nitems++] = item;
    item->owner = object;
    gwyfile_object_propagate_size_change(object, gwyfile_item_size(item), true);
}

static int
gwyfile_compare_items(const void *pa, const void *pb)
{
    const GwyfileItem *a = *(const GwyfileItem**)pa;
    const GwyfileItem *b = *(const GwyfileItem**)pb;

    return strcmp(a->name, b->name);
}

static const char*
gwyfile_object_find_duplicate_item(GwyfileObject *object)
{
    GwyfileItem **items = object->items;
    unsigned int i, n = object->nitems;

    if (n < 2)
        return NULL;

    qsort(items, n, sizeof(GwyfileItem*), &gwyfile_compare_items);

    for (i = 0; i < n-1; i++) {
        if (gwyfile_strequal(items[i]->name, items[i+1]->name))
            return items[i]->name;
    }

    return NULL;
}

static void
gwyfile_object_propagate_size_change(GwyfileObject *object,
                                     size_t size_change,
                                     bool increase)
{
    if (increase) {
        assert(object->data_size + size_change >= object->data_size);
        object->data_size += size_change;
    }
    else {
        assert(size_change <= object->data_size);
        object->data_size -= size_change;
    }

    if (object->owner) {
        gwyfile_item_propagate_size_change(object->owner,
                                           size_change, increase);
    }
}

// XXX: May be useful as a public function?
static inline bool
gwyfile_item_type_is_valid(GwyfileItemType type)
{
    static const char valid_types[] = "bciqdsoCIQDSO";

    return type && !!strchr(valid_types, (char)type);
}

// XXX: May be useful as a public function?
static inline bool
gwyfile_item_type_is_array(GwyfileItemType type)
{
    static const char array_types[] = "CIQDSO";

    return type && !!strchr(array_types, (char)type);
}

static inline char*
gwyfile_strdup(const char *s)
{
    size_t len;
    char *copy;

    if (!s)
        return NULL;

    len = strlen(s);
    copy = malloc(len+1);
    if (!copy) {
        errno = ENOMEM;   /* Generally not guaranteed by OS. */
        return NULL;
    }

    return (char*)memcpy(copy, s, len+1);
}

static inline void*
gwyfile_memdup(const void *p,
               size_t size)
{
    void *copy;

    if (!p)
        return NULL;

    copy = malloc(size);
    if (!copy) {
        errno = ENOMEM;   /* Generally not guaranteed by OS. */
        return NULL;
    }
    return memcpy(copy, p, size);
}

static char*
gwyfile_fread_string(FILE *stream, size_t *max_size,
                     GwyfileError **error, const char *what)
{
    unsigned int len = 0, size = 0;
    char *s = NULL, *snew;
    int c;

    if (!*max_size) {
        gwyfile_set_error_overrun(error, what);
        return NULL;
    }

    /* Read the string char by char to avoid seeking.  For a reasonable GWY
     * file efficiency is not a problem because the strings are not long.
     * For degenerate files do it in a reasonably safe manner, avoiding
     * quadratic-time operations. */
    do {
        if ((c = fgetc(stream)) == EOF) {
            gwyfile_set_error_fread(error, stream, what);
            free(s);
            return NULL;
        }

        if (len == size) {
            if (len == *max_size) {
                gwyfile_set_error_overrun(error, what);
                free(s);
                return NULL;
            }
            if (size >= 0x80000000u) {
                gwyfile_set_error(error,
                                  GWYFILE_ERROR_DOMAIN_DATA,
                                  GWYFILE_ERROR_LONG_STRING,
                                  "Insanely long string.");
                free(s);
                return NULL;
            }
            size = gwyfile_max(2*size, 16);
            size = gwyfile_min(size, *max_size);

            snew = (char*)realloc(s, size);
            if (!snew) {
                errno = ENOMEM;   /* Generally not guaranteed by OS. */
                gwyfile_set_error_errno(error);
                free(s);   /* Sic, ISO C says so. */
                return NULL;
            }
            s = snew;
        }
        s[len++] = (char)c;
    } while (c);

    *max_size -= len;   /* sic, len includes the terminating nul. */

    return s;
}

// XXX: May be useful as a public function?
static bool
gwyfile_is_valid_utf8(const char *s)
{
    unsigned int remains_10xxxxxx = 0;

    if (!s)
        return false;

    while (*s) {
        unsigned int b = *(const unsigned char*)s;
        if (!remains_10xxxxxx) {
            if ((b & 0x80) == 0) { /* 7bit characters */
                /* Do nothing here but do not put this case to else for speed:
                 * it has a high probability. */
            }
            else if ((b & 0xe0) == 0xc0) /* 110xxxxx 10xxxxxx sequence */
                remains_10xxxxxx = 1;
            else if ((b & 0xf0) == 0xe0) /* 1110xxxx 2 x 10xxxxxx sequence */
                remains_10xxxxxx = 2;
            /* Following are valid 32-bit UCS characters, but not 16-bit
             * Unicode. */
            else if ((b & 0xf8) == 0xf0) /* 1110xxxx 3 x 10xxxxxx sequence */
                remains_10xxxxxx = 3;
            else if ((b & 0xfc) == 0xf8) /* 1110xxxx 4 x 10xxxxxx sequence */
                remains_10xxxxxx = 4;
            else if ((b & 0xfe) == 0xfc) /* 1110xxxx 5 x 10xxxxxx sequence */
                remains_10xxxxxx = 5;
            /* If we get here the string is invalid. */
            else
                return false;
        }
        else {
            /* Broken 10xxxxxx sequence? */
            if ((b & 0xc0) != 0x80)
                return false;
            remains_10xxxxxx--;
        }
        s++;
    }

    return !remains_10xxxxxx;
}

static bool
gwyfile_is_valid_identifier(const char *s)
{
    if (!*s)
        return false;

    if (!((*s >= 'A' && *s <= 'Z')
          || (*s >= 'a' && *s <= 'z')))
        return false;

    while (*(++s)) {
        if (!((*s >= 'A' && *s <= 'Z')
              || (*s >= 'a' && *s <= 'z')
              || (*s >= '0' && *s <= '9')
              || *s == '_'))
            return false;
    }

    return true;
}

static bool
gwyfile_fwrite_le(const void *p0, unsigned int itemsize, size_t nitems,
                  FILE *stream)
{
#ifdef WORDS_BIGENDIAN
    /* NB: Must not make it static: would break multithread programs. */
    char staticbuf[BYTESWAP_STATIC_BUF_SIZE];

    const char *p = (const char*)p0;
    size_t size = nitems*itemsize;
    bool need_alloc = (size > BYTESWAP_STATIC_BUF_SIZE);
    size_t bufsize = (size < BYTESWAP_BLOCK_SIZE) ? size : BYTESWAP_BLOCK_SIZE;
    size_t bufnitems = bufsize/itemsize;
    char *buf = need_alloc ? malloc(bufsize) : staticbuf;
    bool retval = true;

    if (!buf) {
        errno = ENOMEM;   /* Generally not guaranteed by OS. */
        return false;
    }

    assert(0xffffffff/itemsize >= nitems);
    assert(bufsize % itemsize == 0);
    while (nitems > 0) {
        unsigned int thisnitems = (bufnitems > nitems) ? nitems : bufnitems;
        size_t thissize = thisnitems*itemsize;
        unsigned int i, j;
        char *bb = buf + (itemsize-1);

        for (i = 0; i < thisnitems; i++) {
            for (j = 0; j < itemsize; j++)
                *(bb--) = *(p++);
            bb += itemsize;
        }

        if (fwrite(buf, 1, thissize, stream) != thissize) {
            retval = false;
            break;
        }

        nitems -= thisnitems;
    }

    if (need_alloc)
        free(buf);

    return retval;
#else
    return fwrite(p0, itemsize, nitems, stream) == nitems;
#endif
}

static bool
gwyfile_fread_le(void *p0, unsigned int itemsize, size_t nitems,
                 FILE *stream)
{
#ifdef WORDS_BIGENDIAN
    char *p = (char*)p0;
    size_t i, size = nitems*itemsize;
    unsigned int j;

    if (fread(p, 1, size, stream) != size)
        return false;

    for (i = 0; i < nitems; i++) {
        char *bb = p + (itemsize-1);
        for (j = 0; j < itemsize/2; j++, bb--, p++) {
            char b = *bb;
            *bb = *p;
            *p = b;
        }
        p += itemsize - itemsize/2;
    }

    return true;
#else
    return fread(p0, itemsize, nitems, stream) == nitems;
#endif
}

static bool
gwyfile_check_size(size_t *max_size, size_t size,
                   GwyfileError **error, const char *what)
{
    if (*max_size < size) {
        gwyfile_set_error_overrun(error, what);
        return false;
    }

    *max_size -= size;
    return true;
}

static void*
gwyfile_alloc_check(size_t nbytes, GwyfileError **error)
{
    void *p = malloc(nbytes);
    if (p)
       return p;

    errno = ENOMEM;   /* Generally not guaranteed by OS. */
    gwyfile_set_error_errno(error);
    return NULL;
}

static GwyfileError*
gwyfile_create_error(GwyfileErrorDomain domain, int code)
{
    GwyfileError *error = (GwyfileError*)malloc(sizeof(GwyfileError));
    assert(error);
    error->domain = domain;
    error->code = code;
    return error;
}

static void
gwyfile_set_error_overrun(GwyfileError **error, const char *what)
{
    gwyfile_set_error(error,
                      GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_CONFINEMENT,
                      "Overrun of parent block inside %s.", what);
}

static void
gwyfile_set_error(GwyfileError **error,
                  GwyfileErrorDomain domain,
                  GwyfileErrorCode code,
                  const char *format, ...)
{
    GwyfileError *err;
    va_list ap;
    /* This is sufficient for a maximum-depth path consisting of all-escaped
     * maximum-length component names.  We use a fixed buffer of this size on
     * MS Windows where vsnprintf() is broken. */
    int len = 65536;

    if (!error)
        return;

    assert(!*error);
#ifndef _WIN32
    {
        /* XXX: vsnprintf() always seems to just return -1 on MS Windows when
         * the string does not fit.  We cannot calculate the required length
         * there just by asking vsnprintf(). */
        char buf[1];
        va_start(ap, format);
        len = vsnprintf(buf, sizeof(buf), format, ap);
        va_end(ap);
    }
#endif

    err = gwyfile_create_error(domain, code);
    if (len > 0) {
        err->message = malloc(len+1);
        assert(err->message);
        va_start(ap, format);
        len = vsnprintf(err->message, len+1, format, ap);
        va_end(ap);
#ifdef _WIN32
        /* Usually, the error messages are much much shorter than the maximum
         * length.  So avoid eating large chunks of memory for each error if we
         * can.  */
        if (len > 0 && len < 32768) {
            char *message = gwyfile_strdup(err->message);
            free(err->message);
            err->message = message;
        }
#endif
        if (len > 0) {
            *error = err;
            return;
        }
        free(err->message);
    }
    /* Hijack err to report something completely different. */
    err->domain = GWYFILE_ERROR_DOMAIN_SYSTEM;
    err->code = errno;
    err->message = gwyfile_strdup("I/O error in vsnprintf() "
                                  "while formatting another error.");
    assert(err->message);
    *error = err;
}

static void
gwyfile_set_error_errno(GwyfileError **error)
{
    GwyfileError *err;
    int myerrno;

    if (!error)
        return;

    myerrno = errno;
    assert(!*error);
    *error = err = (GwyfileError*)malloc(sizeof(GwyfileError));
    assert(err);
    err->domain = GWYFILE_ERROR_DOMAIN_SYSTEM;
    err->code = myerrno;
#ifndef _WIN32
    err->message = gwyfile_strdup(strerror(myerrno));
#else
    char message[GWYFILE_MAX_ERROR_MESSAGE_LENGTH];
    strerror_s(err->message, GWYFILE_MAX_ERROR_MESSAGE_LENGTH, myerrno);
    err->message = gwyfile_strdup(message);
#endif
}

static void
gwyfile_set_error_fread(GwyfileError **error, FILE *stream, const char *what)
{
    if (feof(stream)) {
        gwyfile_set_error(error,
                          GWYFILE_ERROR_DOMAIN_DATA, GWYFILE_ERROR_CONFINEMENT,
                          "File ended inside %s.", what);
    }
    else
        gwyfile_set_error_errno(error);

}

/*!\fn void gwyfile_error_clear(GwyfileError **error)
 * \brief Clears a ::GwyfileError.
 *
 * If the argument is \c NULL or pointer to \c NULL this function is no-op.
 *
 * Otherwise it frees the error structure and sets the pointer back to
 * <tt>NULL</tt>.
 *
 * \param error Error structure to clear.
 */
void
gwyfile_error_clear(GwyfileError **error)
{
    if (!error || !*error)
        return;

    free((*error)->message);
    free(*error);
    *error = NULL;
}

/*!\fn void gwyfile_error_list_init(GwyfileErrorList *errlist)
 * \brief Initializes a ::GwyfileErrorList.
 *
 * The argument should be the pointer to an uninitialized error list structure.
 * It will be initialized to an empty error list.
 *
 * \param errlist Error list structure to initialize.
 */
void
gwyfile_error_list_init(GwyfileErrorList *errlist)
{
    errlist->errors = NULL;
    errlist->n = 0;
}

/*!\fn void gwyfile_error_list_clear(GwyfileErrorList *errlist)
 * \brief Frees all errors in a ::GwyfileErrorList.
 *
 * This function clears (frees) all errors in the errors list and resets the
 * list to empty.  \c NULL items may be present in the list.
 *
 * Note that the structure itself is not freed.
 *
 * \param errlist Error list structure to clear.
 */
void
gwyfile_error_list_clear(GwyfileErrorList *errlist)
{
    unsigned int i;

    for (i = 0; i < errlist->n; i++) {
        gwyfile_error_clear(errlist->errors + i);
        free(errlist->errors[i]);
    }
    free(errlist->errors);
    errlist->errors = NULL;
    errlist->n = 0;
}

static void
gwyfile_error_list_append(GwyfileErrorList *errlist, GwyfileError *err,
                          size_t *nalloc)
{
    if (errlist->n == *nalloc) {
        *nalloc = (*nalloc ? 2*(*nalloc) : 8);
        errlist->errors = realloc(errlist->errors,
                                  (*nalloc)*sizeof(GwyfileError*));
        assert(errlist->errors);
    }
    errlist->errors[errlist->n++] = err;
}

/*!\fn bool gwyfile_check_object(const GwyfileObject *object, unsigned int flags, GwyfileErrorList *errlist)
 * \brief Checks an object for specifications violations.
 *
 * This functions check for problems that are not physically prevented during
 * normal libgwyfile usage.
 *
 * \param object Object to check.
 * \param flags Combination of bits from ::GwyfileCheckFlags defining the
 *              categories of problems to look for.
 * \param errlist Error list for detailer deport.  Pass \c NULL if you are
 *        only interested in OK/not OK information.  You can also pass an error
 *        list that already contains some errors; additional errors will be
 *        added to the list.
 * \return \c true if the object passed the checks.
 * \since 1.1
 */
bool
gwyfile_check_object(const GwyfileObject *object,
                     unsigned int flags,
                     GwyfileErrorList *errlist)
{
    size_t nalloc = errlist ? errlist->n : 0;

    assert(object);
    flags &= GWYFILE_CHECK_FLAG_VALIDITY | GWYFILE_CHECK_FLAG_WARNING;
    if (!flags)
        return true;

    return gwyfile_check_object_internal(object, flags, errlist, &nalloc);
}

static bool
gwyfile_check_valid_utf8(const char *s,
                         GwyfileInvalidCode code,
                         const GwyfileObject *object,
                         const GwyfileItem *item,
                         GwyfileErrorList *errlist,
                         size_t *nalloc)
{
    GwyfileError *err = NULL;
    const char *what = "???";
    char *path;

    if (gwyfile_is_valid_utf8(s))
        return true;

    if (!errlist)
        return false;

    if (code == GWYFILE_INVALID_UTF8_TYPE)
        what = "object type";
    else if (code == GWYFILE_INVALID_UTF8_NAME)
        what = "item name";
    else if (code == GWYFILE_INVALID_UTF8_STRING)
        what = "string value";

    path = gwyfile_format_path(object, item);
    gwyfile_set_error(&err, GWYFILE_ERROR_DOMAIN_VALIDITY, code,
                      "Invalid UTF-8 in %s %s", what, path);
    free(path);
    gwyfile_error_list_append(errlist, err, nalloc);
    return false;
}

static bool
gwyfile_check_valid_identifier(const GwyfileObject *object,
                               GwyfileErrorList *errlist,
                               size_t *nalloc)
{
    GwyfileError *err = NULL;
    const char *s = object->name;
    char *path;

    if (gwyfile_is_valid_identifier(s))
        return true;

    if (!errlist)
        return false;

    path = gwyfile_format_path(object, NULL);
    gwyfile_set_error(&err,
                      GWYFILE_ERROR_DOMAIN_WARNING,
                      GWYFILE_WARNING_TYPE_IDENTIFIER,
                      "Object type is not a valid identifier in %s",
                      path);
    free(path);
    gwyfile_error_list_append(errlist, err, nalloc);
    return false;
}

static bool
gwyfile_check_nonempty_name(const GwyfileItem *item,
                            GwyfileErrorList *errlist,
                            size_t *nalloc)
{
    GwyfileError *err = NULL;
    const char *s = item->name;
    char *path;

    if (strlen(s))
        return true;

    if (!errlist)
        return false;

    path = gwyfile_format_path(item->owner, NULL);
    gwyfile_set_error(&err,
                      GWYFILE_ERROR_DOMAIN_WARNING,
                      GWYFILE_WARNING_EMPTY_NAME,
                      "Empty item name in %s",
                      path);
    free(path);
    gwyfile_error_list_append(errlist, err, nalloc);
    return false;
}

static inline bool
gwyfile_double_isnormal(double x)
{
    GwyfileDouble dbl;
    dbl.v_double = x;
    return !(dbl.mpn.biased_exponent == 0x7ff);
}

static bool
gwyfile_check_double(const GwyfileItem *item,
                     double x,
                     GwyfileErrorList *errlist,
                     size_t *nalloc)
{
    GwyfileError *err = NULL;
    char *path;

    if (gwyfile_double_isnormal(x))
        return true;

    if (!errlist)
        return false;

    path = gwyfile_format_path(NULL, item);
    gwyfile_set_error(&err,
                      GWYFILE_ERROR_DOMAIN_VALIDITY, GWYFILE_INVALID_DOUBLE,
                      "Invalid double precision number in %s",
                      path);
    free(path);
    gwyfile_error_list_append(errlist, err, nalloc);
    return false;
}

static bool
gwyfile_check_object_internal(const GwyfileObject *object,
                              unsigned int flags,
                              GwyfileErrorList *errlist,
                              size_t *nalloc)
{
    size_t oldn = (errlist ? errlist->n : 0);
    unsigned int i;

    if (flags & GWYFILE_CHECK_FLAG_VALIDITY) {
        if (!gwyfile_check_valid_utf8(object->name, GWYFILE_INVALID_UTF8_TYPE,
                                      object, NULL, errlist, nalloc)
            && !errlist)
            return false;
    }

    if (flags & GWYFILE_CHECK_FLAG_WARNING) {
        if (!gwyfile_check_valid_identifier(object, errlist, nalloc)
            && !errlist)
            return false;
    }

    for (i = 0; i < object->nitems; i++) {
        GwyfileItem *item = object->items[i];
        if (!gwyfile_check_item_internal(item, flags, errlist, nalloc)
            && !errlist)
            return false;
    }

    return !errlist || errlist->n == oldn;
}

static bool
gwyfile_check_item_internal(const GwyfileItem *item,
                            unsigned int flags,
                            GwyfileErrorList *errlist,
                            size_t *nalloc)
{
    GwyfileItemType type = item->type;
    size_t oldn = (errlist ? errlist->n : 0);
    unsigned int i, array_length = item->array_length;

    if (flags & GWYFILE_CHECK_FLAG_VALIDITY) {
        if (!gwyfile_check_valid_utf8(item->name, GWYFILE_INVALID_UTF8_NAME,
                                      NULL, item, errlist, nalloc)
            && !errlist)
            return false;
    }

    if (flags & GWYFILE_CHECK_FLAG_WARNING) {
        if (!gwyfile_check_nonempty_name(item, errlist, nalloc)
            && !errlist)
            return false;
    }

    if (flags & GWYFILE_CHECK_FLAG_VALIDITY) {
        if (type == GWYFILE_ITEM_STRING) {
            if (!gwyfile_check_valid_utf8(item->v.s,
                                          GWYFILE_INVALID_UTF8_STRING,
                                          NULL, item, errlist, nalloc)
                && !errlist)
                return false;
        }
        else if (type == GWYFILE_ITEM_STRING_ARRAY) {
            for (i = 0; i < array_length; i++) {
                if (!gwyfile_check_valid_utf8(item->v.sa[i],
                                              GWYFILE_INVALID_UTF8_STRING,
                                              NULL, item, errlist, nalloc)
                    && !errlist)
                    return false;
            }
        }
        else if (type == GWYFILE_ITEM_DOUBLE) {
            if (!gwyfile_check_double(item, item->v.d, errlist, nalloc)
                && !errlist)
                return false;
        }
        else if (type == GWYFILE_ITEM_DOUBLE_ARRAY) {
            for (i = 0; i < array_length; i++) {
                if (!gwyfile_check_double(item, item->v.da[i], errlist, nalloc)
                    && !errlist)
                    return false;
            }
        }
    }

    if (type == GWYFILE_ITEM_OBJECT) {
        if (!gwyfile_check_object_internal(item->v.o, flags, errlist, nalloc)
            && !errlist)
            return false;
    }
    else if (type == GWYFILE_ITEM_OBJECT_ARRAY) {
        for (i = 0; i < array_length; i++) {
            if (!gwyfile_check_object_internal(item->v.oa[i], flags,
                                               errlist, nalloc)
                && !errlist)
                return false;
        }
    }

    return !errlist || errlist->n == oldn;
}

static size_t
gwyfile_escaped_strlen(const char *s)
{
    const unsigned char *us = (const unsigned char*)s;
    unsigned int j, c;
    size_t len = 0;

    for (j = 0; (c = us[j]) && len <= GWYFILE_PATH_ABBREVIATION_LIMIT; j++) {
        if (c == '/' || c == ' ' || c == '\\')
            len += 2;
        else if (c > 0x20 && c < 0x7f)
            len += 1;
        else
            len += 4;
    }
    if (c)
        len += 3;

    return len;
}

static void
gwyfile_escaped_strappend(char *out, const char *s)
{
    static const char hexadecimal[] = "0123456789abcdef";
    const unsigned char *us = (const unsigned char*)s;
    unsigned int j, c;
    size_t len = 0;

    for (j = 0; (c = us[j]) && len <= GWYFILE_PATH_ABBREVIATION_LIMIT; j++) {
        if (c == '/' || c == ' ' || c == '\\') {
            out[len++] = '\\';
            out[len++] = s[j];
        }
        else if (c > 0x20 && c < 0x7f) {
            out[len++] = s[j];
        }
        else {
            out[len++] = '\\';
            out[len++] = 'x';
            out[len++] = hexadecimal[c/16];
            out[len++] = hexadecimal[c % 16];
        }
    }
    if (c) {
        out[len++] = '.';
        out[len++] = '.';
        out[len++] = '.';
    }
}

/* Pass either non-NULL leaf_object or leaf_item (or both NULL for an empty
 * path).  The function formats a /-separated path from the top-level item or
 * object that sort of identifies the leaf there.  All strange characters are
 * escaped (including UTF-8) and too long component names are truncated and
 * ellpisized. */
static char*
gwyfile_format_path(const GwyfileObject *leaf_object,
                    const GwyfileItem *leaf_item)
{
    const GwyfileObject *object;
    const GwyfileItem *item;
    size_t len, pos;
    unsigned int i;
    const char *s;
    char *path;

    assert(!leaf_object || !leaf_item);

    object = leaf_object;
    item = leaf_item;
    len = i = 0;
    while (object || item) {
        if (i++)
            len++;
        if (object) {
            s = object->name;
            item = object->owner;
            object = NULL;
        }
        else {
            s = item->name;
            object = item->owner;
            item = NULL;
        }
        len += gwyfile_escaped_strlen(s);
    }

    if (!len)
        return gwyfile_strdup("the toplevel object");

    path = (char*)malloc(len+1);
    if (!path)
        return gwyfile_strdup("???");

    path[len] = '\0';
    pos = len;
    i = 0;
    object = leaf_object;
    item = leaf_item;
    while (object || item) {
        if (i++) {
            pos--;
            path[pos] = '/';
        }
        if (object) {
            s = object->name;
            item = object->owner;
            object = NULL;
        }
        else {
            s = item->name;
            object = item->owner;
            item = NULL;
        }
        pos -= gwyfile_escaped_strlen(s);
        gwyfile_escaped_strappend(path + pos, s);
    }
    assert(pos == 0);

    return path;
}

/*!\enum GwyfileItemType
 * \brief Type of data items that can be present in a GWY file.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_BOOL
 * \brief Boolean (true or false).
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_CHAR
 * \brief Single character.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_INT32
 * \brief 32bit integer.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_INT64
 * \brief 64bit integer.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_DOUBLE
 * \brief IEEE double precision floating point number.
 *
 * A conforming GWY file may only contain finite floating point values.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_STRING
 * \brief String of characters.
 *
 * All strings in a conforming GWY file must be UTF-8 encoded (or
 * ASCII-encoding, since ASCII is a subset of UTF-8).  See
 * #GWYFILE_ITEM_CHAR_ARRAY for a raw sequence of characters.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_OBJECT
 * \brief Object, i.e. a nested data structure.
 *
 * In libgwyfile the corresponding C data type is ::_GwyfileObject*.  In
 * Gwyddion, these items corresponds to actual objects in the type system.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_CHAR_ARRAY
 * \brief Array of characters.
 *
 * Unlike #GWYFILE_ITEM_STRING, an array of characters is
 * not considered text, just a sequence of bytes.  There is no encoding
 * implied.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_INT32_ARRAY
 * \brief Array of 32bit integers.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_INT64_ARRAY
 * \brief Array of 64bit integers.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_DOUBLE_ARRAY
 * \brief Array of IEEE double precision floating point numbers.
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_STRING_ARRAY
 * \brief Array of character strings.
 *
 * All strings in a conforming GWY file must be UTF-8 encoded (or
 * ASCII-encoding, since ASCII is a subset of UTF-8).
 */

/*!\var GwyfileItemType::GWYFILE_ITEM_OBJECT_ARRAY
 * \brief Array of objects, i.e. a nested data structures.
 * \sa #GWYFILE_ITEM_OBJECT
 */

/*!\struct _GwyfileItem
 * \brief One piece of data in a GWY file.
 *
 * \c GwyfileItem is an opaque structure representing one particular piece of
 * data in a GWY file.  It is also called ‘component’ in the user guide (but
 * usually ‘item’ in Gwyddion code).
 *
 * Data items are non-recyclable.  Item name and type are set upon creation and
 * fixed during its lifetime.  Since a data item corresponds to a particular
 * piece of data in the GWY file, if the same piece of data (for instance a
 * string) occurs multiple times in the file, each has its own GwyfileItem.
 *
 * Data items of different types are created using constructor function such as
 * gwyfile_item_new_bool() or gwyfile_item_new_double().
 *
 * If you derive the item name from external input, make sure it is valid.
 */

/*!\struct _GwyfileObject
 * \brief Data structure with named components.
 *
 * \c GwyfileObject is an opaque structure representing one data structure in
 * a GWY file.  In files created by or for Gwyddion, they correspond to actual
 * objects in the type system and their names correspond to type names in the
 * object system.  If a generic GWY file they just represent a way of grouping
 * data items together in a hieararchical structure.
 */

/*!\fn GwyfileObjectForeachFunc
 * \brief Type of function for iterating over GWY file data object items.
 *
 * This function type is used for gwyfile_object_foreach().
 *
 * \param item An object GWY file data item.
 * \param user_data Data pointer passed to gwyfile_object_foreach().
 */

/*!\struct GwyfileError
 * \brief Detailed information about an error.
 *
 * \c GwyfileError is modelled after \c GError and represents a detailed error
 * information that you can optionally obtain from I/O functions.
 *
 * If you are not interested in the details, you can always pass \c NULL to all
 * functions taking a ::GwyfileError** argument.  If you pass a pointer to a \c
 * NULL initialised ::GwyfileError*, the function will fill it with the error
 * details on failure.
 *
 * Note the error must be \c NULL initialised: error pileup is not permitted.
 * Function gwyfile_error_clear() frees the error structure and sets the
 * pointer to \c NULL again.
 */

/*!\var GwyfileError::domain
 * \brief Identifier of the class of errors.
 */

/*!\var GwyfileError::code
 * \brief Particular error code.  For errors from the system domain it is
 *        equal to \c errno while for libgwyfile-specific errors values from
 *        the ::GwyfileErrorCode enum are used.
 */

/*!\var GwyfileError::message
 * \brief Text message describing the error.  It is allocated when the
 *        error struct is created and freed with gwyfile_error_clear().
 */

/*!\struct GwyfileErrorList
 * \brief List of errors.
 *
 * \c GwyfileErrorList holds a list of errors.  It is useful for non-fatal
 * error handling such as file validity checking.
 *
 * A new error list variable would be typically created on stack and
 * initialized with gwyfile_error_list_init().  After the errors are no longer
 * needed use gwyfile_error_list_clear() to clear the list, freeing all the
 * errors.  The variable can be then reused to gather another list of errors.
 *
 * \since 1.1
 */

/*!\var GwyfileErrorList::errors
 * \brief Array holding the errors.
 */

/*!\var GwyfileErrorList::n
 * \brief Number of errors in the list.
 */

/*!\enum GwyfileErrorDomain
 * \brief Class of errors that can be reported via ::GwyfileError.
 *
 * Each domain has its own set of codes.  An error is uniquely identified by
 * domain and code.
 */

/*!\var GwyfileErrorDomain::GWYFILE_ERROR_DOMAIN_SYSTEM
 * \brief System error domain: codes are equal to \c errno values.  They
 *        reflect I/O failures and other system errors.
 */

/*!\var GwyfileErrorDomain::GWYFILE_ERROR_DOMAIN_DATA
 * \brief Libgwyfle data error domain: codes are equal to ::GwyfileErrorCode
 *        values.  They represent data format errors at the physical level,
 *        preventing serialization or deserialization.
 */

/*!\var GwyfileErrorDomain::GWYFILE_ERROR_DOMAIN_VALIDITY
 * \brief Libgwyfle validity error domain: codes are equal to
 *        ::GwyfileInvalidCode values.  Errors from this domain represent
 *        violations by the GWY file format specifications not physically
 *        prevented during normal libgwyfile calls.  They are only reported by
 *        explicit gwyfile_check_object() calls.
 *
 * \since 1.1
 */

/*!\var GwyfileErrorDomain::GWYFILE_ERROR_DOMAIN_WARNING
 * \brief Libgwyfle validity error domain: codes are equal to
 *        ::GwyfileInvalidCode values.  Errors from this domain represent
 *        problematic uses of the GWY file format that are, however, not
 *        forbidden by the specifications.  They are only reported by explicit
 *        gwyfile_check_object() calls.
 *
 * \since 1.1
 */

/*!\enum GwyfileCheckFlags
 * \brief Flags that can be passed to gwyfile_check_object().
 *
 * Each flag enables the corresponding category of errors from
 * ::GwyfileErrorDomain.
 *
 * \since 1.1
 */

/*!\var GwyfileCheckFlags::GWYFILE_CHECK_FLAG_VALIDITY
 * \brief Enables checking for errors from the
 *        GwyfileErrorDomain::GWYFILE_ERROR_DOMAIN_VALIDITY category
 *        in gwyfile_check_object().
 */

/*!\var GwyfileCheckFlags::GWYFILE_CHECK_FLAG_WARNING
 * \brief Enables checking for errors from the
 *        GwyfileErrorDomain::GWYFILE_ERROR_DOMAIN_WARNING category
 *        in gwyfile_check_object().
 */

/*!\enum GwyfileErrorCode
 * \brief Error codes for libgwyfile-specific errors.
 *
 * They can occur in ::GwyfileError when the domain is
 * #GWYFILE_ERROR_DOMAIN_DATA.
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_MAGIC
 * \brief The file does not have the expected magic header.
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_ITEM_TYPE
 * \brief Unknown data item type was encountered.
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_CONFINEMENT
 * \brief A piece of data does not fit inside its parent object or item.
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_ARRAY_SIZE
 * \brief An array has an invalid size, i.e. zero or mismatching other sizes.
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_DUPLICATE_NAME
 * \brief Multiple items of the same name were encountered in an object.
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_LONG_STRING
 * \brief Too long string was encountered.
 *
 * Currently, libgwyfile has an internal limitation of maximum string size to
 * 0x7ffffffff (2GB), even though the GWY file format does not have such
 * limitation.  No sane file should exceed that.
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_OBJECT_SIZE
 * \brief An object size does not fit into a 32bit integer.
 *
 * This error can occur during file writing on systems with larger than 32bit
 * <tt>size_t</tt>.  While it is possible to construct an object larger than
 * 4GB in memory, it cannot be written to a file because sizes in the GWY file
 * format are 32bit.
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_OBJECT_NAME
 * \brief A Gwyddion-specific GWY file data object has the wrong name (type).
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_MISSING_ITEM
 * \brief A mandatory item in a Gwyddion-specific GWY file data object is
 *        missing.
 */

/*!\var GwyfileErrorCode::GWYFILE_ERROR_TOO_DEEP_NESTING
 * \brief The object/item nesting depth exceeds the allowed maximum.
 *
 * Currently, libgwyfile has an internal limitation of maximum object/item
 * nesting level of 200.  This is to avoid stack overflow for files with
 * devilishly deep nesting.
 */

/*!\enum GwyfileInvalidCode
 * \brief Error codes for validity errors.
 *
 * They can occur in ::GwyfileError when the domain is
 * #GWYFILE_ERROR_DOMAIN_VALIDITY.
 *
 * \since 1.1
 */

/*!\var GwyfileInvalidCode::GWYFILE_INVALID_UTF8_NAME
 * \brief Item name is not a valid UTF-8 string.
 */

/*!\var GwyfileInvalidCode::GWYFILE_INVALID_UTF8_TYPE
 * \brief Object type is not a valid UTF-8 string.
 */

/*!\var GwyfileInvalidCode::GWYFILE_INVALID_UTF8_STRING
 * \brief String value (or string array value) is not a valid UTF-8 string.
 */

/*!\var GwyfileInvalidCode::GWYFILE_INVALID_DOUBLE
 * \brief Double value is infinity or not-a-number.
 */

/*!\enum GwyfileWarningCode
 * \brief Error codes for file format warnings.
 *
 * They can occur in ::GwyfileError when the domain is
 * #GWYFILE_ERROR_DOMAIN_WARNING.
 *
 * \since 1.1
 */

/*!\var GwyfileWarningCode::GWYFILE_WARNING_TYPE_IDENTIFIER
 * \brief Object type is not a valid C identifier.
 */

/*!\var GwyfileWarningCode::GWYFILE_WARNING_EMPTY_NAME
 * \brief Item name is an empty string.
 */

/*!\file gwyfile.h
 * \brief Gwyfile Library
 */

/*!\mainpage
 *
 * The libgwyfile library contains fundamental functions for reading and
 * writing Gwyddion GWY files as foreign data, i.e. without adopting the
 * Gwyddion object system.
 *
 * The latest libgwyfile source code and documentation can be found on the
 * [project web page](http://libgwyfile.sourceforge.net/) at SourceForge.
 *
 * \section namespace Namespace
 *
 * All macros, declarations and exported symbols bear the gwyfile prefix to
 * avoid clash with other names.  Specifically:
 * \li Macro names and constants such as enumerated values are all UPPER_CASE
 *     and prefixed with <tt>GWYFILE_</tt>.
 * \li Function names are all lower_case and prefixed with <tt>gwyfile_</tt>.
 * \li Type names are PascalCase and prefixed with <tt>Gwyfile</tt>.
 *
 * Names of this form are to be treated as reserved and avoided for your own
 * symbols.  This is recommended even if you are embedding the library as it
 * makes easier updating to its future versions.
 *
 * \section ownership Ownership rules
 *
 * Since the GWY file data structures always form a forest of trees, object and
 * items are either roots (including standalone objects and items) or owned by
 * the parent object or item.  When you add an item into an object or put an
 * object to an object-holding item, you always transfer the ownership.  Only
 * the roots are owned by you.
 *
 * Specific non-atomic data, such as arrays and strings, are also typically
 * owned by the data item containing them and the item takes care of freeing
 * them when destroyed itself.  Specifically, this is always the case when they
 * are created by reading a file.  However, the ownership can be transferred
 * between the item and you.
 *
 * For creation of non-atomic data, there are three types of functions:
 * \li Plain, such as gwyfile_item_new_string().  They consume the
 *     data passed to them, i.e. ownership is passed from you to the item and,
 *     generally, you should not touch the data at all afterwards.  The item
 *     will free the data with free() upon its own destruction.
 * \li Copying, such as gwyfile_item_new_string_copy().  They make a copy of
 *     the data passed to them.  No ownership is transferred but, of course, it
 *     incurs some memory overhead.
 * \li Constant, such as gwyfile_item_new_string_const().  No copy is made and
 *     no ownership transferred.  However, the data passed to such function
 *     must not cease to exists and must not change during the item lifetime.
 *     These functions are often the most efficient but they are also most
 *     prone to incorrect usage.
 *
 * Each item construction function has also an item data-setting counterpart.
 * For instance gwyfile_item_set_string(), gwyfile_item_set_string_copy() and
 * gwyfile_item_set_string_const() correspond to the three string item
 * construction functions mentioned above.
 *
 * For obtaining of non-atomic data, two different types of functions exist:
 * \li Plain, such as gwyfile_item_get_string().  They return the data but keep
 *     the ownership hence the item will free the data when destroyed itself.
 * \li Taking, such as gwyfile_item_take_string().  Such function transfers the
 *     ownership from the item to the caller.  Therefore, it can only be used
 *     if the item actually owns the data.  Again, using these functions incurs
 *     the smallest overhead but requires more care.
 *
 * \section errors Error handling
 *
 * Roughly, libgwyfile distinguishes three severities of errors
 * \li Business as usual.  These problems are expected to occur during normal
 *     operation and include I/O errors, data format errors or passing
 *     names of non-existent items to gwyfile_object_get() or
 *     gwyfile_object_remove().  They are reported by the return value.  In the
 *     case of file-related operations, more details can be obtained via
 *     ::GwyfileError.
 * \li Trouble.  This includes primarily failures to allocate large memory
 *     chunks in direct function calls such as
 *     gwyfile_item_new_double_array_copy().  They are reported by an abnormal
 *     function return value (usually <tt>NULL</tt>) and setting \c errno to
 *     <tt>ENOMEM</tt>.  Note too large data encountered during the loading
 *     of a GWY file still belong to the previous category and are reported
 *     with error domain \c GWYFILE_ERROR_DOMAIN_SYSTEM and code
 *     <tt>ENOMEM</tt>.
 * \li Panic.  The library panics and aborts via assert() if an invalid
 *     argument is passed to a function.  This means the function
 *     cannot proceed without breaking invariants and likely causing heap or
 *     stack corruption down the road.  Examples include tring to insert one
 *     item to multiple objects (breaking the forest of trees invariant),
 *     passing \c NULL as item or object arguments (where not permitted) or
 *     trying to take ownership of data that was already taken.  The failure
 *     to allocate a small fixed-size chunk of memory (e.g. a ::_GwyfileObject
 *     struct) leads to the same reaction, as total heap exhaustion is a
 *     non-recoverable error for essentially all programs.
 *
 * \section version Version
 *
 * This documentation was generated from the following source code revision:
 * \verbatim $Id: gwyfile.c 283 2016-04-27 20:48:28Z yeti-dn $\endverbatim
 */

/*!\addtogroup GwyfileHighLevel
 * @{
 * High-level functions help with gathering information about specific data
 * types in Gwyddion GWY files.  In particular, functions for enumeration of
 * all channels, graphs or volume data in a file are provided.  These function
 * also carry out some basic sanity checks, ensuring for instance not that
 * ‘something’ is present at <tt>"/0/data"</tt> but that it actually looks like
 * a valid GwyDataField object.
 */
/**@}*/

/*!\addtogroup GwyObject
 * @{
 * Convenience constructors and information extractors are available for most
 * types of Gwyddion objects.
 *
 * No constructor is provided for \c GwyContainer because it is a generic data
 * container with no mandatory items so gwyfile_object_new() works just fine.
 * Use the application-level functions to manage channels, graph or volume data
 * inside a GwyContainer representing a GWY file.
 *
 * Furthermore, classes such as <tt>GwyCalData</tt>, <tt>Gwy3DSetup</tt> and
 * <tt>GwyStringList</tt> are too specialised to warrant convenience
 * constructors.
 *
 * The convenience information extractors paper over less serious conformance
 * problems, such as missing or non-positive real field dimensions, and return
 * sane and safe default values.  They also supply defaults for optional data
 * items.  This is what one usually wants from a convenience function.  The raw
 * truth can be obtained by the low-level object and item interface.
 */
/**@}*/

/*!\addtogroup GwyfileError
 * @{
 * Details about run-time (expected) errors such as I/O failures or malformed
 * files are reported using \c GwyfileError structures.  See \ref errors for a
 * general overview of error handling.
 *
 * If you are not interested in details of errors you can always pass \c
 * NULL as the \c GwyfileError** pointer and just check the function return
 * values.
 *
 * To request the detailed information, pass the pointer to a \c NULL
 * initialised \c GwyfileError* as the error argument.  You must then always
 * check the success or failure of each function because error pileup (calling
 * functions with the error struct already filled) is not permitted.
 * Furthermore, \c GwyfileError* filled with error details has to be freed
 * with gwyfile_error_clear() when no longer needed.
 *
 * These rules are essentially identical as those for \c GError in GLib.  If
 * you are familiar with \c GError you should feel at home.
 */
/**@}*/

/*!\addtogroup GwyfileCheck
 * @{
 * Libgwyfile functions ensure some minimal level of physical consitency
 * of written files and only accept files that exhibit such consistency.
 * However, there are some things the GWY file format specifications forbid but
 * libgwyfile does not prevent you from doing.  Similar, a few things are not
 * a good idea even though the specifications do not explicitly forbid them.
 *
 * You can use gwyfile_check_object() for further validation of a GWY file.
 * At this moment the function only operates on the generic level, i.e. it does
 * not check specific data organisation and relations in files written by
 * Gwyddion.
 *
 * Generally, you should never write files that do not pass the check with
 * GwyfileCheckFlags::GWYFILE_CHECK_FLAG_VALIDITY (except for error handling
 * testing).  You should never need to read files that do not pass this check.
 *
 * Files with errors only from the
 * GwyfileCheckFlags::GWYFILE_CHECK_FLAG_WARNING category are nonstandard,
 * but can be possibly meaningful as generic (non-Gwyddion) GWY files.
 */
/**@}*/

/*!\example writegwy.c
 * Example showing how to write a simple Gwyddion GWY file with one channel
 * a graph with a couple of curves.
 */

/*!\example readgwy.c
 * Example showing how to read a Gwyddion GWY file, enumerate channels, graphs,
 * volume data, etc. and obtain further information about them.
 */

/*!\example writegeneric.c
 * Example showing how to write a generic GWY file with various kinds of
 * data types.
 */

/*!\example readgeneric.c
 * Example showing how to read a generic GWY file with arbitrary data types.
 * It dumps the hierarchical file structure to the standard output.
 */

/*!\example checkgeneric.c
 * Example demonstrating the functions for checking GWY files beyond the
 * physical consistency enforced by libgwyfile.
 */

/* vim: set cin et ts=4 sw=4 cino=>1s,e0,n0,f0,{0,}0,^0,\:1s,=0,g1s,h0,t0,+1s,c3,(0,u0 : */
