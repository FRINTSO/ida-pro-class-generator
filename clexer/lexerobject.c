#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>
#include <stdbool.h>

#include "lexerobject.h"

#include "tokenobject.h"

/* lexer methods */

static void
lexer_dealloc(PyLexerObject* self)
{
    Py_XDECREF(self->text);
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static int
lexer_init(PyLexerObject* self, PyObject* args)
{
    PyObject* text = NULL, * tmp;

    if (!PyArg_ParseTuple(args, "U", &text))
        return -1;
    
    if (text) {
        tmp = self->text;
        Py_INCREF(text);
        self->text = text;
        Py_XDECREF(tmp);

        const char* source = PyUnicode_AsUTF8(text);
        self->start = source;
        self->current = source;
    }
    self->line = 1;
    
    return 0;
}

static PyMemberDef lexer_members[] = {
    {"text",
        T_OBJECT_EX,
        offsetof(PyLexerObject, text),
        0, "internal text"},
    {"start",
        T_STRING,
        offsetof(PyLexerObject, start),
        0, "start of current token"},
    {"current",
        T_STRING,
        offsetof(PyLexerObject, current),
        0, "current char"},
    {"line",
        T_INT, offsetof(PyLexerObject, line),
        0, "line number"},
    {NULL}
};

static inline bool
lexer_isalpha_impl(char c)
{
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

static PyObject*
lexer_isalpha(PyLexerObject* Py_UNUSED(self), PyObject* args)
{
    char c;
    if (!PyArg_ParseTuple(args, "C", &c))
        return NULL;

    return PyBool_FromLong(lexer_isalpha_impl(c));
}

static inline bool
lexer_isdigit_impl(char c)
{
    return c >= '0' && c <= '9';
}

static PyObject*
lexer_isdigit(PyLexerObject* self, PyObject* args)
{
    char c;
    if (!PyArg_ParseTuple(args, "C", &c))
        return NULL;

    return PyBool_FromLong(lexer_isdigit_impl(c));
}

static inline bool
lexer_isalnum_impl(char c)
{
    return lexer_isalpha_impl(c) || lexer_isdigit_impl(c);
}

static PyObject*
lexer_isalnum(PyLexerObject* self, PyObject* args)
{
    char c;
    if (!PyArg_ParseTuple(args, "C", &c))
        return NULL;

    return PyBool_FromLong(lexer_isalnum_impl(c));
}

static inline bool
lexer_ishex_impl(char c)
{
    return lexer_isdigit_impl(c) || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
}

static PyObject*
lexer_ishex(PyLexerObject* self, PyObject* args)
{
    char c;
    if (!PyArg_ParseTuple(args, "C", &c))
        return NULL;

    return PyBool_FromLong(lexer_ishex_impl(c));
}

static inline bool
lexer_is_at_end_impl(PyLexerObject* self) {
    return *self->current == '\0';
}

static PyObject*
lexer_is_at_end(PyLexerObject* self, PyObject* Py_UNUSED(args))
{
    return PyBool_FromLong(*self->current == '\0');
}

static inline char
lexer_advance_impl(PyLexerObject* self) {
    return *self->current++;
}

static PyObject*
lexer_advance(PyLexerObject* self, PyObject* Py_UNUSED(args))
{
    return Py_BuildValue("C", *self->current++);
}

static inline char
lexer_peek_impl(PyLexerObject* self)
{
    return *self->current;
}

static PyObject*
lexer_peek(PyLexerObject* self, PyObject* Py_UNUSED(args))
{
    PyObject* unicode = PyUnicode_FromOrdinal(*self->current);
    return unicode;
}

static inline char
lexer_peek_next_impl(PyLexerObject* self)
{
    if (lexer_is_at_end_impl(self)) return '\0';
    return self->current[1];
}

static PyObject*
lexer_peek_next(PyLexerObject* self, PyObject* args)
{
    if (lexer_is_at_end(self, args)) return PyUnicode_FromOrdinal('\0');
    return PyUnicode_FromOrdinal(self->current[1]);
}

static inline bool
lexer_match_impl(PyLexerObject* self, char expected)
{
    if (lexer_is_at_end_impl(self)) return false;
    if (*self->current != expected) return false;
    self->current++;
    return true;
}

static PyObject*
lexer_match(PyLexerObject* self, PyObject* args)
{
    char expected;
    if (!PyArg_ParseTuple(args, "C", &expected))
        return NULL;

    if (lexer_is_at_end(self, args)) Py_RETURN_FALSE;
    if (*self->current != expected) Py_RETURN_FALSE;
    self->current++;
    Py_RETURN_TRUE;
}

static inline PyObject*
lexer_make_token_impl(PyLexerObject* self, enum TokenType type)
{
    PyTokenObject* token = (PyTokenObject*)PyType_GenericNew(&PyToken_Type, NULL, NULL);

    if (token == NULL) {
        return NULL;
    }

    size_t size = (size_t)(self->current - self->start);

    if (PyToken_Init(token, type, self->start, size, self->line) < 0) {
        Py_DECREF(token);
        return NULL;
    }

    return (PyObject*)token;
}

static PyObject*
lexer_make_token(PyLexerObject* self, PyObject* args)
{
    PyTokenObject* token;
    PyObject* argList;
    PyObject* literal;
    int type;
    
    if (!PyArg_ParseTuple(args, "i", &type))
        return NULL;

    literal = PyUnicode_FromKindAndData(1, self->start, (Py_ssize_t)(self->current - self->start));
    if (literal == NULL)
        return NULL;

    argList = Py_BuildValue("iOi", self->line, literal, type);
    Py_DECREF(literal);
    if (argList == NULL)
        return NULL;

    token = (PyTokenObject*)PyObject_CallObject((PyObject*)&PyToken_Type, argList);
    Py_DECREF(argList);
    if (token == NULL)
        return NULL;

    self->start = self->current;

    return (PyObject*)token;
}

static inline void
lexer_skip_whitespace_impl(PyLexerObject* self)
{
    for (;;) {
        char c = lexer_peek_impl(self);
        switch (c) {
        case ' ':
        case '\r':
        case '\t':
            lexer_advance_impl(self);
            break;
        case '\n':
            self->line++;
            lexer_advance_impl(self);
            break;
        default:
            return;
        }
    }
}

static PyObject*
lexer_skip_whitespace(PyLexerObject* self, PyObject* Py_UNUSED(args))
{
    lexer_skip_whitespace_impl(self);
    Py_RETURN_NONE;
}

static inline PyObject*
lexer_number_impl(PyLexerObject* self)
{
    while (lexer_isdigit_impl(lexer_peek_impl(self))) lexer_advance_impl(self);

    return lexer_make_token_impl(self, TOKEN_NUMBER);
}

static PyObject*
lexer_number(PyLexerObject* self, PyObject* Py_UNUSED(args))
{
    return lexer_number_impl(self);
}

static inline PyObject*
lexer_hexadecimal_impl(PyLexerObject* self)
{
    while (lexer_ishex_impl(lexer_peek_impl(self))) lexer_advance_impl(self);

    return lexer_make_token_impl(self, TOKEN_HEX);
}

static PyObject*
lexer_hexadecimal(PyLexerObject* self, PyObject* Py_UNUSED(args))
{
    return lexer_hexadecimal_impl(self);
}

static inline PyObject*
lexer_identifier_impl(PyLexerObject* self)
{
    while (lexer_isalnum_impl(lexer_peek_impl(self)) || lexer_peek_impl(self) == '_') lexer_advance_impl(self);
    return lexer_make_token_impl(self, TOKEN_IDENTIFIER);
}

static PyObject*
lexer_identifier(PyLexerObject* self, PyObject* Py_UNUSED(args))
{
    return lexer_identifier_impl(self);
}

static inline PyObject*
lexer_scan_token_impl(PyLexerObject* self)
{
    lexer_skip_whitespace_impl(self);

    self->start = self->current;

    if (lexer_is_at_end_impl(self)) return lexer_make_token_impl(self, TOKEN_EOF);

    char c = lexer_advance_impl(self);

    if (lexer_isdigit_impl(c)) {
        return lexer_match_impl(self, 'x')
            ? lexer_hexadecimal_impl(self)
            : lexer_number_impl(self);
    }

    if (lexer_isalpha_impl(c) || c == '_') {
        return lexer_identifier_impl(self);
    }

    switch (c)
    {
    case '(': return lexer_make_token_impl(self, TOKEN_LEFT_PAREN);
    case ')': return lexer_make_token_impl(self, TOKEN_RIGHT_PAREN);
    case '<': return lexer_make_token_impl(self, TOKEN_LEFT_ANGLE);
    case '>': return lexer_make_token_impl(self, TOKEN_RIGHT_ANGLE);
    case ':': return lexer_make_token_impl(self, lexer_match_impl(self, ':') ? TOKEN_DOUBLECOLON : TOKEN_COLON);
    case '`': return lexer_make_token_impl(self, TOKEN_BACKTICK);
    case '\'': return lexer_make_token_impl(self, TOKEN_APOSTROPHE);
    case '.': return lexer_make_token_impl(self, TOKEN_DOT);
    case ',': return lexer_make_token_impl(self, TOKEN_COMMA);
    case '&': return lexer_make_token_impl(self, TOKEN_AMPERSAND);
    case '*': return lexer_make_token_impl(self, TOKEN_ASTERISK);
    case '_': return lexer_make_token_impl(self, TOKEN_UNDERSCORE);
    case '-': return lexer_make_token_impl(self, lexer_match_impl(self, '>') ? TOKEN_ARROW :  TOKEN_HYPHEN);
    }

    return lexer_make_token_impl(self, TOKEN_ERROR);
}

static PyObject*
lexer_scan_token(PyLexerObject* self, PyObject* Py_UNUSED(args))
{
    return lexer_scan_token_impl(self);
}

static PyMethodDef lexer_methods[] = {
    {"isalpha",
        (PyCFunction)lexer_isalpha,
        METH_VARARGS | METH_STATIC, NULL},
    {"isdigit",
        (PyCFunction)lexer_isdigit,
        METH_VARARGS | METH_STATIC, NULL},
    {"isalnum",
        (PyCFunction)lexer_isalnum,
        METH_VARARGS | METH_STATIC, NULL},
    {"skip_whitespace",
        (PyCFunction)lexer_skip_whitespace,
        METH_NOARGS, NULL},
    {"is_at_end",
        (PyCFunction)lexer_is_at_end,
        METH_NOARGS, NULL},
    {"advance",
        (PyCFunction)lexer_advance,
        METH_NOARGS, NULL},
    {"peek",
        (PyCFunction)lexer_peek,
        METH_NOARGS, NULL},
    {"peek_next",
        (PyCFunction)lexer_peek_next,
        METH_NOARGS, NULL},
    {"match",
        (PyCFunction)lexer_match,
        METH_VARARGS, NULL},
    {"make_token",
        (PyCFunction)lexer_make_token,
        METH_VARARGS, NULL},
    {"scan_token",
        (PyCFunction)lexer_scan_token,
        METH_VARARGS, NULL},
    {NULL}
};

PyTypeObject PyLexer_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "clex.Lexer",
    .tp_basicsize = sizeof(PyLexerObject),
    .tp_itemsize = 0,
    /* methods */
    .tp_dealloc = (destructor)lexer_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,

    .tp_methods = lexer_methods,
    .tp_members = lexer_members,
    .tp_init = (initproc)lexer_init,
    .tp_new = PyType_GenericNew,
};
