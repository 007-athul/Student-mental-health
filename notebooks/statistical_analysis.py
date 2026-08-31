# ============================================
# MINDSENSE
# 03 - STATISTICAL ANALYSIS
# ============================================

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import pandas as pd
from scipy.stats import pearsonr, spearmanr

from src.data_loader import load_main_data
from src.data_cleaning import standardize_column_names


# ============================================
# LOAD DATA
# ============================================

df = load_main_data()

df = standardize_column_names(df)


print("\n")
print("=" * 70)
print("MINDSENSE - STATISTICAL ANALYSIS")
print("=" * 70)


# ============================================
# OUTPUT DIRECTORY
# ============================================

REPORT_DIR = (
    ROOT_DIR /
    "outputs" /
    "reports"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================
# FUNCTION: CORRELATION TEST
# ============================================

def correlation_test(
    df,
    variable_x,
    variable_y
):

    data = df[
        [
            variable_x,
            variable_y
        ]
    ].dropna()

    if len(data) < 3:

        print(
            f"Not enough data for "
            f"{variable_x} vs {variable_y}"
        )

        return None


    # Pearson correlation

    pearson_r, pearson_p = pearsonr(
        data[variable_x],
        data[variable_y]
    )


    # Spearman correlation

    spearman_r, spearman_p = spearmanr(
        data[variable_x],
        data[variable_y]
    )


    result = {

        "variable_x":
            variable_x,

        "variable_y":
            variable_y,

        "sample_size":
            len(data),

        "pearson_r":
            pearson_r,

        "pearson_p_value":
            pearson_p,

        "spearman_rho":
            spearman_r,

        "spearman_p_value":
            spearman_p
    }


    return result


# ============================================
# SELECTED RELATIONSHIPS
# ============================================

possible_tests = [

    (
        "semester_credit_load",
        "stress_level"
    ),

    (
        "cgpa",
        "stress_level"
    ),

    (
        "stress_level",
        "anxiety_score"
    ),

    (
        "stress_level",
        "depression_score"
    ),

    (
        "anxiety_score",
        "depression_score"
    )
]


# ============================================
# RUN TESTS
# ============================================

results = []


for variable_x, variable_y in possible_tests:

    if (
        variable_x in df.columns
        and variable_y in df.columns
    ):

        result = correlation_test(
            df,
            variable_x,
            variable_y
        )

        if result:

            results.append(
                result
            )

            print("\n")
            print("-" * 60)

            print(
                f"{variable_x} VS {variable_y}"
            )

            print("-" * 60)

            print(
                f"Sample size: "
                f"{result['sample_size']}"
            )

            print(
                f"Pearson r: "
                f"{result['pearson_r']:.3f}"
            )

            print(
                f"Pearson p-value: "
                f"{result['pearson_p_value']:.5f}"
            )

            print(
                f"Spearman rho: "
                f"{result['spearman_rho']:.3f}"
            )

            print(
                f"Spearman p-value: "
                f"{result['spearman_p_value']:.5f}"
            )


            if result[
                "pearson_p_value"
            ] < 0.05:

                print(
                    "Result: "
                    "Statistically significant"
                )

            else:

                print(
                    "Result: "
                    "Not statistically significant"
                )


# ============================================
# SAVE RESULTS
# ============================================

if results:

    results_df = pd.DataFrame(
        results
    )

    results_df.to_csv(
        REPORT_DIR /
        "correlation_tests.csv",
        index=False
    )

    print("\n")
    print(
        "Statistical results saved to:"
    )

    print(
        REPORT_DIR /
        "correlation_tests.csv"
    )


# ============================================
# FINAL NOTE
# ============================================

print("\n")
print("=" * 70)

print(
    "IMPORTANT:"
)

print(
    "Correlation indicates association, "
    "not causation."
)

print("=" * 70)