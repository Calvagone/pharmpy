"""
This module contain functions for checking the format of an nlmixr model conversion 
in order to inform the users of any errors or mistakes that can could be made.

It serves purpose in catching known errors that are not yet solved, or limitations 
that are found in the conversion software
"""

import pharmpy.model
import warnings
from pharmpy.deps import sympy
from pharmpy.modeling import (
    has_additive_error_model,
    has_proportional_error_model,
    has_combined_error_model,
    remove_iiv,
)


def check_model(model: pharmpy.model) -> pharmpy.model:
    """
    Perform all neccessary checks to see if there are any issues with the input
    model. Such as if the error model is unknown, or if there are other limitations
    in the handling of the model.

    Parameters
    ----------
    model : pharmpy.model
        pharmpy model object

    Returns
    -------
    pharmpy.model
        Issues will be printed to the terminal and model is returned.

    """
    # Checks for the dataset
    if model.dataset is not None or len(model.dataset) != 0:
        if "TIME" in model.dataset.columns:
            if same_time(model):
                print_warning(
                    "Observation and bolus dose at the same time in the data. Modified for nlmixr model"
                )
                model = change_same_time(model)

    # Checks regarding error model
    if not known_error_model(model):
        print_warning(
            "Format of error model cannot be determined. Will try to translate either way"
        )

    # Checks regarding random variables
    if rvs_same(model, sigma=True):
        print_warning("Sigma with value same not supported. Updated as follows.")
        model = change_rvs_same(model, sigma=True)
    if rvs_same(model, omega=True):
        print_warning("Omega with value same not supported. Updated as follows.")
        model = change_rvs_same(model, omega=True)

    return model


def known_error_model(model: pharmpy.model.Model) -> bool:
    """
    Check if the associated error model is known to pharmpy. Currently check if
    model hase
    - additive error model
    - proportional error model
    - combined error model

    Parameters
    ----------
    model : pharmpy.model.Model
        pharmpy model object

    Returns
    -------
    bool
        True if error model is defined. False if unknown.

    """
    return (
        has_additive_error_model(model)
        or has_combined_error_model(model)
        or has_proportional_error_model(model)
    )


def same_time(model: pharmpy.model) -> bool:
    temp_model = model
    temp_model = temp_model.replace(dataset=temp_model.dataset.reset_index())
    dataset = temp_model.dataset

    if "RATE" in dataset.columns:
        rate = True
    else:
        rate = False

    evid_ignore = [0, 3, 4]

    for index, row in dataset.iterrows():
        if index != 0:
            if row["ID"] == dataset.loc[index - 1]["ID"]:
                if row["TIME"] == dataset.loc[index - 1]["TIME"]:
                    ID = row["ID"]
                    TIME = row["TIME"]
                    subset = dataset[(dataset["ID"] == ID) & (dataset["TIME"] == TIME)]
                    if any([x not in evid_ignore for x in subset["EVID"].unique()]) and any(
                        [x in evid_ignore for x in subset["EVID"].unique()]
                    ):
                        if rate:
                            if any([x != 0 for x in subset["RATE"].unique()]) and any(
                                [x == 0 for x in subset["RATE"].unique()]
                            ):
                                return True
                        else:
                            return True

    return False


def change_same_time(model: pharmpy.model) -> pharmpy.model:
    """
    Force dosing to happen after observation, if bolus dose is given at the
    exact same time.

    Parameters
    ----------
    model : pharmpy.model
        A pharmpy.model object

    Returns
    -------
    model : TYPE
        The same model with a changed dataset.

    """
    dataset = model.dataset.copy()
    dataset = dataset.reset_index()
    time = dataset["TIME"]

    if "RATE" in dataset.columns:
        rate = True
    else:
        rate = False

    evid_ignore = [0, 3, 4]

    for index, row in dataset.iterrows():
        if index != 0:
            if row["ID"] == dataset.loc[index - 1]["ID"]:
                if row["TIME"] == dataset.loc[index - 1]["TIME"]:
                    ID = row["ID"]
                    TIME = row["TIME"]
                    subset = dataset[(dataset["ID"] == ID) & (dataset["TIME"] == TIME)]
                    if any([x not in evid_ignore for x in subset["EVID"].unique()]) and any(
                        [x in evid_ignore for x in subset["EVID"].unique()]
                    ):
                        if rate:
                            if any([x != 0 for x in subset["RATE"].unique()]) and any(
                                [x == 0 for x in subset["RATE"].unique()]
                            ):
                                dataset.loc[
                                    (dataset["ID"] == ID)
                                    & (dataset["TIME"] == TIME)
                                    & (dataset["RATE"] == 0)
                                    & (~dataset["EVID"].isin(evid_ignore)),
                                    "TIME",
                                ] += 0.000001
                        else:
                            return True

    with warnings.catch_warnings():
        # Supress a numpy deprecation warning
        warnings.simplefilter("ignore")
        for index, row in dataset.iterrows():
            if index != 0:
                if row["ID"] == dataset.loc[index - 1]["ID"]:
                    if row["TIME"] == dataset.loc[index - 1]["TIME"]:
                        temp = index - 1
                        while dataset.loc[temp]["TIME"] == row["TIME"]:
                            if dataset.loc[temp]["EVID"] not in [0, 3]:
                                if rate:
                                    if dataset.loc[temp]["RATE"] == 0:
                                        time[temp] = time[temp] + 10**-6
                                else:
                                    time[temp] = time[temp] + 10**-6
                            temp += 1
    model.dataset["TIME"] = time
    return model


def rvs_same(model, sigma=False, omega=False):
    if sigma:
        rvs = model.random_variables.epsilons
    elif omega:
        rvs = model.random_variables.etas

    checked_variance = []
    for rv in rvs:
        var = rv.variance
        if var in checked_variance:
            return True
        else:
            checked_variance.append(var)
    return False


def change_rvs_same(model, sigma=False, omega=False):
    if sigma:
        rvs = model.random_variables.epsilons
    elif omega:
        rvs = model.random_variables.etas

    checked_variance = []
    var_to_add = {}
    rvs_and_var = {}
    for rv in rvs:
        var = rv.variance
        if var in checked_variance:
            n = 1
            new_var = sympy.Symbol(var.name + "_" + f'{n}')
            while new_var in checked_variance:
                n += 1
                new_var = sympy.Symbol(var.name + "_" + f'{n}')

            var_to_add[new_var] = var

            checked_variance.append(new_var)

            rvs_and_var[rv.names] = new_var
            print(rv, " : ", new_var)
        else:
            checked_variance.append(var)

    for rv in rvs:
        if rv.names in rvs_and_var:
            new_rv = rv.replace(variance=rvs_and_var[rv.names])

            all_rvs = model.random_variables
            keep = [name for name in all_rvs.names if name not in [rv.names[0]]]

            model = model.replace(random_variables=all_rvs[keep])
            model = model.replace(random_variables=model.random_variables + new_rv)

    params = model.parameters
    for s in var_to_add:
        param = model.parameters[var_to_add[s]].replace(name=s.name)
        params = params + param
    model = model.replace(parameters=params)

    # Add newline after all updated sigma values have been printed
    print()
    return model


def print_warning(warning: str) -> None:
    """
    Help function for printing warning messages to the console

    Parameters
    ----------
    warning : str
        warning description to be printed

    Returns
    -------
    None
        Prints warning to console

    """
    print(f'-------\nWARNING : \n{warning}\n-------')
