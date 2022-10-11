from pathlib import Path

import pharmpy.modeling as modeling
from pharmpy.deps import numpy as np
from pharmpy.deps import pandas as pd
from pharmpy.plugins.nonmem.parsing import parameter_translation
from pharmpy.plugins.nonmem.results_file import NONMEMResultsFile
from pharmpy.plugins.nonmem.table import NONMEMTableFile
from pharmpy.plugins.nonmem.update import rv_translation
from pharmpy.results import ChainedModelfitResults, ModelfitResults
from pharmpy.workflows.log import Log


def parse_modelfit_results(model, path):
    if path is None:
        return None

    try:
        ext_path = path / (model.name + '.ext')
        res = NONMEMChainedModelfitResults(ext_path, model=model)
        return res
    except (FileNotFoundError, OSError):
        return None


class NONMEMModelfitResults(ModelfitResults):
    def __init__(self, chain):
        self._chain = chain
        super().__init__()

    def _set_covariance_status(self, results_file, table_with_cov=None):
        covariance_status = {
            'requested': True
            if self.standard_errors is not None
            else (table_with_cov == self.table_number),
            'completed': (self.standard_errors is not None),
            'warnings': None,
        }
        if self.standard_errors is not None and results_file is not None:
            status = results_file.covariance_status(self.table_number)
            if status['covariance_step_ok'] is not None:
                covariance_status['warnings'] = not status['covariance_step_ok']

        self._covariance_status = covariance_status

    def _set_estimation_status(self, results_file, requested):
        estimation_status = {'requested': requested}
        status = NONMEMResultsFile.unknown_termination()
        if results_file is not None:
            status = results_file.estimation_status(self.table_number)
        for k, v in status.items():
            estimation_status[k] = v
        self._estimation_status = estimation_status
        self.minimization_successful = estimation_status['minimization_successful']
        self.function_evaluations = estimation_status['function_evaluations']
        self.significant_digits = estimation_status['significant_digits']
        if estimation_status['maxevals_exceeded'] is True:
            self.termination_cause = 'maxevals_exceeded'
        elif estimation_status['rounding_errors'] is True:
            self.termination_cause = 'rounding_errors'
        else:
            self.termination_cause = None


