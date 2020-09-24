# Common modeling pipeline elements


def update_source(model):
    """Update source

       Let the code of the underlying source language be updated to reflect
       changes in the model object.
    """
    model.update_source()
    return model


def fix_parameters(model, parameter_names):
    """Fix parameters

       Fix all listed parameters
    """
    d = {name: True for name in parameter_names}
    model.parameters.fix = d
    return model


def unfix_parameters(model, parameter_names):
    """Unfix parameters

       Unfix all listed parameters
    """
    d = {name: False for name in parameter_names}
    model.parameters.fix = d
    return model
