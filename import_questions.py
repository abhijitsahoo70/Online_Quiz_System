import sqlite3
import pandas as pd
import os

# Connect Database
conn = sqlite3.connect("quiz.db")

files = [
    "c_questions.csv",
    "python_questions.csv",
    "java_questions.csv",
    "dbms_questions.csv",
    "dsa_questions.csv",
    "aptitude_questions.csv"
]

for file in files:

    path = os.path.join("data", file)

    if os.path.exists(path):

        df = pd.read_csv(path)

        df.to_sql(
            "questions",
            conn,
            
            if_exists="append",
            index=False
        )

        print(file, "Imported Successfully")

    else:

        print(file, "Not Found")

conn.close()

print("All Questions Imported Successfully!")