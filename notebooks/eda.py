# ============================================
# MINDSENSE
# 02 - EXPLORATORY DATA ANALYSIS
# ============================================

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.data_loader import load_main_data
from src.data_cleaning import standardize_column_names


# ============================================
# SETTINGS
# ============================================

sns.set_theme(
    style="whitegrid"
)


# ============================================
# LOAD DATA
# ============================================

df = load_main_data()

df = standardize_column_names(df)


print("\n")
print("=" * 70)
print("MINDSENSE - EXPLORATORY DATA ANALYSIS")
print("=" * 70)


# ============================================
# CREATE OUTPUT DIRECTORY
# ============================================

FIGURE_DIR = (
    ROOT_DIR /
    "outputs" /
    "figures"
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================
# HELPER FUNCTION
# ============================================

def save_plot(filename):

    plt.tight_layout()

    plt.savefig(
        FIGURE_DIR / filename,
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    plt.close()


# ============================================
# 1. AGE DISTRIBUTION
# ============================================

if "age" in df.columns:

    plt.figure(
        figsize=(8, 5)
    )

    sns.histplot(
        data=df,
        x="age",
        kde=True
    )

    plt.title(
        "Distribution of Student Age"
    )

    plt.xlabel("Age")
    plt.ylabel("Number of Students")

    save_plot(
        "01_age_distribution.png"
    )


# ============================================
# 2. GENDER DISTRIBUTION
# ============================================

if "gender" in df.columns:

    plt.figure(
        figsize=(8, 5)
    )

    sns.countplot(
        data=df,
        x="gender",
        order=df["gender"].value_counts().index
    )

    plt.title(
        "Gender Distribution"
    )

    plt.xlabel("Gender")
    plt.ylabel("Number of Students")

    plt.xticks(
        rotation=30
    )

    save_plot(
        "02_gender_distribution.png"
    )


# ============================================
# 3. STRESS LEVEL DISTRIBUTION
# ============================================

if "stress_level" in df.columns:

    plt.figure(
        figsize=(8, 5)
    )

    sns.countplot(
        data=df,
        x="stress_level"
    )

    plt.title(
        "Distribution of Stress Levels"
    )

    plt.xlabel("Stress Level")
    plt.ylabel("Number of Students")

    save_plot(
        "03_stress_distribution.png"
    )


# ============================================
# 4. ANXIETY SCORE
# ============================================

if "anxiety_score" in df.columns:

    plt.figure(
        figsize=(8, 5)
    )

    sns.histplot(
        data=df,
        x="anxiety_score",
        kde=True
    )

    plt.title(
        "Distribution of Anxiety Scores"
    )

    plt.xlabel("Anxiety Score")
    plt.ylabel("Number of Students")

    save_plot(
        "04_anxiety_distribution.png"
    )


# ============================================
# 5. DEPRESSION SCORE
# ============================================

if "depression_score" in df.columns:

    plt.figure(
        figsize=(8, 5)
    )

    sns.histplot(
        data=df,
        x="depression_score",
        kde=True
    )

    plt.title(
        "Distribution of Depression Scores"
    )

    plt.xlabel("Depression Score")
    plt.ylabel("Number of Students")

    save_plot(
        "05_depression_distribution.png"
    )


# ============================================
# 6. SLEEP QUALITY VS STRESS
# ============================================

if (
    "sleep_quality" in df.columns
    and "stress_level" in df.columns
):

    plt.figure(
        figsize=(9, 5)
    )

    sns.boxplot(
        data=df,
        x="sleep_quality",
        y="stress_level"
    )

    plt.title(
        "Sleep Quality vs Stress Level"
    )

    plt.xlabel("Sleep Quality")
    plt.ylabel("Stress Level")

    save_plot(
        "06_sleep_vs_stress.png"
    )


# ============================================
# 7. FINANCIAL STRESS VS ANXIETY
# ============================================

if (
    "financial_stress" in df.columns
    and "anxiety_score" in df.columns
):

    plt.figure(
        figsize=(9, 5)
    )

    sns.boxplot(
        data=df,
        x="financial_stress",
        y="anxiety_score"
    )

    plt.title(
        "Financial Stress vs Anxiety Score"
    )

    plt.xlabel("Financial Stress")
    plt.ylabel("Anxiety Score")

    save_plot(
        "07_financial_stress_vs_anxiety.png"
    )


# ============================================
# 8. PHYSICAL ACTIVITY VS STRESS
# ============================================

if (
    "physical_activity" in df.columns
    and "stress_level" in df.columns
):

    plt.figure(
        figsize=(9, 5)
    )

    sns.boxplot(
        data=df,
        x="physical_activity",
        y="stress_level"
    )

    plt.title(
        "Physical Activity vs Stress Level"
    )

    plt.xlabel("Physical Activity")
    plt.ylabel("Stress Level")

    save_plot(
        "08_physical_activity_vs_stress.png"
    )


# ============================================
# 9. SOCIAL SUPPORT VS ANXIETY
# ============================================

if (
    "social_support" in df.columns
    and "anxiety_score" in df.columns
):

    plt.figure(
        figsize=(9, 5)
    )

    sns.boxplot(
        data=df,
        x="social_support",
        y="anxiety_score"
    )

    plt.title(
        "Social Support vs Anxiety Score"
    )

    plt.xlabel("Social Support")
    plt.ylabel("Anxiety Score")

    save_plot(
        "09_social_support_vs_anxiety.png"
    )


# ============================================
# 10. ACADEMIC LOAD VS STRESS
# ============================================

if (
    "semester_credit_load" in df.columns
    and "stress_level" in df.columns
):

    plt.figure(
        figsize=(8, 5)
    )

    sns.scatterplot(
        data=df,
        x="semester_credit_load",
        y="stress_level",
        alpha=0.4
    )

    sns.regplot(
        data=df,
        x="semester_credit_load",
        y="stress_level",
        scatter=False
    )

    plt.title(
        "Academic Load vs Stress Level"
    )

    plt.xlabel(
        "Semester Credit Load"
    )

    plt.ylabel(
        "Stress Level"
    )

    save_plot(
        "10_academic_load_vs_stress.png"
    )


# ============================================
# 11. CGPA VS STRESS
# ============================================

if (
    "cgpa" in df.columns
    and "stress_level" in df.columns
):

    plt.figure(
        figsize=(8, 5)
    )

    sns.scatterplot(
        data=df,
        x="cgpa",
        y="stress_level",
        alpha=0.4
    )

    plt.title(
        "CGPA vs Stress Level"
    )

    plt.xlabel("CGPA")
    plt.ylabel("Stress Level")

    save_plot(
        "11_cgpa_vs_stress.png"
    )


# ============================================
# 12. CORRELATION HEATMAP
# ============================================

numerical_df = df.select_dtypes(
    include="number"
)

if numerical_df.shape[1] >= 2:

    plt.figure(
        figsize=(14, 10)
    )

    correlation = (
        numerical_df.corr()
    )

    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0
    )

    plt.title(
        "Correlation Matrix"
    )

    save_plot(
        "12_correlation_heatmap.png"
    )


# ============================================
# END
# ============================================

print("\n")
print("=" * 70)
print("EDA COMPLETED")
print("=" * 70)

print(
    f"\nFigures saved in:\n{FIGURE_DIR}"
)