class NONMEMChainedModelfitResults(ChainedModelfitResults):
    def __init__(self, path, model=None, subproblem=None):
        # Path is path to any result file
        self.log = Log()
        path = Path(path)
        self._path = path
        self._subproblem = subproblem
        self.model = model
        extensions = ['.lst', '.ext', '.cov', '.cor', '.coi', '.phi']
        self.tool_files = [self._path.with_suffix(ext) for ext in extensions]
        super().__init__()
        self._read_ext_table()
        self._read_lst_file()
        self._read_cov_table()
        self._read_cor_table()
        self._read_coi_table()
        self._calculate_cov_cor_coi()
        (
            self.individual_ofv,
            self.individual_estimates,
            self.individual_estimates_covariance,
        ) = parse_phi(model, path)
        table_df = parse_tables(model, path)
        self.residuals = parse_residuals(table_df)
        self.predictions = parse_predictions(table_df)

    def __getattr__(self, item):
        # Avoid infinite recursion when deepcopying
        # See https://stackoverflow.com/questions/47299243/recursionerror-when-python-copy-deepcopy
        if item.startswith('__'):
            raise AttributeError('')
        return super().__getattribute__(item)

    def __getitem__(self, key):
        return super().__getitem__(key)

    def __bool__(self):
        # without this, an existing but 'unloaded' object will evaluate to False
        return len(self) > 0

    def _read_ext_table(self):
        try:
            ext_tables = NONMEMTableFile(self._path.with_suffix('.ext'))
        except ValueError:
            # The ext-file is illegal
            self.log.log_error(f"Broken ext-file {self._path.with_suffix('.ext')}")
            result_obj = NONMEMModelfitResults(self)
            result_obj.model_name = self._path.stem
            result_obj.model = self.model
            is_covariance_step = self.model.estimation_steps[0].cov
            result_obj = self._fill_empty_results(result_obj, is_covariance_step)
            result_obj.table_number = 1
            self.append(result_obj)
            return
        final_ofv, ofv_iterations = parse_ext(self._path, self._subproblem)
        self.ofv = final_ofv
        self.ofv_iterations = ofv_iterations
        for table in ext_tables:
            if self._subproblem and table.subproblem != self._subproblem:
                continue
            result_obj = NONMEMModelfitResults(self)
            result_obj.model_name = self._path.stem
            result_obj.model = self.model
            result_obj.table_number = table.number

            try:
                table.data_frame
            except ValueError:
                self.log.log_error(
                    f"Broken table in ext-file {self._path.with_suffix('.ext')}, "
                    f"table no. {table.number}"
                )
                is_covariance_step = self.model.estimation_steps[table.number - 1].cov
                result_obj = self._fill_empty_results(result_obj, is_covariance_step)
                self.append(result_obj)
                continue

            ests = table.final_parameter_estimates
            try:
                fix = table.fixed
            except KeyError:
                # NM 7.2 does not have row -1000000006 indicating FIXED status
                if self.model:
                    fixed = pd.Series(self.model.parameters.fix)
                    fix = pd.concat(
                        [fixed, pd.Series(True, index=ests.index.difference(fixed.index))]
                    )
            ests = ests[~fix]
            if self.model:
                ests = ests.rename(index=parameter_translation(self.model.internals.control_stream))
            result_obj.parameter_estimates = ests
            try:
                sdcorr = table.omega_sigma_stdcorr[~fix]
            except KeyError:
                pass
            else:
                if self.model:
                    sdcorr = sdcorr.rename(
                        index=parameter_translation(self.model.internals.control_stream)
                    )
                sdcorr_ests = ests.copy()
                sdcorr_ests.update(sdcorr)
                result_obj.parameter_estimates_sdcorr = sdcorr_ests
            try:
                ses = table.standard_errors
                result_obj._set_covariance_status(table)

            except Exception:
                # If there are no standard errors in ext-file it means
                # there can be no cov, cor or coi either
                result_obj.standard_errors = None
                result_obj.covariance_matrix = None
                result_obj.correlation_matrix = None
                result_obj.information_matrix = None
                result_obj._set_covariance_status(None)
            else:
                ses = ses[~fix]
                sdcorr = table.omega_sigma_se_stdcorr[~fix]
                if self.model:
                    ses = ses.rename(
                        index=parameter_translation(self.model.internals.control_stream)
                    )
                    sdcorr = sdcorr.rename(
                        index=parameter_translation(self.model.internals.control_stream)
                    )
                result_obj.standard_errors = ses
                sdcorr_ses = ses.copy()
                sdcorr_ses.update(sdcorr)
                if self.model:
                    sdcorr_ses = sdcorr_ses.rename(
                        index=parameter_translation(self.model.internals.control_stream)
                    )
                result_obj.standard_errors_sdcorr = sdcorr_ses
            self.append(result_obj)

    def _fill_empty_results(self, result_obj, is_covariance_step):
        # Parameter estimates NaN for all parameters that should be estimated
        pe = pd.Series(
            np.nan, name='estimates', index=list(self.model.parameters.nonfixed.inits.keys())
        )
        result_obj.parameter_estimates = pe
        result_obj.ofv = np.nan
        if is_covariance_step:
            se = pd.Series(
                np.nan, name='SE', index=list(self.model.parameters.nonfixed.inits.keys())
            )
            result_obj.standard_errors = se
        else:
            result_obj.standard_errors = None
        return result_obj

    def _read_lst_file(self):
        try:
            rfile = NONMEMResultsFile(self._path.with_suffix('.lst'), self.log)
        except OSError:
            return
        table_with_cov = -99
        if self.model is not None:
            if len(self.model.internals.control_stream.get_records('COVARIANCE')) > 0:
                table_with_cov = self[-1].table_number  # correct unless interrupted
        for table_no, result_obj in enumerate(self, 1):
            result_obj._set_estimation_status(rfile, requested=True)
            # _covariance_status already set to None if ext table did not have standard errors
            result_obj._set_covariance_status(rfile, table_with_cov=table_with_cov)
            try:
                result_obj.estimation_runtime = rfile.table[table_no]['estimation_runtime']
            except (KeyError, FileNotFoundError):
                result_obj.estimation_runtime = np.nan
            try:
                result_obj.log_likelihood = rfile.table[table_no]['ofv_with_constant']
            except (KeyError, FileNotFoundError):
                result_obj.log_likelihood = np.nan
            result_obj.runtime_total = rfile.runtime_total

    def _read_cov_table(self):
        try:
            cov_table = NONMEMTableFile(self._path.with_suffix('.cov'))
        except OSError:
            for result_obj in self:
                if not hasattr(result_obj, 'covariance_matrix'):
                    result_obj.covariance_matrix = None
            return
        for result_obj in self:
            if _check_covariance_status(result_obj):
                df = cov_table.table_no(result_obj.table_number).data_frame
                if df is not None:
                    if self.model:
                        df = df.rename(
                            index=parameter_translation(self.model.internals.control_stream)
                        )
                        df.columns = df.index
                result_obj.covariance_matrix = df
            else:
                result_obj.covariance_matrix = None

    def _read_coi_table(self):
        try:
            coi_table = NONMEMTableFile(self._path.with_suffix('.coi'))
        except OSError:
            for result_obj in self:
                if not hasattr(result_obj, 'information_matrix'):
                    result_obj.information_matrix = None
            return
        for result_obj in self:
            if _check_covariance_status(result_obj):
                df = coi_table.table_no(result_obj.table_number).data_frame
                if df is not None:
                    if self.model:
                        df = df.rename(
                            index=parameter_translation(self.model.internals.control_stream)
                        )
                        df.columns = df.index
                result_obj.information_matrix = df
            else:
                result_obj.information_matrix = None

    def _read_cor_table(self):
        try:
            cor_table = NONMEMTableFile(self._path.with_suffix('.cor'))
        except OSError:
            for result_obj in self:
                if not hasattr(result_obj, 'correlation_matrix'):
                    result_obj.correlation_matrix = None
            return
        for result_obj in self:
            if _check_covariance_status(result_obj):
                cor = cor_table.table_no(result_obj.table_number).data_frame
                if cor is not None:
                    if self.model:
                        cor = cor.rename(
                            index=parameter_translation(self.model.internals.control_stream)
                        )
                        cor.columns = cor.index
                    np.fill_diagonal(cor.values, 1)
                result_obj.correlation_matrix = cor
            else:
                result_obj.correlation_matrix = None

    def _calculate_cov_cor_coi(self):
        for obj in self:
            if obj.covariance_matrix is None:
                if obj.correlation_matrix is not None:
                    obj.covariance_matrix = modeling.calculate_cov_from_corrse(
                        obj.correlation_matrix, obj.standard_errors
                    )
                elif obj.information_matrix is not None:
                    obj.covariance_matrix = modeling.calculate_cov_from_inf(obj.information_matrix)
            if obj.correlation_matrix is None:
                if obj.covariance_matrix is not None:
                    obj.correlation_matrix = modeling.calculate_corr_from_cov(obj.covariance_matrix)
                elif obj.information_matrix is not None:
                    obj.correlation_matrix = modeling.calculate_corr_from_inf(
                        obj.information_matrix
                    )
            if obj.information_matrix is None:
                if obj.covariance_matrix is not None:
                    obj.information_matrix = modeling.calculate_inf_from_cov(obj.covariance_matrix)
                elif obj.correlation_matrix is not None:
                    obj.information_matrix = modeling.calculate_inf_from_corrse(
                        obj.correlation_matrix, obj.standard_errors
                    )
            if obj.standard_errors is None:
                if obj.covariance_matrix is not None:
                    obj.standard_errors = modeling.calculate_se_from_cov(obj.covariance_matrix)
                elif obj.information_matrix is not None:
                    obj.standard_errors = modeling.calculate_se_from_inf(obj.information_matrix)


