import pandas as pd

df = pd.DataFrame({'Name': ['John', 'Jane', 'Jack'], 'Age': [20, 25, 30]})

print(df['Age'].mean())