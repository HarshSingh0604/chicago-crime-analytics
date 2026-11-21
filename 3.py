#use_case3.py
#Use Case 3 - Statistical Insights & Pattern Detection

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import os

#--- CONNECT TO THE SAME DATABASE BUILT IN USE CASE 1 ---
DATABASE_URL = "sqlite:///chicago_crime.db"
engine = create_engine(DATABASE_URL)

try:
    df = pd.read_sql("SELECT * FROM crimes", con=engine)
    print("Loaded crimes table from database.")
    print("Shape:", df.shape)
except Exception as e:
    print(f"ERROR: Could not load 'crimes' table - {e}")
    print("Make sure 'use_case1.py' has been run first to create the database.")
    raise

output_dir = "output/charts"
os.makedirs(output_dir, exist_ok=True)


#--- TASK 1: CRIME INTENSITY BY TIME (HOURLY DISTRIBUTION) ---

crimes_by_hour = df.groupby('Hour').size()

print("\nCrimes by hour of day:")
print(crimes_by_hour)

plt.figure(figsize=(10, 5))
crimes_by_hour.plot(kind='line', marker='o', color='darkorange')
plt.title("Crime Intensity by Hour of Day")
plt.xlabel("Hour (0-23)")
plt.ylabel("Number of Crimes")
plt.xticks(range(0, 24))
plt.grid(True)
plt.tight_layout()
plt.savefig(f"{output_dir}/crimes_by_hour.png")
plt.show()

peak_hour = crimes_by_hour.idxmax()
print(f"\nPeak crime hour: {peak_hour}:00 ({crimes_by_hour.max()} crimes)")


#--- TASK 2: COMMUNITY AREA CLUSTERS USING NUMPY + IQR OUTLIER DETECTION ---

crimes_per_community = df.groupby('community_code').size()

#NumPy - mean crime count per community area
mean_crime_per_area = np.mean(crimes_per_community.values)
print(f"\nMean crimes per community area: {mean_crime_per_area:.2f}")

#box plot to visualize spread and outliers
plt.figure(figsize=(6, 6))
sns.boxplot(y=crimes_per_community.values, color='lightblue')
plt.title("Crime Count Distribution Across Community Areas")
plt.ylabel("Number of Crimes")
plt.tight_layout()
plt.savefig(f"{output_dir}/community_area_boxplot.png")
plt.show()

#IQR method to identify outlier community areas
Q1 = np.percentile(crimes_per_community.values, 25)
Q3 = np.percentile(crimes_per_community.values, 75)
IQR = Q3 - Q1

lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

print(f"\nQ1: {Q1}, Q3: {Q3}, IQR: {IQR}")
print(f"Lower bound: {lower_bound}, Upper bound: {upper_bound}")

outlier_areas = crimes_per_community[
    (crimes_per_community < lower_bound) | (crimes_per_community > upper_bound)
]

print("\nCommunity areas that are extreme outliers in crime count:")
print(outlier_areas)


#--- TASK 3: CRIME CROSS-CORRELATION ---

#select numeric features relevant for correlation
numeric_df = df[['year', 'Month', 'Hour', 'arrest', 'domestic',
                  'ward_no', 'community_code', 'beat_num', 'district_code']].copy()

#convert boolean columns to int so they participate in correlation
numeric_df['arrest'] = numeric_df['arrest'].astype(int)
numeric_df['domestic'] = numeric_df['domestic'].astype(int)

correlation_matrix = numeric_df.corr()

print("\nCorrelation matrix:")
print(correlation_matrix.round(2))

plt.figure(figsize=(9, 7))
sns.heatmap(correlation_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0,linewidths=0.5)
plt.title("Correlation Matrix - Numeric Crime Features")
plt.tight_layout()
plt.savefig(f"{output_dir}/correlation_matrix.png")
plt.show()


#--- SUMMARY ---

print("\n" + "=" * 50)
print("USE CASE 3 - SUMMARY ANSWERS")
print("=" * 50)
print(f"Peak crime hour: {peak_hour}:00")
print(f"Mean crimes per community area: {mean_crime_per_area:.2f}")
print(f"Number of outlier community areas (IQR method): {len(outlier_areas)}")
strongest_corr = correlation_matrix['arrest'].drop('arrest').abs().idxmax()
print(f"Feature most correlated with arrest: {strongest_corr} "
      f"(corr = {correlation_matrix['arrest'][strongest_corr]:.2f})")