def parse_phi(model, path):
    try:
        phi_tables = NONMEMTableFile(path.with_suffix('.phi'))
    except FileNotFoundError:
        return None, None, None
    table = phi_tables.tables[-1]

    if table is not None:
        trans = rv_translation(model.internals.control_stream, reverse=True)
        rv_names = [name for name in model.random_variables.etas.names if name in trans]
        try:
            individual_ofv = table.iofv
            individual_estimates = table.etas.rename(
                columns=rv_translation(model.internals.control_stream)
            )[rv_names]
            covs = table.etcs
            covs = covs.transform(
                lambda cov: cov.rename(
                    columns=rv_translation(model.internals.control_stream),
                    index=rv_translation(model.internals.control_stream),
                )
            )
            covs = covs.transform(lambda cov: cov[rv_names].loc[rv_names])
            return individual_ofv, individual_estimates, covs
        except KeyError:
            pass
    return None, None, None


def parse_tables(model, path):
    """Parse $TABLE and table files into one large dataframe of useful columns"""
    interesting_columns = {
        'ID',
        'TIME',
        'PRED',
        'CIPREDI',
        'CPRED',
        'IPRED',
        'RES',
        'WRES',
        'CWRES',
        'MDV',
    }

    table_recs = model.internals.control_stream.get_records('TABLE')
    found = set()
    df = pd.DataFrame()
    for table_rec in table_recs:
        columns_in_table = []
        for key, value in table_rec.all_options:
            if key in interesting_columns and key not in found and value is None:
                # FIXME: Cannot handle synonyms here
                colname = key
            elif value in interesting_columns and value not in found:
                colname = value
            else:
                continue

            found.add(colname)
            columns_in_table.append(colname)

            noheader = table_rec.has_option("NOHEADER")
            notitle = table_rec.has_option("NOTITLE") or noheader
            nolabel = table_rec.has_option("NOLABEL") or noheader
            path = path.parent / table_rec.path
            try:
                table_file = NONMEMTableFile(path, notitle=notitle, nolabel=nolabel)
            except IOError:
                continue
            table = table_file.tables[0]
            df[columns_in_table] = table.data_frame[columns_in_table]

    if 'ID' in df.columns:
        df['ID'] = df['ID'].convert_dtypes()
    return df


