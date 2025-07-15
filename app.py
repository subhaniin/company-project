from flask import Flask, render_template, request, send_file
import psycopg2
import csv
import io

app = Flask(__name__)

def get_connection():
    return psycopg2.connect(
        dbname="company",
        user="postgres",
        password="Pqsql",
        host="localhost",
        port="5432"
    )

@app.route('/', methods=['GET', 'POST'])
def index():
    query = "SELECT * FROM employees"
    filters = []
    values = []

    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        name = request.form.get('name')
        dept = request.form.get('department')
        position = request.form.get('position')

        if emp_id:
            filters.append("emp_id = %s")
            values.append(emp_id)
        if name:
            filters.append("(first_name || ' ' || last_name) ILIKE %s")
            values.append(f"%{name}%")

        if dept:
            filters.append("department ILIKE %s")
            values.append(f"%{dept}%")
        if position:
            filters.append("position ILIKE %s")
            values.append(f"%{position}%")

    if filters:
        query += " WHERE " + " AND ".join(filters)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, tuple(values))
    employees = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('index.html', employees=employees)

@app.route('/export_csv')
def export_csv():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees")
    employees = cur.fetchall()
    cur.close()
    conn.close()

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Dept', 'Position', 'Salary', 'Hire Date', 'Status'])
    writer.writerows(employees)
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='employees.csv')

if __name__ == '__main__':
    app.run(debug=True)
