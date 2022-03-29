from statement import LinkedModuleBlock, ModuleBlock, Class, VTable


def link_modules(
        class_modules: list[ModuleBlock[Class]],
        vtable_modules: list[ModuleBlock[VTable]]
) -> list[LinkedModuleBlock]:
    linked_modules: list[LinkedModuleBlock] = []
    for class_module, vtable_module in zip(class_modules, vtable_modules):
        if class_module.module != vtable_module.module: raise Exception("Different modules tried to be linked.")
        classes: list[Class] = class_module.statements
        vtables: list[VTable] = vtable_module.statements
        linked_modules.append(LinkedModuleBlock(class_module.module, classes, vtables))

    return linked_modules