def _extract_from_df(df, mandatory, optional):
    # Extract all mandatory and at least one optional column from df
    columns = set(df.columns)
    if not (set(mandatory) <= columns):
        return None

    found_optionals = [col for col in optional if col in columns]
    if not found_optionals:
        return None
    return df[mandatory + found_optionals]


def parse_residuals(df):
    index_cols = ['ID', 'TIME']
    cols = ['RES', 'WRES', 'CWRES']
    df = _extract_from_df(df, index_cols, cols)
    if df is not None:
        df.set_index(['ID', 'TIME'], inplace=True)
        df = df.loc[(df != 0).any(axis=1)]  # Simple way of removing non-observations
    return df


def parse_predictions(df):
    index_cols = ['ID', 'TIME']
    cols = ['PRED', 'CIPREDI', 'CPRED', 'IPRED']
    df = _extract_from_df(df, index_cols, cols)
    if df is not None:
        df.set_index(['ID', 'TIME'], inplace=True)
    return df


def parse_ext(path, subproblem):
    ext_tables = NONMEMTableFile(path.with_suffix('.ext'))
    step = []
    iteration = []
    ofv = []
    for i, table in enumerate(ext_tables, start=1):
        if subproblem and table.subproblem != subproblem:
            continue
        df = table.data_frame
        df = df[df['ITERATION'] >= 0]
        n = len(df)
        step += [i] * n
        iteration += list(df['ITERATION'])
        ofv += list(df['OBJ'])
        final_ofv = table.final_ofv
    ofv_iterations = pd.Series(ofv, name='OFV', dtype='float64', index=[step, iteration])
    return final_ofv, ofv_iterations


def simfit_results(model, model_path):
    """Read in modelfit results from a simulation/estimation model"""
    nsubs = model.internals.control_stream.get_records('SIMULATION')[0].nsubs
    results = []
    for i in range(1, nsubs + 1):
        res = NONMEMChainedModelfitResults(model_path, model=model, subproblem=i)
        results.append(res)
    return results


def _check_covariance_status(result):
    return (
        isinstance(result, NONMEMModelfitResults) and result._covariance_status['warnings'] is False
    )
