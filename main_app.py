from flask import Flask, render_template, request
import os
from utils import save_uploaded_file, read_and_clean_csv, process_dataframe, highlight_incomplete_rows, calculate_working_hours_and_breaks, highlight_fridays
import pandas as pd
app = Flask(__name__)

# Ensure the upload folder exists
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('upload.html', error='No file part in the request.')

        file = request.files['file']
        if file.filename == '':
            return render_template('upload.html', error='No selected file.')

        if file and file.filename.endswith('.csv'):
            filepath = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
            df = read_and_clean_csv(filepath)
            df = process_dataframe(df)
            print(df.columns)  # Check if 'Record Type' is in the columns

            action = request.form.get('action')

            if action == 'details':
                # Group by User ID and create a table for each user
                tables = {}
                for user_id, group in df.groupby('User ID'):
                    user_table_html = group.to_html(classes='table table-striped', index=False)
                    user_table_html = highlight_incomplete_rows(group, user_table_html)
                    tables[user_id] = user_table_html

                # Pass the grouped tables to the template
                return render_template('display.html', tables=tables, title="Records Details")

            elif action == 'attendance':
                # Summarize data
                summary_df = df.groupby(['User ID', 'Date']).agg({
                    'DateTime': ['min', 'max'],
                    'Record Type': 'count',
                    'Incomplete': 'first'
                }).reset_index()

                summary_df.columns = ['User ID', 'Date', 'First Clock In', 'Last Clock Out', 'Number of Records', 'Incomplete']

                tables = {}
                for user_id, group in summary_df.groupby('User ID'):
                    user_table_html = group.to_html(classes='table table-striped', index=False)
                    user_table_html = highlight_incomplete_rows(group, user_table_html)
                    tables[user_id] = user_table_html

                return render_template('display.html', tables=tables, title="Attendance")
            elif action == 'summary':
                    # Redirect to the summary route, passing the file data
                    return summary(df)
        else:
            return render_template('upload.html', error='Invalid file format. Please upload a CSV file.')

    return render_template('upload.html')


#----------------------------------------------------------------------------
@app.route('/summary', methods=['POST'])
def summary(df=None):
    print("Summary route triggered")

    if df is None:
        return "Error: No DataFrame passed to the summary function."

    try:
        # Check if any record has 'Incomplete' marked as 'Yes'
        if (df['Incomplete'] == 'Yes').any():
            return render_template('summary.html', has_incomplete_records=True)

        # Initialize the summary table for each employee
        tables = {}
        for user_id, group in df.groupby('User ID'):
            # Create a summary for each date
            summary_rows = []
            for date, day_data in group.groupby('Date'):
                # Identify the first Clock In and last Clock Out
                actual_clock_in = day_data[day_data['Record Type'] == 'Clock In']['DateTime'].min()
                clock_out = day_data[day_data['Record Type'] == 'Clock Out']['DateTime'].max()

                # Adjust Clock In for calculation purposes only if it's before 8:00 AM
                work_start_time = pd.Timestamp(year=actual_clock_in.year, month=actual_clock_in.month, day=actual_clock_in.day, hour=8, minute=0)
                clock_in_for_calculation = actual_clock_in if actual_clock_in >= work_start_time else work_start_time

                # Calculate total break time (sum of all breaks)
                break_time = pd.Timedelta(0)
                breaks = day_data[day_data['Record Type'].isin(['Break Start', 'Break End'])]
                for i in range(0, len(breaks), 2):
                    if i + 1 < len(breaks):  # Ensure there is a pair (Break Start followed by Break End)
                        break_start = breaks.iloc[i]['DateTime']
                        break_end = breaks.iloc[i + 1]['DateTime']
                        break_time += break_end - break_start

                # Calculate total working hours (Clock Out - Adjusted Clock In - Break Time)
                working_hours = clock_out - clock_in_for_calculation - break_time

                # Format the break time and working hours to HH:MM
                formatted_break_time = f"{break_time.components.hours:02}:{break_time.components.minutes:02}"
                formatted_working_hours = f"{working_hours.components.hours:02}:{working_hours.components.minutes:02}"

                # Add the summary row for this day
                summary_rows.append({
                    'Date': date,
                    'Clock In': actual_clock_in,  # Display the actual clock-in time
                    'Clock Out': clock_out,
                    'Break Time': formatted_break_time,
                    'Working Hours': formatted_working_hours
                })

            # Convert the summary rows to a DataFrame and generate HTML
            summary_df = pd.DataFrame(summary_rows)
            summary_df_html = summary_df.to_html(classes='table table-striped', index=False)
            tables[user_id] = summary_df_html

        # Pass the tables to the template
        return render_template('summary.html', tables=tables, has_incomplete_records=False)

    except Exception as e:
        # If any error occurs, display the error message
        return f"Error displaying the summary: {str(e)}"


#----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)
