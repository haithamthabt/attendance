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
    df = df.drop(['State', 'Verify Mode'], axis=1)

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
def calculate_working_hours_and_breaks(df):
    # Ensure the 'DateTime' column is in datetime format
    df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')

    # Create a new DataFrame with all dates between the first and last date
    all_dates = pd.date_range(start=df['DateTime'].min().date(), end=df['DateTime'].max().date())

    # Initialize a summary DataFrame
    summary_df = pd.DataFrame(all_dates, columns=['Date'])

    # Add day of the week
    summary_df['DayOfWeek'] = summary_df['Date'].dt.day_name()

    # Mark Fridays
    summary_df['IsFriday'] = summary_df['DayOfWeek'] == 'Friday'

    # Group the original DataFrame by 'User ID' and 'Date' to calculate working hours and breaks
    df['Date'] = df['DateTime'].dt.date  # Extract the date
    grouped = df.groupby(['User ID', 'Date'])

    working_hours = []
    break_times = []

    # Calculate working hours and breaks for each date
    for date in all_dates:
        day_data = df[df['Date'] == date.date()]

        if len(day_data) > 0:
            # Assume first record is Clock In and last is Clock Out
            first_clock_in = day_data['DateTime'].min()
            last_clock_out = day_data['DateTime'].max()

            # Calculate total working hours
            total_work = last_clock_out - first_clock_in

            # Only calculate break time if 'Record Type' exists in the subset
            if 'Record Type' in day_data.columns:
                break_time = day_data[(day_data['Record Type'] == 'Break Start') | (day_data['Record Type'] == 'Break End')]
                total_break = pd.Timedelta(0)  # Initialize break time

                # Iterate through break start and end pairs
                for i in range(0, len(break_time), 2):
                    if i + 1 < len(break_time):
                        total_break += break_time.iloc[i + 1]['DateTime'] - break_time.iloc[i]['DateTime']
            else:
                total_break = pd.Timedelta(0)  # No break time if 'Record Type' is missing

            working_hours.append(total_work)
            break_times.append(total_break)
        else:
            working_hours.append(pd.NaT)  # No data for this day
            break_times.append(pd.NaT)

    # Add the calculated working hours and break times to the summary
    summary_df['WorkingHours'] = working_hours
    summary_df['BreakTime'] = break_times

    return summary_df


#--------------------------------------------------
def highlight_fridays(df_html):
    row_html = df_html.splitlines()
    for i, line in enumerate(row_html):
        if 'Friday' in line:  # Identify rows that contain 'Friday'
            row_html[i] = line.replace('<tr>', '<tr class="friday-row">')  # Add class for styling
    return '\n'.join(row_html)

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

#--------------------------------------------------


