import datetime

import altair as alt
import pandas as pd
import streamlit as st
from inspirational_quotes import quote

from constants import TYPE_COLORS
from utils import format_pace, get_recommended_lift_of_the_week

st.set_page_config(page_title="Marathon Training Dashboard", layout="wide")


# -------------------------------
# ----- Load & Setup Data -------
# -------------------------------

df = pd.read_csv("data/higdon_intermediate1.csv")
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

today = pd.Timestamp("2026-02-04")


# Streamlit slider wants native datetime.date (or datetime); convert to/from pandas Timestamp
selected_date = st.sidebar.slider(
    "Date Selector",
    min_value=df["date"].min().date(),
    max_value=df["date"].max().date(),
    value=today.date(),
    format="MM/DD/YYYY",
)
today = pd.Timestamp(selected_date)

# Lock plan out at max date
if today > df["date"].max():
    today = df["date"].max()

# Training start & end
start_date = df["date"].min()
end_date = df["date"].max()

# Key metadata
start_day = today
days = [start_day + pd.Timedelta(days=i) for i in range(7)]
df["week"] = ((df["date"] - start_date).dt.days // 7 + 1).astype(int)
current_week = int(((today - start_date).days // 7) + 1)

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
    "Goal Marathon Time (HH:MM:SS)", value=datetime.time(hour=3, minute=40)
)

# Convert marathon goal time to minutes per mile
goal_seconds = (
    goal_marathon_time.hour * 3600
    + goal_marathon_time.minute * 60
    + goal_marathon_time.second
)
goal_pace_seconds = goal_seconds / 26.2


# Long run pace suggestions (rough guideline)
easy_lr_pace = goal_pace_seconds + 60  # 1:00 slower than MP
easy_lr_pace_fast = goal_pace_seconds + 30  # 0:30 slower than MP

long_run_pace_range = f"{format_pace(easy_lr_pace_fast)} – {format_pace(easy_lr_pace)}"


# -------------------------------
# --------- Dashboard -----------
# -------------------------------

st.title("Marathon Training Dashboard")


@st.cache_data
def get_daily_quote(day_str: str):
    # cache keyed by the day string so the quote changes once per day
    return quote()


q = get_daily_quote(today.strftime("%Y-%m-%d"))
st.markdown(f"> _{q['quote']}_ \n — {q['author']}")

# ---- PROGRESS BAR --------------------------------------------------
st.markdown(f"### Training Progress - Week {current_week}")
st.progress(progress_pct / 100)
st.write(f"**{progress_pct}% complete** ({days_completed} / {days_total} days)")

st.divider()

# ---- NEXT 7 DAYS (ROLLING) ----------------------------------------
st.subheader(f"Today: {today.strftime('%A, %B %d, %Y')}")
# Build a rolling window: today + next 6 days

cols = st.columns(7)

for col, day in zip(cols, days):
    # find run for the day
    day_row = df[df["date"] == day]
    is_today = day == today
    with col:
        # slightly larger styling for today's tile
        min_height = 200 if is_today else 120
        if len(day_row) == 0:
            # no run scheduled
            st.markdown(
                f"""
                <div style="
                    background-color:#374151;
                    padding:12px;
                    border-radius:8px;
                    min-height:120px;
                    color:#fff;
                    text-align:center;
                ">
                    <strong>{day.strftime("%a")}</strong><br>
                    {day.strftime("%m/%d")}<br><br>
                    <em>Rest</em>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            r = day_row.iloc[0]
            run_type_key = r["Type"].lower()
            bg = TYPE_COLORS.get(run_type_key, "#374151")
            is_long = run_type_key == "long"

            st.markdown(
                f"""
                <div style="
                    background-color:{bg};
                    padding:16px;
                    border-radius:12px;
                    min-height:120px;
                    color:#fff;
                ">
                    <strong>{r["dow"][:3]}</strong><br>
                    {r["date"].strftime("%m/%d")}<br><br>
                    <div style="font-size:20px; font-weight:700; line-height:1;">{r["distance"]} mi</div>
                    <div style="margin-top:6px; font-style:italic">{r["Type"]}</div>
                    {"<div style='margin-top:8px'><strong>Pace:</strong> " + long_run_pace_range + "</div>" if is_long else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )


rec = get_recommended_lift_of_the_week(current_week)

html = """
<style>
.lift-table {border-collapse: collapse; width: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;}
.lift-table thead th {background:#111827; color:#ffffff; padding:10px 12px; text-align:left; font-size:14px;}
.lift-table tbody td {padding:10px 12px; border-bottom:1px solid #e5e7eb; font-size:13px; color:#0f172a;}
.lift-table tbody tr:hover {background: #f8fafc;}
.lift-table tbody td:first-child {font-weight:600; width:30%;}
</style>

<table class="lift-table" role="table" aria-label="Recommended lift of the week">
    <thead>
        <tr><th>Muscle Group</th><th>Exercise</th></tr>
    </thead>
    <tbody>
"""

for key in ("legs", "core", "upper body"):
    exercise = rec.get(key, "-")
    html += f"<tr><td>{key.capitalize()}</td><td>{exercise}</td></tr>"

html += "</tbody></table>"

st.markdown("_Recommended lift of the week:_")
st.markdown(html, unsafe_allow_html=True)


st.divider()

# ---- WEEKLY MILEAGE CHART -------------------------------------------
st.markdown("### Weekly Mileage")

weekly = df.groupby("week")["distance"].sum().reset_index()


default_max = (
    int(weekly["distance"].max() * 1.05) if not weekly["distance"].empty else 10
)
y_min = 0
y_max = default_max

try:
    # ensure a safe integer domain for the x axis
    x_min = 1
    x_max = 18

    area = (
        alt.Chart(weekly)
        .mark_area(color="#1f77b4", opacity=0.4)
        .encode(
            x=alt.X(
                "week:Q",
                title="Week",
                axis=alt.Axis(tickMinStep=1, format="d"),
                scale=alt.Scale(domain=[x_min, x_max]),
            ),
            y=alt.Y(
                "distance:Q",
                title="Distance (miles)",
                scale=alt.Scale(domain=[y_min, y_max]),
            ),
            tooltip=[
                alt.Tooltip("week:Q", title="Week"),
                alt.Tooltip("distance:Q", title="Mileage"),
            ],
        )
    )

    # Vertical rule for current week
    rule_df = pd.DataFrame({"week": [current_week]})
    rule = alt.Chart(rule_df).mark_rule(color="red", strokeWidth=2).encode(x="week:Q")
    label = (
        alt.Chart(rule_df)
        .mark_text(align="left", dx=7, dy=-5, color="black", size=15)
        .encode(x="week:Q", text=alt.value(f"Week {current_week}"))
    )

    chart = (area + rule + label).properties(width=700, height=300)
    st.altair_chart(chart, width="stretch")
except Exception:
    # Fallback to line chart if Altair isn't available or fails
    st.warning("Altair chart failed or is not installed; showing simple line chart.")
    st.line_chart(weekly, x="week", y="distance")

# ---- RAW DATA -------------------------------------------------------
with st.expander("Show Full Training Plan Table"):
    st.dataframe(df)
