import os
import pandas as pd

#--------------------------------------------------
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
    record_counts = df.groupby(['User ID', 'Date']).size()
    odd_record_days = record_counts[record_counts % 2 != 0]
    df['Incomplete'] = df.apply(
        lambda row: 'Yes' if (row['User ID'], row['Date']) in odd_record_days.index else 'No', axis=1
    )
    return df

#--------------------------------------------------
# Function to process the dataframe (combining record assignment and incomplete day marking)
def process_dataframe(df):
    df['Record Type'] = assign_record_type(df)
    df = mark_incomplete_days(df)
    return df

#--------------------------------------------------
# Helper function to calculate break time for each day
def calculate_break_time(day_data):
    break_time = pd.Timedelta(0)
    breaks = day_data[day_data['Record Type'].isin(['Break Start', 'Break End'])]
    for i in range(0, len(breaks), 2):
        if i + 1 < len(breaks):
            break_start = breaks.iloc[i]['DateTime']
            break_end = breaks.iloc[i + 1]['DateTime']
            break_time += break_end - break_start
    return break_time

#--------------------------------------------------
# Helper function to enforce the 30-minute break rule
def enforce_break_rule(break_time):
    allowed_break_time = pd.Timedelta(minutes=30)
    if break_time < allowed_break_time:
        return allowed_break_time
    else:
        return pd.Timedelta(minutes=round(break_time.total_seconds() / 60))

#--------------------------------------------------
# Helper function to calculate working hours (including clock-in adjustment for before 8:00 AM)
def calculate_working_hours(day_data, clock_in, clock_out, break_time):
    work_start_time = pd.Timestamp(year=clock_in.year, month=clock_in.month, day=clock_in.day, hour=8, minute=0)
    clock_in_for_calculation = clock_in if clock_in >= work_start_time else work_start_time
    working_hours = clock_out - clock_in_for_calculation - break_time
    return pd.Timedelta(minutes=round(working_hours.total_seconds() / 60))

#--------------------------------------------------
# Helper function to calculate and summarize data for each employee
def summarize_employee_data(group):
    summary_rows = []
    total_working_seconds = 0
    total_shortage_seconds = 0  # Initialize total shortage in seconds

    for date, day_data in group.groupby('Date'):
        actual_clock_in = day_data[day_data['Record Type'] == 'Clock In']['DateTime'].min()
        clock_out = day_data[day_data['Record Type'] == 'Clock Out']['DateTime'].max()
        day_of_week = pd.Timestamp(date).strftime('%A')

        break_time = calculate_break_time(day_data)
        break_time = enforce_break_rule(break_time)
        working_hours = calculate_working_hours(day_data, actual_clock_in, clock_out, break_time)

        capped_total_working_hours = min(working_hours + pd.Timedelta(minutes=30), pd.Timedelta(hours=8))
        total_working_seconds += capped_total_working_hours.total_seconds()

        formatted_break_time = f"{break_time.components.hours:02}:{break_time.components.minutes:02}"
        formatted_working_hours = f"{working_hours.components.hours:02}:{working_hours.components.minutes:02}"

        expected_working_hours = pd.Timedelta(hours=7, minutes=30)
        if working_hours < expected_working_hours:
            time_shortage = expected_working_hours - working_hours
            shortage_flag = f"Short by {time_shortage.components.hours}h {time_shortage.components.minutes}m"
            total_shortage_seconds += time_shortage.total_seconds()  # Add shortage to total
        else:
            shortage_flag = "No"

        summary_rows.append({
            'Date': f"{date} ({day_of_week})",
            'Clock In': actual_clock_in,
            'Clock Out': clock_out,
            'Break Time': formatted_break_time,
            'Working Hours': formatted_working_hours,
            'Shortage': shortage_flag
        })

    # Convert the summary rows to a DataFrame
    summary_df = pd.DataFrame(summary_rows)

    # Convert total working seconds back to hours and minutes for display
    total_hours = total_working_seconds // 3600
    total_minutes = (total_working_seconds % 3600) // 60
    total_working_hours_str = f"{int(total_hours)}h {int(total_minutes)}m"

    # Convert total shortage seconds to hours and minutes for display
    total_shortage_hours = total_shortage_seconds // 3600
    total_shortage_minutes = (total_shortage_seconds % 3600) // 60
    total_shortage_str = f"{int(total_shortage_hours)}h {int(total_shortage_minutes)}m"

    return summary_df, total_working_hours_str, total_shortage_str

#--------------------------------------------------
# Helper function to highlight incomplete rows
def highlight_incomplete_rows(df, df_html):
    row_html = df_html.splitlines()
    row_counter = 0
    for i, line in enumerate(row_html):
        if '<tr>' in line:
            if df.iloc[row_counter]['Incomplete'] == 'Yes':
                row_html[i] = line.replace('<tr>', '<tr class="incomplete-row">')
            row_counter += 1
    return '\n'.join(row_html)

#--------------------------------------------------
# Helper function to highlight Fridays
def highlight_fridays(df_html):
    row_html = df_html.splitlines()
    for i, line in enumerate(row_html):
        if 'Friday' in line:
            row_html[i] = line.replace('<tr>', '<tr class="friday-row">')
    return '\n'.join(row_html)

#--------------------------------------------------
# Helper function to drop variants of 'State' and 'Verify Mode' columns
def drop_column_variants(df):
    state_variants = ['State', 'state', 'STATE']
    verify_mode_variants = ['Verify Mode', 'VerifyMode', 'Verify_Mode', 'verifyMode', 'verifymode', 'Verifymode']

    for variant in state_variants:
        if variant in df.columns:
            df = df.drop(variant, axis=1)
            break

    for variant in verify_mode_variants:
        if variant in df.columns:
            df = df.drop(variant, axis=1)
            break

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