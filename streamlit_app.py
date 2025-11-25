import datetime

import pandas as pd
import streamlit as st

from constants import TYPE_COLORS

st.set_page_config(page_title="Marathon Training Dashboard", layout="wide")


# -------------------------------
# ----- Load & Setup Data -------
# -------------------------------

st.sidebar.header("Runner")

runner = st.sidebar.selectbox("Select runner:", ["Josh", "Andrew"])

file_map = {"Josh": "data/plan_josh.csv", "Andrew": "data/plan_andrew.csv"}

df = pd.read_csv(file_map[runner])
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

today = pd.Timestamp("2026-02-09")

# Training start & end
start_date = df["date"].min()
end_date = df["date"].max()

# Training progress %
days_total = (end_date - start_date).days + 1
days_completed = max(0, (today - start_date).days)
progress_pct = min(100, round(days_completed / days_total * 100, 1))

# Today's run
today_run = df[df["date"] == today]

# -------------------------------
# ---- PACE SETTINGS ------------
# -------------------------------

st.sidebar.subheader("Pace Settings")

goal_marathon_time = st.sidebar.time_input(
    "Goal Marathon Time (HH:MM:SS)", value=datetime.time(hour=3, minute=15)
)

# Convert marathon goal time to minutes per mile
goal_seconds = (
    goal_marathon_time.hour * 3600
    + goal_marathon_time.minute * 60
    + goal_marathon_time.second
)
goal_pace_seconds = goal_seconds / 26.2


def format_pace(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m}:{s:02d}/mi"


# Long run pace suggestions (rough guideline)
easy_lr_pace = goal_pace_seconds + 60  # 1:00 slower than MP
easy_lr_pace_fast = goal_pace_seconds + 30  # 0:30 slower than MP

long_run_pace_range = f"{format_pace(easy_lr_pace_fast)} – {format_pace(easy_lr_pace)}"


# -------------------------------
# --------- Dashboard -----------
# -------------------------------

st.title("🏃 Marathon Training Dashboard")

# ---- TODAY’S RUN ---------------------------------------------------
st.subheader("Today's Run")

if len(today_run) == 0:
    st.info("No scheduled run today.")
else:
    row = today_run.iloc[0]
    pace_note = ""

    if row["Type"].lower() == "long":
        pace_note = f"\n\n**Suggested Long-Run Pace:** {long_run_pace_range}"

    st.markdown(f"""
    ### **{row["distance"]} miles** – {row["Type"]}
    **Day:** {row["dow"]}  
    **Date:** {row["date"].date()}
    {pace_note}
    """)

# ---- PROGRESS BAR --------------------------------------------------
st.markdown("### Training Progress")
st.progress(progress_pct / 100)
st.write(f"**{progress_pct}% complete** ({days_completed} / {days_total} days)")

# ---- WEEK OVERVIEW (HORIZONTAL) ----
st.subheader("This Week Overview")
# calculate week number starting from start_date (week 1 starts on start_date)
df["week"] = ((df["date"] - start_date).dt.days // 7 + 1).astype(int)
current_week = int(((today - start_date).days // 7) + 1)
week_plan = df[df["week"] == current_week]

if len(week_plan) == 0:
    st.info("No scheduled runs this week.")
else:
    cols = st.columns(len(week_plan))

    for col, (_, r) in zip(cols, week_plan.iterrows()):
        run_type_key = r["Type"].lower()
        bg = TYPE_COLORS.get(run_type_key, "#374151")  # choose tile color
        is_long = run_type_key == "long"

        with col:
            st.markdown(
                f"""
                <div style="
                    background-color:{bg};
                    padding:12px;
                    border-radius:8px;
                    min-height:120px;
                    color:#fff;
                ">
                    <strong>{r["dow"]}</strong><br>
                    {r["date"].strftime("%m/%d")}<br><br>
                    {r["distance"]} miles<br>
                    <em>{r["Type"]}</em>
                    {"<br><br><strong>LR Pace:</strong><br>" + long_run_pace_range if is_long else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )
# ---- WEEKLY MILEAGE CHART -------------------------------------------
st.markdown("### Weekly Mileage")

weekly = df.groupby("week")["distance"].sum().reset_index()

st.line_chart(
    weekly,
    x="week",
    y="distance",
)

# ---- RAW DATA -------------------------------------------------------
with st.expander("Show Full Training Plan Table"):
    st.dataframe(df)
