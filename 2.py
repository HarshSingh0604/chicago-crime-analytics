#use_case2.py
#Use Case 2 - Exploratory Analysis & Visualization of Crime

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import os

#--- CONNECT TO THE SAME DATABASE BUILT IN USE CASE 1 ---
DATABASE_URL = "sqlite:///chicago_crime.db"
engine = create_engine(DATABASE_URL)

#read the cleaned crimes table (not the CSV - single source of truth)
try:
    df = pd.read_sql("SELECT * FROM crimes", con=engine)
    print("Loaded crimes table from database.")
    print("Shape:", df.shape)
except Exception as e:
    print(f"ERROR: Could not load 'crimes' table - {e}")
    print("Make sure 'use_case1.py' has been run first to create the database.")
    raise

#folder to save charts for the web app (Tabs 2-5) and PDF screenshots
output_dir = "output/charts"
os.makedirs(output_dir, exist_ok=True)


# --- TASK 1: CRIME TREND OVER YEARS ---

# Count crimes by year
crime_by_year = (
    df.groupby('year')
      .size()
      .reset_index(name='Crime_Count')
)

print("\nCrime count by year:")
print(crime_by_year)


# Visualization
plt.figure(figsize=(8, 5))

plt.plot(
    crime_by_year["year"],
    crime_by_year["Crime_Count"],
    marker="o",
    linewidth=2
)

plt.title("Crime Trend Over Years")
plt.xlabel("Year")
plt.ylabel("Number of Crimes")

plt.grid(True)
plt.tight_layout()

# Save chart for PDF/web application
plt.savefig(f"{output_dir}/crime_trend_by_year.png")

plt.show()


#--- TASK 2: CRIME DISTRIBUTION BY CATEGORY ---

# Count crime categories
crime_counts = df["primary_type"].value_counts()

# Get top 10 crime categories
top10_crimes = crime_counts.head(10)
print("\nTop 10 crime categories:")
print(top10_crimes)

# Calculate percentage of total crimes
crime_percentage = (
    top10_crimes / len(df)
) * 100

#here we have 
crime_summary = pd.DataFrame({
    "Crime Count": top10_crimes,
    "Percentage": crime_percentage.round(2)
})

print("\nTop 10 crime category summary:")
print(crime_summary)

# Visualization

plt.figure(figsize=(10, 6))

sns.barplot(
    x=top10_crimes.values,
    y=top10_crimes.index,
    palette='viridis'
)

plt.title("Top 10 Crime Categories")
plt.xlabel("Number of Crimes")
plt.ylabel("Primary Type")

plt.tight_layout()

# Save chart
plt.savefig(f"{output_dir}/top10_crime_categories.png")

plt.show()


#--- TASK 3: ARRESTS AND CRIME OUTCOMES ---

arrest_rate = df['arrest'].mean() * 100
print(f"\nOverall arrest rate: {arrest_rate:.2f}%")

#arrest rate consistency across years
arrest_rate_by_year = df.groupby('year')['arrest'].mean() * 100
print("\nArrest rate by year (%):")
print(arrest_rate_by_year.round(2))

plt.figure(figsize=(10, 5))
arrest_rate_by_year.plot(kind='bar', color='indianred')
plt.title("Arrest Rate by Year")
plt.xlabel("Year")
plt.ylabel("Arrest Rate (%)")
plt.ylim(20, 36)
plt.tight_layout()
plt.savefig(f"{output_dir}/arrest_rate_by_year.png")
plt.show()

#--- TASK 4: HEATMAP OF CRIME BY MONTH AND DAY OF WEEK ---

#pivot: rows = DayOfWeek, columns = Month, values = crime count
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

heatmap_data = df.pivot_table(
    index='DayOfWeek',
    columns='Month',
    values='id',
    aggfunc='count'
).reindex(day_order)

plt.figure(figsize=(13, 8))
sns.heatmap(heatmap_data, cmap='YlOrRd', annot=True, fmt='g')
plt.title("Crime Frequency: Month vs Day of Week")
plt.xlabel("Month")
plt.ylabel("Day of Week")
plt.tight_layout()
plt.savefig(f"{output_dir}/heatmap_month_day.png")
plt.show()

#which month has the highest crime frequency
crimes_by_month = df.groupby('Month').size()
highest_month = crimes_by_month.idxmax()
print(f"\nMonth with highest crime frequency: {highest_month} "
      f"({crimes_by_month.max()} crimes)")


#--- TASK 5: TOP COMMUNITY AREAS ---

top10_community = df['community_code'].value_counts().head(10)

print("\nTop 10 community areas with highest crime counts:")
print(top10_community)

plt.figure(figsize=(10, 6))

sns.barplot(
    x=top10_community.index.astype(str),
    y=top10_community.values,
    palette='mako'
)

plt.title("Top 10 Community Areas by Crime Count")
plt.xlabel("Community Area Code")
plt.ylabel("Number of Crimes")

plt.tight_layout()
plt.savefig(f"{output_dir}/top10_community_areas.png")
plt.show()

#--- ANSWERS TO USE CASE 2 QUESTIONS ---

print("\n" + "=" * 50)
print("USE CASE 2 - SUMMARY ANSWERS")
print("=" * 50)

most_frequent_crime = df['primary_type'].value_counts().idxmax()
print(f"Most frequent crime category: {most_frequent_crime}")

print(
    f"Highest crime month: {highest_month} "
    f"({crimes_by_month.max()} crimes)"
)

arrest_std = arrest_rate_by_year.std()

print(
    f"Arrest rate standard deviation across years: "
    f"{arrest_std:.2f} percentage points"
)

arrest_range = arrest_rate_by_year.max() - arrest_rate_by_year.min()

print(
    f"Arrest rate range across years: "
    f"{arrest_range:.2f} percentage points"
)

