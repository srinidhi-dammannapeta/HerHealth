import sqlite3
import io
import zipfile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from pathlib import Path
from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

# -------------------------------
# Page configuration
# -------------------------------
st.set_page_config(
    page_title="HerHealth",
    page_icon="🌸",
    layout="wide"
)


# -------------------------------
# HerHealth Custom Design Theme
# -------------------------------
st.markdown("""
<style>
/* Main application background */
.stApp {
    background: linear-gradient(135deg, #fff7fb 0%, #f8f4ff 55%, #fff9f5 100%);
    color: #382b40;
}

/* Main content spacing */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}

/* Main headings */
h1 {
    color: #783d68 !important;
    font-weight: 750 !important;
    letter-spacing: -1px;
}

h2, h3 {
    color: #895078 !important;
    font-weight: 650 !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f5e5f1 0%, #eee7fb 100%);
    border-right: 1px solid #ead7e8;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #783d68 !important;
}

/* Navigation radio options */
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: rgba(255, 255, 255, 0.65);
    border-radius: 12px;
    padding: 9px 12px;
    margin-bottom: 5px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: #ffffff;
    border-color: #e5c4df;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid #f0ddea;
    border-radius: 18px;
    padding: 18px 20px;
    box-shadow: 0 4px 16px rgba(111, 63, 103, 0.06);
}

div[data-testid="stMetricLabel"] {
    color: #806b82;
}

div[data-testid="stMetricValue"] {
    color: #783d68;
    font-weight: 750;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #a94e86, #8055a4);
    color: white !important;
    border: none;
    border-radius: 12px;
    padding: 0.55rem 1.15rem;
    font-weight: 600;
    transition: all 0.2s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    background: linear-gradient(135deg, #913d73, #70428f);
    color: white !important;
    border: none;
    box-shadow: 0 5px 14px rgba(128, 85, 164, 0.2);
}

/* Input fields */
.stTextInput input,
.stTextArea textarea,
.stDateInput input,
.stTimeInput input {
    border-radius: 10px;
    border-color: #e6d5e5;
    background-color: #fffdfd;
}

/* Select boxes and other form controls */
div[data-baseweb="select"] > div {
    border-radius: 10px;
    border-color: #e6d5e5;
}

/* Data tables */
div[data-testid="stDataFrame"] {
    border: 1px solid #efdeec;
    border-radius: 14px;
    overflow: hidden;
}

/* Expanders */
div[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.75);
    border: 1px solid #efdeec;
    border-radius: 14px;
}

/* Information and success messages */
div[data-testid="stAlert"] {
    border-radius: 12px;
}

/* Dividers */
hr {
    border-color: #ead9e8;
}

/* Footer */
footer {
    visibility: hidden;
}

/* Keep the design comfortable on smaller screens */
@media (max-width: 768px) {
    .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    h1 {
        font-size: 1.8rem !important;
    }
}
</style>
""", unsafe_allow_html=True)


# -------------------------------
# Sidebar navigation
# -------------------------------
st.sidebar.title("🌸 HerHealth")
st.sidebar.write("Women's Health Platform")

page = st.sidebar.radio(
    "Navigate",
    [
        "Home",
        "Symptom Tracking",
        "Health Dashboard",
        "Cycle Tracker",
        "Health Awareness",
        "Health Reminders",
        "Health Summary Report",
        "Symptom Calendar",
        "Symptom Trend Comparison",
        "Complete Health Report"
    ]
)

# -------------------------------
# Database configuration
# -------------------------------
DB_PATH = Path(__file__).resolve().parent / "herhealth.db"


def initialize_database():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS symptoms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symptom TEXT NOT NULL,
                date TEXT NOT NULL,
                severity TEXT NOT NULL,
                notes TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS cycle_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT NOT NULL UNIQUE
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_type TEXT NOT NULL,
                title TEXT NOT NULL,
                reminder_date TEXT NOT NULL,
                reminder_time TEXT NOT NULL,
                notes TEXT,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)

        # Add status to an existing reminders table if needed.
        reminder_columns = pd.read_sql_query(
            "PRAGMA table_info(reminders)",
            connection
        )["name"].tolist()

        if "status" not in reminder_columns:
            connection.execute("""
                ALTER TABLE reminders
                ADD COLUMN status TEXT NOT NULL DEFAULT 'Pending'
            """)


# -------------------------------
# Symptom database functions
# -------------------------------
def save_symptom(symptom, date, severity, notes):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO symptoms (symptom, date, severity, notes)
            VALUES (?, ?, ?, ?)
            """,
            (symptom, str(date), severity, notes)
        )


def get_symptoms():
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(
            """
            SELECT id, symptom, date, severity, notes
            FROM symptoms
            ORDER BY date DESC, id DESC
            """,
            connection
        )


# -------------------------------
# Cycle database functions
# -------------------------------
def save_cycle_start(start_date):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO cycle_records (start_date) VALUES (?)",
            (str(start_date),)
        )


def get_cycle_history():
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(
            """
            SELECT id, start_date
            FROM cycle_records
            ORDER BY start_date DESC, id DESC
            """,
            connection
        )


# -------------------------------
# Reminder database functions
# -------------------------------
def save_reminder(reminder_type, title, reminder_date,
                  reminder_time, notes):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO reminders
            (reminder_type, title, reminder_date,
             reminder_time, notes, active, status)
            VALUES (?, ?, ?, ?, ?, 1, 'Pending')
            """,
            (
                reminder_type,
                title,
                str(reminder_date),
                str(reminder_time),
                notes
            )
        )


def get_reminders():
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(
            """
            SELECT id, reminder_type, title,
                   reminder_date, reminder_time,
                   notes, active, status
            FROM reminders
            ORDER BY reminder_date ASC, reminder_time ASC
            """,
            connection
        )


# Initialize database before displaying pages.
initialize_database()
history = get_symptoms()

# -------------------------------
# Home page
# -------------------------------
if page == "Home":
    st.title("🌸 Welcome to HerHealth")
    st.subheader("Women's Health Monitoring & Awareness")
    st.write(
        "Track your symptoms, understand patterns, "
        "and prepare useful health summaries."
    )
    st.info(
        "HerHealth supports health awareness and symptom tracking. "
        "It does not diagnose medical conditions."
    )

    st.markdown("### Explore HerHealth")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📝 Symptom Tracking")
        st.write("Record symptoms, severity, dates, and notes.")
        st.markdown("#### 📊 Health Dashboard")
        st.write("Review charts and summaries of recorded symptoms.")

    with col2:
        st.markdown("#### 🌷 Cycle Tracker")
        st.write("Estimate a possible next period date.")
        st.markdown("#### 💗 Health Awareness")
        st.write("Explore educational information about women's health.")

    st.metric("Saved symptom records", len(history))

    
