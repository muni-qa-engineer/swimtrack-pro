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
    .login-container { display: flex; height: 80vh; border-radius: 20px; overflow: hidden; background: white; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .left-panel { flex: 1; padding: 40px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    .right-panel { flex: 1; background: linear-gradient(135deg, #6fb1fc, #4364f7); color: white; display: flex; align-items: center; justify-content: center; text-align: center; padding: 30px; }
    .title-text { font-size: 28px; font-weight: bold; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown("<div class='left-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='title-text'>🏊‍♂️ Welcome to SwimTrack</div>", unsafe_allow_html=True)
        st.info("📢 Note: Please complete all steps carefully while booking your slot.")
        role = st.radio("Login Type", ["Guest", "Admin"], horizontal=True)
        if role == "Guest":
            name = st.text_input("Enter your name")
            if st.button("Continue as Guest", use_container_width=True):
                if name.strip():
                    st.session_state.user_role = "guest"
                    st.session_state.logged_in_user = name.strip()
                    st.session_state.selected_student = ""
                    st.rerun()
        elif role == "Admin":
            pwd = st.text_input("Enter password", type="password")
            if st.button("Login as Admin", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.user_role = "admin"
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='right-panel'><h2>Start your journey</h2><p>Learn a life skill and enjoy swimming</p><h3>🏊‍♂️</h3></div>", unsafe_allow_html=True)
    st.stop()

# --- CONFIG & PERSISTENCE ---
## st.set_page_config(page_title="SwimTrack Pro", layout="wide")  # REMOVED DUPLICATE
DATA_FILE = "swim_data.json"

def generate_booking_id(student, start_date, time_str):
    return hashlib.md5(f"{student}{start_date}{time_str}".encode()).hexdigest()


# --- STUDENT COLOR FUNCTION ---
def get_student_color(name):
    return f"#{hashlib.md5(name.encode()).hexdigest()[:6]}"

def load_data():
    try:
        sheet = connect_gsheet()
        students_sheet = sheet.worksheet("students")
        bookings_sheet = sheet.worksheet("bookings")

        students = students_sheet.get_all_records()
        bookings = bookings_sheet.get_all_records()

        student_list = [s.get("name") for s in students if s.get("name")]

        for b in bookings:
            if b.get('start_date'):
                b['start_date'] = datetime.strptime(b['start_date'], "%Y-%m-%d").date()

            if b.get('end_date'):
                b['end_date'] = datetime.strptime(b['end_date'], "%Y-%m-%d").date()

            b['days'] = [d for d in b.get('days', "").split(",") if d]

            b.setdefault("address", "")
            b.setdefault("status", "Pending")
            b.setdefault("method", None)
            b.setdefault("created_by", "unknown")
            b.setdefault("duration", 60)
            b.setdefault("people", 1)
            b.setdefault("color", get_student_color(b.get("student", "default")))

        return {"students": student_list, "bookings": bookings}

    except Exception as e:
        st.error(f"Failed to load data from Google Sheets: {e}")
        return {"students": [], "bookings": []}

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

if 'selected_student' not in st.session_state: st.session_state.selected_student = ""
if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
if 'edit_index' not in st.session_state: st.session_state.edit_index = None  
if 'enroll_sub_tab' not in st.session_state: st.session_state.enroll_sub_tab = "📊 Registered Swimmers"


days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# --- GLOBAL CSS ---
st.markdown("""
<style>
    .month-title { text-align: center; font-size: 2rem; font-weight: bold; margin-bottom: 10px; }
    .calendar-header { text-align: center; font-weight: bold; background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; font-size: 0.8rem; }
    .calendar-cell { border: 1px solid #dee2e6; min-height: 140px; padding: 5px; background-color: white; }
    .student-tile { color: white; font-size: 0.65rem; padding: 4px 6px; border-radius: 4px; margin-bottom: 4px; line-height: 1.1; font-weight: 600; }
    .completed-tile { background: #e5e5ea !important; color: #a1a1a6 !important; text-decoration: line-through; font-size: 0.65rem; padding: 4px 6px; border-radius: 4px; margin-bottom: 4px; line-height: 1.1; font-weight: 400; border: 1px solid #d1d1d6; }
    .label-text { color: #888; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; }
    .student-name { font-size: 1.8rem; font-weight: 800; color: #1d1d1f; margin-top: 5px; }
    .price-text { font-size: 2.2rem; font-weight: 800; color: #1d1d1f; }
    .scrolling-banner-inline { width: 100%; overflow: hidden; white-space: nowrap; position: relative; margin-top: 15px; }
    .scrolling-text-inline, .scrolling-text-inline-red { display: inline-block; padding-left: 100%; animation: scroll-left-inline 12s linear infinite; font-weight: 600; font-size: 1rem; }
    .scrolling-text-inline { color: #1f77b4; }
    .scrolling-text-inline-red { color: red; }
    @keyframes scroll-left-inline { 0% { transform: translateX(0%); } 100% { transform: translateX(-100%); } }
    .card-gradient {
        background: linear-gradient(135deg, #6fb1fc, #4364f7);
        border-radius: 12px;
        padding: 12px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    if st.button("🚪 Logout"):
        st.session_state.user_role = None
        st.session_state.logged_in_user = ""
        st.rerun()

# --- HEADER ---
col_title, col_banner = st.columns([3, 5])
with col_title:
    st.markdown("<h1 style='margin:0;'>🏊‍♂️ SwimTrack Pro</h1>", unsafe_allow_html=True)
with col_banner:
    st.markdown("""
    <div class="scrolling-banner-inline"><div class="scrolling-text-inline">🏊 Swimming classes are open now!</div></div>
    <div class="scrolling-banner-inline"><div class="scrolling-text-inline-red">Note: I will be not available from May 25th, 2026 onwards..</div></div>
    """, unsafe_allow_html=True)

# --- MAIN TABS ---
if st.session_state.user_role == "guest":
    tab_list = ["📝 Book Slot", "📋 My Bookings"]
else:
    tab_list = ["📅 Monthly Calendar", "📝 Enrollment & Swimmer", "💰 Payments"]

# Safe index handling for tab selection
safe_index = min(st.session_state.active_tab_index, len(tab_list) - 1)
chosen_tab = st.radio("Nav", tab_list, index=safe_index, horizontal=True, label_visibility="collapsed", key="nav_radio")

if tab_list.index(chosen_tab) != st.session_state.active_tab_index:
    st.session_state.active_tab_index = tab_list.index(chosen_tab)

# --- TAB: MY BOOKINGS (GUEST) ---
if chosen_tab == "📋 My Bookings":
    st.subheader("📋 Your Bookings")
    if st.button("➕ Book New Slot", use_container_width=True):
        st.session_state.active_tab_index = 0
        st.session_state.edit_mode = False
        st.rerun()
    user_bookings = [b for b in st.session_state.bookings if b.get("created_by") == st.session_state.logged_in_user]
    if not user_bookings:
        st.info("No bookings yet.")
    else:
        for r_idx in range(0, len(user_bookings), 3):
            row_items = user_bookings[r_idx:r_idx+3]; cols = st.columns(3)
            for c_idx, b in enumerate(row_items):
                with cols[c_idx]:
                    with st.container(border=True):
                        st.markdown(f"**{b['student']}**")

                        col_a, col_b = st.columns(2)
                        col_a.markdown(f"📅 {b['start_date']}")
                        col_b.markdown(f"⏰ {b['time']}")

                        st.markdown(f"💰 ₹{b['fee']}/-")

                        # Additional details
                        if b.get("days"):
                            st.markdown(f"📆 Days: {', '.join(b['days'])}")

                        if b.get("people"):
                            st.markdown(f"👥 Persons: {b.get('people')}")

                        if st.button("✏️ Edit", key=f"edit_guest_{b.get('id')}_{r_idx}_{c_idx}", use_container_width=True):
                            edit_idx = next((i for i, bb in enumerate(st.session_state.bookings) if bb.get("id") == b.get("id")), None)
                            if edit_idx is not None:
                                st.session_state.edit_mode, st.session_state.edit_index, st.session_state.active_tab_index = True, edit_idx, 0
                                st.rerun()

# --- TAB: MONTHLY CALENDAR ---
elif chosen_tab == "📅 Monthly Calendar":
    now = datetime.now(); today_date, current_time = now.date(), now.time()
    h_col1, h_center, _ = st.columns([1, 3, 1])
    with h_col1:
        with st.popover("📅 Select Month"):
            m_name = st.selectbox("Month", list(calendar.month_name)[1:], index=st.session_state.view_date.month-1)
            y_val = st.number_input("Year", value=st.session_state.view_date.year)
            if st.button("Apply"):
                st.session_state.view_date = datetime(y_val, list(calendar.month_name).index(m_name), 1); st.rerun()
    with h_center: 
        st.markdown(f"<div class='month-title'>{calendar.month_name[st.session_state.view_date.month]} {st.session_state.view_date.year}</div>", unsafe_allow_html=True)
    
    cal = calendar.monthcalendar(st.session_state.view_date.year, st.session_state.view_date.month)
    h_cols = st.columns(7)
    for i, d in enumerate(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]): h_cols[i].markdown(f"<div class='calendar-header'>{d}</div>", unsafe_allow_html=True)
    
    for week in cal:
        w_cols = st.columns(7)
        for i, day_val in enumerate(week):
            with w_cols[i]:
                if day_val != 0:
                    curr_d = datetime(st.session_state.view_date.year, st.session_state.view_date.month, day_val).date()
                    html = f"<div class='calendar-cell'><div style='color:#ccc; font-size:0.8rem;'>{day_val}</div>"
                    for b in st.session_state.bookings:
                        if days_names[i] in b['days'] and b['start_date'] <= curr_d <= b.get('end_date', curr_d):
                            is_passed = (curr_d < today_date) or (curr_d == today_date and current_time > datetime.strptime(b['time'].split('-')[0], "%I:%M%p").time())
                            bg = "" if is_passed else f"background:{b['color']};"
                            html += f"<div class='{'completed-tile' if is_passed else 'student-tile'}' style='{bg}'><b>{b['student']}</b><br>{b['time']}</div>"
                    html += "</div>"; st.markdown(html, unsafe_allow_html=True)
                else: st.markdown("<div class='calendar-cell' style='background-color:#fcfcfc;'></div>", unsafe_allow_html=True)

# --- TAB: ENROLLMENT & SWIMMER (ADMIN / BOOK SLOT GUEST) ---
elif chosen_tab == "📝 Enrollment & Swimmer" or chosen_tab == "📝 Book Slot":
    # 1. Sub-navigation for Admin
    if st.session_state.user_role == "admin":
        # Handle programmatic tab switch BEFORE widget creation
        if st.session_state.get("go_to_book_tab"):
            st.session_state.enroll_sub_tab = "📝 Book Slot"
            st.session_state.go_to_book_tab = False

        view_mode = st.radio(
            "",
            ["📊 Registered Swimmers", "📝 Book Slot"],
            key="enroll_sub_tab",
            horizontal=True
        )
    else:
        view_mode = "📝 Book Slot"

    # 2. Registered Swimmers Grid (Admin View)
    if st.session_state.user_role == "admin" and view_mode == "📊 Registered Swimmers":
        grouped = {}
        for b in st.session_state.bookings:
            owner = b.get("created_by", "Unknown")
            grouped.setdefault(owner, set()).add(b["student"])
        
        owners = list(grouped.items())
        for row_start in range(0, len(owners), 3):
            cols = st.columns(3); row_items = owners[row_start:row_start+3]
            for col_idx, (owner, students) in enumerate(row_items):
                with cols[col_idx]:
                    with st.container(border=True):
                        st.markdown(f"### 👤 {owner}")
                        for idx, s in enumerate(sorted(students)):
                            # Get address from any booking of this student
                            addr = next((b.get("address", "") for b in st.session_state.bookings 
                                         if b["student"] == s and b.get("created_by") == owner), "")

                            r = st.columns([3, 1, 1])
                            with r[0]:
                                label = f"🔵 {s}" if st.session_state.selected_student == s else s
                                st.button(label, key=f"sel_{owner}_{s}", use_container_width=True)

                                if addr:
                                    st.caption(f"📍 {addr}")

                            if r[1].button("✏️", key=f"ed_{owner}_{s}", use_container_width=True):
                                idx_to_edit = next((i for i, b in enumerate(st.session_state.bookings) 
                                                    if b["student"] == s and b.get("created_by") == owner), None)
                                if idx_to_edit is not None:
                                    st.session_state.edit_mode, st.session_state.edit_index = True, idx_to_edit
                                    st.session_state.selected_student = s
                                    st.session_state.go_to_book_tab = True
                                    st.rerun()

                            if r[2].button("🗑️", key=f"del_{owner}_{s}", use_container_width=True):
                                st.session_state.bookings = [
                                    b for b in st.session_state.bookings 
                                    if not (b["student"] == s and b.get("created_by") == owner)
                                ]
                                save_data()
                                st.rerun()
        st.stop()

    # 3. Combined Swimmer Registration & Booking Form
    col_manage, col_enroll = st.columns([1.2, 2])
    
    with col_manage:
        st.subheader("👥 My Swimmers")
        with st.container(border=True, height=540):
            new_n = st.text_input("Register Swimmer Name")
            if st.button("Add Swimmer", use_container_width=True):
                if new_n.strip(): 
                    st.session_state.students.append(new_n.strip()); 
                    st.session_state.selected_student = new_n.strip(); 
                    save_data(); st.rerun()
            st.divider()
            
            # Show swimmers belonging to the logged-in guest (or all for admin)
            if st.session_state.user_role == "guest":
                visible_students = sorted({b["student"] for b in st.session_state.bookings if b.get("created_by") == st.session_state.logged_in_user})
            else:
                visible_students = sorted(list(set(st.session_state.students)))
                
            for idx, s in enumerate(visible_students):
                if st.button(f"🔵 {s}" if st.session_state.selected_student == s else s, key=f"swimmer_list_{idx}", use_container_width=True):
                    st.session_state.selected_student = s; st.rerun()

    with col_enroll:
        st.subheader("✏️ Edit Booking" if st.session_state.edit_mode else "📝 Book Your Slot")
        with st.container(border=True, height=540):
            edit_b = st.session_state.bookings[st.session_state.edit_index] if (st.session_state.edit_mode and st.session_state.edit_index is not None) else None
            st_name = edit_b['student'] if edit_b else st.session_state.selected_student

            # # Move Class Days full width
            # st_days = st.multiselect("Class Days*", days_names, default=edit_b['days'] if edit_b else [])

            c1, c2 = st.columns(2, gap="large")
            c1.text_input("Select Swimmer*", value=st_name, disabled=True)

            t_d = datetime.now().date()
            def_s = edit_b['start_date'] if edit_b else t_d
            # Prevent past dates for new booking
            if st.session_state.edit_mode:
                min_d = min(def_s, t_d)  # allow old date while editing
            else:
                min_d = t_d
            st_start = c1.date_input("Start Date", value=def_s, min_value=min_d)

            pkgs = ["Single Session", "Monthly (3/week)", "Custom"]
            st_package = c2.selectbox("Package", pkgs, index=pkgs.index(edit_b['package']) if edit_b else 0)

            # --- End Date Logic ---
            if st_package == "Single Session":
                st_end = st_start
                c1.date_input("End Date", value=st_end, disabled=True)

            elif st_package == "Monthly (3/week)":
                st_end = st_start + timedelta(days=30)
                c1.date_input("End Date", value=st_end, disabled=True)

            else:  # Custom
                default_end = edit_b['end_date'] if edit_b else st_start + timedelta(days=7)
                st_end = c1.date_input("End Date", value=default_end, min_value=st_start)

            # Generate time slots
            all_times = [(datetime.combine(t_d, dtime(0,0)) + timedelta(minutes=i)).strftime("%I:%M %p") for i in range(0, 1440, 15)]

            # Filter past times if selected date is today
            now_dt = datetime.now()
            if st_start == now_dt.date():
                t_lbls = [
                    t for t in all_times
                    if datetime.combine(st_start, datetime.strptime(t, "%I:%M %p").time()) >= now_dt
                ]
            else:
                t_lbls = all_times

            # Fallback safety (if all times filtered)
            if not t_lbls:
                st.warning("No available time slots for today.")
                st.stop()

            st_time_str = c2.selectbox("Start Time", t_lbls)
            st_time = datetime.strptime(st_time_str, "%I:%M %p").time()

            # Auto-set class day for Single Session
            if st_package == "Single Session":
                auto_day = st_start.strftime("%A")
                st_days = [auto_day]
                st.markdown(f"📆 Class Day: **{auto_day}**")
            else:
                st_days = st.multiselect("Class Days*", days_names, default=edit_b['days'] if edit_b else [])

            # Restored detailed Fee Logic
            people = c2.number_input("People", 1, 5, 1)
            if not st.session_state.edit_mode:
                if st_package == "Single Session": base_fee = 750 * len(st_days) * people
                elif st_package == "Monthly (3/week)": base_fee = 9000 * people
                else: base_fee = 750
            else: base_fee = edit_b['fee']

            final_fee = st.number_input("Fee (₹)", value=int(base_fee))
            st_address = st.text_area(
                "Location",
                value=edit_b.get("address", "") if edit_b else "",
                height=80
            )

            if st.button("Confirm" if not st.session_state.edit_mode else "Update", use_container_width=True):
                if not st_days:
                    st.error("Please select at least one class day.")
                else:
                    end_t = (datetime.combine(datetime.today(), st_time) + timedelta(minutes=60)).time()
                    b_data = {
                        "id": edit_b["id"] if edit_b else generate_booking_id(st_name, st_start, st_time_str),
                        "student": st_name,
                        "created_by": st.session_state.logged_in_user if st.session_state.user_role == "guest" else edit_b.get('created_by', 'admin') if edit_b else 'admin',
                        "days": st_days,
                        "start_date": st_start,
                        "end_date": st_end,
                        "package": st_package,
                        "time": f"{st_time.strftime('%I:%M%p')}-{end_t.strftime('%I:%M%p')}",
                        "color": get_student_color(st_name),
                        "fee": final_fee,
                        "people": people,
                        "status": edit_b.get('status', 'Pending') if edit_b else 'Pending',
                        "method": edit_b.get('method', None) if edit_b else None,
                        "address": st_address
                    }
                    if st.session_state.edit_mode:
                        st.session_state.bookings[st.session_state.edit_index] = b_data
                        st.session_state.edit_mode = False
                    else:
                        st.session_state.bookings.append(b_data)
                    save_data()
                    st.session_state.active_tab_index = 1 if st.session_state.user_role == "guest" else 0
                    st.rerun()

# --- TAB: PAYMENTS (ADMIN ONLY) ---
elif chosen_tab == "💰 Payments" and st.session_state.user_role == "admin":
    cats = ["Single Session", "Monthly (3/week)", "Custom"]
    p_tabs = st.tabs(cats)
    for i, cat in enumerate(cats):
        with p_tabs[i]:
            fltrd = [b for b in st.session_state.bookings if b.get('package') == cat]
            if not fltrd:
                st.info(f"No bookings for {cat}")
            else:
                for r_idx in range(0, len(fltrd), 3):
                    row_items = fltrd[r_idx:r_idx+3]; grid = st.columns(3)
                    for c_idx, b in enumerate(row_items):
                        with grid[c_idx]:
                            with st.container(border=True):
                                st.markdown(f"**{b['student']}**")

                                col_a, col_b = st.columns(2)
                                col_a.markdown(f"📅 {b['start_date']}")
                                col_b.markdown(f"⏰ {b['time']}")

                                st.markdown(f"💰 ₹{b['fee']}/-")
                                st.markdown(f"👤 {b.get('created_by', 'Unknown')}")

                                if b.get("days"):
                                    st.markdown(f"📆 Days: {', '.join(b['days'])}")

                                if b.get("people"):
                                    st.markdown(f"👥 Persons: {b.get('people')}")
                                if b.get('status') == "Pending":
                                    pay_m = st.radio("Method", ["UPI", "Cash"], key=f"p_radio_{b['id']}", horizontal=True)
                                    if st.button("Payment Done", key=f"p_btn_{b['id']}", use_container_width=True):
                                        b['status'], b['method'] = "Received", pay_m
                                        save_data(); st.rerun()
                                else:
                                    st.success(f"Paid via {b.get('method', 'Unknown')}")
                                    if st.button("Reset Status", key=f"res_btn_{b['id']}"):
                                        b['status'], b['method'] = "Pending", None
                                        save_data(); st.rerun()

st.markdown("<div style='text-align:center; padding:15px; color:#888;'><b>SwimTrack Pro</b></div>", unsafe_allow_html=True)