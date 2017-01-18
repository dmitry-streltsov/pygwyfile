/*
 * $Id: gwyfile.h 266 2016-02-29 13:35:53Z yeti-dn $
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

#ifndef __GWYFILE_GWYFILE_H__
#define __GWYFILE_GWYFILE_H__ 1

#if 1
#include <stdbool.h>
#else
/* For an antique pre-C99 compiler you can define instead: */
typedef enum { false = 0, true = 1 } bool;
#endif

#if 1
#include <stdint.h>
#else
/* For an antique pre-C99 compiler you need to define int32_t, uint32_t,
 * int64_t and uint64_t to EXACTLY(!) 32bit and 64bit signed and unsigned
 * integral types.  The following may not be correct for your system. */
typedef int int32_t;
typedef unsigned int uint32_t;
typedef long long int int64_t;
typedef unsigned long long int uint64_t;
#endif

#if 1
#else
/* For an antique pre-C99 compiler you may also need to #define `inline' to an
 * empty comment. */
#define inline /* */
#endif

#include <stdio.h>
#include <stdlib.h>

/* gwyfile_read_wfile() and gwyfile_write_wfile() are defined only on MS
 * Windows.  Avoid including wchar.h elsewhere. */
#ifdef _WIN32
#include <wchar.h>
#endif

#ifndef DOXYGEN_SHOULD_SKIP_THIS
#ifdef __GNUC__
#define GWYFILE_NULL_TERMINATED __attribute__((sentinel))
#define GWYFILE_MALLOC __attribute__((malloc))
#define GWYFILE_PURE __attribute__((pure))
#else
#define GWYFILE_NULL_TERMINATED /* */
#define GWYFILE_MALLOC /* */
#define GWYFILE_PURE /* */
#endif
#endif

/*!\defgroup Files File reading and writing
 * @{
 */
/**@}*/

/*!\defgroup GwyfileObject Objects
 * @{
 */
/**@}*/

/*!\defgroup GwyfileItem Items
 * @{
 */
typedef enum {
    GWYFILE_ITEM_BOOL         = 'b',
    GWYFILE_ITEM_CHAR         = 'c',
    GWYFILE_ITEM_INT32        = 'i',
    GWYFILE_ITEM_INT64        = 'q',
    GWYFILE_ITEM_DOUBLE       = 'd',
    GWYFILE_ITEM_STRING       = 's',
    GWYFILE_ITEM_OBJECT       = 'o',
    GWYFILE_ITEM_CHAR_ARRAY   = 'C',
    GWYFILE_ITEM_INT32_ARRAY  = 'I',
    GWYFILE_ITEM_INT64_ARRAY  = 'Q',
    GWYFILE_ITEM_DOUBLE_ARRAY = 'D',
    GWYFILE_ITEM_STRING_ARRAY = 'S',
    GWYFILE_ITEM_OBJECT_ARRAY = 'O',
} GwyfileItemType;
/**@}*/

typedef struct _GwyfileItem GwyfileItem;
typedef struct _GwyfileObject GwyfileObject;

/*!\defgroup GwyfileError Errors
 * @{
 */
typedef enum {
    GWYFILE_ERROR_DOMAIN_SYSTEM   = 0,
    GWYFILE_ERROR_DOMAIN_DATA     = 1,
    GWYFILE_ERROR_DOMAIN_VALIDITY = 2,
    GWYFILE_ERROR_DOMAIN_WARNING  = 3,
} GwyfileErrorDomain;

typedef enum {
    GWYFILE_ERROR_MAGIC            = 0,
    GWYFILE_ERROR_ITEM_TYPE        = 1,
    GWYFILE_ERROR_CONFINEMENT      = 2,
    GWYFILE_ERROR_ARRAY_SIZE       = 3,
    GWYFILE_ERROR_DUPLICATE_NAME   = 4,
    GWYFILE_ERROR_LONG_STRING      = 5,
    GWYFILE_ERROR_OBJECT_SIZE      = 6,
    GWYFILE_ERROR_OBJECT_NAME      = 7,
    GWYFILE_ERROR_MISSING_ITEM     = 8,
    GWYFILE_ERROR_TOO_DEEP_NESTING = 9,
} GwyfileErrorCode;

typedef struct {
    GwyfileErrorDomain domain;
    int code;
    char *message;
} GwyfileError;

typedef struct {
    GwyfileError **errors;
    size_t n;
} GwyfileErrorList;

