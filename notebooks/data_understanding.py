# ============================================
# MINDSENSE
# 01 - DATA UNDERSTANDING
# ============================================

import sys
from pathlib import Path

# Allow Python to find the src folder
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import pandas as pd

from src.data_loader import load_main_data
from src.data_cleaning import (
    standardize_column_names
)


# ============================================
# LOAD DATA
# ============================================

df = load_main_data()

df = standardize_column_names(df)


# ============================================
# PROJECT TITLE
# ============================================

print("\n")
print("=" * 70)
print("MINDSENSE - DATA UNDERSTANDING")
print("=" * 70)


# ============================================
# 1. DATASET SHAPE
# ============================================

print("\n1. DATASET SHAPE")
print("-" * 70)

print(
    f"Rows    : {df.shape[0]:,}"
)

print(
    f"Columns : {df.shape[1]:,}"
)


# ============================================
# 2. COLUMN NAMES
# ============================================

print("\n2. COLUMN NAMES")
print("-" * 70)

for number, column in enumerate(
    df.columns,
    start=1
):

    print(
        f"{number:02d}. {column}"
    )


# ============================================
# 3. DATA TYPES
# ============================================

print("\n3. DATA TYPES")
print("-" * 70)

print(
    df.dtypes.to_string()
)


# ============================================
# 4. MISSING VALUES
# ============================================

print("\n4. MISSING VALUES")
print("-" * 70)

missing = pd.DataFrame({

    "missing_count":
        df.isnull().sum(),

    "missing_percentage":
        (
            df.isnull().mean() * 100
        ).round(2)

})

missing = missing.sort_values(
    "missing_count",
    ascending=False
)

print(missing.to_string())


# ============================================
# 5. DUPLICATES
# ============================================

print("\n5. DUPLICATES")
print("-" * 70)

duplicate_count = df.duplicated().sum()

print(
    f"Duplicate rows: {duplicate_count}"
)


# ============================================
# 6. NUMERICAL FEATURES
# ============================================

print("\n6. NUMERICAL FEATURES")
print("-" * 70)

numerical_columns = (
    df.select_dtypes(
        include="number"
    ).columns.tolist()
)

for column in numerical_columns:

    print(f"- {column}")


# ============================================
# 7. CATEGORICAL FEATURES
# ============================================

print("\n7. CATEGORICAL FEATURES")
print("-" * 70)

categorical_columns = (
    df.select_dtypes(
        exclude="number"
    ).columns.tolist()
)

for column in categorical_columns:

    print(f"- {column}")


# ============================================
# 8. UNIQUE VALUES
# ============================================

print("\n8. UNIQUE VALUES")
print("-" * 70)

for column in categorical_columns:

    print(
        f"\n{column}:"
    )

    print(
        df[column]
        .value_counts(dropna=False)
        .head(15)
        .to_string()
    )


# ============================================
# 9. DESCRIPTIVE STATISTICS
# ============================================

print("\n9. DESCRIPTIVE STATISTICS")
print("-" * 70)

print(
    df.describe(
        include="all"
    ).transpose().to_string()
)


# ============================================
# 10. FIRST FIVE ROWS
# ============================================

print("\n10. FIRST FIVE ROWS")
print("-" * 70)

print(
    df.head().to_string()
)


print("\n")
print("=" * 70)
print("DATA UNDERSTANDING COMPLETED")
print("=" * 70)