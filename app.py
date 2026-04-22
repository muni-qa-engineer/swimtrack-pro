import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import calendar
import hashlib
import json
import os
import time
from datetime import datetime, time as dtime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="SwimTrack Pro", layout="wide")

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="bookings", ttl="0")
        if df.empty:
            return {"students": ["Avanti", "Vihan"], "bookings": []}
        
        bookings = df.to_dict(orient="records")
        for b in bookings:
            # Convert string days back to list
            if isinstance(b['days'], str):
                b['days'] = b['days'].split(', ')
            # Convert strings to date objects
            b['start_date'] = pd.to_datetime(b['start_date']).date()
            b['end_date'] = pd.to_datetime(b['end_date']).date()
        
        students = list(set([b['student'] for b in bookings] + ["Avanti", "Vihan"]))
        return {"students": students, "bookings": bookings}
    except Exception as e:
        return {"students": ["Avanti", "Vihan"], "bookings": []}

def save_data(bookings_list):
    df = pd.DataFrame(bookings_list)
    if not df.empty:
        df['days'] = df['days'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        # Ensure dates are strings for Google Sheets
        df['start_date'] = df['start_date'].apply(lambda x: str(x))
        df['end_date'] = df['end_date'].apply(lambda x: str(x))
    conn.update(worksheet="bookings", data=df)

# --- INITIALIZE STATE ---
if 'init_done' not in st.session_state:
    data = load_data()
    st.session_state.students = data["students"]
    st.session_state.bookings = data["bookings"]
    st.session_state.view_date = datetime.now()
    st.session_state.active_tab_index = 0
    st.session_state.init_done = True

def get_student_color(name):
    return f"#{hashlib.md5(name.encode()).hexdigest()[:6]}"

days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# --- CSS ---
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

st.title("🏊‍♂️ SwimTrack Pro")

tab_list = ["📅 Monthly Calendar", "📝 Enrollment & Students", "💰 Payments"]
chosen_tab = st.radio("Nav", tab_list, index=st.session_state.active_tab_index, horizontal=True, label_visibility="collapsed")
st.session_state.active_tab_index = tab_list.index(chosen_tab)

# --- TAB 1: CALENDAR (FIXED DATE RANGE) ---
if chosen_tab == "📅 Monthly Calendar":
    now = datetime.now(); today_date, current_time = now.date(), now.time()
    h_col1, h_center, _ = st.columns([1, 3, 1])
    with h_col1:
        with st.popover("📅 Select Month"):
            m_name = st.selectbox("Month", list(calendar.month_name)[1:], index=st.session_state.view_date.month-1)
            y_val = st.number_input("Year", value=st.session_state.view_date.year)
            if st.button("Apply"):
                st.session_state.view_date = datetime(y_val, list(calendar.month_name).index(m_name), 1); st.rerun()
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
                        # FIX: Check if date is within START and END range
                        if days_names[i] in b['days'] and b['start_date'] <= curr_d <= b['end_date']:
                            is_passed = (curr_d < today_date) or (curr_d == today_date and current_time > datetime.strptime(b['time'].split('-')[0], "%I:%M%p").time())
                            style = "completed-tile" if is_passed else "student-tile"
                            bg = "" if is_passed else f"background:{b['color']};"
                            html += f"<div class='{style}' style='{bg}'><b>{b['student']}</b><br>{b['time']}</div>"
                    html += "</div>"; st.markdown(html, unsafe_allow_html=True)
                else: st.markdown("<div class='calendar-cell' style='background-color:#fcfcfc;'></div>", unsafe_allow_html=True)

# --- TAB 2: ENROLLMENT (ADDED END DATE LOGIC) ---
elif chosen_tab == "📝 Enrollment & Students":
    col_manage, col_enroll = st.columns([1.2, 2])
    with col_manage:
        st.subheader("👥 Students")
        new_n = st.text_input("Register Name")
        if st.button("Add Student", use_container_width=True):
            if new_n and new_n not in st.session_state.students:
                st.session_state.students.append(new_n); st.rerun()
        st.divider(); s_list = st.container(height=340)
        for s in sorted(st.session_state.students):
            with s_list:
                c1, c2 = st.columns([4, 1]); c1.text(f"• {s}")
                if c2.button("🗑️", key=f"del_{s}"):
                    st.session_state.students.remove(s)
                    st.session_state.bookings = [b for b in st.session_state.bookings if b['student']!=s]
                    save_data(st.session_state.bookings); st.rerun()
    with col_enroll:
        st.subheader("📝 New Enrollment")
        with st.container(border=True, height=540):
            c1, c2 = st.columns(2)
            st_name = c1.selectbox("Select Student*", [""] + sorted(st.session_state.students))
            st_days = c1.multiselect("Class Days*", days_names)
            st_start = c1.date_input("Start Date", datetime.now())
            st_time = c2.time_input("Start Time", value=dtime(6, 30))
            st_package = c2.selectbox("Package", ["Single Session", "Monthly (3/week)", "Custom"])
            st_people = c2.number_input("Total Persons", 1, 4, 1)
            base = 750 if "Single" in st_package else (9000 if "Monthly" in st_package else 0)
            final_fee = st.number_input("Final Fee (₹)", value=int(base * st_people))
            
            # DUPLICATE PROTECTION
            is_blocked = False
            if st_name and st_days:
                new_start_t = datetime.combine(datetime.today(), st_time)
                for b in st.session_state.bookings:
                    if b['student'] == st_name:
                        ex_start_t = datetime.strptime(b['time'].split('-')[0], "%I:%M%p")
                        if set(st_days).intersection(set(b['days'])) and (new_start_t.time() < (ex_start_t + timedelta(hours=1)).time() and (new_start_t + timedelta(hours=1)).time() > ex_start_t.time()):
                            is_blocked = True; break

            if st.button("Confirm Enrollment", disabled=is_blocked or not (st_name and st_days), use_container_width=True):
                # FIX: Set end date to +30 days for Monthly, or same day for Single
                days_to_add = 30 if "Monthly" in st_package else 0
                st_end = st_start + timedelta(days=days_to_add)
                
                end_t_obj = (datetime.combine(datetime.today(), st_time) + timedelta(hours=1)).time()
                st.session_state.bookings.append({
                    "student": st_name, "days": st_days, "start_date": st_start, 
                    "end_date": st_end, "package": st_package, 
                    "time": f"{st_time.strftime('%I:%M%p')}-{end_t_obj.strftime('%I:%M%p')}", 
                    "color": get_student_color(st_name), "fee": final_fee, "status": "Pending", "method": None
                })
                save_data(st.session_state.bookings); st.session_state.active_tab_index = 1; st.rerun()

# --- TAB 3: PAYMENTS ---
elif chosen_tab == "💰 Payments":
    cats = ["Single Session", "Monthly (3/week)", "Custom"]
    p_tabs = st.tabs(cats)
    for i, cat in enumerate(cats):
        with p_tabs[i]:
            filtered = [b for b in st.session_state.bookings if b.get('package') == cat]
            if not filtered: st.info("No records.")
            else:
                for r_idx in range(0, len(filtered), 2):
                    row_items = filtered[r_idx:r_idx+2]; grid = st.columns(2)
                    for c_idx, b in enumerate(row_items):
                        with grid[c_idx]:
                            with st.container(border=True):
                                period_str = f"{b['start_date'].strftime('%b %d')} - {b['end_date'].strftime('%b %d, %Y')}"
                                st.markdown(f"""<div class="camp-badge">{cat.upper()}</div><div class="label-text">Training Package</div><div class="student-name">{b['student']}</div><div style="color:#888; font-size:0.85rem; margin-bottom:10px;">📅 Period: <b>{period_str}</b></div><div class="badge-row"><div class="pill">Days: {', '.join(b['days'])}</div><div class="pill">Slot: {b['time']}</div></div>""", unsafe_allow_html=True)
                                st.markdown(f"<div class='price-text'>₹{b['fee']}/-</div>", unsafe_allow_html=True)
                                
                                if b['status'] == "Pending":
                                    pay_m = st.radio("Select Method", ["UPI", "Cash"], key=f"p_{cat}_{r_idx}_{c_idx}", horizontal=True, label_visibility="collapsed")
                                else: st.markdown(f"<div style='color:#2e7bcf; font-weight:700; font-size:1.1rem; margin-bottom:10px;'>{b['method']}</div>", unsafe_allow_html=True)
                                
                                st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
                                act1, act2 = st.columns([3, 1])
                                if b['status'] == "Pending":
                                    if act1.button("Confirm Payment", key=f"b_{cat}_{r_idx}_{c_idx}", use_container_width=True):
                                        for o in st.session_state.bookings:
                                            if o == b: o['status'] = "Received"; o['method'] = pay_m; save_data(st.session_state.bookings); st.rerun()
                                else:
                                    act1.markdown(f"""<div style="background-color:#f0fff4; color:#22543d; border:1px solid #c6f6d5; padding:8px; border-radius:8px; text-align:center; font-size:0.9rem; font-weight:600; height:38px; display:flex; align-items:center; justify-content:center; width:100%;">Payment Successful ({b['method']})</div>""", unsafe_allow_html=True)
                                if act2.button("Reset", key=f"res_{cat}_{r_idx}_{c_idx}", use_container_width=True):
                                    for o in st.session_state.bookings:
                                        if o == b: o['status'] = "Pending"; save_data(st.session_state.bookings); st.rerun()