# -------------------------------
# Symptom Tracking page
# -------------------------------
elif page == "Symptom Tracking":
    st.title("📝 Symptom Tracking")
    st.write("Record a symptom and review your saved history.")

    with st.form("symptom_form", clear_on_submit=True):
        symptom = st.selectbox(
            "Select a symptom",
            [
                "Menstrual pain",
                "Pelvic pain",
                "Headache",
                "Fatigue",
                "Mood changes",
                "Other"
            ]
        )
        date = st.date_input("Date")
        severity = st.select_slider(
            "Symptom severity",
            options=["Mild", "Moderate", "Severe"]
        )
        notes = st.text_area("Additional notes (optional)")
        submitted = st.form_submit_button("Save Symptom")

        if submitted:
            save_symptom(symptom, date, severity, notes.strip())
            st.success("Your symptom record has been saved!")
            st.rerun()

    st.divider()
    st.header("📋 Symptom History")
    history = get_symptoms()

    if history.empty:
        st.info("No symptom records yet. Add your first record above.")
    else:
        st.metric("Total symptom records", len(history))
        st.dataframe(
            history.drop(columns=["id"]),
            use_container_width=True,
            hide_index=True
        )
        csv_data = history.drop(columns=["id"]).to_csv(index=False)
        st.download_button(
            "Download Symptom History (CSV)",
            data=csv_data,
            file_name="herhealth_symptom_history.csv",
            mime="text/csv"
        )


