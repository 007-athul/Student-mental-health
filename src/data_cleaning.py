import pandas as pd

# STANDARDIZE COLUMN NAMES

def standardize_column_names(df):
    df = df.copy()
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df

# REMOVE DUPLICATES

def remove_duplicates(df):
    df = df.copy()
    duplicate_count = df.duplicated().sum()
    print(
        f"Duplicate rows found: {duplicate_count}"
    )
    df = df.drop_duplicates()
    print(
        f"Rows after removing duplicates: {len(df)}"
    )

    return df

# HANDLE MISSING VALUES

def handle_missing_values(df):
    df = df.copy()
    numerical_columns = (
        df.select_dtypes(
            include="number"
        ).columns
    )

    categorical_columns = (
        df.select_dtypes(
            exclude="number"
        ).columns
    )


    for column in numerical_columns:

        if df[column].isnull().sum() > 0:
            df[column] = df[column].fillna(
                df[column].median()
            )


    for column in categorical_columns:

        if df[column].isnull().sum() > 0:
            mode_value = df[column].mode()

            if not mode_value.empty:
                df[column] = df[column].fillna(
                    mode_value[0]
                )

    return df

# COMPLETE CLEANING PIPELINE


def clean_data(df):
    print("\nStarting data cleaning...")
    df = standardize_column_names(df)
    df = remove_duplicates(df)
    df = handle_missing_values(df)
    print("Data cleaning completed.")

    return df