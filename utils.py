# Standard library imports
import base64
import json
import os
import re
import io

# Third-party library imports
import requests
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_random_exponential
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import streamlit as st

# Pillow (PIL) imports
from PIL import Image

# PyMuPDF import
import fitz

# pandas import
import pandas as pd

# tqdm import
from tqdm.auto import tqdm

# BytesIO import
from io import BytesIO

# OpenAI API Key
api_key = st.secrets["mistral_api_key"]

# Azure Document Intelligence credentials
endpoint = st.secrets["az-endpoint"]
az_api_key = st.secrets["az-api-key"]

def pdf_to_img(pdf_path, page_num, dpi=300, output_path=None):
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]

    pix = page.get_pixmap(dpi=dpi)
    if pix.n < 8:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)

    if output_path:
        img.save(output_path)

    return img

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def extract_data(pdf_path):
    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(az_api_key)
    )

    poller = document_analysis_client.begin_analyze_document("prebuilt-layout", pdf_path)
    result = poller.result()

    tables_content = []

    for table_idx, table in enumerate(result.tables):
        # tables_content.append("Table # {} has {} rows and {} columns\n".format(
        #     table_idx, table.row_count, table.column_count
        # ))

        row_contents = []
        for cell in table.cells:
            # Add the cell content to the current row
            row_contents.append(cell.content.encode("utf-8").decode())
            if cell.column_index == table.column_count - 1:
                # If this is the last cell in the row, add the row to the table content
                tables_content.append('\t'.join(row_contents) + '\n')
                row_contents = []  # Reset the row content for the next row
        if row_contents:
            # If the last row of the table does not have cells in all columns, add it to the table content
            tables_content.append('\t'.join(row_contents) + '\n')

    unified_string = ''.join(tables_content)
    print(unified_string)
    return unified_string

def table_to_markdown(table_str):
    # Read the table into a pandas DataFrame, using whitespace as the delimiter
    df = pd.read_csv(io.StringIO(table_str), sep="\s+", header=0)

    # Convert the DataFrame to a markdown-formatted string
    markdown_table = df.to_markdown(index=False)

    return markdown_table


def date_from_filename(filename):
        # Define the regular expression pattern
    pattern = r"(\d{2})_(\d{2})_(\d{4})"

    # Search for the pattern in the filename
    match = re.search(pattern, filename)

    # If a match is found, extract the groups and format the date
    if match:
        day, month, year = match.groups()
        formatted_date = f"{day}.{month}.{year}"
        print(formatted_date)
        return formatted_date
    else:
        print("No date found in the filename")
    


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def extract_value(text, value):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {
                "role": "user",
                "content": """
Aufgabenbeschreibung:
Du bist ein Experte für die Auswertung von Blutwertanalysen.
Deine Aufgabe ist es, einen Wert in einer Tabelle zu durchsuchen.
Werte aus dem Referenzbereich sind nicht relevant.
Es ist extrem wichtig das die gefundenen Werte richtig sind!

Format:
Gebe NUR den Wert als Zahl aus und sonst nichts. Falls Du den Wert nicht finden kannst, gebe ausschließlich ein 'NaN' aus.
Dein Output sollte also entweder so aussehen: 00
oder so: NaN

Hälst Du dieses Format nicht ein, werde ich deinen Output NICHT verarbeiten!
Neben der Zahl sollte niemals und unter keinen Umständen weiterer Text oder eine Beschreibung hinzugefügt werden.
                """.strip()
            },
            {
                "role": "user",
                "content": f"<<< Durchsuche diese Tabelle nach dem genannten Wert: {text} >>>"
            },
            {
                "role": "user",
                "content": f"<<< Suche den folgenden Wert: {value} >>>"
            }
        ],
        "max_tokens": 5,
        "temperature": 0.0
    }

    response = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, data=json.dumps(payload))
    response.raise_for_status()  # Raise an exception for HTTP errors
    response_object = response.json()
    print(response_object)
    answer = response_object["choices"][0]["message"]["content"]
    if "NaN" in answer: 
        return "NaN"
    return answer

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    format1 = workbook.add_format({'num_format': '0.00'}) 
    worksheet.set_column('A:A', None, format1)  
    writer.close()
    processed_data = output.getvalue()
    return processed_data