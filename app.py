import streamlit as st
# MUST be first Streamlit command
st.set_page_config(page_title="SwimTrack", layout="wide")
import pandas as pd
import calendar
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, time as dtime, timedelta

import gspread
from google.oauth2.service_account import Credentials

def connect_gsheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    return client.open_by_key("1o9Uy0hnZXRh5GYUsMaQjMoqkgyaqaRQ9m1PDoCJwilE")

# --- LOGIN LOGIC ---
ADMIN_PASSWORD = "mine1"

if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = ""

# --- LOGIN SCREEN ---
if st.session_state.user_role is None:

    st.markdown("""
    <style>
    .login-container {
        display: flex;
        height: 80vh;
        border-radius: 20px;
        overflow: hidden;
        background: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .left-panel {
        flex: 1;
        padding: 40px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .right-panel {
        flex: 1;
        background: linear-gradient(135deg, #6fb1fc, #4364f7);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 30px;
    }
    .title-text {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("<div class='left-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='title-text'>🏊‍♂️ Welcome to SwimTrack</div>", unsafe_allow_html=True)

        role = st.radio("Login Type", ["Guest", "Admin"], horizontal=True)

        if role == "Guest":
            name = st.text_input("Enter your name")
            if st.button("Continue as Guest", use_container_width=True):
                if name.strip():
                    st.session_state.user_role = "guest"
                    st.session_state.logged_in_user = name.strip()
                    st.session_state.selected_student = ""
                    st.rerun()
                else:
                    st.warning("Enter valid name")

        elif role == "Admin":
            pwd = st.text_input("Enter password", type="password")
            if st.button("Login as Admin", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.user_role = "admin"
                    st.rerun()
                else:
                    st.error("Invalid password")

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='right-panel'>", unsafe_allow_html=True)
        st.markdown("""
        <h2>Start your journey</h2>
        <p>Learn a life skill and enjoy swimming</p>
        <h3>🏊‍♂️</h3>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# --- CONFIG & PERSISTENCE ---
## st.set_page_config(page_title="SwimTrack Pro", layout="wide")  # REMOVED DUPLICATE
DATA_FILE = "swim_data.json"

def load_data():
    sheet = connect_gsheet()
    students_sheet = sheet.worksheet("students")
    bookings_sheet = sheet.worksheet("bookings")

    students = students_sheet.get_all_records()
    bookings = bookings_sheet.get_all_records()

    student_list = [s.get("name") for s in students if s.get("name")]

    for b in bookings:
        b['start_date'] = datetime.strptime(b['start_date'], "%Y-%m-%d").date()
        
        if b.get('end_date'):
            b['end_date'] = datetime.strptime(b['end_date'], "%Y-%m-%d").date()

        b['days'] = b.get('days', "").split(",")

        # Safe defaults (important)
        b.setdefault("address", "")
        b.setdefault("status", "Pending")
        b.setdefault("method", None)
        b.setdefault("created_by", "unknown")
        b.setdefault("duration", 60)

    return {"students": student_list, "bookings": bookings}

def save_data():
    try:
        sheet = connect_gsheet()
        
        students_ws = sheet.worksheet("students")
        bookings_ws = sheet.worksheet("bookings")

        # Clear existing data (keep headers)
        students_ws.clear()
        bookings_ws.clear()

        # Re-add headers
        students_ws.append_row(["name"])
        bookings_ws.append_row([
            "id","student","created_by","days","start_date","end_date",
            "package","time","fee","status","method","duration","address"
        ])

        # Save students
        for s in st.session_state.students:
            students_ws.append_row([s])

        # Save bookings
        for b in st.session_state.bookings:
            bookings_ws.append_row([
                b.get("id"),
                b.get("student"),
                b.get("created_by"),
                ",".join(b.get("days", [])),
                str(b.get("start_date")),
                str(b.get("end_date")),
                b.get("package"),
                b.get("time"),
                b.get("fee"),
                b.get("status"),
                b.get("method"),
                b.get("duration"),
                b.get("address")
            ])

    except Exception as e:
        st.error(f"Error saving data: {e}")

    # Removed JSON save block as per instructions

if 'students' not in st.session_state:
    saved = load_data()
    st.session_state.students, st.session_state.bookings = saved["students"], saved["bookings"]
    st.session_state.view_date = datetime.now()
    st.session_state.active_tab_index = 0

if 'selected_student' not in st.session_state:
    st.session_state.selected_student = ""
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None  

def get_student_color(name):
    return f"#{hashlib.md5(name.encode()).hexdigest()[:6]}"

days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# --- GLOBAL CSS ---
st.markdown("""
<style>
    .month-title { text-align: center; font-size: 2rem; font-weight: bold; margin-bottom: 10px; }
    .calendar-header { text-align: center; font-weight: bold; background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; font-size: 0.8rem; }
    .calendar-cell { border: 1px solid #dee2e6; min-height: 140px; padding: 5px; background-color: white; }
    .student-tile { color: white; font-size: 0.65rem; padding: 4px 6px; border-radius: 4px; margin-bottom: 4px; line-height: 1.1; font-weight: 600; }
    .completed-tile { background: #e5e5ea !important; color: #a1a1a6 !important; text-decoration: line-through; font-size: 0.65rem; padding: 4px 6px; border-radius: 4px; margin-bottom: 4px; line-height: 1.1; font-weight: 400; border: 1px solid #d1d1d6; }
    
    .premium-card { background: white; padding: 25px; border-radius: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #f0f0f0; width: 100%; max-width: 600px; margin: auto; }
    .label-text { color: #888; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; }
    .student-name { font-size: 1.8rem; font-weight: 800; color: #1d1d1f; margin-top: 5px; }
    .badge-row { display: flex; gap: 8px; margin: 15px 0; }
    .pill { background: #f2f2f7; color: #666; padding: 6px 12px; border-radius: 20px; font-size: 0.75rem; }
    .camp-badge { background: #a33b3b; color: white; padding: 6px 15px; border-radius: 20px; font-size: 0.7rem; font-weight: bold; float: right; }
    .price-text { font-size: 2.2rem; font-weight: 800; color: #1d1d1f; }
    .divider { border-top: 1px solid #eee; margin: 15px 0; }
</style>
""", unsafe_allow_html=True)

# --- GLOBAL UI CSS (custom) ---
st.markdown("""
<style>
.stTextInput, .stNumberInput, .stDateInput, .stSelectbox {
    width: 100% !important;
}
div[data-baseweb="select"] {
    width: 100% !important;
}
input {
    border-radius: 10px !important;
}
button {
    border-radius: 10px !important;
    height: 45px !important;
}
</style>
""", unsafe_allow_html=True)

# --- ENLARGE CODE INPUT BOX CSS ---
st.markdown("""
<style>
div[data-baseweb="input"] {
    width: 100% !important;
}

div[data-baseweb="input"] input {
    height: 52px !important;
    font-size: 18px !important;
    padding: 12px !important;
}
</style>
""", unsafe_allow_html=True)



with st.sidebar:
    if st.button("🚪 Logout"):
        st.session_state.user_role = None
        st.session_state.logged_in_user = ""
        st.rerun()

# --- INLINE TITLE & SCROLLING BANNER ---
col_title, col_banner = st.columns([3, 5])

with col_title:
    st.markdown("<h1 style='margin:0;'>🏊‍♂️ SwimTrack Pro</h1>", unsafe_allow_html=True)

with col_banner:
    st.markdown("""
    <style>
    .scrolling-banner-inline {
        width: 100%;
        overflow: hidden;
        white-space: nowrap;
        position: relative;
        margin-top: 15px;
    }
    .scrolling-banner-inline1 {
        width: 100%;
        overflow: hidden;
        white-space: nowrap;
        position: relative;
        margin-top: 15px;
    }
    .scrolling-text-inline {
        display: inline-block;
        padding-left: 100%;
        animation: scroll-left-inline 12s linear infinite;
        font-weight: 600;
        color: #1f77b4;
        font-size: 1rem;
    }
    .scrolling-text-inline-red {
        display: inline-block;
        padding-left: 100%;
        animation: scroll-left-inline 12s linear infinite;
        font-weight: 600;
        color: red;
        font-size: 1rem;
    }
    @keyframes scroll-left-inline {
        0% { transform: translateX(0%); }
        100% { transform: translateX(-100%); }
    }
    </style>

    <div class="scrolling-banner-inline">
        <div class="scrolling-text-inline">
            🏊 Swimming classes are open now!
        </div>
    </div>
    <div class="scrolling-banner-inline1">
        <div class="scrolling-text-inline-red">
            Note: I will be not available from May 25th, 2026 onwards..
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- USER IDENTITY DISPLAY ---
if st.session_state.user_role == "guest":
    st.markdown(f"👤 **Logged in as:** {st.session_state.logged_in_user}")
elif st.session_state.user_role == "admin":
    st.markdown("🔐 **Admin Mode**")

# --- TAB SELECTION BASED ON ROLE ---
if st.session_state.user_role == "guest":
    tab_list = ["📝 Enrollment & Swimmer"]
else:
    tab_list = ["📅 Monthly Calendar", "📝 Enrollment & Swimmer", "💰 Payments"]

chosen_tab = st.radio("Nav", tab_list, horizontal=True, label_visibility="collapsed")

if 'active_tab_index' not in st.session_state:
    st.session_state.active_tab_index = 0

# --- SAFE TAB INDEX HANDLING ---
if st.session_state.active_tab_index >= len(tab_list):
    st.session_state.active_tab_index = 0

if tab_list[st.session_state.active_tab_index] != chosen_tab:
    st.session_state.active_tab_index = tab_list.index(chosen_tab)
    st.rerun()

# --- TAB 1 & 2 (Kept fully functional) ---
if chosen_tab == "📅 Monthly Calendar":
    now = datetime.now(); today_date, current_time = now.date(), now.time()
    h_col1, h_center, _ = st.columns([1, 3, 1])
    with h_col1:
        with st.popover("📅 Select Month"):
            m_name = st.selectbox("Month", list(calendar.month_name)[1:], index=st.session_state.view_date.month-1)
            y_val = st.number_input("Year", value=st.session_state.view_date.year)
            if st.button("Apply"): st.session_state.view_date = datetime(y_val, list(calendar.month_name).index(m_name), 1); st.rerun()
    with h_center: st.markdown(f"<div class='month-title'>{calendar.month_name[st.session_state.view_date.month]} {st.session_state.view_date.year}</div>", unsafe_allow_html=True)
    cal = calendar.monthcalendar(st.session_state.view_date.year, st.session_state.view_date.month)
    h_cols = st.columns(7)
    for i, d in enumerate(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]): h_cols[i].markdown(f"<div class='calendar-header'>{d}</div>", unsafe_allow_html=True)
    for week in cal:
        w_cols = st.columns(7)
        for i, day_val in enumerate(week):
            with w_cols[i]:
                if day_val != 0:
                    html = f"<div class='calendar-cell'><div class='day-num' style='color:#ccc; font-size:0.8rem;'>{day_val}</div>"
                    curr_d = datetime(st.session_state.view_date.year, st.session_state.view_date.month, day_val).date()
                    for b in st.session_state.bookings:
                        if days_names[i] in b['days'] and b['start_date'] <= curr_d <= b.get('end_date', curr_d):
                            is_passed = (curr_d < today_date) or (curr_d == today_date and current_time > datetime.strptime(b['time'].split('-')[0], "%I:%M%p").time())
                            style = "completed-tile" if is_passed else "student-tile"
                            color = b.get("color", get_student_color(b.get("student", "")))
                            bg = "" if is_passed else f"background:{color};"
                            html += f"<div class='{style}' style='{bg}'><b>{b['student']}</b><br>{b['time']}</div>"
                    html += "</div>"; st.markdown(html, unsafe_allow_html=True)
                else: st.markdown("<div class='calendar-cell' style='background-color:#fcfcfc;'></div>", unsafe_allow_html=True)

elif chosen_tab == "📝 Enrollment & Swimmer":
    col_manage, col_enroll = st.columns([1.2, 2])
    with col_manage:
        st.subheader("👥 Swimmers")
        with st.container(border=True, height=540):
            new_n = st.text_input("Register Swimmer Name")
            if st.button("Add Swimmer", use_container_width=True):
                clean_name = new_n.strip()
                if clean_name and clean_name not in st.session_state.students:
                    st.session_state.students.append(clean_name)
                    st.session_state.selected_student = clean_name
                    save_data()
                    st.rerun()
            st.divider()
            for idx, s in enumerate(sorted(st.session_state.students)):
                col1, col2, col3 = st.columns([4,1,1])
                if col1.button(f"🔵 {s}" if st.session_state.selected_student == s else s,
                               key=f"sel_{s}_{idx}", use_container_width=True):
                    st.session_state.selected_student = s
                    st.rerun()
                if col2.button("✏️", key=f"edit_{s}_{idx}"):
                    for i, b in enumerate(st.session_state.bookings):
                        if b["student"] == s:
                            st.session_state.edit_mode = True
                            st.session_state.edit_index = i
                            st.rerun()
                if col3.button("🗑️", key=f"del_{s}_{idx}"):
                    st.session_state.bookings = [b for b in st.session_state.bookings if b["student"] != s]
                    st.session_state.students = [st for st in st.session_state.students if st != s]
                    save_data()
                    st.rerun()
    with col_enroll:
        st.subheader("📝 Book Your Slot")
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True, height=540):
            c1, c2 = st.columns([1, 1], gap="large")
            if st.session_state.edit_mode and st.session_state.edit_index is not None:
                edit_b = st.session_state.bookings[st.session_state.edit_index]
                st_name = edit_b['student']
            else:
                st_name = st.session_state.selected_student
            c1.text_input("Select Swimmer*", value=st_name, disabled=True)
            if not st_name:
                st.warning("Select a swimmer from the left panel")
            # --- Start Date ---
            default_start = edit_b['start_date'] if st.session_state.edit_mode else datetime.now()
            today = datetime.now().date()
            st_start = c1.date_input("Start Date", default_start, min_value=today, key="form_start")

            # --- Package ---
            packages = ["Single Session", "Monthly (3/week)", "Custom"]
            default_pkg = packages.index(edit_b.get('package',"Single Session")) if st.session_state.edit_mode else 0
            st_package = c2.selectbox("Package", packages, index=default_pkg, key="form_package")

            # --- Class Days Logic ---
            default_days = edit_b['days'] if st.session_state.edit_mode else st.session_state.get("form_days", [])

            if st_package == "Single Session":
                auto_day = st_start.strftime("%A")
                st_days = [auto_day]
                st.markdown(f"📆 Class Day: **{auto_day}**")
            else:
                st_days = c1.multiselect("Class Days*", days_names, default=default_days, key="form_days")

            default_time = datetime.strptime(edit_b['time'].split('-')[0], "%I:%M%p").time() if st.session_state.edit_mode else dtime(6,30)

            # Dynamic time options (disable past times for today)
            now_dt = datetime.now()
            time_options = []
            base_time = datetime.combine(st_start, dtime(0, 0))

            for i in range(0, 24 * 60, 15):  # 15-minute slots
                t = (base_time + timedelta(minutes=i)).time()
                if st_start == now_dt.date():
                    if datetime.combine(st_start, t) >= now_dt:
                        time_options.append(t)
                else:
                    time_options.append(t)

            # Convert to display format
            time_labels = [t.strftime("%I:%M %p") for t in time_options]

            # Handle default selection safely
            try:
                default_index = next(i for i, t in enumerate(time_options) if t >= default_time)
            except:
                default_index = 0

            selected_label = c2.selectbox("Start Time", time_labels, index=default_index, key="form_time_select")
            st_time = datetime.strptime(selected_label, "%I:%M %p").time()


            if st_package == "Single Session":
                st_end = st_start
                c1.date_input("End Date", value=st_end, disabled=True)

            elif st_package == "Monthly (3/week)":
                st_end = st_start + timedelta(days=30)
                c1.date_input("End Date", value=st_end, disabled=True)

            else:
                st_end = c2.date_input("End Date", st_start + timedelta(days=7))
            st_people = c2.number_input("Total Persons", 1, 4, 1, key="form_people")
            if st_package == "Single Session":
                base = 750
            elif st_package == "Monthly (3/week)":
                base = 9000
            else:
                base = 0
            final_fee = st.number_input("Fee for Selected Package (₹)", value=int(base * st_people), key="form_fee")

            # Prefill address in edit mode
            if st.session_state.edit_mode and st.session_state.edit_index is not None:
                edit_b = st.session_state.bookings[st.session_state.edit_index]
                if "form_address" not in st.session_state:
                    st.session_state.form_address = edit_b.get("address", "")

            st_address = st.text_area(
                "Enter your location (Google Maps link or address)",
                placeholder="Paste Google Maps link or type full address",
                key="form_address"
            )

            # Initialize block flag
            is_blocked = False
            # DUPLICATE PROTECTION
            if st_name and st_days:
                new_start_dt = datetime.combine(datetime.today(), st_time)
                for idx, b in enumerate(st.session_state.bookings):
                    if st.session_state.edit_mode and idx == st.session_state.edit_index:
                        continue
                    if b['student'] == st_name:
                        ex_start_dt = datetime.combine(datetime.today(), datetime.strptime(b['time'].split('-')[0], "%I:%M%p").time())
                        st_end = st_end if 'st_end' in locals() else st_start
                        duration = b.get('duration', 60)
                        if (
                            set(st_days).intersection(set(b['days'])) and
                            not (st_end < b['start_date'] or st_start > b.get('end_date', st_start)) and
                            new_start_dt < ex_start_dt + timedelta(minutes=duration) and
                            new_start_dt + timedelta(minutes=duration) > ex_start_dt
                        ):
                            is_blocked = True
                            break

            # Prevent past date booking (extra safety)
            if st_start < datetime.now().date():
                st.error("Cannot book for past dates")
                is_blocked = True

            btn_placeholder = st.empty()

            # --- Auto reset success state (prevents stale message) ---
            if st.session_state.get("enroll_success"):
                if time.time() - st.session_state.get("enroll_time", 0) >= 2:
                    st.session_state.enroll_success = False
                    st.session_state.toast_msg = ""

            # --- Button state ---
            if st.session_state.get("enroll_success"):
                # Highlight success button with solid green (no transparency)
                st.markdown("""
                <style>
                button[kind="secondary"]:disabled {
                    background-color: #00b894 !important;
                    color: white !important;
                    opacity: 1 !important;
                    border: none !important;
                    font-weight: 700 !important;
                }
                </style>
                """, unsafe_allow_html=True)

                btn_label = st.session_state.toast_msg if st.session_state.toast_msg else "Done"
                btn_disabled = True
            else:
                btn_label = "Update Booking" if st.session_state.edit_mode else "Confirm Enrollment"
                btn_disabled = is_blocked or not (st_name and st_days)

            if btn_placeholder.button(btn_label, disabled=btn_disabled, use_container_width=True):
                duration = 60
                end_t = (datetime.combine(datetime.today(), st_time) + timedelta(minutes=duration)).time()
                if st.session_state.edit_mode:
                    st.session_state.bookings[st.session_state.edit_index].update({
                        "student": st_name,
                        "days": st_days,
                        "start_date": st_start,
                        "end_date": st_end,
                        "package": st_package,
                        "time": f"{st_time.strftime('%I:%M%p')}-{end_t.strftime('%I:%M%p')}",
                        "fee": final_fee,
                        "color": get_student_color(st_name),
                        "duration": duration,
                        "address": st_address,
                    })
                    st.session_state.edit_mode = False
                    st.session_state.edit_index = None
                    # Toast for update
                    st.session_state.toast_msg = "🔵 Successfully updated!"
                else:
                    st.session_state.bookings.append({
                        "id": str(uuid.uuid4()),
                        "student": st_name,
                        "created_by": st.session_state.logged_in_user,
                        "days": st_days,
                        "start_date": st_start,
                        "end_date": st_end, # Now correctly saves the custom end date
                        "package": st_package,
                        "time": f"{st_time.strftime('%I:%M%p')}-{end_t.strftime('%I:%M%p')}",
                        "color": get_student_color(st_name),
                        "fee": final_fee,
                        "status": "Pending",
                        "method": None,
                        "duration": duration,
                        "address": st_address,
                    })
                    # Toast for enroll
                    st.session_state.toast_msg = "🟢 Successfully enrolled!"
                save_data()
                # Show success message
                st.session_state.enroll_success = True
                st.session_state.enroll_time = time.time()

                # Reset selected student also
                st.session_state.selected_student = ""

                # Safe reset (remove keys so widgets reinitialize)
                for key in ["form_days", "form_start", "form_package", "form_time", "form_people", "form_fee", "form_address"]:
                    if key in st.session_state:
                        del st.session_state[key]

                st.session_state.active_tab_index = 1
                btn_placeholder.empty()
                st.rerun()

# --- TAB 3: PAYMENTS (NEW ALIGNMENT UNDER PRICE) ---
if chosen_tab == "💰 Payments":

    if st.session_state.user_role != "admin":
        st.warning("⚠️ Access restricted to admin only")
        st.stop()

    cats = ["Single Session", "Monthly (3/week)", "Custom"]
    p_tabs = st.tabs(cats)

    for i, cat in enumerate(cats):
        with p_tabs[i]:
            filtered = [b for b in st.session_state.bookings if b.get('package') == cat]

            if not filtered:
                st.info("No records.")
            else:
                for r_idx in range(0, len(filtered), 3):
                    row_items = filtered[r_idx:r_idx+3]
                    grid = st.columns(3)

                    for c_idx, b in enumerate(row_items):
                        with grid[c_idx]:
                            with st.container(border=True):
                                end_period = b.get('end_date', b['start_date'] + timedelta(days=30))
                                period_str = f"{b['start_date'].strftime('%b %d')} - {end_period.strftime('%b %d, %Y')}"

                                st.markdown(f"""<div class="camp-badge">{cat.upper()}</div>
                                <div class="label-text">Training Package</div>
                                <div class="student-name">{b['student']}</div>
                                <div style="color:#888; font-size:0.85rem; margin-bottom:10px;">
                                📅 Period: <b>{period_str}</b></div>
                                <div class="badge-row">
                                <div class="pill">Days: {', '.join(b['days'])}</div>
                                <div class="pill">Slot: {b['time']}</div>
                                </div>""", unsafe_allow_html=True)

                                st.markdown(f"<div class='price-text'>₹{b['fee']}/-</div>", unsafe_allow_html=True)

                                if b['status'] == "Pending":
                                    pay_m = st.radio("Select Method", ["UPI", "Cash"], key=f"p_{cat}_{r_idx}_{c_idx}", horizontal=True, label_visibility="collapsed")
                                else:
                                    st.markdown(f"<div style='color:#2e7bcf; font-weight:700; font-size:1.1rem; margin-bottom:10px;'>{b['method']}</div>", unsafe_allow_html=True)

                                st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

                                act1, act2 = st.columns([3, 1])

                                if b['status'] == "Pending":
                                    if act1.button("Payment Done", key=f"b_{cat}_{r_idx}_{c_idx}", use_container_width=True):
                                        for o in st.session_state.bookings:
                                            if o.get('id') == b.get('id'):
                                                o['status'] = "Received"
                                                o['method'] = pay_m
                                                save_data()
                                                st.rerun()
                                else:
                                    act1.markdown(f"""<div style="background-color:#f0fff4; color:#22543d; border:1px solid #c6f6d5; padding:8px; border-radius:8px; text-align:center; font-size:0.9rem; font-weight:600; height:38px; display:flex; align-items:center; justify-content:center; width:100%;">
                                    Payment Successful ({b['method']})
                                    </div>""", unsafe_allow_html=True)

                                if act2.button("🔄", key=f"res_{cat}_{r_idx}_{c_idx}", use_container_width=True):
                                    for o in st.session_state.bookings:
                                        if o.get('id') == b.get('id'):
                                            o['status'] = "Pending"
                                            o['method'] = None
                                            save_data()
                                            st.rerun()
st.markdown("""
<div style='text-align:center; font-size:0.9rem; color:#555; padding:15px;'>
    <b>Contact Us  -  SwimTrack Pro</b><br>
    📞 +91 9133851400 &nbsp; | &nbsp;
    📧 pmuniswim16@gmail.com &nbsp; | &nbsp;
    📍 Hyderabad
</div>
""", unsafe_allow_html=True)