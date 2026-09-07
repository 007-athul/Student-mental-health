# ============================================
# DATA PREPROCESSING
# ============================================

import sys
from pathlib import Path

# Allow Python to find the src folder
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data_loader import load_main_data
from src.data_cleaning import standardize_column_names


# ============================================
# SETTINGS
# ============================================

TARGET_COLUMN = "stress_level"

TEST_SIZE = 0.20
RANDOM_STATE = 42

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
REPORT_DIR = ROOT_DIR / "outputs" / "reports"


# ============================================
# OUTLIER DETECTION
# ============================================

def detect_outliers(df):
    """
    Detect potential numerical outliers using
    the IQR (Interquartile Range) method.

    Potential outliers are reported but not
    automatically removed because unusual values
    may still be valid student observations.
    """

    numerical_columns = df.select_dtypes(
        include="number"
    ).columns

    results = []

    for column in numerical_columns:

        q1 = df[column].quantile(0.25)
        q3 = df[column].quantile(0.75)

        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outlier_mask = (
            (df[column] < lower_bound)
            | (df[column] > upper_bound)
        )

        outlier_count = outlier_mask.sum()

        results.append({
            "feature": column,
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "iqr": round(iqr, 2),
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2),
            "outlier_count": int(outlier_count),
            "outlier_percentage": round(
                (outlier_count / len(df)) * 100,
                2
            )
        })

    return pd.DataFrame(results)


# ============================================
# INVALID VALUE CHECK
# ============================================

def check_invalid_values(df):
    """
    Check important numerical variables against
    their expected domain ranges.
    """

    expected_ranges = {
        "age": (18, 35),
        "cgpa": (0, 4),
        "stress_level": (0, 5),
        "depression_score": (0, 5),
        "anxiety_score": (0, 5),
        "financial_stress": (0, 5),
        "semester_credit_load": (0, None)
    }

    results = []

    for column, (minimum, maximum) in expected_ranges.items():

        if column not in df.columns:
            continue

        invalid_count = 0

        if minimum is not None:
            invalid_count += (
                df[column] < minimum
            ).sum()

        if maximum is not None:
            invalid_count += (
                df[column] > maximum
            ).sum()

        results.append({
            "feature": column,
            "invalid_count": int(invalid_count)
        })

    return pd.DataFrame(results)


# ============================================
# PREPROCESSING PIPELINE
# ============================================

def build_preprocessor(X):
    """
    Create separate preprocessing pipelines for
    numerical and categorical features.
    """

    numerical_features = X.select_dtypes(
        include="number"
    ).columns.tolist()

    categorical_features = X.select_dtypes(
        exclude="number"
    ).columns.tolist()

    print("\nNumerical features:")
    for feature in numerical_features:
        print(f"- {feature}")

    print("\nCategorical features:")
    for feature in categorical_features:
        print(f"- {feature}")

    # ----------------------------------------
    # NUMERICAL PIPELINE
    # ----------------------------------------

    numerical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                )
            ),
            (
                "scaler",
                StandardScaler()
            )
        ]
    )

    # ----------------------------------------
    # CATEGORICAL PIPELINE
    # ----------------------------------------

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                )
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False
                )
            )
        ]
    )

    # ----------------------------------------
    # COMBINE BOTH PIPELINES
    # ----------------------------------------

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numerical",
                numerical_pipeline,
                numerical_features
            ),
            (
                "categorical",
                categorical_pipeline,
                categorical_features
            )
        ]
    )

    return preprocessor


# ============================================
# MAIN PREPROCESSING FUNCTION
# ============================================

