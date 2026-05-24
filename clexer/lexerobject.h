#ifndef Py_LEXEROBJECT_H
#define Py_LEXEROBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PY_SSIZE_T_CLEAN
#include <Python.h>

typedef struct {
	PyObject_HEAD
	PyObject* text;
	const char* start;
	const char* current;
	int line;
} PyLexerObject;

PyAPI_DATA(PyTypeObject) PyLexer_Type;

#ifdef __cplusplus
}
#endif
#endif /* !defined(Py_LEXEROBJECT_H) */
