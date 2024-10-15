import os
import pandas as pd

# Helper function to save the uploaded file
def save_uploaded_file(file, upload_folder):
    filepath = os.path.join(upload_folder, file.filename)
    file.save(filepath)
    return filepath

#--------------------------------------------------

# Helper function to read and clean CSV data
def read_and_clean_csv(filepath):
    df = pd.read_csv(filepath)

    # Drop unnecessary columns
    df = drop_column_variants(df)  # Drop variations of 'State' and 'Verify Mode'

    # Convert 'DateTime' to datetime type
    df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')

    # Extract date and time
    df['Date'] = df['DateTime'].dt.date
    df['Time'] = df['DateTime'].dt.time

    # Sort by User ID, Date, and Time
    df = df.sort_values(by=['User ID', 'Date', 'Time'])
    return df

#--------------------------------------------------

# Function to assign record types
def assign_record_type(df):
    record_types = []
    for _, group in df.groupby(['User ID', 'Date']):
        group = group.reset_index(drop=True)
        group_size = len(group)
        for i in range(group_size):
            if i == 0:
                record_types.append('Clock In')
            elif i == group_size - 1:
                record_types.append('Clock Out')
            elif i % 2 == 1:
                record_types.append('Break Start')
            else:
                record_types.append('Break End')
    return record_types

#--------------------------------------------------

# Function to mark incomplete days
def mark_incomplete_days(df):
    # Group data by User ID and Date and count records
    record_counts = df.groupby(['User ID', 'Date']).size()

    # Find days with odd number of records
    odd_record_days = record_counts[record_counts % 2 != 0]

    # Mark incomplete days
    df['Incomplete'] = df.apply(
        lambda row: 'Yes' if (row['User ID'], row['Date']) in odd_record_days.index else 'No', axis=1
    )
    return df

#--------------------------------------------------

# New function that processes the dataframe by calling both assign_record_type and mark_incomplete_days
def process_dataframe(df):
    df['Record Type'] = assign_record_type(df)
    df = mark_incomplete_days(df)
    return df

#--------------------------------------------------

# Helper function to modify HTML and add custom CSS classes
def highlight_incomplete_rows(df, df_html):
    # Split the HTML into lines
    row_html = df_html.splitlines()

    # Identify all <tr> lines in the HTML table
    row_counter = 0
    for i, line in enumerate(row_html):
        if '<tr>' in line:  # Look for the start of each row in the HTML
            if df.iloc[row_counter]['Incomplete'] == 'Yes':  # Check if the corresponding DataFrame row is marked as 'Yes'
                # Add the class to the <tr> tag
                row_html[i] = line.replace('<tr>', '<tr class="incomplete-row">')
            row_counter += 1  # Move to the next row in the DataFrame

    # Join the modified HTML lines back together
    return '\n'.join(row_html)

#--------------------------------------------------

#--------------------------------------------------
def highlight_fridays(df_html):
    row_html = df_html.splitlines()
    for i, line in enumerate(row_html):
        if 'Friday' in line:  # Identify rows that contain 'Friday'
            row_html[i] = line.replace('<tr>', '<tr class="friday-row">')  # Add class for styling
    return '\n'.join(row_html)

#--------------------------------------------------
def drop_column_variants(df):
    # Define possible variations for 'State' and 'Verify Mode'
    state_variants = ['State', 'state', 'STATE']
    verify_mode_variants = ['Verify Mode', 'VerifyMode', 'VERIFyMODE', 'Verify_Mode', 'verifyMode', 'verifymode', 'Verifymode']

    # Drop 'State' column variations if they exist
    for variant in state_variants:
        if variant in df.columns:
            df = df.drop(variant, axis=1)
            break  # Stop once a matching column is found and dropped

    # Drop 'Verify Mode' column variations if they exist
    for variant in verify_mode_variants:
        if variant in df.columns:
            df = df.drop(variant, axis=1)
            break  # Stop once a matching column is found and dropped

    return df


#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------

#--------------------------------------------------


