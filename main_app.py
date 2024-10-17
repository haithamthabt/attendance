from flask import Flask, render_template, request
import os
from utils import save_uploaded_file, read_and_clean_csv, process_dataframe, highlight_incomplete_rows, summarize_employee_data
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
                return display_details(df)

            elif action == 'attendance':
                return display_attendance(df)

            elif action == 'summary':
                return summary(df)

        else:
            return render_template('upload.html', error='Invalid file format. Please upload a CSV file.')

    return render_template('upload.html')

#----------------------------------------------------------------------------
# Helper function to display details for each user
def display_details(df):
    tables = {}
    for user_id, group in df.groupby('User ID'):
        user_table_html = group.to_html(classes='table table-striped', index=False)
        user_table_html = highlight_incomplete_rows(group, user_table_html)
        tables[user_id] = user_table_html
    return render_template('display.html', tables=tables, title="Records Details")

#----------------------------------------------------------------------------
# Helper function to display summarized attendance for each user
def display_attendance(df):
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

#----------------------------------------------------------------------------
# Summary route (called when 'summary' is selected)
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
            summary_df, total_working_hours_str = summarize_employee_data(group)

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
