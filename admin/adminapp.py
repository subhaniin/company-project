from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import psycopg2
import csv
import io

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for flash messages
from flask import g, session, has_request_context

def get_connection():
    """
    Open a new DB connection and set the session-scoped audit.username variable
    so the trigger can read who performed the change.
    Note: If you later switch to a connection pool, set this variable each time
    you check out a connection from the pool.
    """
    conn = psycopg2.connect(
        dbname="company",
        user="postgres",
        password="Pqsql",
        host="localhost",
        port="5432"
    )
    try:
        # determine audit user: prefer g.audit_user (set in before_request),
        # then session['username'], else fallback to 'system'
        audit_user = None
        if has_request_context():
            audit_user = getattr(g, 'audit_user', None) or session.get('username') or session.get('user')
        audit_user = audit_user or 'adminWEBapp'

        with conn.cursor() as cur:
            cur.execute("SELECT set_config('audit.username', %s, true)", (str(audit_user),))
            # commit is not needed for set_config when is_local = true but safe to keep autocommit behavior
        return conn
    except Exception:
        # ensure conn closed on error
        conn.close()
        raise



@app.route('/', methods=['GET', 'POST'])
def index():
    query = "SELECT emp_id, emp_name, email, phone, dept_id, role_, salary, hire_date, status FROM employees"
    filters = []
    values = []

    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        name = request.form.get('name')
        dept = request.form.get('department')
        position = request.form.get('position')

        if emp_id:
            try:
                emp_id_val = int(emp_id)
                filters.append("emp_id = %s")
                values.append(emp_id)
            except ValueError:
                pass
        if name:
            filters.append("emp_name ILIKE %s")
            values.append(f"%{name}%")
        if dept:
            try:
                dept_id_val = int(dept)
                filters.append("dept_id = %s")
                values.append(dept)
            except ValueError:
                pass
        if position:
            filters.append("role_ ILIKE %s")
            values.append(f"%{position}%")

    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY emp_id"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, tuple(values))
    employees = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('index.html', employees=employees)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        emp_name = request.form.get('emp_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        dept_id = request.form.get('dept_id')
        role_ = request.form.get('role_')
        salary = request.form.get('salary')
        hire_date = request.form.get('hire_date')
        status = request.form.get('status')

        if not emp_name or not email:
            flash('Employee name and email are required')
            return redirect(url_for('add_employee'))

        conn = get_connection()
        cur = conn.cursor()
        insert_query = """
            INSERT INTO employees (emp_name, email, phone, dept_id, role_, salary, hire_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (emp_name, email, phone, dept_id, role_, salary, hire_date, status))
        conn.commit()
        cur.close()
        conn.close()
        flash('Employee added successfully')
        return redirect(url_for('index'))

    return render_template('add_employee.html')

@app.route('/edit_employee/<int:emp_id>', methods=['GET', 'POST'])
def edit_employee(emp_id):
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        emp_name = request.form.get('emp_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        dept_id = request.form.get('dept_id')
        role_ = request.form.get('role_')
        salary = request.form.get('salary')
        hire_date = request.form.get('hire_date')
        status = request.form.get('status')

        update_query = """
            UPDATE employees
            SET emp_name=%s, email=%s, phone=%s, dept_id=%s, role_=%s, salary=%s, hire_date=%s, status=%s
            WHERE emp_id=%s
        """
        cur.execute(update_query, (emp_name, email, phone, dept_id, role_, salary, hire_date, status, emp_id))
        conn.commit()
        cur.close()
        conn.close()
        flash('Employee updated successfully')
        return redirect(url_for('index'))
    else:
        # Retrieve the existing employee data
        cur.execute("SELECT emp_id, emp_name, email, phone, dept_id, role_, salary, hire_date, status FROM employees WHERE emp_id = %s", (emp_id,))
        emp = cur.fetchone()
        cur.close()
        conn.close()
        return render_template('edit_employee.html', emp=emp)


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
    writer.writerow(['ID', 'Employee Name', 'Email', 'Phone', 'Dept', 'Position', 'Salary', 'Hire Date', 'Status'])
    writer.writerows(employees)
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='employees.csv')

if __name__ == '__main__':
    app.run(port=5005,debug=True)