void gwyfile_error_clear     (GwyfileError **error);
void gwyfile_error_list_init (GwyfileErrorList *errlist);
void gwyfile_error_list_clear(GwyfileErrorList *errlist);
/**@}*/

/*!\defgroup GwyfileCheck Validity checking
 * @{
 */
typedef enum {
    GWYFILE_CHECK_FLAG_VALIDITY = (1 << GWYFILE_ERROR_DOMAIN_VALIDITY),
    GWYFILE_CHECK_FLAG_WARNING  = (1 << GWYFILE_ERROR_DOMAIN_WARNING),
} GwyfileCheckFlags;

typedef enum {
    GWYFILE_INVALID_UTF8_NAME   = 0,
    GWYFILE_INVALID_UTF8_TYPE   = 1,
    GWYFILE_INVALID_UTF8_STRING = 2,
    GWYFILE_INVALID_DOUBLE      = 3,
} GwyfileInvalidCode;

typedef enum {
    GWYFILE_WARNING_TYPE_IDENTIFIER = 0,
    GWYFILE_WARNING_EMPTY_NAME      = 1,
} GwyfileWarningCode;

bool gwyfile_check_object(const GwyfileObject *object,
                          unsigned int flags,
                          GwyfileErrorList *errlist);
/**@}*/

/*!\ingroup Files
 * @{
 */
bool           gwyfile_write_file(GwyfileObject *object,
                                  const char *filename,
                                  GwyfileError **error);
GwyfileObject* gwyfile_read_file (const char *filename,
                                  GwyfileError **error) GWYFILE_MALLOC;

bool           gwyfile_fwrite    (GwyfileObject *object,
                                  FILE *stream,
                                  GwyfileError **error);
GwyfileObject* gwyfile_fread     (FILE *stream,
                                  size_t max_size,
                                  GwyfileError **error) GWYFILE_MALLOC;

#ifdef _WIN32
bool           gwyfile_write_wfile(GwyfileObject *object,
                                   const wchar_t *filename,
                                   GwyfileError **error);
GwyfileObject* gwyfile_read_wfile (const wchar_t *filename,
                                   GwyfileError **error) GWYFILE_MALLOC;
#endif
/**@}*/

/*!\ingroup GwyfileObject
 * @{
 */
typedef void (*GwyfileObjectForeachFunc)(const GwyfileItem *item,
                                         void *user_data);

