#!/usr/bin/env python3
# =============================================================================
# Purpose: Flag participants for inclusion/exclusion based on user-defined
#          brain coverage thresholds.
# =============================================================================

import os
from datetime import datetime

import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    # Input CSV of per-subject automated coverage metrics.
    "input_csv": "/mnt/synapse/neurocat-lab/R21MH133229_asd_dmri_lifespan/analysis/brain_coverage/precision_recall_analyses/input_files/pr_analysis_data.csv",

    # Output directory and filename for the flagged-subjects CSV.
    "output_dir": "/mnt/synapse/neurocat-lab/R21MH133229_asd_dmri_lifespan/analysis/brain_coverage/precision_recall_analyses/results/exclusion",
    "output_csv_name": "coverage_exclusion_flags.csv",

    # Column names in the input CSV. Defaults match the input format used
    # for the precision-recall analysis.
    "id_col": "participant_id",
    "dataset_col": "dataset",  # set to None if your input CSV has no dataset column

    "coverage_cols": {
        "full_brain_mask": "coverage_full_brain_mask",
        "regional_masks": "min_coverage_regional_masks",
    },

    # Two coverage thresholds (0-100 percent) per metric. coverage >= "full"
    # -> full; between "cropped" and "full" -> minimally cropped; below
    # "cropped" -> cropped. "full" must be greater than "cropped".
    "thresholds": {
        "full_brain_mask": {"full": 98, "cropped": 90},
        "regional_masks": {"full": 95, "cropped": 85},
    },

    # How to treat subjects that land in the "minimally cropped" band:
    #   "pass" -- grouped with "full" (subject passes that metric)
    #   "fail" -- grouped with "cropped" (subject fails that metric)
    "minimally_cropped_treatment": "pass",

    # Which metric(s) to apply. Subject is excluded if it fails ANY of these.
    "metrics_to_apply": ["full_brain_mask", "regional_masks"],
}


# =============================================================================
# FUNCTIONS
# =============================================================================

def validate_config(config):
    applied = config["metrics_to_apply"]
    if not applied:
        raise ValueError("CONFIG['metrics_to_apply'] is empty -- specify at least one metric")

    if config["minimally_cropped_treatment"] not in ("pass", "fail"):
        raise ValueError(
            "CONFIG['minimally_cropped_treatment'] must be 'pass' or 'fail', "
            f"got: {config['minimally_cropped_treatment']!r}"
        )

    for metric in applied:
        if metric not in config["coverage_cols"]:
            raise ValueError(f"Metric '{metric}' in metrics_to_apply has no entry in coverage_cols")
        if metric not in config["thresholds"]:
            raise ValueError(f"Metric '{metric}' in metrics_to_apply has no entry in thresholds")

        thr = config["thresholds"][metric]
        if "full" not in thr or "cropped" not in thr:
            raise ValueError(f"thresholds['{metric}'] must have both 'full' and 'cropped' keys")
        if thr["full"] <= thr["cropped"]:
            raise ValueError(
                f"thresholds['{metric}']: 'full' ({thr['full']}) must be greater than "
                f"'cropped' ({thr['cropped']})"
            )


def load_input(config):
    input_csv = config["input_csv"]
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    df = pd.read_csv(input_csv)
    df.columns = [c.strip() for c in df.columns]

    required = [config["id_col"]] + [
        config["coverage_cols"][m] for m in config["metrics_to_apply"]
    ]
    if config["dataset_col"]:
        required.append(config["dataset_col"])

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Input CSV is missing required column(s): {missing}")

    return df


def categorize_coverage(coverage, full_threshold, cropped_threshold):
    """Map a numeric coverage Series to 'full' / 'minimally_cropped' /
    'cropped' / 'undetermined' (missing)."""
    category = pd.Series("cropped", index=coverage.index, dtype=object)
    category[coverage >= cropped_threshold] = "minimally_cropped"
    category[coverage >= full_threshold] = "full"
    category[coverage.isna()] = "undetermined"
    return category


def flag_subjects(df, config):
    applied = config["metrics_to_apply"]
    thresholds = config["thresholds"]
    coverage_cols = config["coverage_cols"]
    minimal_treatment = config["minimally_cropped_treatment"]

    out = pd.DataFrame()
    out[config["id_col"]] = df[config["id_col"]]
    if config["dataset_col"]:
        out[config["dataset_col"]] = df[config["dataset_col"]]

    fail_flags = pd.DataFrame(index=df.index)
    undetermined_flags = pd.DataFrame(index=df.index)
    minimal_flags = pd.DataFrame(index=df.index)

    for metric in applied:
        col = coverage_cols[metric]
        thr = thresholds[metric]
        coverage = pd.to_numeric(df[col], errors="coerce")
        category = categorize_coverage(coverage, thr["full"], thr["cropped"])

        out[col] = coverage
        out[f"{metric}_category"] = category

        fails_this_metric = (category == "cropped") | (
            (category == "minimally_cropped") & (minimal_treatment == "fail")
        )
        # Nullable boolean dtype so "undetermined" subjects can hold <NA>
        # instead of a misleading True/False for that metric.
        out[f"{metric}_pass"] = (~fails_this_metric).astype("boolean")
        out.loc[category == "undetermined", f"{metric}_pass"] = pd.NA

        fail_flags[metric] = fails_this_metric
        undetermined_flags[metric] = category == "undetermined"
        minimal_flags[metric] = category == "minimally_cropped"

    out["excluded"] = fail_flags.any(axis=1)
    out["undetermined"] = undetermined_flags.any(axis=1)
    out["any_minimally_cropped"] = minimal_flags.any(axis=1)

    def joined(flags_df, row_idx):
        return ", ".join(m for m in applied if flags_df.loc[row_idx, m])

    out["failed_metrics"] = [joined(fail_flags, i) for i in df.index]
    out["undetermined_metrics"] = [joined(undetermined_flags, i) for i in df.index]
    out["minimally_cropped_metrics"] = [joined(minimal_flags, i) for i in df.index]

    # Subjects with missing data are flagged "undetermined" rather than
    # silently passing or failing.
    out.loc[out["undetermined"], "excluded"] = False

    return out


def main():
    validate_config(CONFIG)

    output_dir = CONFIG["output_dir"]
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, CONFIG["output_csv_name"])

    start = datetime.now()
    print(f"Started at {start}")
    print(f"Input CSV:                     {CONFIG['input_csv']}")
    print(f"Output CSV:                    {output_csv}")
    print(f"Metrics applied:               {CONFIG['metrics_to_apply']}")
    print(f"Thresholds:                    { {m: CONFIG['thresholds'][m] for m in CONFIG['metrics_to_apply']} }")
    print(f"Minimally cropped treatment:   {CONFIG['minimally_cropped_treatment']}")

    df = load_input(CONFIG)
    print(f"Loaded {len(df)} subjects")

    results = flag_subjects(df, CONFIG)
    results.to_csv(output_csv, index=False)

    n_excluded = int(results["excluded"].sum())
    n_undetermined = int(results["undetermined"].sum())
    n_minimal = int(results["any_minimally_cropped"].sum())
    n_included = len(results) - n_excluded - n_undetermined

    print(f"\nSaved flags for {len(results)} subjects to: {output_csv}")
    print(f"  Included:               {n_included}")
    print(f"  Excluded:               {n_excluded}")
    print(f"  Undetermined:           {n_undetermined}")
    print(f"  (of which, landed in 'minimally cropped' band on >=1 metric: {n_minimal})")
    print(f"Total runtime: {datetime.now() - start}")


if __name__ == "__main__":
    main()
