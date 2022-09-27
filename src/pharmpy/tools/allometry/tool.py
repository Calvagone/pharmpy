from functools import partial
from typing import Optional

from pharmpy.deps import sympy
from pharmpy.expressions import sympify
from pharmpy.model import Model, Results
from pharmpy.modeling import (
    add_allometry,
    get_pk_parameters,
    summarize_errors,
    summarize_individuals,
    summarize_individuals_count_table,
    summarize_modelfit_results,
)
from pharmpy.tools.modelfit import create_fit_workflow
from pharmpy.utils import same_signature_as
from pharmpy.workflows import Task, Workflow


def create_workflow(
    model: Optional[Model] = None,
    allometric_variable='WT',
    reference_value=70,
    parameters=None,
    initials=None,
    lower_bounds=None,
    upper_bounds=None,
    fixed=True,
):
    """Run allometry tool. For more details, see :ref:`allometry`.

    Parameters
    ----------
    model : Model
        Pharmpy model
    allometric_variable : str
        Name of the variable to use for allometric scaling (default is WT)
    reference_value : float
        Reference value for the allometric variable (default is 70)
    parameters : list
        Parameters to apply scaling to (default is all CL, Q and V parameters)
    initials : list
        Initial estimates for the exponents. (default is to use 0.75 for CL and Qs and 1 for Vs)
    lower_bounds : list
        Lower bounds for the exponents. (default is 0 for all parameters)
    upper_bounds : list
        Upper bounds for the exponents. (default is 2 for all parameters)
    fixed : bool
        Should the exponents be fixed or not. (default True)

    Returns
    -------
    AllometryResults
        Allometry tool result object

    Examples
    --------
    >>> from pharmpy.modeling import *
    >>> model = load_example_model("pheno")
    >>> from pharmpy.tools import run_allometry # doctest: +SKIP
    >>> run_allometry(model=model, allometric_variable='WGT')      # doctest: +SKIP

    """

    wf = Workflow()
    wf.name = "allometry"
    if model is not None:
        start_task = Task('start_allometry', start, model)
    else:
        start_task = Task('start_allometry', start)
    _add_allometry = partial(
        _add_allometry_on_model,
        allometric_variable=allometric_variable,
        reference_value=reference_value,
        parameters=parameters,
        initials=initials,
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
        fixed=fixed,
    )
    task_add_allometry = Task('add allometry', _add_allometry)
    wf.add_task(task_add_allometry, predecessors=start_task)
    fit_wf = create_fit_workflow(n=1)
    wf.insert_workflow(fit_wf, predecessors=task_add_allometry)
    results_task = Task('results', results)
    wf.add_task(results_task, predecessors=[start_task] + fit_wf.output_tasks)
    return wf


def start(model):
    return model


def _add_allometry_on_model(
    input_model,
    allometric_variable,
    reference_value,
    parameters,
    initials,
    lower_bounds,
    upper_bounds,
    fixed,
):
    model = input_model.copy()
    add_allometry(
        model,
        allometric_variable=allometric_variable,
        reference_value=reference_value,
        parameters=parameters,
        initials=initials,
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
        fixed=fixed,
    )

    model.name = "scaled_model"
    model.description = "Allometry model"
    return model


@same_signature_as(create_workflow)
def validate_input(
    model,
    allometric_variable,
    reference_value,
    parameters,
    initials,
    lower_bounds,
    upper_bounds,
    fixed,
):
    if not isinstance(allometric_variable, (str, sympy.Expr)):
        raise TypeError(
            f'Invalid allometric_variable: got "{allometric_variable}"'
            f' of type {type(allometric_variable)}, must be a str/sympy.Expr.'
        )

    if not isinstance(reference_value, (str, int, float, sympy.Expr)):
        raise TypeError(
            f'Invalid reference_value: got "{reference_value}"'
            f' of type {type(reference_value)}, must be a str/int/float/sympy.Expr.'
        )

    if not isinstance(parameters, (type(None), list)):
        raise TypeError(
            f'Invalid parameters: got "{parameters}" of type {type(parameters)}, must be None/NULL or a list.'
        )

    if not isinstance(initials, (type(None), list)):
        raise TypeError(
            f'Invalid initials: got "{initials}" of type {type(initials)}, must be None/NULL or a list.'
        )
    if not isinstance(lower_bounds, (type(None), list)):
        raise TypeError(
            f'Invalid lower_bounds: got "{lower_bounds}" of type {type(lower_bounds)}, must be None/NULL or a list.'
        )
    if not isinstance(upper_bounds, (type(None), list)):
        raise TypeError(
            f'Invalid upper_bounds: got "{upper_bounds}" of type {type(upper_bounds)}, must be None/NULL or a list.'
        )

    if not isinstance(fixed, bool):
        raise TypeError(f'Invalid fixed: got "{fixed}" of type {type(fixed)}, must be a bool.')

    if model is not None:
        if not isinstance(model, Model):
            raise TypeError(
                f'Invalid model: got "{model}" of type {type(model)}, must be a {Model}.'
            )

        if not set(map(str, sympify(allometric_variable).free_symbols)).issubset(
            model.datainfo.names
        ):
            raise ValueError(
                f'Invalid allometric_variable: got "{allometric_variable}",'
                f' free symbols must be a subset of {sorted(model.datainfo.names)}.'
            )

        if parameters is not None:
            allowed_parameters = set(get_pk_parameters(model)).union(
                str(statement.symbol) for statement in model.statements.before_odes
            )
            if not set(parameters).issubset(allowed_parameters):
                raise ValueError(
                    f'Invalid parameters: got "{parameters}",'
                    f' must be NULL/None or a subset of {sorted(allowed_parameters)}.'
                )


def results(start_model, allometry_model):

    allometry_model_failed = allometry_model.modelfit_results is None
    best_model = start_model if allometry_model_failed else allometry_model

    summods = summarize_modelfit_results([start_model, allometry_model])
    suminds = summarize_individuals([start_model, allometry_model])
    sumcount = summarize_individuals_count_table(df=suminds)
    sumerrs = summarize_errors([start_model, allometry_model])

    res = AllometryResults(
        summary_models=summods,
        summary_individuals=suminds,
        summary_individuals_count=sumcount,
        summary_errors=sumerrs,
        final_model_name=best_model.name,
    )

    return res


class AllometryResults(Results):
    def __init__(
        self,
        summary_models=None,
        summary_individuals=None,
        summary_individuals_count=None,
        summary_errors=None,
        final_model_name=None,
        tool_database=None,
    ):
        self.summary_models = summary_models
        self.summary_individuals = summary_individuals
        self.summary_individuals_count = summary_individuals_count
        self.summary_errors = summary_errors
        self.final_model_name = final_model_name
        self.tool_database = tool_database