def prepare_data():

    print("\n")
    print("=" * 70)
    print("MINDSENSE - DATA PREPROCESSING")
    print("=" * 70)

    # ========================================
    # 1. LOAD DATA
    # ========================================

    df = load_main_data()

    df = standardize_column_names(df)

    print("\n1. DATA LOADED")
    print("-" * 70)

    print(
        f"Rows    : {df.shape[0]:,}"
    )

    print(
        f"Columns : {df.shape[1]:,}"
    )

    # ========================================
    # 2. REMOVE DUPLICATES
    # ========================================

    print("\n2. DUPLICATE REMOVAL")
    print("-" * 70)

    duplicate_count = df.duplicated().sum()

    print(
        f"Duplicate rows found: {duplicate_count}"
    )

    if duplicate_count > 0:

        df = df.drop_duplicates().copy()

        print(
            f"Rows after removal: {len(df):,}"
        )

    else:

        print("No duplicate rows found.")

    # ========================================
    # 3. MISSING VALUE HANDLING
    # ========================================

    print("\n3. MISSING VALUE HANDLING")
    print("-" * 70)

    missing_before = df.isnull().sum()

    missing_before = missing_before[
        missing_before > 0
    ]

    if missing_before.empty:

        print("No missing values found.")

    else:

        print("Missing values found:")

        print(
            missing_before.to_string()
        )

        print(
            "\nMissing numerical values "
            "will be imputed using the median."
        )

        print(
            "Missing categorical values "
            "will be imputed using the most frequent value."
        )

    # ========================================
    # 4. TARGET VALIDATION
    # ========================================

    print("\n4. TARGET VALIDATION")
    print("-" * 70)

    if TARGET_COLUMN not in df.columns:

        raise ValueError(
            f"Target column '{TARGET_COLUMN}' "
            "was not found in the dataset."
        )

    print(
        f"Target variable: {TARGET_COLUMN}"
    )

    missing_target = df[
        TARGET_COLUMN
    ].isnull().sum()

    print(
        f"Missing target values: {missing_target}"
    )

    # A missing target cannot be used for
    # supervised learning, so remove those rows.
    if missing_target > 0:

        df = df.dropna(
            subset=[TARGET_COLUMN]
        ).copy()

    # ========================================
    # 5. INVALID VALUE CHECK
    # ========================================

    print("\n5. INVALID VALUE CHECK")
    print("-" * 70)

    invalid_report = check_invalid_values(df)

    print(
        invalid_report.to_string(
            index=False
        )
    )

    # ========================================
    # 6. OUTLIER DETECTION
    # ========================================

    print("\n6. OUTLIER DETECTION")
    print("-" * 70)

    # Target is excluded because it is not
    # a predictor feature.
    predictor_data = df.drop(
        columns=[TARGET_COLUMN]
    )

    outlier_report = detect_outliers(
        predictor_data
    )

    print(
        outlier_report.to_string(
            index=False
        )
    )

    print(
        "\nNote: Potential outliers are not "
        "automatically removed."
    )

    print(
        "Values are retained when they fall "
        "within a valid domain range."
    )

    # ========================================
    # 7. FEATURE / TARGET SEPARATION
    # ========================================

    print("\n7. FEATURE SELECTION")
    print("-" * 70)

    X = df.drop(
        columns=[TARGET_COLUMN]
    )

    y = df[TARGET_COLUMN]

    print(
        f"Target: {TARGET_COLUMN}"
    )

    print(
        f"Candidate predictor features: {X.shape[1]}"
    )

    print(
        "\nDepression_Score and Anxiety_Score "
        "are retained as candidate features."
    )

    print(
        "Their usefulness will be evaluated "
        "during model development rather than "
        "removed based only on correlation."
    )

    # ========================================
    # 8. TRAIN / TEST SPLIT
    # ========================================

    print("\n8. TRAIN / TEST SPLIT")
    print("-" * 70)

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=y
        )
    )

    print(
        f"Training samples: {len(X_train):,}"
    )

    print(
        f"Testing samples : {len(X_test):,}"
    )

    # ========================================
    # 9. BUILD PREPROCESSOR
    # ========================================

    print("\n9. BUILDING PREPROCESSING PIPELINE")
    print("-" * 70)

    preprocessor = build_preprocessor(
        X_train
    )

    print(
        "\nNumerical:"
        "\n  Median Imputation"
        "\n  Standard Scaling"
    )

    print(
        "\nCategorical:"
        "\n  Most-Frequent Imputation"
        "\n  One-Hot Encoding"
    )

    # ========================================
    # 10. FIT ON TRAINING DATA
    # ========================================

    print("\n10. FITTING PREPROCESSOR")
    print("-" * 70)

    # IMPORTANT:
    # The preprocessor is fitted ONLY on
    # training data to prevent data leakage.

    X_train_processed = (
        preprocessor.fit_transform(
            X_train
        )
    )

    X_test_processed = (
        preprocessor.transform(
            X_test
        )
    )

    print(
        "Preprocessor fitted on training data."
    )

    print(
        "Test data transformed using "
        "training parameters."
    )

    # ========================================
    # 11. GET FINAL FEATURE NAMES
    # ========================================

    feature_names = (
        preprocessor
        .get_feature_names_out()
    )

    # ========================================
    # 12. CONVERT TO DATAFRAMES
    # ========================================

    X_train_processed = pd.DataFrame(
        X_train_processed,
        columns=feature_names,
        index=X_train.index
    )

    X_test_processed = pd.DataFrame(
        X_test_processed,
        columns=feature_names,
        index=X_test.index
    )

    # ========================================
    # 13. FINAL DATASET CHECK
    # ========================================

    print("\n13. FINAL DATASET")
    print("-" * 70)

    print(
        f"Original predictor features : {X.shape[1]}"
    )

    print(
        f"Encoded/scaled features     : "
        f"{X_train_processed.shape[1]}"
    )

    print(
        f"Training dataset shape      : "
        f"{X_train_processed.shape}"
    )

    print(
        f"Testing dataset shape       : "
        f"{X_test_processed.shape}"
    )

    print(
        f"Training missing values     : "
        f"{X_train_processed.isnull().sum().sum()}"
    )

    print(
        f"Testing missing values      : "
        f"{X_test_processed.isnull().sum().sum()}"
    )

    # ========================================
    # 14. SAVE PROCESSED DATA
    # ========================================

    print("\n14. SAVING PROCESSED DATA")
    print("-" * 70)

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    X_train_processed.to_csv(
        PROCESSED_DIR /
        "X_train_processed.csv",
        index=False
    )

    X_test_processed.to_csv(
        PROCESSED_DIR /
        "X_test_processed.csv",
        index=False
    )

    y_train.to_csv(
        PROCESSED_DIR /
        "y_train.csv",
        index=False
    )

    y_test.to_csv(
        PROCESSED_DIR /
        "y_test.csv",
        index=False
    )

    outlier_report.to_csv(
        REPORT_DIR /
        "outlier_report.csv",
        index=False
    )

    invalid_report.to_csv(
        REPORT_DIR /
        "invalid_value_report.csv",
        index=False
    )

    print(
        "Processed datasets and reports saved."
    )

    # ========================================
    # COMPLETED
    # ========================================

    print("\n")
    print("=" * 70)
    print("DATA PREPROCESSING COMPLETED")
    print("=" * 70)

    return (
        X_train_processed,
        X_test_processed,
        y_train,
        y_test,
        preprocessor,
        outlier_report
    )


# ============================================
# RUN
# ============================================

if __name__ == "__main__":

    prepare_data()