# -------------------------------
# Health Dashboard page
# -------------------------------
elif page == "Health Dashboard":
    st.title("📊 Your Health Dashboard")
    history = get_symptoms()

    if history.empty:
        st.info("Record some symptoms to see your dashboard.")
    else:
        dashboard = history.copy()
        dashboard["date"] = pd.to_datetime(
            dashboard["date"], errors="coerce"
        )
        dashboard = dashboard.dropna(subset=["date"])

        if dashboard.empty:
            st.info("No valid symptom dates are available.")
            st.stop()

        min_date = dashboard["date"].min().date()
        max_date = dashboard["date"].max().date()

        st.subheader("Symptom Analysis")
        st.write("Select a date range to analyze your symptoms.")

        selected_dates = st.date_input(
            "Choose date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="symptom_date_range"
        )

        if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
            st.info("Please select both a start date and an end date.")
            st.stop()

        start_date, end_date = selected_dates
        dashboard = dashboard[
            (dashboard["date"].dt.date >= start_date)
            & (dashboard["date"].dt.date <= end_date)
        ]

        if dashboard.empty:
            st.warning("No symptom records found in this date range.")
            st.stop()

        total_records = len(dashboard)
        severe_records = int((dashboard["severity"] == "Severe").sum())
        most_common = dashboard["symptom"].mode()
        most_common_symptom = (
            most_common.iloc[0] if not most_common.empty else "N/A"
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Records", total_records)
        col2.metric("Severe Records", severe_records)
        col3.metric("Most Recorded Symptom", most_common_symptom)

        st.subheader("Symptom Frequency")
        symptom_counts = (
            dashboard["symptom"]
            .value_counts()
            .rename_axis("Symptom")
            .reset_index(name="Records")
        )
        fig_symptoms = px.bar(
            symptom_counts,
            x="Symptom",
            y="Records",
            title="Number of Records per Symptom",
            text="Records"
        )
        st.plotly_chart(fig_symptoms, use_container_width=True)

        st.subheader("Symptom Severity Distribution")
        severity_order = ["Mild", "Moderate", "Severe"]
        severity_counts = (
            dashboard["severity"]
            .value_counts()
            .reindex(severity_order, fill_value=0)
            .rename_axis("Severity")
            .reset_index(name="Records")
        )
        fig_severity = px.pie(
            severity_counts,
            names="Severity",
            values="Records",
            title="Distribution of Recorded Severity",
            hole=0.4
        )
        st.plotly_chart(fig_severity, use_container_width=True)

        st.subheader("Records Over Time")
        daily_counts = (
            dashboard.groupby(dashboard["date"].dt.date)
            .size()
            .reset_index(name="Records")
            .rename(columns={"date": "Date"})
            .sort_values("Date")
        )
        fig_timeline = px.line(
            daily_counts,
            x="Date",
            y="Records",
            markers=True,
            title="Symptom Entries by Date"
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # -------------------------------
        # Symptom Insights
        # -------------------------------
        st.subheader("Symptom Insights")
        symptom_counts = dashboard["symptom"].value_counts()

        if symptom_counts.empty:
            st.info("No symptom data is available for analysis.")
        else:
            most_common_symptom = symptom_counts.index[0]
            most_common_count = int(symptom_counts.iloc[0])

            severity_insights = (
                dashboard["severity"]
                .astype(str)
                .str.strip()
                .str.title()
                .value_counts()
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Recorded Entries", len(dashboard))
            with col2:
                st.metric("Most Frequent Symptom", most_common_symptom)
            with col3:
                st.metric("Times Recorded", most_common_count)

            st.write("### Severity Breakdown")
            severity_df = severity_insights.rename_axis(
                "Severity"
            ).reset_index(name="Number of Records")
            st.dataframe(
                severity_df,
                use_container_width=True,
                hide_index=True
            )

            st.write("### Frequently Recorded Symptoms")
            symptom_df = symptom_counts.rename_axis(
                "Symptom"
            ).reset_index(name="Number of Records")
            st.bar_chart(symptom_df.set_index("Symptom"))

            st.caption(
                "These insights summarize recorded entries only. "
                "They do not diagnose conditions or predict illness."
            )

        st.caption(
            "Charts summarize recorded entries, not disease risk. "
            "More records on a date do not necessarily mean "
            "symptoms were more severe."
        )

        st.subheader("Download Symptom Analysis")
        csv_data = dashboard.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Filtered Symptom Report",
            data=csv_data,
            file_name="herhealth_symptom_report.csv",
            mime="text/csv"
        )


# -------------------------------
# Menstrual Cycle Tracker page
# -------------------------------
elif page == "Cycle Tracker":
    st.title("🌷 Menstrual Cycle Tracker")
    st.write(
        "Save the first day of each period to build your cycle history. "
        "Cycle estimates are approximate and can vary."
    )

    today = pd.Timestamp.today().date()
    st.subheader("Record a Period Start Date")

    with st.form("cycle_record_form", clear_on_submit=True):
        period_start = st.date_input(
            "First day of your period",
            value=today,
            max_value=today,
            key="period_start_entry"
        )
        cycle_saved = st.form_submit_button("Save Period Date")

    if cycle_saved:
        save_cycle_start(period_start)
        st.success(
            "Period date saved. If this date was already recorded, "
            "it was not added twice."
        )
        st.rerun()

    st.divider()
    st.subheader("Estimate Your Next Period")

    cycle_length = st.number_input(
        "Usual cycle length (days)",
        min_value=15,
        max_value=60,
        value=28,
        step=1,
        key="usual_cycle_length"
    )

    cycle_history = get_cycle_history()

    if cycle_history.empty:
        st.info(
            "Save at least one period start date above to calculate "
            "an estimated next period."
        )
    else:
        most_recent_start = pd.to_datetime(
            cycle_history.iloc[0]["start_date"]
        ).date()
        next_period = most_recent_start + timedelta(days=int(cycle_length))
        days_remaining = (next_period - today).days

        st.write(
            "Most recently recorded period start:",
            most_recent_start.strftime("%d %B %Y")
        )
        st.write(
            "Estimated next period date:",
            next_period.strftime("%d %B %Y")
        )

        if days_remaining > 0:
            st.metric("Estimated days remaining", days_remaining)
        elif days_remaining == 0:
            st.info("Your next period is estimated for today.")
        else:
            st.info(
                "The estimated date has passed. Your actual cycle may vary; "
                "record your next period when it begins."
            )

    st.caption(
        "This calendar estimate is not a medical prediction or a "
        "contraception method."
    )

    st.divider()
    st.subheader("📅 Previous Period Dates")
    cycle_history = get_cycle_history()

    if cycle_history.empty:
        st.info("Your saved period dates will appear here.")
    else:
        cycle_history["start_date"] = pd.to_datetime(
            cycle_history["start_date"], errors="coerce"
        )
        chronological = cycle_history.sort_values("start_date").copy()
        chronological["cycle_length_days"] = (
            chronological["start_date"].diff().dt.days
        )

        display_history = chronological.copy()
        display_history["start_date"] = display_history[
            "start_date"
        ].dt.strftime("%d %B %Y")
        display_history["cycle_length_days"] = display_history[
            "cycle_length_days"
        ].apply(
            lambda value: (
                "Not available yet" if pd.isna(value)
                else f"{int(value)} days"
            )
        )

        display_history = display_history.iloc[::-1].rename(
            columns={
                "start_date": "Period Start Date",
                "cycle_length_days": "Days Since Previous Period"
            }
        )
        st.dataframe(
            display_history[
                ["Period Start Date", "Days Since Previous Period"]
            ],
            use_container_width=True,
            hide_index=True
        )

        if len(chronological) >= 2:
            cycle_chart_data = chronological.dropna(
                subset=["cycle_length_days"]
            )
            if not cycle_chart_data.empty:
                fig_cycle = px.line(
                    cycle_chart_data,
                    x="start_date",
                    y="cycle_length_days",
                    markers=True,
                    title="Recorded Days Between Period Starts",
                    labels={
                        "start_date": "Period Start Date",
                        "cycle_length_days": "Days Between Starts"
                    }
                )
                st.plotly_chart(fig_cycle, use_container_width=True)

    st.caption(
        "Cycle lengths are calculated from the dates you enter. "
        "A small number of entries may not represent your usual pattern. "
        "This tool does not diagnose menstrual conditions."
    )

    # -------------------------------
    # Cycle and Symptom History Comparison
    # -------------------------------
    st.divider()
    st.header("🌸 Cycle and Symptom History Comparison")
    st.write(
        "Review symptom records around a selected period start date. "
        "This feature compares recorded dates and does not identify "
        "the cause of any symptom."
    )

    cycle_compare = get_cycle_history()

    if cycle_compare.empty:
        st.info(
            "Save at least one period start date above "
            "to compare it with your symptom history."
        )
    else:
        valid_cycle_dates = (
            pd.to_datetime(cycle_compare["start_date"], errors="coerce")
            .dropna()
            .dt.strftime("%Y-%m-%d")
            .drop_duplicates()
            .sort_values(ascending=False)
            .tolist()
        )

        if not valid_cycle_dates:
            st.warning("No valid period dates are available.")
        else:
            st.subheader("1. Select a Period Date")
            selected_period = st.selectbox(
                "Choose a recorded period start date",
                options=valid_cycle_dates,
                format_func=lambda value: pd.to_datetime(
                    value
                ).strftime("%d %B %Y"),
                key="comparison_period_date"
            )

            st.subheader("2. Choose the Date Range")
            col1, col2 = st.columns(2)

            with col1:
                days_before = st.number_input(
                    "Days before period start",
                    min_value=0,
                    max_value=30,
                    value=7,
                    step=1,
                    key="comparison_days_before"
                )

            with col2:
                days_after = st.number_input(
                    "Days after period start",
                    min_value=0,
                    max_value=30,
                    value=7,
                    step=1,
                    key="comparison_days_after"
                )

            selected_date = pd.to_datetime(selected_period).date()
            window_start = selected_date - timedelta(days=int(days_before))
            window_end = selected_date + timedelta(days=int(days_after))

            st.write(
                f"**Comparison window:** "
                f"{window_start.strftime('%d %B %Y')} to "
                f"{window_end.strftime('%d %B %Y')}"
            )

            symptoms_compare = get_symptoms()

            if not symptoms_compare.empty:
                symptoms_compare["date_parsed"] = pd.to_datetime(
                    symptoms_compare["date"], errors="coerce"
                ).dt.date
                window_symptoms = symptoms_compare[
                    symptoms_compare["date_parsed"].notna()
                    & (symptoms_compare["date_parsed"] >= window_start)
                    & (symptoms_compare["date_parsed"] <= window_end)
                ].copy()
                window_symptoms = window_symptoms.sort_values(
                    ["date_parsed", "id"]
                )
            else:
                window_symptoms = pd.DataFrame()

            st.subheader("3. Symptoms Around This Period")

            if window_symptoms.empty:
                st.info(
                    "No symptom records were found in this date range. "
                    "You can add records in the Symptom Tracking page."
                )
            else:
                st.metric(
                    "Symptom records in this window",
                    len(window_symptoms)
                )
                symptom_display = window_symptoms[
                    ["date_parsed", "symptom", "severity", "notes"]
                ].copy()
                symptom_display["date_parsed"] = symptom_display[
                    "date_parsed"
                ].apply(lambda value: value.strftime("%d %B %Y"))
                symptom_display = symptom_display.rename(
                    columns={
                        "date_parsed": "Date",
                        "symptom": "Symptom",
                        "severity": "Severity",
                        "notes": "Notes"
                    }
                )
                st.dataframe(
                    symptom_display,
                    use_container_width=True,
                    hide_index=True
                )

            st.subheader("4. Combined Cycle and Symptom Timeline")
            timeline_rows = [
                {
                    "Date": selected_date,
                    "Event": "Period Start",
                    "Severity": "-",
                    "Notes": "Recorded period start date"
                }
            ]

            if not window_symptoms.empty:
                for _, record in window_symptoms.iterrows():
                    timeline_rows.append(
                        {
                            "Date": record["date_parsed"],
                            "Event": record["symptom"],
                            "Severity": record["severity"],
                            "Notes": (
                                record["notes"]
                                if pd.notna(record["notes"])
                                else ""
                            )
                        }
                    )

            timeline = pd.DataFrame(timeline_rows).sort_values(
                ["Date", "Event"]
            ).reset_index(drop=True)
            timeline["Date"] = timeline["Date"].apply(
                lambda value: value.strftime("%d %B %Y")
            )
            st.dataframe(
                timeline,
                use_container_width=True,
                hide_index=True
            )

            timeline_csv = timeline.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Cycle and Symptom Timeline (CSV)",
                data=timeline_csv,
                file_name="herhealth_cycle_symptom_timeline.csv",
                mime="text/csv",
                key="download_cycle_symptom_timeline"
            )

            st.caption(
                "This timeline shows recorded dates and symptoms only. "
                "Symptoms near a period date are not necessarily caused "
                "by the menstrual cycle. This feature does not diagnose "
                "medical conditions."
            )


# -------------------------------
# Women's Health Awareness page
# -------------------------------
elif page == "Health Awareness":
    st.title("💗 Women's Health Awareness")
    st.write(
        "Learn about common women's health topics "
        "and when to seek professional medical advice."
    )

    health_topic = st.selectbox(
        "Choose a health topic",
        [
            "Menstrual Health",
            "PCOS Awareness",
            "Endometriosis Awareness",
            "Iron Deficiency Awareness",
            "When to Seek Medical Help"
        ],
        key="health_awareness_topic"
    )

    if health_topic == "Menstrual Health":
        st.subheader("🌷 Understanding Menstrual Health")
        st.write(
            "Menstrual cycles vary from person to person. "
            "Tracking period dates, pain, bleeding patterns, "
            "and other symptoms can help you understand "
            "your own patterns."
        )
        st.info(
            "Consult a healthcare professional if period pain "
            "is severe, bleeding is unusually heavy, or symptoms "
            "interfere with daily activities."
        )

    elif health_topic == "PCOS Awareness":
        st.subheader("🌼 PCOS Awareness")
        st.write(
            "Polycystic ovary syndrome (PCOS) is a hormonal "
            "condition that can affect menstrual cycles, skin, "
            "hair growth, and ovulation."
        )
        st.info(
            "Irregular periods alone do not confirm PCOS. "
            "A healthcare professional can assess symptoms "
            "and recommend appropriate tests."
        )

    elif health_topic == "Endometriosis Awareness":
        st.subheader("🌸 Endometriosis Awareness")
        st.write(
            "Endometriosis is a condition in which tissue "
            "similar to the lining of the uterus grows outside "
            "the uterus. It may cause significant menstrual "
            "pain or pelvic pain."
        )
        st.info(
            "Persistent or severe period pain deserves "
            "medical evaluation. Pain should not be dismissed "
            "as something you must simply tolerate."
        )

    elif health_topic == "Iron Deficiency Awareness":
        st.subheader("🌿 Iron Deficiency Awareness")
        st.write(
            "Iron deficiency can contribute to fatigue, "
            "weakness, dizziness, and reduced energy. "
            "Heavy menstrual bleeding can increase the risk."
        )
        st.info(
            "These symptoms can have many causes. A healthcare "
            "professional can determine whether testing or "
            "treatment is needed."
        )

    elif health_topic == "When to Seek Medical Help":
        st.subheader("🩺 Health and Safety")
        st.write(
            "- Seek medical advice for persistent pelvic pain, "
            "unusually heavy bleeding, or repeated changes "
            "in your menstrual cycle."
        )
        st.write(
            "- Seek urgent medical care for severe or sudden "
            "pelvic pain, fainting, or heavy bleeding with "
            "weakness or dizziness."
        )
        st.write(
            "- If pregnancy is possible and you experience "
            "severe pain or fainting, seek emergency care."
        )

    st.caption(
        "Educational information only. HerHealth does not "
        "diagnose conditions or replace professional care."
    )


# -------------------------------
# Health Reminders page
# -------------------------------
elif page == "Health Reminders":
    st.title("🔔 Health Reminders")
    st.write(
        "Create and manage reminders for period tracking, "
        "medicine schedules, and symptom logging."
    )

    # -------------------------------
    # Cycle-based reminder suggestions
    # -------------------------------
    st.subheader("🌷 Suggested Period Reminder")
    cycle_history = get_cycle_history()

    if cycle_history.empty:
        st.info(
            "Record a period start date in Cycle Tracker "
            "to receive a suggested reminder."
        )
    else:
        latest_start = pd.to_datetime(
            cycle_history.iloc[0]["start_date"]
        ).date()

        suggested_cycle_length = st.number_input(
            "Usual cycle length (days)",
            min_value=15,
            max_value=60,
            value=28,
            step=1,
            key="reminder_cycle_length"
        )

        suggested_date = latest_start + timedelta(
            days=int(suggested_cycle_length)
        )

        st.write(
            f"Estimated next period date: "
            f"**{suggested_date.strftime('%d %B %Y')}**"
        )
        st.caption(
            "This is an estimate based on your last recorded "
            "period date and selected cycle length."
        )

        if st.button("Use This Date for a Reminder"):
            st.session_state["suggested_reminder_date"] = (
                suggested_date.isoformat()
            )
            st.success(
                "Suggested date selected. You can use it "
                "in the reminder form below."
            )

    st.divider()
    st.subheader("Create a Reminder")

    with st.form("reminder_form"):
        reminder_type = st.selectbox(
            "Reminder Type",
            ["Period", "Medicine", "Symptom Logging"]
        )
        title = st.text_input(
            "Reminder Title",
            placeholder="Example: Record today's symptoms"
        )

        default_reminder_date = pd.Timestamp.today().date()
        if "suggested_reminder_date" in st.session_state:
            default_reminder_date = pd.to_datetime(
                st.session_state["suggested_reminder_date"]
            ).date()

        reminder_date = st.date_input(
            "Reminder Date",
            value=default_reminder_date,
            key="reminder_date_input"
        )
        reminder_time = st.time_input("Reminder Time")
        notes = st.text_area("Additional Notes (Optional)")
        submitted = st.form_submit_button("Save Reminder")

        if submitted:
            if not title.strip():
                st.error("Please enter a reminder title.")
            else:
                save_reminder(
                    reminder_type,
                    title.strip(),
                    reminder_date,
                    reminder_time,
                    notes.strip()
                )
                st.success("Reminder saved successfully!")

    # -------------------------------
    # Reminder Status and History
    # -------------------------------
    st.divider()
    st.subheader("📋 Reminder Status and History")
    reminders = get_reminders()

    if reminders.empty:
        st.info("No reminders saved yet.")
    else:
        reminders["reminder_datetime"] = pd.to_datetime(
            reminders["reminder_date"].astype(str)
            + " "
            + reminders["reminder_time"].astype(str),
            errors="coerce"
        )

        now = pd.Timestamp.now()
        active_mask = reminders["active"] == 1
        pending_mask = reminders["status"] == "Pending"

        due_mask = (
            active_mask
            & pending_mask
            & reminders["reminder_datetime"].notna()
            & (reminders["reminder_datetime"] <= now)
        )

        if due_mask.any():
            due_ids = reminders.loc[due_mask, "id"].astype(int).tolist()
            with sqlite3.connect(DB_PATH) as connection:
                connection.executemany(
                    "UPDATE reminders SET status = 'Due' WHERE id = ?",
                    [(reminder_id,) for reminder_id in due_ids]
                )
            reminders.loc[due_mask, "status"] = "Due"

        active_reminders = reminders[reminders["active"] == 1].copy()
        inactive_reminders = reminders[reminders["active"] == 0].copy()

        upcoming_count = int(
            (
                active_reminders["reminder_datetime"].notna()
                & (active_reminders["reminder_datetime"] > now)
                & (active_reminders["status"] != "Completed")
            ).sum()
        )
        due_count = int((active_reminders["status"] == "Due").sum())
        completed_count = int((reminders["status"] == "Completed").sum())

        col1, col2, col3 = st.columns(3)
        col1.metric("Upcoming", upcoming_count)
        col2.metric("Due", due_count)
        col3.metric("Completed", completed_count)

        st.subheader("Active Reminders")
        if active_reminders.empty:
            st.info("You have no active reminders.")
        else:
            st.dataframe(
                active_reminders[
                    [
                        "id", "reminder_type", "title",
                        "reminder_date", "reminder_time",
                        "status", "notes"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            reminder_ids = active_reminders["id"].tolist()
            selected_id = st.selectbox(
                "Select an active reminder",
                options=reminder_ids,
                format_func=lambda reminder_id: (
                    f"ID {reminder_id} - "
                    f"{active_reminders.loc[active_reminders['id'] == reminder_id, 'title'].iloc[0]}"
                ),
                key="status_selected_reminder"
            )

            action = st.radio(
                "Choose an action",
                ["Mark as Completed", "Deactivate Reminder"],
                horizontal=True,
                key="reminder_action"
            )

            if st.button("Apply Action"):
                with sqlite3.connect(DB_PATH) as connection:
                    if action == "Mark as Completed":
                        connection.execute(
                            """
                            UPDATE reminders
                            SET status = 'Completed', active = 0
                            WHERE id = ?
                            """,
                            (int(selected_id),)
                        )
                    else:
                        connection.execute(
                            """
                            UPDATE reminders
                            SET active = 0
                            WHERE id = ?
                            """,
                            (int(selected_id),)
                        )

                st.success("Reminder updated successfully.")
                st.rerun()

        st.subheader("Reminder History")
        if inactive_reminders.empty:
            st.info("No inactive reminders in your history yet.")
        else:
            st.dataframe(
                inactive_reminders[
                    [
                        "id", "reminder_type", "title",
                        "reminder_date", "reminder_time",
                        "status", "notes"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        
        st.subheader("✏️ Edit Reminder Title")

        all_reminders = get_reminders()

        if all_reminders.empty:
            st.info("No reminders are available to edit.")
        else:
            edit_id = st.selectbox(
                "Select the reminder with the incorrect title",
                options=all_reminders["id"].tolist(),
                format_func=lambda reminder_id: (
                    f"ID {reminder_id} - "
                    f"{all_reminders.loc[all_reminders['id'] == reminder_id, 'title'].iloc[0]}"
                ),
                key="edit_reminder_id"
            )

            current_title = all_reminders.loc[
                all_reminders["id"] == edit_id, "title"
            ].iloc[0]

            with st.form("edit_reminder_title_form"):
                new_title = st.text_input(
                    "Correct reminder title",
                    value=current_title,
                    key=f"new_reminder_title_{edit_id}"
                )

                save_title = st.form_submit_button("Save Corrected Title")

                if save_title:
                    if not new_title.strip():
                        st.error("Please enter a reminder title.")
                    else:
                        with sqlite3.connect(DB_PATH) as connection:
                            connection.execute(
                                "UPDATE reminders SET title = ? WHERE id = ?",
                                (new_title.strip(), int(edit_id))
                            )

                        st.success("Reminder title updated successfully!")
                        st.rerun()



# -------------------------------
# Health Summary Report page
# -------------------------------
elif page == "Health Summary Report":
    st.title("📄 Health Summary Report")
    st.write(
        "Review your recorded symptoms and menstrual cycle history "
        "in one place. This report summarizes your entries and "
        "does not diagnose medical conditions."
    )

    # Load existing records
    summary_symptoms = get_symptoms()
    summary_cycles = get_cycle_history()

    st.subheader("1. Symptom Summary")

    if summary_symptoms.empty:
        st.info("No symptom records available yet.")
        total_symptoms = 0
        severe_symptoms = 0
        most_common_symptom = "N/A"
    else:
        total_symptoms = len(summary_symptoms)
        severe_symptoms = int(
            (summary_symptoms["severity"] == "Severe").sum()
        )

        symptom_counts = summary_symptoms["symptom"].value_counts()
        most_common_symptom = (
            symptom_counts.index[0]
            if not symptom_counts.empty
            else "N/A"
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Symptom Records", total_symptoms)
        col2.metric("Severe Records", severe_symptoms)
        col3.metric("Most Recorded Symptom", most_common_symptom)

        st.write("### Severity Breakdown")
        severity_counts = (
            summary_symptoms["severity"]
            .value_counts()
            .reindex(["Mild", "Moderate", "Severe"], fill_value=0)
            .rename_axis("Severity")
            .reset_index(name="Number of Records")
        )
        st.dataframe(
            severity_counts,
            use_container_width=True,
            hide_index=True
        )

    st.divider()
    st.subheader("2. Menstrual Cycle History")

    if summary_cycles.empty:
        st.info("No period dates have been recorded yet.")
    else:
        summary_cycles["start_date"] = pd.to_datetime(
            summary_cycles["start_date"], errors="coerce"
        )
        summary_cycles = summary_cycles.dropna(subset=["start_date"])
        summary_cycles = summary_cycles.sort_values(
            "start_date", ascending=False
        )

        cycle_display = summary_cycles.copy()
        cycle_display["start_date"] = cycle_display[
            "start_date"
        ].dt.strftime("%d %B %Y")

        st.write(
            f"Total recorded period start dates: {len(cycle_display)}"
        )
        st.dataframe(
            cycle_display[["start_date"]].rename(
                columns={"start_date": "Period Start Date"}
            ),
            use_container_width=True,
            hide_index=True
        )

    st.divider()
    st.subheader("3. Download Your Health Summary")

    report_lines = [
        "HerHealth - Personal Health Summary",
        "This report summarizes user-entered records only.",
        "It is not a medical diagnosis.",
        "",
        "SYMPTOM SUMMARY",
        f"Total symptom records: {total_symptoms}",
        f"Severe symptom records: {severe_symptoms}",
        f"Most frequently recorded symptom: {most_common_symptom}",
        "",
        "SYMPTOM HISTORY"
    ]

    if not summary_symptoms.empty:
        symptom_export = summary_symptoms[
            ["symptom", "date", "severity", "notes"]
        ].copy()
        symptom_export.columns = [
            "Symptom", "Date", "Severity", "Notes"
        ]
    else:
        symptom_export = pd.DataFrame(
            columns=["Symptom", "Date", "Severity", "Notes"]
        )

    cycle_export = get_cycle_history()

    if not cycle_export.empty:
        cycle_export = cycle_export[["start_date"]].copy()
        cycle_export.columns = ["Period Start Date"]
    else:
        cycle_export = pd.DataFrame(
            columns=["Period Start Date"]
        )

    st.download_button(
        label="Download Symptom History (CSV)",
        data=symptom_export.to_csv(index=False).encode("utf-8"),
        file_name="herhealth_health_summary_symptoms.csv",
        mime="text/csv"
    )

    st.download_button(
        label="Download Period History (CSV)",
        data=cycle_export.to_csv(index=False).encode("utf-8"),
        file_name="herhealth_health_summary_periods.csv",
        mime="text/csv"
    )

    st.caption(
        "Your report reflects only the information you have entered. "
        "Cycle estimates and symptom records cannot confirm a diagnosis."
    )


# -------------------------------
# Symptom Calendar page
# -------------------------------
elif page == "Symptom Calendar":
    import calendar

    st.title("🗓️ Symptom Calendar")
    st.write(
        "Explore your recorded symptoms by date. "
        "Dates without records do not necessarily mean "
        "that no symptoms occurred."
    )

    calendar_history = get_symptoms()

    if calendar_history.empty:
        st.info(
            "No symptom records are available yet. "
            "Add records on the Symptom Tracking page first."
        )
    else:
        calendar_history["date"] = pd.to_datetime(
            calendar_history["date"], errors="coerce"
        ).dt.date

        calendar_history = calendar_history.dropna(subset=["date"])

        if calendar_history.empty:
            st.warning("No valid symptom dates were found.")
        else:
            today = pd.Timestamp.today().date()

            col1, col2 = st.columns(2)

            with col1:
                selected_month = st.selectbox(
                    "Select month",
                    options=list(range(1, 13)),
                    index=today.month - 1,
                    format_func=lambda month: calendar.month_name[month],
                    key="symptom_calendar_month"
                )

            with col2:
                available_years = sorted(
                    {record.year for record in calendar_history["date"]}
                    | {today.year},
                    reverse=True
                )

                selected_year = st.selectbox(
                    "Select year",
                    options=available_years,
                    index=available_years.index(today.year),
                    key="symptom_calendar_year"
                )

            st.subheader(
                f"{calendar.month_name[selected_month]} {selected_year}"
            )

            month_records = calendar_history[
                (calendar_history["date"].apply(
                    lambda date: date.month == selected_month
                    and date.year == selected_year
                ))
            ].copy()

            daily_counts = month_records["date"].value_counts().to_dict()

            month_weeks = calendar.monthcalendar(
                selected_year, selected_month
            )

            st.caption(
                "Dates marked with 📝 have recorded symptom entries."
            )

            headers = st.columns(7)
            for column, day_name in zip(
                headers, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            ):
                column.markdown(f"**{day_name}**")

            for week in month_weeks:
                day_columns = st.columns(7)

                for column, day_number in zip(day_columns, week):
                    with column:
                        if day_number == 0:
                            st.write(" ")
                        else:
                            current_date = pd.Timestamp(
                                selected_year,
                                selected_month,
                                day_number
                            ).date()

                            count = daily_counts.get(current_date, 0)

                            if count > 0:
                                st.markdown(
                                    f"**{day_number} 📝**"
                                )
                                st.caption(f"{count} record(s)")
                            else:
                                st.write(str(day_number))

            st.divider()
            st.subheader("View Symptoms for a Specific Date")

            dates_with_records = sorted(
                daily_counts.keys(),
                reverse=True
            )

            if not dates_with_records:
                st.info(
                    "No symptoms were recorded in the selected month."
                )
            else:
                chosen_date = st.selectbox(
                    "Choose a date with recorded symptoms",
                    options=dates_with_records,
                    format_func=lambda date: date.strftime("%d %B %Y"),
                    key="symptom_calendar_selected_date"
                )

                selected_records = month_records[
                    month_records["date"] == chosen_date
                ]

                st.metric(
                    "Records on selected date",
                    len(selected_records)
                )

                st.dataframe(
                    selected_records[
                        ["symptom", "severity", "notes"]
                    ].rename(
                        columns={
                            "symptom": "Symptom",
                            "severity": "Severity",
                            "notes": "Notes"
                        }
                    ),
                    use_container_width=True,
                    hide_index=True
                )

            st.caption(
                "This calendar displays saved entries only. "
                "It does not diagnose conditions or predict symptoms."
            )


# -------------------------------
# Symptom Trend Comparison page
# -------------------------------
elif page == "Symptom Trend Comparison":
    st.title("📈 Symptom Trend Comparison")
    st.write(
        "Compare symptom records across two date ranges. "
        "The comparison reflects recorded entries only; "
        "it does not indicate whether a medical condition is improving."
    )

    trend_history = get_symptoms()

    if trend_history.empty:
        st.info(
            "No symptom records are available yet. "
            "Add records on the Symptom Tracking page first."
        )
    else:
        trend_history["date"] = pd.to_datetime(
            trend_history["date"], errors="coerce"
        )
        trend_history = trend_history.dropna(subset=["date"])

        if trend_history.empty:
            st.warning("No valid symptom dates were found.")
        else:
            min_date = trend_history["date"].min().date()
            max_date = trend_history["date"].max().date()

            st.subheader("Choose the First Date Range")
            col1, col2 = st.columns(2)

            with col1:
                first_start = st.date_input(
                    "First range — start date",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="trend_first_start"
                )

            with col2:
                first_end = st.date_input(
                    "First range — end date",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="trend_first_end"
                )

            st.subheader("Choose the Second Date Range")
            col3, col4 = st.columns(2)

            with col3:
                second_start = st.date_input(
                    "Second range — start date",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="trend_second_start"
                )

            with col4:
                second_end = st.date_input(
                    "Second range — end date",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="trend_second_end"
                )

            if first_start > first_end or second_start > second_end:
                st.error(
                    "For both ranges, the start date must be "
                    "on or before the end date."
                )
            else:
                first_data = trend_history[
                    (trend_history["date"].dt.date >= first_start)
                    & (trend_history["date"].dt.date <= first_end)
                ].copy()

                second_data = trend_history[
                    (trend_history["date"].dt.date >= second_start)
                    & (trend_history["date"].dt.date <= second_end)
                ].copy()

                st.divider()
                st.subheader("Comparison Summary")

                first_count = len(first_data)
                second_count = len(second_data)
                difference = second_count - first_count

                col1, col2, col3 = st.columns(3)
                col1.metric("First Range Records", first_count)
                col2.metric("Second Range Records", second_count)
                col3.metric(
                    "Change in Record Count",
                    difference,
                    delta=f"{difference:+d} records"
                )

                st.caption(
                    "A higher or lower record count does not necessarily "
                    "mean symptoms became better or worse."
                )

                st.subheader("Compare Individual Symptoms")

                first_counts = first_data["symptom"].value_counts()
                second_counts = second_data["symptom"].value_counts()

                all_symptoms = sorted(
                    set(first_counts.index) | set(second_counts.index)
                )

                comparison = pd.DataFrame({
                    "Symptom": all_symptoms,
                    "First Range": [
                        int(first_counts.get(symptom, 0))
                        for symptom in all_symptoms
                    ],
                    "Second Range": [
                        int(second_counts.get(symptom, 0))
                        for symptom in all_symptoms
                    ]
                })

                if comparison.empty:
                    st.info(
                        "No symptom records were found in either "
                        "selected date range."
                    )
                else:
                    comparison["Difference"] = (
                        comparison["Second Range"]
                        - comparison["First Range"]
                    )

                    st.dataframe(
                        comparison,
                        use_container_width=True,
                        hide_index=True
                    )

                    chart_data = comparison.melt(
                        id_vars="Symptom",
                        value_vars=["First Range", "Second Range"],
                        var_name="Date Range",
                        value_name="Records"
                    )

                    fig = px.bar(
                        chart_data,
                        x="Symptom",
                        y="Records",
                        color="Date Range",
                        barmode="group",
                        title="Symptom Records Across Two Date Ranges",
                        text="Records"
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    st.download_button(
                        "Download Trend Comparison (CSV)",
                        data=comparison.to_csv(index=False).encode("utf-8"),
                        file_name="herhealth_symptom_trend_comparison.csv",
                        mime="text/csv"
                    )


elif page == "Complete Health Report":
    st.title("📦 Complete Health Report")
    st.write(
        "Download your symptom history, period history, "
        "reminder history, and health summary."
    )

    symptoms_report = get_symptoms().drop(
        columns=["id"], errors="ignore"
    )
    cycles_report = get_cycle_history().drop(
        columns=["id"], errors="ignore"
    )
    reminders_report = get_reminders().drop(
        columns=["id"], errors="ignore"
    )

    severe_count = 0
    if not symptoms_report.empty:
        severe_count = int(
            symptoms_report["severity"]
            .astype(str)
            .str.lower()
            .eq("severe")
            .sum()
        )

    completed_count = 0
    if not reminders_report.empty:
        completed_count = int(
            reminders_report["status"]
            .astype(str)
            .str.lower()
            .eq("completed")
            .sum()
        )

    summary_report = pd.DataFrame(
        [
            ["Total symptom records", len(symptoms_report)],
            ["Severe symptom records", severe_count],
            ["Period start dates recorded", len(cycles_report)],
            ["Total reminders", len(reminders_report)],
            ["Completed reminders", completed_count],
        ],
        columns=["Metric", "Value"],
    )

    
    # Report date-range filter
    st.subheader("Filter Report by Date")

    today = pd.Timestamp.today().date()

    date_col1, date_col2 = st.columns(2)

    with date_col1:
        report_start_date = st.date_input(
            "Start date",
            value=today.replace(day=1),
            key="complete_report_start_date",
        )

    with date_col2:
        report_end_date = st.date_input(
            "End date",
            value=today,
            key="complete_report_end_date",
        )

    if report_start_date > report_end_date:
        st.error("Start date must be before or equal to end date.")
        st.stop()

    # Keep only records within the selected date range
    symptoms_report = symptoms_report.copy()
    cycles_report = cycles_report.copy()
    reminders_report = reminders_report.copy()

    if not symptoms_report.empty:
        symptoms_report["date"] = pd.to_datetime(
            symptoms_report["date"], errors="coerce"
        ).dt.date

        symptoms_report = symptoms_report[
            (symptoms_report["date"] >= report_start_date)
            & (symptoms_report["date"] <= report_end_date)
        ]

    if not cycles_report.empty:
        cycles_report["start_date"] = pd.to_datetime(
            cycles_report["start_date"], errors="coerce"
        ).dt.date

        cycles_report = cycles_report[
            (cycles_report["start_date"] >= report_start_date)
            & (cycles_report["start_date"] <= report_end_date)
        ]

    if not reminders_report.empty:
        reminders_report["reminder_date"] = pd.to_datetime(
            reminders_report["reminder_date"], errors="coerce"
        ).dt.date

        reminders_report = reminders_report[
            (reminders_report["reminder_date"] >= report_start_date)
            & (reminders_report["reminder_date"] <= report_end_date)
        ]


    st.subheader("Health Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Symptom Records", len(symptoms_report))
    col2.metric("Period Dates", len(cycles_report))
    col3.metric("Reminders", len(reminders_report))

    st.dataframe(summary_report, use_container_width=True)

    
    # Visual summary of filtered symptom records
    st.subheader("Symptom Analysis")

    if symptoms_report.empty:
        st.info("No symptom records found in the selected date range.")
    else:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.write("**Most Frequently Recorded Symptoms**")

            symptom_counts = (
                symptoms_report["symptom"]
                .value_counts()
                .reset_index()
            )
            symptom_counts.columns = ["Symptom", "Records"]

            symptom_chart = px.bar(
                symptom_counts,
                x="Symptom",
                y="Records",
                title="Symptom Frequency",
                text="Records",
            )
            st.plotly_chart(
                symptom_chart,
                use_container_width=True,
            )

        with chart_col2:
            st.write("**Severity Distribution**")

            severity_counts = (
                symptoms_report["severity"]
                .value_counts()
                .reset_index()
            )
            severity_counts.columns = ["Severity", "Records"]

            severity_chart = px.pie(
                severity_counts,
                names="Severity",
                values="Records",
                title="Recorded Symptom Severity",
                hole=0.35,
            )
            st.plotly_chart(
                severity_chart,
                use_container_width=True,
            )

    
    # Report preview
    st.subheader("Report Preview")

    with st.expander("View symptom records", expanded=False):
        if symptoms_report.empty:
            st.info("No symptom records for the selected dates.")
        else:
            st.dataframe(
                symptoms_report,
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("View menstrual cycle history", expanded=False):
        if cycles_report.empty:
            st.info("No period records for the selected dates.")
        else:
            st.dataframe(
                cycles_report,
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("View reminder history", expanded=False):
        if reminders_report.empty:
            st.info("No reminders for the selected dates.")
        else:
            st.dataframe(
                reminders_report,
                use_container_width=True,
                hide_index=True,
            )

    st.caption(
        "Review the filtered records above before downloading the PDF or ZIP report."
    )


    # ZIP download containing four CSV files
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer, "w", zipfile.ZIP_DEFLATED
    ) as zip_file:
        zip_file.writestr(
            "symptom_history.csv",
            symptoms_report.to_csv(index=False),
        )
        zip_file.writestr(
            "period_history.csv",
            cycles_report.to_csv(index=False),
        )
        zip_file.writestr(
            "reminder_history.csv",
            reminders_report.to_csv(index=False),
        )
        zip_file.writestr(
            "health_summary.csv",
            summary_report.to_csv(index=False),
        )

    st.download_button(
        "⬇️ Download Complete Report (ZIP)",
        data=zip_buffer.getvalue(),
        file_name="herhealth_complete_report.zip",
        mime="application/zip",
        key="complete_report_zip",
    )

    # PDF download
    pdf_buffer = io.BytesIO()

    pdf_document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    content = [
        Paragraph("HerHealth - Complete Health Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            "Women's Health Monitoring and Awareness",
            styles["Normal"],
        ),
        Spacer(1, 16),
    ]

    def add_pdf_section(title, dataframe):
        content.append(Paragraph(title, styles["Heading2"]))
        content.append(Spacer(1, 8))

        if dataframe.empty:
            content.append(
                Paragraph("No records available.", styles["Normal"])
            )
            content.append(Spacer(1, 12))
            return

        table_data = [
            [Paragraph(str(column), styles["BodyText"])
             for column in dataframe.columns]
        ]

        for _, record in dataframe.iterrows():
            row = []
            for value in record:
                text_value = "" if pd.isna(value) else str(value)
                text_value = (
                    text_value.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                row.append(
                    Paragraph(text_value, styles["BodyText"])
                )
            table_data.append(row)

        available_width = landscape(A4)[0] - 60
        column_count = max(len(dataframe.columns), 1)
        column_width = available_width / column_count

        report_table = Table(
            table_data,
            colWidths=[column_width] * column_count,
            repeatRows=1,
        )
        report_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        content.append(report_table)
        content.append(Spacer(1, 16))

    add_pdf_section("1. Health Summary", summary_report)
    add_pdf_section("2. Symptom History", symptoms_report)
    add_pdf_section("3. Menstrual Cycle History", cycles_report)
    add_pdf_section("4. Health Reminder History", reminders_report)

    content.append(
        Paragraph(
            "This report summarizes information entered into HerHealth. "
            "It does not diagnose medical conditions.",
            styles["Italic"],
        )
    )

    pdf_document.build(content)

    st.download_button(
        "⬇️ Download Complete Report (PDF)",
        data=pdf_buffer.getvalue(),
        file_name="herhealth_complete_report.pdf",
        mime="application/pdf",
        key="complete_report_pdf",
    )


# -------------------------------
# Footer
# -------------------------------
st.divider()
st.caption("HerHealth | Your health, your awareness, your wellbeing.")
