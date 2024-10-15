from flask import Flask, render_template, request
import os
from utils import save_uploaded_file, read_and_clean_csv, process_dataframe, highlight_incomplete_rows, highlight_fridays
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
            summary_rows = []
            total_working_seconds = 0  # Initialize total working time in seconds for this employee

            for date, day_data in group.groupby('Date'):
                actual_clock_in = day_data[day_data['Record Type'] == 'Clock In']['DateTime'].min()
                clock_out = day_data[day_data['Record Type'] == 'Clock Out']['DateTime'].max()

                # Get the day of the week for the date
                day_of_week = pd.Timestamp(date).strftime('%A')

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

                # Enforce 30 minutes break rule
                allowed_break_time = pd.Timedelta(minutes=30)
                if break_time < allowed_break_time:
                    break_time = allowed_break_time

                # Calculate actual working hours (Clock Out - Adjusted Clock In - Break Time)
                working_hours = clock_out - clock_in_for_calculation - break_time

                # Round working hours and break time to nearest minute to avoid floating-point errors
                working_hours = pd.Timedelta(minutes=round(working_hours.total_seconds() / 60))
                break_time = pd.Timedelta(minutes=round(break_time.total_seconds() / 60))

                # Cap the total working hours for the day at 8 hours
                capped_total_working_hours = min(working_hours + allowed_break_time, pd.Timedelta(hours=8))

                # Add the capped total working hours to the total in seconds
                total_working_seconds += capped_total_working_hours.total_seconds()

                # Format the break time and working hours for display
                formatted_break_time = f"{break_time.components.hours:02}:{break_time.components.minutes:02}"
                formatted_working_hours = f"{working_hours.components.hours:02}:{working_hours.components.minutes:02}"

                # Determine shortage: if working hours < 7.5 hours
                expected_working_hours = pd.Timedelta(hours=7, minutes=30)
                if working_hours < expected_working_hours:
                    time_shortage = expected_working_hours - working_hours
                    shortage_flag = f"Short by {time_shortage.components.hours}h {time_shortage.components.minutes}m"
                else:
                    shortage_flag = "No"

                # Add the summary row for this day
                summary_rows.append({
                    'Date': f"{date} ({day_of_week})",  # Display date and day of the week
                    'Clock In': actual_clock_in,
                    'Clock Out': clock_out,
                    'Break Time': formatted_break_time,
                    'Working Hours': formatted_working_hours,
                    'Shortage': shortage_flag
                })

            # Convert the summary rows to a DataFrame
            summary_df = pd.DataFrame(summary_rows)

            # Convert total working seconds back to hours and minutes for display
            total_hours = total_working_seconds // 3600  # Total hours
            total_minutes = (total_working_seconds % 3600) // 60  # Total remaining minutes

            total_working_hours_str = f"{int(total_hours)}h {int(total_minutes)}m"

            # Generate the HTML for the employee's summary
            summary_df_html = summary_df.to_html(classes='table table-striped', index=False)

            # Append total working hours to the bottom of the table
            summary_df_html += f"<tfoot><tr><td colspan='4'><strong>Total Working Hours:</strong></td><td colspan='2'>{total_working_hours_str}</td></tr></tfoot>"

            # Add to the user-specific table
            tables[user_id] = summary_df_html

        # Pass the tables to the template
        return render_template('summary.html', tables=tables, has_incomplete_records=False)

    except Exception as e:
        # If any error occurs, display the error message
        return f"Error displaying the summary: {str(e)}"



#----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)
