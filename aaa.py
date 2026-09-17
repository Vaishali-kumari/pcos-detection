import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Load Dataset
df = pd.read_csv("C:\\Users\\HP\\Desktop\\ml_datasets\\pcos_prediction_dataset.csv")

print("\nInitial Data Types:\n", df.dtypes)

# Handle Missing Values
df.fillna(df.select_dtypes(include=['number']).median(), inplace=True)
for col in df.select_dtypes(include=['object']).columns:
    df[col] = df[col].fillna(df[col].mode()[0])

# Encode Categorical Columns
label_encoders = {}

binary_columns = ['Hirsutism', 'Acne Severity', 'Menstrual Regularity', 'Family History of PCOS']
for col in binary_columns:
    if col in df.columns:
        df[col] = df[col].map({'Yes': 1, 'No': 0})

categorical_columns = ['Country', 'Urban/Rural', 'Socioeconomic Status', 'Awareness of PCOS', 'Ethnicity']
for col in categorical_columns:
    if col in df.columns:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        label_encoders[col] = le

if 'BMI' in df.columns and df['BMI'].dtype == 'object':
    le_bmi = LabelEncoder()
    df['BMI'] = le_bmi.fit_transform(df['BMI'])
    label_encoders['BMI'] = le_bmi

X = df.drop(columns=['Diagnosis'])
y = df['Diagnosis']

# Ensure numeric types
X = X.apply(pd.to_numeric, errors='coerce')

# Handle NaN & Inf values safely
X.replace([np.inf, -np.inf], np.nan, inplace=True)
X.fillna(X.median(numeric_only=True), inplace=True)
X = X.dropna(axis=1, how='all')  # Drop any all-NaN columns

# Final checks with diagnostics
print("\nChecking for problematic values before scaling...")
print("Columns with NaN values:\n", X.columns[X.isna().any()].tolist())
print("Columns with infinite values:\n", X.columns[np.isinf(X).any()].tolist())
print("Any total NaN or infinite?", np.isnan(X.values).any() or np.isinf(X.values).any())

# Assertions (will stop execution if still bad)
assert not X.isna().values.any(), "NaNs still exist in X"
assert not np.isinf(X.values).any(), "Infs still exist in X"

# Normalize Data
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Train Model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Predictions & Evaluation
y_pred = model.predict(X_test)

print("\nModel Evaluation:")
print("Accuracy:", accuracy_score(y_test, y_pred))
print("Classification Report:\n", classification_report(y_test, y_pred))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))

# Save Model and Tools
joblib.dump(model, 'pcos_model.pkl')
joblib.dump(label_encoders, 'label_encoders.pkl')
joblib.dump(scaler, 'scaler.pkl')

print("\nModel and preprocessing objects saved successfully!")
