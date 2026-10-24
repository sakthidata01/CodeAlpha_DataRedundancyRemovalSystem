
from pathlib import Path
import sqlite3
import re
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px


# --------------------------------------------------
# FILE PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "students.db"
CSS_FILE = BASE_DIR / "style.css"
BACKUP_DIR = BASE_DIR / "database_backups"


# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="Student Manager | CodeAlpha",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# LOAD EXISTING CSS + SMALL LAYOUT OVERRIDES
# --------------------------------------------------

def load_css():
    """Keep the existing project theme and improve the new layout."""
    if CSS_FILE.exists():
        css = CSS_FILE.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        /* Compact input labels and form spacing */
        div[data-testid="stTextInput"] {
            margin-bottom: 0.45rem;
        }

        div[data-testid="stSelectbox"] {
            margin-bottom: 0.35rem;
        }

        div[data-testid="stForm"] {
            padding: 14px;
            border-radius: 16px;
        }

        /* Three aligned dashboard sections */
        .protection-card {
            box-sizing: border-box;
            min-height: 265px;
            height: 100%;
            padding: 18px 14px;
            border-radius: 18px;
            border: 1px solid #C4CE91;
            background: linear-gradient(145deg, #F0F2CE, #E5EAB9);
            color: #352F22;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .protection-card .shield {
            font-size: 38px;
            margin-bottom: 7px;
        }

        .protection-card h3 {
            color: #283719;
            font-family: Georgia, serif;
            font-size: 19px;
            line-height: 1.25;
            margin: 5px 0 12px 0;
        }

        .protection-card p {
            font-size: 14px;
            line-height: 1.55;
            margin: 0;
        }

        .protection-card .ornament {
            color: #A56A20;
            margin-top: 14px;
            font-size: 12px;
        }

        .book-panel {
            box-sizing: border-box;
            min-height: 265px;
            height: 100%;
            padding: 12px;
            border-radius: 18px;
            border: 1px solid #D6A64F;
            background: linear-gradient(145deg, #FFF0D3, #E9C47E);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        .book-panel .book-art {
            font-size: 76px;
            line-height: 1.2;
        }

        .book-panel .cap-art {
            font-size: 42px;
            line-height: 1.2;
        }

        .book-panel h3 {
            color: #5B4033;
            font-family: Georgia, serif;
            font-size: 17px;
            margin: 8px 0 3px 0;
        }

        .book-panel p {
            color: #5B4033;
            font-size: 12px;
            margin: 0;
        }

        /* Let Streamlit columns adapt on smaller screens */
        @media (max-width: 900px) {
            .protection-card,
            .book-panel {
                min-height: 220px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def connect_db():
    conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------
# CREATE / UPDATE DATABASE SAFELY
# --------------------------------------------------

def create_database():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                department TEXT NOT NULL,
                academic_year TEXT NOT NULL DEFAULT 'Not set',
                added_on TEXT NOT NULL DEFAULT ''
            )
        """)

        # Check the existing database columns.
        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(students)"
            ).fetchall()
        }

        if "academic_year" not in columns:
            conn.execute("""
                ALTER TABLE students
                ADD COLUMN academic_year TEXT NOT NULL DEFAULT 'Not set'
            """)

        if "added_on" not in columns:
            conn.execute("""
                ALTER TABLE students
                ADD COLUMN added_on TEXT NOT NULL DEFAULT ''
            """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_stats (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            INSERT OR IGNORE INTO app_stats (key, value)
            VALUES ('duplicate_attempts', 0)
        """)


# --------------------------------------------------
# ADD STUDENT AND PREVENT DUPLICATES
# --------------------------------------------------

def add_student(name, email, department, academic_year):
    name = name.strip()
    email = email.strip().lower()

    if not name:
        return False, "Please enter the student's name."

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Please enter a valid email address."

    valid_years = [
        "1st Year",
        "2nd Year",
        "3rd Year",
        "4th Year",
    ]

    if academic_year not in valid_years:
        return False, "Please select a valid academic year."

    
    try:
        with connect_db() as conn:
            # Check whether this email already exists.
            existing = conn.execute(
                "SELECT id FROM students WHERE LOWER(TRIM(email)) = ?",
                (email,),
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE app_stats
                    SET value = value + 1
                    WHERE key = 'duplicate_attempts'
                """)
                return (
                    False,
                    "That email address is already registered."
                )

            conn.execute("""
                INSERT INTO students
                    (name, email, department, academic_year, year, added_on)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                email,
                department,
                academic_year,
                academic_year,
                datetime.now().strftime("%d %b %Y, %I:%M %p"),
            ))

        return True, f"Student {name} was added successfully."

    except sqlite3.IntegrityError as error:
        return False, f"Database integrity error: {error}"
# --------------------------------------------------
# GET STUDENT RECORDS
# --------------------------------------------------
def get_students(search=""):
    with connect_db() as conn:
        if search.strip():
            term = f"%{search.strip()}%"

            rows = conn.execute("""
                SELECT id, name, email, department,
                       academic_year, added_on
                FROM students
                WHERE name LIKE ?
                   OR email LIKE ?
                   OR department LIKE ?
                   OR academic_year LIKE ?
                ORDER BY id ASC
            """, (term, term, term, term)).fetchall()

        else:
            rows = conn.execute("""
                SELECT id, name, email, department,
                       academic_year, added_on
                FROM students
                ORDER BY id ASC
            """).fetchall()

    return [dict(row) for row in rows]

# --------------------------------------------------
# GET DUPLICATE COUNT
# --------------------------------------------------

def get_duplicate_count():
    with connect_db() as conn:
        row = conn.execute(
            """
            SELECT value
            FROM app_stats
            WHERE key = 'duplicate_attempts'
            """
        ).fetchone()

    return int(row[0]) if row else 0


# --------------------------------------------------
# DELETE A STUDENT
# --------------------------------------------------

def delete_student(student_id):
    with connect_db() as conn:
        conn.execute(
            "DELETE FROM students WHERE id = ?",
            (student_id,),
        )


def update_student(student_id, name, email, department, academic_year):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE students
            SET name = ?, email = ?, department = ?, academic_year = ?
            WHERE id = ?
            """,
            (name, email, department, academic_year, student_id),
        )
        conn.commit()

        if cursor.rowcount == 0:
            return False, "Student record not found."

        return True, "Student record updated successfully."

    except sqlite3.IntegrityError:
        return False, "This email is already used by another student."

    finally:
        conn.close()



# --------------------------------------------------
# DATABASE BACKUP
# --------------------------------------------------

def create_database_backup():
    """Create a timestamped backup using SQLite's backup API."""
    if not DB_FILE.exists():
        raise FileNotFoundError("The students.db database was not found.")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"students_backup_{timestamp}.db"

    with sqlite3.connect(str(DB_FILE)) as source:
        with sqlite3.connect(str(backup_path)) as destination:
            source.backup(destination)

    return backup_path


# --------------------------------------------------
# COMPACT ADD STUDENT FORM + PROTECTION + BOOK
# --------------------------------------------------

def show_add_form():
    form_col, protection_col, book_col = st.columns(
        [1.55, 0.95, 0.90],
        gap="medium",
        vertical_alignment="center",
    )

    # LEFT: compact student form
    with form_col:
        st.markdown(
            '<div class="section-heading">📝 &nbsp; Add a student</div>',
            unsafe_allow_html=True,
        )

        with st.form("student_form", clear_on_submit=True):
            # Name and email occupy the same row.
            name_col, email_col = st.columns(2, gap="small")

            with name_col:
                name = st.text_input(
                    "👤 Full name",
                    placeholder="Full name",
                )

            with email_col:
                email = st.text_input(
                    "📧 Email address",
                    placeholder="Email address",
                )

            # Department and academic year occupy the next row.
            dept_col, year_col = st.columns(2, gap="small")

            with dept_col:
                department = st.selectbox(
                    "🏛️ Department",
                    [
                        "Information Technology",
                        "Computer Science",
                        "Electronics",
                        "Electrical",
                        "Mechanical",
                        "Civil",
                        "Other",
                    ],
                )

            with year_col:
                academic_year = st.selectbox(
                    "🎓 Academic Year",
                    options=[
                        "1st Year",
                        "2nd Year",
                        "3rd Year",
                        "4th Year",
                    ],
                    index=0,
                    key="academic_year_select",
                )
            
            submitted = st.form_submit_button(
                "➕  Add student",
                use_container_width=True,
            )

        if submitted:
            ok, message = add_student(
                name,
                email,
                department,
                academic_year,
            )

            if ok:
                st.success(f"✅ {message}")
                st.rerun()
            else:
                st.error(f"⚠️ {message}")

    # MIDDLE: short duplicate-protection card
    with protection_col:
        st.markdown(
            """
            <div class="protection-card">
                <div class="shield">🛡️</div>
                <h3>Duplicate Protection</h3>
                <p>
                    Each email can be registered once.
                    Duplicates are checked automatically,
                    even when letter casing differs.
                </p>
                <div class="ornament">✦ DATA INTEGRITY ✦</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # RIGHT: compact book and graduation-cap illustration.
    # This stays in the same row; no second book card is added below.
    
   
    # RIGHT: Test book illustration
    with book_col:
        st.markdown(
            """
            <div style="background-color:#FFF0D3;
                        border:2px solid #D6A64F;
                        border-radius:18px;
                        padding:25px 10px;
                        text-align:center;
                        min-height:260px;">
                <div style="font-size:55px;">🎓</div>
                <div style="font-size:75px;">📚</div>
                <h3 style="color:#5B4033;">Learn. Grow. Succeed.</h3>
                <p style="color:#5B4033;">Every student has a story.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )



# --------------------------------------------------
# DISPLAY STUDENT RECORDS + CSV EXPORT
# --------------------------------------------------


def render_records(show_delete=False):
    search = st.text_input(
        "🔍 Search records",
        placeholder="Search by name, email, department or year...",
        key="record_search",
    )

    records = get_students(search)

    if not records:
        st.info("📭 No student records found. Add a student to get started.")
        return

    display_rows = [
        {
            "🆔 ID": row["id"],
            "👤 Full Name": row["name"],
            "📧 Email Address": row["email"],
            "🏛️ Department": row["department"],
            "🎓 Academic Year": (
                row["academic_year"]
                if row["academic_year"]
                and str(row["academic_year"]).strip()
                and str(row["academic_year"]).strip().lower()
                not in ("none", "not set")
                else "Not set"
            ),
            "📅 Added On": row["added_on"],
        }
        for row in records
    ]

    # Keep CSV export
    csv_data = (
        pd.DataFrame(display_rows)
        .to_csv(index=False)
        .encode("utf-8-sig")
    )

    st.download_button(
        "📥 Download records as CSV",
        data=csv_data,
        file_name="student_records.csv",
        mime="text/csv",
        key="download_student_records",
    )

    # Table headings
    st.markdown("### 📋 Student Records")

    with st.container(key="records_table"):
        header = st.columns([0.45, 1.3, 1.7, 1.1, 0.9, 1.0, 1.2])

    headings = [
        "ID",
        "Full Name",
        "Email",
        "Department",
        "Year",
        "Added On",
        "Actions",
    ]

    for col, heading in zip(header, headings):
        col.markdown(f"**{heading}**")

    # Each student gets their own row and action buttons
    for row in records:
        cols = st.columns([0.45, 1.3, 1.7, 1.1, 0.9, 1.0, 1.2])

        academic_year = (
            row["academic_year"]
            if row["academic_year"]
            and str(row["academic_year"]).strip()
            and str(row["academic_year"]).strip().lower()
            not in ("none", "not set")
            else "Not set"
        )

        cols[0].write(row["id"])
        cols[1].write(row["name"])
        cols[2].write(row["email"])
        cols[3].write(row["department"])
        cols[4].write(academic_year)
        cols[5].write(row["added_on"])

        with cols[6]:
            edit_col, delete_col = st.columns(2, gap="small")

            if edit_col.button(
                "Edit",
                key=f"edit_student_{row['id']}",
                help="Edit this student",
            ):
                st.session_state["editing_student_id"] = row["id"]
                st.session_state.pop("confirm_delete_id", None)
                st.rerun()

            if delete_col.button(
                "Delete",
                key=f"delete_student_{row['id']}",
                help="Delete this student",
            ):
                st.session_state["confirm_delete_id"] = row["id"]
                st.session_state.pop("editing_student_id", None)
                st.rerun()


    # Edit form for the selected student
    editing_id = st.session_state.get("editing_student_id")

    if editing_id is not None:
        selected_student = next(
            (row for row in records if row["id"] == editing_id),
            None,
        )

        if selected_student is None:
            st.warning(
                "This student is not in the current search results. "
                "Clear the search to edit the record."
            )
        else:
            st.markdown("### Edit Student Record")

            with st.form(key=f"edit_form_{editing_id}"):
                edit_name = st.text_input(
                    "Full Name",
                    value=selected_student["name"] or "",
                )
                edit_email = st.text_input(
                    "Email Address",
                    value=selected_student["email"] or "",
                )
                edit_department = st.text_input(
                    "Department",
                    value=selected_student["department"] or "",
                )
                edit_year = st.text_input(
                    "Academic Year",
                    value=selected_student["academic_year"] or "",
                )

                save_col, cancel_col = st.columns(2)

                with save_col:
                    save_changes = st.form_submit_button(
                        "💾 Save Changes",
                        use_container_width=True,
                    )

                with cancel_col:
                    cancel_edit = st.form_submit_button(
                        "Cancel",
                        use_container_width=True,
                    )

            if save_changes:
                if not all(
                    value.strip()
                    for value in (
                        edit_name,
                        edit_email,
                        edit_department,
                        edit_year,
                    )
                ):
                    st.error("Please fill in all fields.")
                else:
                    success, message = update_student(
                        editing_id,
                        edit_name.strip(),
                        edit_email.strip(),
                        edit_department.strip(),
                        edit_year.strip(),
                    )

                    if success:
                        st.session_state.pop("editing_student_id", None)
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

            if cancel_edit:
                st.session_state.pop("editing_student_id", None)
                st.rerun()

    # Confirmation before deleting a student
    deleting_id = st.session_state.get("confirm_delete_id")

    if deleting_id is not None:
        deleting_student = next(
            (row for row in records if row["id"] == deleting_id),
            None,
        )

        if deleting_student is not None:
            st.markdown(
                f"""
                <div style="
                    background-color: #FFF8E8;
                    color: #352F22;
                    padding: 16px;
                    border: 1px solid #D6A64F;
                    border-radius: 10px;
                    font-size: 16px;
                    margin-bottom: 12px;
            ">
            Delete <strong>{deleting_student['name']}</strong>
            ({deleting_student['email']}) permanently?
        </div>
        """,
        unsafe_allow_html=True,
    )

            confirm_col, cancel_col = st.columns(2)

            with confirm_col:
                if st.button(
                    "Yes, Delete Record",
                    key=f"confirm_delete_{deleting_id}",
                    type="primary",
                ):
                    delete_student(deleting_id)
                    st.session_state.pop("confirm_delete_id", None)
                    st.success("Student record deleted.")
                    st.rerun()

            with cancel_col:
                if st.button(
                    "Cancel Delete",
                    key=f"cancel_delete_{deleting_id}",
                ):
                    st.session_state.pop("confirm_delete_id", None)
                    st.rerun()


# --------------------------------------------------
# MAIN APPLICATION
# --------------------------------------------------

def main():
    load_css()
    create_database()

    # SIDEBAR NAVIGATION
    with st.sidebar:
        st.markdown(
            '<div class="brand-mark">🎓</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="brand-title">Student<br>Manager</div>',
            unsafe_allow_html=True,
        )

        page_options = {
            "🏠  Dashboard": "Dashboard",
            "➕  Add Student": "Add Student",
            "📋  View Records": "View Records",
            "🌿  About": "About",
            "❓  Help": "Help",
        }

        selected_label = st.radio(
            "Navigate",
            list(page_options.keys()),
            label_visibility="collapsed",
        )

        page = page_options[selected_label]

        st.markdown(
            """
            <div class="sidebar-note">
                <div class="book-art">📚</div>
                <div>
                    <strong>Organise. Protect. Grow.</strong><br>
                    <small>Your student data, beautifully managed.</small>
                </div>
                <div>✦ ✦ ✦</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


    # DASHBOARD STATISTICS
    with connect_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        departments = conn.execute(
            "SELECT COUNT(DISTINCT department) FROM students"
        ).fetchone()[0]

    # ----------------------------------------------
    # DASHBOARD PAGE
    # ----------------------------------------------

    if page == "Dashboard":
        st.markdown(
            """
            <div class="hero">
                <div class="hero-icon">📖</div>
                <div class="hero-copy">
                    <h1>Data Redundancy Removal System</h1>
                    <p>A smarter, safer way to manage student records.</p>
                </div>
                <div class="connection-pill">
                    ● DATABASE CONNECTED<br>
                    <small>SQLite · Local storage</small>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)

        cards = [
            (c1, "green", "👨‍🎓", "TOTAL STUDENTS", str(total)),
            (c2, "brown", "🛡️", "DUPLICATES BLOCKED",
             str(get_duplicate_count())),
            (c3, "green", "🏛️", "DEPARTMENTS", str(departments)),
            (c4, "brown", "🗄️", "DATABASE", "SQLite"),
        ]

        for col, color, symbol, label, value in cards:
            with col:
                st.markdown(
                    f"""
                    <div class="stat-card {color}">
                        <span>{symbol}</span>
                        <p>{label}</p>
                        <h2>{value}</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # All three sections now sit in one horizontal row.
        show_add_form()

        # Dashboard charts
        st.markdown("### 📊 Student Overview")
        all_students = get_students()

        if not all_students:
            st.info("Add a student to see dashboard charts.")
        else:
            student_df = pd.DataFrame(all_students)

            # Count students in each department
            department_counts = (
                student_df["department"]
                .value_counts()
                .rename_axis("Department")
                .reset_index(name="Number of Students")
                .sort_values("Number of Students", ascending=False)
            )

            # Count students in each academic year
            year_counts = (
                student_df["academic_year"]
                .value_counts()
                .rename_axis("Academic Year")
                .reset_index(name="Number of Students")
            )

            chart_left, chart_right = st.columns(2)

            with chart_left:
                st.markdown("#### 🏢 Students by Department")

                fig_department = px.bar(
                    department_counts,
                    x="Department",
                    y="Number of Students",
                    text="Number of Students",
                    color_discrete_sequence=["#52632d"],
                    labels={
                        "Department": "Department",
                        "Number of Students": "Number of Students",
                    },
                )

                fig_department.update_traces(
                    textposition="outside",
                    hovertemplate=(
                        "Department: %{x}<br>"
                        "Number of Students: %{y}<extra></extra>"
                    ),
                    cliponaxis=False,
                )

                fig_department.update_layout(
                    height=420,
                    plot_bgcolor="#fffaf1",
                    paper_bgcolor="#fffaf1",
                    font=dict(family="Arial",size=13,color="#20260f",
),
                    
                    xaxis=dict(
                        title="Department",
                        title_font=dict(color="#20260f", size=14),
                        tickfont=dict(color="#20260f", size=12),
                        tickangle=0,
                        automargin=True,
                        showgrid=False,
                        type="category",
                ),
                    
                    yaxis=dict(
                        title="Number of Students",
                        title_font=dict(color="#20260f", size=14),
                        tickfont=dict(color="#20260f", size=12),
                        rangemode="tozero",
                        dtick=1,
                        gridcolor="#d8d0bd",
                        zerolinecolor="#20260f",
                    ),
                    margin=dict(l=15, r=15, t=35, b=80),
                )

                st.plotly_chart(
                    fig_department,
                    use_container_width=True,
                )

                top_department = department_counts.iloc[0]
            
                st.markdown(
                    f"""
                    <div style="
                        background-color: #e8eddc;
                        color: #20260f;
                        padding: 14px;
                        border-left: 5px solid #52632d;
                        border-radius: 8px;
                        font-size: 15px;
                        line-height: 1.6;
                    ">
                        <b>Department Insight</b><br>
                        {
                            f"{top_department['Department']} has the most students "
                            f"({top_department['Number of Students']})."
                            if department_counts["Number of Students"].iloc[0]
                            > department_counts["Number of Students"].iloc[-1]
                            else
                            "Student enrollment is tied between departments "
                            f"with {top_department['Number of Students']} student(s) "
                            "each at the highest count."
                            if len(department_counts) > 1
                            and department_counts["Number of Students"].iloc[0]
                            == department_counts["Number of Students"].iloc[1]
                            else
                            f"{top_department['Department']} has "
                            f"{top_department['Number of Students']} student(s)."
                        }
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    
            with chart_right:
                st.markdown("#### 🎓 Students by Academic Year")

                fig_year = px.bar(
                    year_counts,
                    x="Academic Year",
                    y="Number of Students",
                    text="Number of Students",
                    color_discrete_sequence=["#e9a23b"],
                    labels={
                        "Academic Year": "Academic Year",
                        "Number of Students": "Number of Students",
                    },
                )

                fig_year.update_traces(
                    textposition="outside",
                    hovertemplate=(
                        "Academic Year: %{x}<br>"
                        "Number of Students: %{y}<extra></extra>"
                    ),
                    cliponaxis=False,
                )

                
                fig_year.update_layout(
                    height=420,
                    plot_bgcolor="#fffaf1",
                    paper_bgcolor="#fffaf1",
                    font=dict(
                        family="Arial",
                        size=13,
                        color="#20260f",
                    ),
                    xaxis=dict(
                        title="Academic Year",
                        title_font=dict(color="#20260f", size=14),
                        tickfont=dict(color="#20260f", size=12),
                        tickangle=0,
                        automargin=True,
                        showgrid=False,
                        type="category",
                    ),
                    yaxis=dict(
                        title="Number of Students",
                        title_font=dict(color="#20260f", size=14),
                        tickfont=dict(color="#20260f", size=12),
                        rangemode="tozero",
                        dtick=1,
                        gridcolor="#d8d0bd",
                        zerolinecolor="#20260f",
                    ),
                    margin=dict(l=15, r=15, t=35, b=80),
                )

                st.plotly_chart(
                    fig_year,
                    use_container_width=True,
                )

                
                top_year = year_counts.iloc[0]

                if (
                    len(year_counts) > 1
                    and year_counts["Number of Students"].iloc[0]
                    == year_counts["Number of Students"].iloc[1]
                ):
                    year_insight = (
                        "The highest enrollment is tied between academic years, "
                        f"with {top_year['Number of Students']} student(s) "
                        "in each tied year."
                    )
                else:
                    year_insight = (
                        f"{top_year['Academic Year']} has the most students "
                        f"({top_year['Number of Students']})."
                    )

                st.markdown(
                    f"""
                    <div style="
                        background-color: #f8e8c9;
                        color: #2c2117;
                        padding: 14px;
                        border-left: 5px solid #e9a23b;
                        border-radius: 8px;
                        font-size: 15px;
                        line-height: 1.6;
                    ">
                        <b>Academic Year Insight</b><br>
                        {year_insight}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown(
            '<div class="records-heading">'
            '📋 &nbsp; Student records'
            '</div>',
            unsafe_allow_html=True,
        )

        render_records()



    # ----------------------------------------------
    # ADD STUDENT PAGE
    # ----------------------------------------------

    elif page == "Add Student":
        st.markdown(
            """
            <div class="hero">
                <div class="hero-icon">📝</div>
                <div class="hero-copy">
                    <h1>Add a Student</h1>
                    <p>Register a student safely in your local database.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        show_add_form()

    # ----------------------------------------------
    # VIEW RECORDS PAGE
    # ----------------------------------------------

    elif page == "View Records":
        st.markdown(
            """
            <div class="hero">
                <div class="hero-icon">📋</div>
                <div class="hero-copy">
                    <h1>Student Records</h1>
                    <p>Search, review, and manage saved student information.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_records(show_delete=True)

    # ----------------------------------------------
    # ABOUT PAGE
    # ----------------------------------------------

    elif page == "About":
        st.markdown(
            """
            <div class="hero">
                <div class="hero-icon">🌿</div>
                <div class="hero-copy">
                    <h1>About This Project</h1>
                    <p>CodeAlpha Internship · Data Redundancy Removal System</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            ### 📘 Project Overview

            This project demonstrates how a student-record system
            can reduce redundant data using Python, Streamlit, and SQLite.

            - 🛡️ **Duplicate prevention:** Email addresses are unique
              and checked without case sensitivity.
            - 🗄️ **Persistent storage:** Records remain saved in `students.db`.
            - 🔍 **Search:** Find records by name, email, department, or year.
            - ✅ **Validation:** Names and email formats are checked.
            - 📊 **Analytics:** Charts summarize the student records.
            - 📥 **CSV export:** Download student records.
            - 💾 **Backup:** Create a timestamped database backup.
            """
        )

        st.markdown(
            """
            ### 🧰 Technologies Used

            - 🐍 Python — application logic
            - 🎨 Streamlit — user interface
            - 🗄️ SQLite — local database
            - 🖌️ CSS — existing green, gold, brown and cream theme
            """
        )

    # ----------------------------------------------
    # HELP PAGE
    # ----------------------------------------------

    elif page == "Help":
        st.markdown(
            """
            <div class="hero">
                <div class="hero-icon">❓</div>
                <div class="hero-copy">
                    <h1>Help & User Guide</h1>
                    <p>Quick instructions for using Student Manager.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("➕ How do I add a student?"):
            st.write(
                "Enter the student's full name and email, select a "
                "department and academic year, then click Add student. "
                "An email already registered in the database is rejected."
            )

        with st.expander("🔍 How do I find student records?"):
            st.write(
                "Open View Records and search by name, email, department, "
                "or academic year."
            )

        with st.expander("📥 How do I export records?"):
            st.write(
                "Use the Download records as CSV button on the Dashboard "
                "or View Records page. The download includes the records "
                "currently displayed by the search."
            )

        with st.expander("💾 How do I back up the database?"):
            st.write(
                "Create a timestamped backup below. Backup files are saved "
                "in the database_backups folder beside app.py."
            )

        with st.expander("🔐 How do I protect student data?"):
            st.write(
                "Keep your database and backups in a secure location. "
                "Avoid sharing student contact information publicly."
            )

        st.divider()
        st.subheader("💾 Database Backup")

        if st.button("Create Database Backup", use_container_width=True):
            try:
                backup_path = create_database_backup()
                st.success("Database backup created successfully.")
                st.code(str(backup_path))
            except (sqlite3.Error, OSError) as error:
                st.error(f"Backup failed: {error}")

    # ----------------------------------------------
    # FOOTER
    # ----------------------------------------------

    st.markdown(
        """
        <div class="footer">
            ✦ &nbsp; Built with Python, Streamlit & SQLite
            &nbsp; ✦ &nbsp; CodeAlpha Internship
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
