import pandas as pd

# Path to Excel file
excel_file = "D:\\Documents\\python_project\\3tire_app\\excel\\HMB.xlsx"

# Load the Excel file
df = pd.read_excel(excel_file)

# Convert to JSON
json_data = df.to_json(orient='records', indent=4)

# Save to JSON file
with open("HMB.json", "w") as f:
    f.write(json_data)

print("Conversion completed. JSON saved as output.json")
