import streamlit as st
import pandas as pd
from utils import *
import hmac
import streamlit as st


def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.

df = pd.read_excel("./sheets/base-file.xlsx")

# Create a button to upload a PDF file
st.write('### Neue Blutwertanalyse hochladen')
st.text("!! Wichtig !! Der Dateiname muss ein Datum mit diesem Format beinhalten: tt_mm_jjjj")
uploaded_file = st.file_uploader("Bitte PDF auswählen", type="pdf")
st.text("")
st.text("")

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    with col1:
        st.write("#### Dateiname")
        st.write(uploaded_file.name)
    with col2:
        st.write("#### Dateigröße")
        st.write(uploaded_file.size)
        
    # Save the uploaded file
    with open(f"./pdfs/{uploaded_file.name}", "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Extract the data from the PDF file
    with st.spinner("Extrahiere Daten..."):
        table = extract_data(uploaded_file)
    #md_table = table_to_markdown(table)
    st.success("Daten erfolgreich extrahiert! Analyse mit LLM wird unten gestartet...")
    st.text(table)
    st.text("")
    st.text("")
    st.divider()

    # Get the blood values from the base DataFrame
    blood_values = df["Datum"].tolist()
    
    with st.spinner('Inhalt wird mit LLM analysiert. Dies kann ein paar Minuten dauern...'):

        # Initialize the progress bar
        progress_bar = st.progress(0)
        
        # Get the date from the filename
        date = date_from_filename(str(uploaded_file.name))
        if not date: 
            st.warning("Kein Datum im Dateinamen gefunden. Bitte Datum mit Format tt_mm_jjjj im Dateinamen hochladen.")
            st.stop()
        
        # Create a dictionary to store the extracted data
        data = {
            date: []
        }
        for bv_idx, bv in enumerate(blood_values):
            # Update the progress bar
            progress = (bv_idx + 1) / len(blood_values)
            progress_bar.progress(progress)

            extracted_value = extract_value(table, bv)
            data[date].append(extracted_value)

        # Mark the progress bar as complete
        progress_bar.empty()
        
    st.success("Datei erfolgreich von LLM verarbeitet!")
    
    # Add the extracted data to the base DataFrame
    total_columns = len(df.columns)
    third_from_right_position = total_columns - 2
    column_names = df.columns.tolist()
    for entry in list(data.keys()):
        column_names.insert(third_from_right_position, entry)
        df.insert(third_from_right_position, entry, data[entry])

    # Clean up the column names and values
    df.columns = df.columns.astype(str).str.replace("00:00:00", "").str.replace("-", ".")
    df = df.replace("NaN", "")

    # Create a button to download the DataFrame as an Excel file
    st.write('## Download der Daten als Excel-Datei')
    
    df_xlsx = to_excel(df)
    st.download_button(
        label='📥 Download Current Result',
        data=df_xlsx ,
        file_name= 'gpt-modified-file.xlsx'
    )
    
    # Create a table to display the DataFrame
    st.write('### Vorschau')
    st.dataframe(data=df)