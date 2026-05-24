#ifndef Py_TOKENOBJECT_H
#define Py_TOKENOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PY_SSIZE_T_CLEAN
#include <Python.h>

typedef enum {
	TOKEN_EOF,
	TOKEN_IDENTIFIER,
	TOKEN_MODULE,
	TOKEN_COLON,
	TOKEN_LEFT_PAREN,
	TOKEN_RIGHT_PAREN,
	TOKEN_LEFT_ANGLE,
	TOKEN_RIGHT_ANGLE,
	TOKEN_HEX,
	TOKEN_ARROW,
	TOKEN_EMPTY_LINE,
	TOKEN_NUMBER,
	TOKEN_KEYWORD,
	TOKEN_ERROR,
	TOKEN_DOUBLECOLON,
	TOKEN_BACKTICK,
	TOKEN_APOSTROPHE,
	TOKEN_DOT,
	TOKEN_COMMA,
	TOKEN_AMPERSAND,
	TOKEN_ASTERISK,
	TOKEN_HYPHEN,
	TOKEN_UNDERSCORE
} TokenType;

#define CLEX_STRINGIFY(token_type) #token_type

typedef struct {
	PyObject_HEAD
	PyObject* literal;
	enum TokenType type;
	int line;
} PyTokenObject;

PyAPI_DATA(PyTypeObject) PyToken_Type;

PyAPI_FUNC(int) PyToken_Init(PyTokenObject* self, enum TokenType type, const char* literal, size_t size, int line);

#ifdef __cplusplus
}
#endif
#endif /* !defined(Py_TOKENOBJECT_H) */
