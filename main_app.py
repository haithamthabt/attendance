from flask import Flask, render_template, request
import os
from utils import save_uploaded_file, read_and_clean_csv, process_dataframe, highlight_incomplete_rows

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

            action = request.form.get('action')

            if action == 'details':
                # Group by User ID and create a table for each user
                tables = {}
                for user_id, group in df.groupby('User ID'):
                    user_table_html = group.to_html(classes='table table-striped', index=False)
                    user_table_html = highlight_incomplete_rows(group, user_table_html)
                    tables[user_id] = user_table_html

                # Pass the grouped tables to the template
                return render_template('display.html', tables=tables)

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

                return render_template('display.html', tables=tables)
        else:
            return render_template('upload.html', error='Invalid file format. Please upload a CSV file.')

    return render_template('upload.html')


if __name__ == '__main__':
    app.run(debug=True)
