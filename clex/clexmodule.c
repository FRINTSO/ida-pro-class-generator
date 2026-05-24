#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "tokenobject.h"
#include "lexerobject.h"

static struct PyModuleDef moduledef = {
	.m_base = PyModuleDef_HEAD_INIT,
	.m_name = "clex",
	.m_size = -1,
};

/* Initialization function for the module */
PyMODINIT_FUNC PyInit_clex(void) {
	PyObject *m, *d, *s;

	/* Create the module and add the functions */
	m = PyModule_Create(&moduledef);
	if (!m) {
		return NULL;
	}

	/* Add some symbolic constants to the module */
	d = PyModule_GetDict(m);
	if (!d) {
		goto err;
	}

	if (PyType_Ready(&PyToken_Type) < 0)
		goto err;

	if (PyType_Ready(&PyLexer_Type) < 0)
		goto err;

#define ADDTOKEN(NAME) \
	s = PyLong_FromLong(NAME); \
	PyDict_SetItemString(d, #NAME, s); \
	Py_DECREF(s)


	ADDTOKEN(TOKEN_EOF);
	ADDTOKEN(TOKEN_IDENTIFIER);
	ADDTOKEN(TOKEN_MODULE);
	ADDTOKEN(TOKEN_COLON);
	ADDTOKEN(TOKEN_LEFT_PAREN);
	ADDTOKEN(TOKEN_RIGHT_PAREN);
	ADDTOKEN(TOKEN_LEFT_ANGLE);
	ADDTOKEN(TOKEN_RIGHT_ANGLE);
	ADDTOKEN(TOKEN_HEX);
	ADDTOKEN(TOKEN_ARROW);
	ADDTOKEN(TOKEN_EMPTY_LINE);
	ADDTOKEN(TOKEN_NUMBER);
	ADDTOKEN(TOKEN_KEYWORD);
	ADDTOKEN(TOKEN_ERROR);
	ADDTOKEN(TOKEN_DOUBLECOLON);
	ADDTOKEN(TOKEN_BACKTICK);
	ADDTOKEN(TOKEN_APOSTROPHE);
	ADDTOKEN(TOKEN_DOT);
	ADDTOKEN(TOKEN_COMMA);
	ADDTOKEN(TOKEN_AMPERSAND);
	ADDTOKEN(TOKEN_ASTERISK);
	ADDTOKEN(TOKEN_HYPHEN);
	ADDTOKEN(TOKEN_UNDERSCORE);
#undef ADDTOKEN

	Py_INCREF(&PyToken_Type);
	if (PyModule_AddObject(m, "Token", (PyObject*)&PyToken_Type) < 0) {
		Py_DECREF(&PyToken_Type);
		goto err;
	}

	// PyDict_SetItemString(d, "Token", (PyObject*)&PyToken_Type);
	PyDict_SetItemString(d, "Lexer", (PyObject*)&PyLexer_Type);

	return m;

err:
	if (!PyErr_Occurred()) {
		PyErr_SetString(PyExc_RuntimeError,
			"cannot load clex module.");
	}
	Py_DECREF(m);
	return NULL;
}

int
main(int argc, char* argv[])
{
	wchar_t* program = Py_DecodeLocale(argv[0], NULL);
	if (program == NULL) {
		fprintf(stderr, "Fatal error: cannot decode argv[0]\n");
		exit(1);
	}

	/* Add a built-in module, before Py_Initialize */
	if (PyImport_AppendInittab("clex", PyInit_clex) == -1) {
		fprintf(stderr, "Error: could not extend in-built modules table\n");
		exit(1);
	}

	/* Pass argv[0] to the Python interpreter */
	Py_SetProgramName(program);

	/* Initialize the Python interpreter.  Required.
	   If this step fails, it will be a fatal error. */
	Py_Initialize();

	/* Optionally import the module; alternatively,
	   import can be deferred until the embedded script
	   imports it. */
	PyObject* pmodule = PyImport_ImportModule("clex");
	if (!pmodule) {
		PyErr_Print();
		fprintf(stderr, "Error: could not import module 'clex'\n");
	}

	PyMem_RawFree(program);
	return 0;
}