GwyfileObject* gwyfile_object_new           (const char *name,
                                             ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
GwyfileObject* gwyfile_object_newv          (const char *name,
                                             GwyfileItem **items,
                                             unsigned int nitems) GWYFILE_MALLOC;
void           gwyfile_object_free          (GwyfileObject *object);
const char*    gwyfile_object_name          (const GwyfileObject *object) GWYFILE_PURE;
size_t         gwyfile_object_size          (const GwyfileObject *object) GWYFILE_PURE;
bool           gwyfile_object_add           (GwyfileObject *object,
                                             GwyfileItem *item);
bool           gwyfile_object_remove        (GwyfileObject *object,
                                             const char *name);
GwyfileItem*   gwyfile_object_get           (const GwyfileObject *object,
                                             const char *name) GWYFILE_PURE;
GwyfileItem*   gwyfile_object_take          (GwyfileObject *object,
                                             const char *name);
GwyfileItem*   gwyfile_object_get_with_type (const GwyfileObject *object,
                                             const char *name,
                                             GwyfileItemType type) GWYFILE_PURE;
GwyfileItem*   gwyfile_object_take_with_type(GwyfileObject *object,
                                             const char *name,
                                             GwyfileItemType type);
void           gwyfile_object_foreach       (const GwyfileObject *object,
                                             GwyfileObjectForeachFunc function,
                                             void *user_data);
unsigned int   gwyfile_object_nitems        (const GwyfileObject *object) GWYFILE_PURE;
const char**   gwyfile_object_item_names    (const GwyfileObject *object) GWYFILE_MALLOC;
bool           gwyfile_object_fwrite        (GwyfileObject *object,
                                             FILE *stream,
                                             GwyfileError **error);
GwyfileObject* gwyfile_object_fread         (FILE *stream,
                                             size_t max_size,
                                             GwyfileError **error) GWYFILE_MALLOC;
/**@}*/

/*!\defgroup GwyObject Gwyddion-specific objects
 * @{
 */
GwyfileObject* gwyfile_object_new_datafield         (int xres,
                                                     int yres,
                                                     double xreal,
                                                     double yreal,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_datafield_get         (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_dataline          (int res,
                                                     double real,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_dataline_get          (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_brick             (int xres,
                                                     int yres,
                                                     int zres,
                                                     double xreal,
                                                     double yreal,
                                                     double zreal,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_brick_get             (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_surface           (int n,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_surface_get           (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_spectra           (int ncurves,
                                                     GwyfileObject **curves,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_spectra_get           (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_graphmodel        (int ncurves,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_graphmodel_get        (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_graphcurvemodel   (int ndata,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_graphcurvemodel_get   (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_selectionpoint    (int nsel,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_selectionpoint_get    (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_selectionline     (int nsel,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_selectionline_get     (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_selectionrectangle(int nsel,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_selectionrectangle_get(const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_selectionellipse  (int nsel,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_selectionellipse_get  (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_selectionlattice  (int nsel,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_selectionlattice_get  (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_selectionaxis     (int nsel,
                                                     int orientation,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_selectionaxis_get     (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_selectionpath     (int nsel,
                                                     double slackness,
                                                     bool closed,
                                                     ...) GWYFILE_NULL_TERMINATED GWYFILE_MALLOC;
bool           gwyfile_object_selectionpath_get     (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
GwyfileObject* gwyfile_object_new_siunit            (const char *unitstr) GWYFILE_MALLOC;
bool           gwyfile_object_siunit_get            (const GwyfileObject *object,
                                                     GwyfileError **error,
                                                     ...) GWYFILE_NULL_TERMINATED;
/**@}*/

/*!\defgroup GwyfileHighLevel High level data management
 * @{
 */
int* gwyfile_object_container_enumerate_channels(const GwyfileObject *object,
                                                 unsigned int *nchannels) GWYFILE_MALLOC;
int* gwyfile_object_container_enumerate_volume  (const GwyfileObject *object,
                                                 unsigned int *nvolume) GWYFILE_MALLOC;
int* gwyfile_object_container_enumerate_graphs  (const GwyfileObject *object,
                                                 unsigned int *ngraphs) GWYFILE_MALLOC;
int* gwyfile_object_container_enumerate_xyz     (const GwyfileObject *object,
                                                 unsigned int *nxyz) GWYFILE_MALLOC;
int* gwyfile_object_container_enumerate_spectra (const GwyfileObject *object,
                                                 unsigned int *nspectra) GWYFILE_MALLOC;
/**@}*/

/*!\defgroup GwyfileItem Items
 * @{
 */
void            gwyfile_item_free        (GwyfileItem *item);
GwyfileItemType gwyfile_item_type        (const GwyfileItem *item) GWYFILE_PURE;
const char*     gwyfile_item_name        (const GwyfileItem *item) GWYFILE_PURE;
uint32_t        gwyfile_item_array_length(const GwyfileItem *item) GWYFILE_PURE;
size_t          gwyfile_item_size        (const GwyfileItem *item) GWYFILE_PURE;
size_t          gwyfile_item_data_size   (const GwyfileItem *item) GWYFILE_PURE;
bool            gwyfile_item_fwrite      (const GwyfileItem *item,
                                          FILE *stream,
                                          GwyfileError **error);
GwyfileItem*    gwyfile_item_fread       (FILE *stream,
                                          size_t max_size,
                                          GwyfileError **error) GWYFILE_MALLOC;
bool            gwyfile_item_owns_data   (const GwyfileItem *item) GWYFILE_PURE;
/**@}*/

/*!\defgroup GwyfileItemBool Item – boolean
 * @{
 */
GwyfileItem* gwyfile_item_new_bool(const char *name,
                                   bool value) GWYFILE_MALLOC;
bool         gwyfile_item_get_bool(const GwyfileItem *item);
void         gwyfile_item_set_bool(GwyfileItem *item,
                                   bool value);
/**@}*/

/*!\defgroup GwyfileItemChar Item – character
 * @{
 */
GwyfileItem* gwyfile_item_new_char(const char *name,
                                   char value) GWYFILE_MALLOC;
char         gwyfile_item_get_char(const GwyfileItem *item) GWYFILE_PURE;
void         gwyfile_item_set_char(GwyfileItem *item,
                                   char value);
/**@}*/

/*!\defgroup GwyfileItemInt32 Item – 32bit integer
 * @{
 */
GwyfileItem* gwyfile_item_new_int32(const char *name,
                                    int32_t value) GWYFILE_MALLOC;
int32_t      gwyfile_item_get_int32(const GwyfileItem *item) GWYFILE_PURE;
void         gwyfile_item_set_int32(GwyfileItem *item,
                                    int32_t value);
/**@}*/

/*!\defgroup GwyfileItemInt64 Item – 64bit integer
 * @{
 */
GwyfileItem* gwyfile_item_new_int64(const char *name,
                                    int64_t value) GWYFILE_MALLOC;
int64_t      gwyfile_item_get_int64(const GwyfileItem *item) GWYFILE_PURE;
void         gwyfile_item_set_int64(GwyfileItem *item,
                                    int64_t value);
/**@}*/

/*!\defgroup GwyfileItemDouble Item – double
 * @{
 */
GwyfileItem* gwyfile_item_new_double(const char *name,
                                     double value) GWYFILE_MALLOC;
double       gwyfile_item_get_double(const GwyfileItem *item) GWYFILE_PURE;
void         gwyfile_item_set_double(GwyfileItem *item,
                                     double value);
/**@}*/

/*!\defgroup GwyfileItemString Item – string
 * @{
 */
GwyfileItem* gwyfile_item_new_string      (const char *name,
                                           char *value) GWYFILE_MALLOC;
GwyfileItem* gwyfile_item_new_string_copy (const char *name,
                                           const char *value) GWYFILE_MALLOC;
GwyfileItem* gwyfile_item_new_string_const(const char *name,
                                           const char *value) GWYFILE_MALLOC;
const char*  gwyfile_item_get_string      (const GwyfileItem *item) GWYFILE_PURE;
char*        gwyfile_item_take_string     (GwyfileItem *item);
void         gwyfile_item_set_string      (GwyfileItem *item,
                                           char *value);
void         gwyfile_item_set_string_copy (GwyfileItem *item,
                                           const char *value);
void         gwyfile_item_set_string_const(GwyfileItem *item,
                                           const char *value);
/**@}*/

/*!\defgroup GwyfileItemObject Item – object
 * @{
 */
GwyfileItem*   gwyfile_item_new_object    (const char *name,
                                           GwyfileObject *value) GWYFILE_MALLOC;
GwyfileObject* gwyfile_item_get_object    (const GwyfileItem *item) GWYFILE_PURE;
GwyfileObject* gwyfile_item_release_object(GwyfileItem *item);
void           gwyfile_item_set_object    (GwyfileItem *item,
                                           GwyfileObject *value);
/**@}*/

/*!\defgroup GwyfileItemCharArray Item – character array
 * @{
 */
GwyfileItem* gwyfile_item_new_char_array      (const char *name,
                                               char *value,
                                               uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem* gwyfile_item_new_char_array_copy (const char *name,
                                               const char *value,
                                               uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem* gwyfile_item_new_char_array_const(const char *name,
                                               const char *value,
                                               uint32_t array_length) GWYFILE_MALLOC;
const char*  gwyfile_item_get_char_array      (const GwyfileItem *item) GWYFILE_PURE;
char*        gwyfile_item_take_char_array     (GwyfileItem *item);
void         gwyfile_item_set_char_array      (GwyfileItem *item,
                                               char *value,
                                               uint32_t array_length);
void         gwyfile_item_set_char_array_copy (GwyfileItem *item,
                                               const char *value,
                                               uint32_t array_length);
void         gwyfile_item_set_char_array_const(GwyfileItem *item,
                                               const char *value,
                                               uint32_t array_length);
/**@}*/

/*!\defgroup GwyfileItemInt32Array Item – 32bit integer array
 * @{
 */
GwyfileItem*   gwyfile_item_new_int32_array      (const char *name,
                                                  int32_t *value,
                                                  uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem*   gwyfile_item_new_int32_array_copy (const char *name,
                                                  const int32_t *value,
                                                  uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem*   gwyfile_item_new_int32_array_const(const char *name,
                                                  const int32_t *value,
                                                  uint32_t array_length) GWYFILE_MALLOC;
const int32_t* gwyfile_item_get_int32_array      (const GwyfileItem *item) GWYFILE_PURE;
int32_t*       gwyfile_item_take_int32_array     (GwyfileItem *item);
void           gwyfile_item_set_int32_array      (GwyfileItem *item,
                                                  int32_t *value,
                                                  uint32_t array_length);
void           gwyfile_item_set_int32_array_copy (GwyfileItem *item,
                                                  const int32_t *value,
                                                  uint32_t array_length);
void           gwyfile_item_set_int32_array_const(GwyfileItem *item,
                                                  const int32_t *value,
                                                  uint32_t array_length);
/**@}*/

/*!\defgroup GwyfileItemInt64Array Item – 64bit integer array
 * @{
 */
GwyfileItem*   gwyfile_item_new_int64_array      (const char *name,
                                                  int64_t *value,
                                                  uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem*   gwyfile_item_new_int64_array_copy (const char *name,
                                                  const int64_t *value,
                                                  uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem*   gwyfile_item_new_int64_array_const(const char *name,
                                                  const int64_t *value,
                                                  uint32_t array_length) GWYFILE_MALLOC;
const int64_t* gwyfile_item_get_int64_array      (const GwyfileItem *item) GWYFILE_PURE;
int64_t*       gwyfile_item_take_int64_array     (GwyfileItem *item);
void           gwyfile_item_set_int64_array      (GwyfileItem *item,
                                                  int64_t *value,
                                                  uint32_t array_length);
void           gwyfile_item_set_int64_array_copy (GwyfileItem *item,
                                                  const int64_t *value,
                                                  uint32_t array_length);
void           gwyfile_item_set_int64_array_const(GwyfileItem *item,
                                                  const int64_t *value,
                                                  uint32_t array_length);
/**@}*/

/*!\defgroup GwyfileItemDoubleArray Item – double array
 * @{
 */
GwyfileItem*  gwyfile_item_new_double_array      (const char *name,
                                                  double *value,
                                                  uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem*  gwyfile_item_new_double_array_copy (const char *name,
                                                  const double *value,
                                                  uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem*  gwyfile_item_new_double_array_const(const char *name,
                                                  const double *value,
                                                  uint32_t array_length) GWYFILE_MALLOC;
const double* gwyfile_item_get_double_array      (const GwyfileItem *item) GWYFILE_PURE;
double*       gwyfile_item_take_double_array     (GwyfileItem *item);
void          gwyfile_item_set_double_array      (GwyfileItem *item,
                                                  double *value,
                                                  uint32_t array_length);
void          gwyfile_item_set_double_array_copy (GwyfileItem *item,
                                                  const double *value,
                                                  uint32_t array_length);
void          gwyfile_item_set_double_array_const(GwyfileItem *item,
                                                  const double *value,
                                                  uint32_t array_length);
/**@}*/

/*!\defgroup GwyfileItemStringArray Item – string array
 * @{
 */
GwyfileItem*       gwyfile_item_new_string_array      (const char *name,
                                                       char **value,
                                                       uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem*       gwyfile_item_new_string_array_copy (const char *name,
                                                       const char *const *value,
                                                       uint32_t array_length) GWYFILE_MALLOC;
GwyfileItem*       gwyfile_item_new_string_array_const(const char *name,
                                                       const char *const *value,
                                                       uint32_t array_length) GWYFILE_MALLOC;
const char* const* gwyfile_item_get_string_array      (const GwyfileItem *item) GWYFILE_PURE;
char**             gwyfile_item_take_string_array     (GwyfileItem *item);
void               gwyfile_item_set_string_array      (GwyfileItem *item,
                                                       char **value,
                                                       uint32_t array_length);
void               gwyfile_item_set_string_array_copy (GwyfileItem *item,
                                                       const char *const *value,
                                                       uint32_t array_length);
void               gwyfile_item_set_string_array_const(GwyfileItem *item,
                                                       const char *const *value,
                                                       uint32_t array_length);
/**@}*/

/*!\defgroup GwyfileItemObjectArray Item – object array
 * @{
 */
GwyfileItem*          gwyfile_item_new_object_array     (const char *name,
                                                         GwyfileObject **value,
                                                         uint32_t array_length) GWYFILE_MALLOC;
GwyfileObject* const* gwyfile_item_get_object_array     (const GwyfileItem *item) GWYFILE_PURE;
void                  gwyfile_item_set_object_array     (GwyfileItem *item,
                                                         GwyfileObject **value,
                                                         uint32_t array_length);
/**@}*/

#endif

/* vim: set cin et ts=4 sw=4 cino=>1s,e0,n0,f0,{0,}0,^0,\:1s,=0,g1s,h0,t0,+1s,c3,(0,u0 : */
