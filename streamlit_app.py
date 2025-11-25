import datetime

import pandas as pd
import streamlit as st
from inspirational_quotes import quote

from constants import TYPE_COLORS

st.set_page_config(page_title="Marathon Training Dashboard", layout="wide")


# -------------------------------
# ----- Load & Setup Data -------
# -------------------------------

df = pd.read_csv("data/higdon_intermediate.csv")
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

today = pd.Timestamp("2026-02-11")

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
    "Goal Marathon Time (HH:MM:SS)", value=datetime.time(hour=3, minute=40)
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


@st.cache_data
def get_daily_quote(day_str: str):
    # cache keyed by the day string so the quote changes once per day
    return quote()


q = get_daily_quote(today.strftime("%Y-%m-%d"))
st.markdown(f"> _{q['quote']}_ \n — {q['author']}")

# ---- PROGRESS BAR --------------------------------------------------
st.markdown("### Training Progress")
st.progress(progress_pct / 100)
st.write(f"**{progress_pct}% complete** ({days_completed} / {days_total} days)")


st.divider()
# ---- NEXT 7 DAYS (ROLLING) ----------------------------------------


st.subheader(f"Today: {today.strftime('%A, %B %d, %Y')}")
# Build a rolling window: today + next 6 days
start_day = today
days = [start_day + pd.Timedelta(days=i) for i in range(7)]
df["week"] = ((df["date"] - start_date).dt.days // 7 + 1).astype(int)
current_week = int(((today - start_date).days // 7) + 1)

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

# Sidebar controls for chart bounds
st.sidebar.subheader("Weekly Mileage Chart")
use_custom_bounds = st.sidebar.checkbox("Set custom y-axis bounds", value=False)
default_max = (
    float(weekly["distance"].max() * 1.05) if not weekly["distance"].empty else 10.0
)
if use_custom_bounds:
    y_min = float(st.sidebar.number_input("Y-axis min", value=1, step=1))
    y_max = float(st.sidebar.number_input("Y-axis max", value=default_max, step=1))
else:
    y_min = 0
    y_max = default_max

try:
    import altair as alt

    area = (
        alt.Chart(weekly)
        .mark_area(color="#1f77b4", opacity=0.4)
        .encode(
            x=alt.X("week:Q", title="Week"),
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
        .mark_text(align="left", dx=5, dy=-5, color="red")
        .encode(x="week:Q", text=alt.value(f"Week {current_week}"))
    )

    chart = (area + rule + label).properties(width=700, height=300)
    st.altair_chart(chart, use_container_width=True)
except Exception:
    # Fallback to line chart if Altair isn't available or fails
    st.warning("Altair chart failed or is not installed; showing simple line chart.")
    st.line_chart(weekly, x="week", y="distance")

# ---- RAW DATA -------------------------------------------------------
with st.expander("Show Full Training Plan Table"):
    st.dataframe(df)
