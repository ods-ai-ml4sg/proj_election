import pandas as pd

class WalkDownResult:

    NONDATA_ROWS_PROTOCOL = ['protocol_url', 'path', 'commission_name']

    def __init__(self, protocol_data, candidate_performance, unmapped_rows, errors):
        self.protocol_data = protocol_data
        self.candidate_performance = candidate_performance
        self.unmapped_rows = unmapped_rows
        self.errors = errors

    @staticmethod
    def create_empty():
        return WalkDownResult(protocol_data = pd.DataFrame(),
                              candidate_performance = pd.DataFrame(),
                              unmapped_rows = {},
                              errors=[])

    def _is_empty(self):
        return self.protocol_data.empty

    def add(self, new_result: 'WalkDownResult', add_type: str or None = None):
        assign = {'candidate_list_type': add_type} if add_type else {}
        self.protocol_data = pd.concat([self.protocol_data, new_result.protocol_data.assign(**assign)], axis=0)
        self.candidate_performance = pd.concat([self.candidate_performance, new_result.candidate_performance.assign(**assign)], axis=0)
        self.unmapped_rows.update(new_result.unmapped_rows)
        self.errors += new_result.errors

    @staticmethod
    def _combine_from_dict(dict_):
        '''
        dict_ - dict up to size 2 containing WalkdownResult as values
        '''
        protocol_combined = pd.concat([v.protocol_data.assign(election_type=k) for k,v in dict_.items()], axis=0)
        performance_combined = pd.concat([v.candidate_performance.assign(election_type=k) for k, v in dict_.items()], axis=0)
        errors_combined = [item for val in dict_.values() for item in val.errors]
        unmapped_rows = {k:v for d in dict_.values() for k,v in d.items()}
        return WalkDownResult(protocol_data = protocol_combined,
                              candidate_performance = performance_combined,
                              unmapped_rows = unmapped_rows,
                              errors=errors_combined)


    def compare_totals(self, result_to_compare: 'WalkDownResult'):
        first_check = self.compare_protocol_totals(result_to_compare)
        second_check = self.compare_candidate_performance(result_to_compare)
        return first_check & second_check

    def compare_protocol_totals(self, result_to_compare):
        summed = result_to_compare.protocol_data.drop(self.NONDATA_ROWS_PROTOCOL, axis=1).sum(axis=0)
        return summed.equals(self.protocol_data.drop(self.NONDATA_ROWS_PROTOCOL, axis = 1).sum(axis=0))

    def compare_candidate_performance(self, result_to_compare):
        summed = result_to_compare.candidate_performance.groupby('name')['votes'].sum()
        return summed.equals(self.candidate_performance.groupby('name')['votes'].sum())

    def add_compare_errors(self, url):
        self.errors.append({'type': 'total_check', 'url': url})