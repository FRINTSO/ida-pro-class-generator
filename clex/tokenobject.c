#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>

#include "tokenobject.h"

static int
token_clear(PyTokenObject* self) {
	Py_CLEAR(self->literal);
	return 0;
}

static void
token_dealloc(PyTokenObject* self) {
	PyObject_GC_UnTrack(self);
	token_clear(self);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

#define CLEX_LABELIZE(token_type) case token_type: \
	type_str = #token_type; \
	break

static PyObject*
token_str(PyTokenObject* self) {
	const char* type_str;
	switch (self->type)
	{
		CLEX_LABELIZE(TOKEN_EOF);
		CLEX_LABELIZE(TOKEN_IDENTIFIER);
		CLEX_LABELIZE(TOKEN_MODULE);
		CLEX_LABELIZE(TOKEN_COLON);
		CLEX_LABELIZE(TOKEN_LEFT_ANGLE);
		CLEX_LABELIZE(TOKEN_RIGHT_ANGLE);
		CLEX_LABELIZE(TOKEN_HEX);
		CLEX_LABELIZE(TOKEN_ARROW);
		CLEX_LABELIZE(TOKEN_EMPTY_LINE);
		CLEX_LABELIZE(TOKEN_NUMBER);
		CLEX_LABELIZE(TOKEN_KEYWORD);
		CLEX_LABELIZE(TOKEN_ERROR);
		CLEX_LABELIZE(TOKEN_DOUBLECOLON);
		CLEX_LABELIZE(TOKEN_BACKTICK);
		CLEX_LABELIZE(TOKEN_APOSTROPHE);
		CLEX_LABELIZE(TOKEN_DOT);
		CLEX_LABELIZE(TOKEN_COMMA);
		CLEX_LABELIZE(TOKEN_AMPERSAND);
		CLEX_LABELIZE(TOKEN_ASTERISK);
		CLEX_LABELIZE(TOKEN_HYPHEN);
		CLEX_LABELIZE(TOKEN_UNDERSCORE);

	default:
		type_str = "UNKNOWN TOKEN";
		break;
	}
	return PyUnicode_FromFormat("Token(%s, %S, %i)", type_str, self->literal, self->line);
}

#undef CLEX_LABELIZE

static int
token_traverse(PyTokenObject* self, visitproc visit, void* arg) {
	Py_VISIT(self->literal);
	return 0;
}

static PyMemberDef token_members[] = {
	{"type", T_INT, offsetof(PyTokenObject, type), 0, "token type"},
	{"line", T_INT, offsetof(PyTokenObject, line), 0, "line number"},
	{NULL}
};

static PyObject*
token_getliteral(PyTokenObject* self, void* closure) {
	Py_INCREF(self->literal);
	return self->literal;
}

static int
token_setliteral(PyTokenObject* self, PyObject* value, void* closure) {
	PyObject* tmp;
	if (value == NULL) {
		PyErr_SetString(PyExc_TypeError, "Cannot delete the literal attribute");
		return -1;
	}
	if (!PyUnicode_Check(value)) {
		PyErr_SetString(PyExc_TypeError, "The literal attribute value must be a string");
		return -1;
	}
	tmp = self->literal;
	Py_INCREF(value);
	self->literal = value;
	Py_DECREF(tmp);
	return 0;
}

static PyGetSetDef token_getsetters[] = {
	{"literal", (getter)token_getliteral, (setter)token_setliteral, "string literal", NULL},
	{NULL}
};

int
PyToken_Init(PyTokenObject* self, TokenType type, const char* literal, size_t size, int line)
{
	PyObject* unicode = NULL, *tmp;

	unicode = PyUnicode_New(size, 1); // assume ascii
	if (unicode == NULL)
		return -1;
	
	memcpy(PyUnicode_DATA(unicode), literal, size);

	tmp = self->literal;
	self->literal = unicode;
	Py_XDECREF(tmp);
	self->type = type;
	self->line = line;
	return 0;
}

static int
token_init(PyTokenObject* self, PyObject* args) {
	PyObject* literal = NULL, * tmp;

	if (!PyArg_ParseTuple(args, "iUi", &self->type, &literal, &self->line))
		return -1;
	
	if (literal) {
		tmp = self->literal;
		Py_INCREF(literal);
		self->literal = literal;
		Py_XDECREF(tmp);
	}
	return 0;
}

PyTypeObject PyToken_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_name = "clex.Token",
	.tp_basicsize = sizeof(PyTokenObject),
	.tp_itemsize = 0,
	/* methods */
	.tp_dealloc = (destructor)token_dealloc,
	.tp_repr = (reprfunc)token_str,
	.tp_str = (reprfunc)token_str,
	.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,

	.tp_traverse = (traverseproc)token_traverse,
	.tp_clear = (inquiry)token_clear,
	.tp_members = token_members,
	.tp_getset = token_getsetters,
	.tp_init = (initproc)token_init,
	.tp_new = PyType_GenericNew,
};
