import numpy as np
import pandas as pd

def calcELOD(x:pd.Series): # x is a pandas series
    med = np.median(x)
    absDiff = np.abs(x-med)
    medDiff = np.median(absDiff)
    eLOD = med+3*(1.4826*medDiff)
    return eLOD


class AdatMathHelpers:
    """A collection of methods to help with performing common and standard computations on the adat.
    """

    def e_lod_by_reagent(self):
        df = self.pick_on_meta(axis=0, name='SampleType', values=['Buffer'])
        df.columns = df.columns.get_level_values('SeqId')
        e_lod_df = df.apply(calcELOD)
        return e_lod_df


    @staticmethod
    def _compute_intra_cv(adat, groupby):
        sums = {}
        for group_name, group_df in adat.groupby(level=groupby):
            group_means = group_df.mean(axis=0)
            square_diff_df = np.power(group_df - group_means, 2)
            sums[group_name] = square_diff_df.sum(axis=0)
        sums_df = pd.DataFrame(sums)
        df = pd.DataFrame(100 * np.sqrt(sums_df.sum(axis=1) / (adat.shape[0] - 1)) / adat.mean(axis=0))
        return(df.T)

    @staticmethod
    def _compute_inter_cv(adat, groupby):
        sums = {}
        total_means = adat.mean(axis=0)
        for group_name, group_df in adat.groupby(level=groupby):
            group_means = group_df.mean(axis=0)
            square_diff_df = np.power(group_means - total_means, 2)
            sums[group_name] = square_diff_df * group_df.shape[0]
        sums_df = pd.DataFrame(sums)
        df = pd.DataFrame(100 * np.sqrt(sums_df.sum(axis=1) / (adat.shape[0] - 1)) / total_means)
        return(df.T)

    def cv_decomp(self, groupby=None, sample_type=None, sample_id=None):
        groupby = groupby or "PlateId"
        if sample_id:
            adat = self.xs(sample_id, level="SampleId")
        elif sample_type:
            adat = self.xs(sample_type, level="SampleType")
        else:
            adat = self.copy()

        intra_cv_df = self._compute_intra_cv(adat, groupby)
        inter_cv_df = self._compute_inter_cv(adat, groupby)
        total_cv_df = np.sqrt(np.power(intra_cv_df, 2) + np.power(inter_cv_df, 2))

        cv_decomps = {
            "Total": total_cv_df,
            "Intra": intra_cv_df,
            "Inter": inter_cv_df
        }
        cv_decomp_df = pd.concat(cv_decomps)
        cv_decomp_df.index = cv_decomp_df.index.droplevel(level=1)

        return (cv_decomp_df.T)
