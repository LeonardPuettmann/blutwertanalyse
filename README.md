### Overview
A simple streamlit application to analyze medical values from PDF files and insert them into an Excel spreadsheet to save time. 
For the data extraction, Azure Document Intelligence is use. The individual values are than extracted by a LLM and inserted to a DataFrame, which can then be downloaded as an Excel spreadsheet.

### Tools used
- Azure Document Intelligence (Data extraction from PDF)
- mistral-small Large Language Model from Mistral AI(Data processing)
- Streamlit for the UI
- Python

