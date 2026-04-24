import streamlit as st
import pandas as pd
import calendar
import hashlib
import json
import os
import time
from datetime import datetime, time as dtime, timedelta

# --- CONFIG & PERSISTENCE ---
st.set_page_config(page_title="SwimTrack Pro", layout="wide")
DATA_FILE = "swim_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                st.warning("Data file corrupted. Resetting data.")
                return {"students": [], "bookings": []}
            for b in data.get("bookings", []):
                b['start_date'] = datetime.strptime(b['start_date'], "%Y-%m-%d").date()
                if 'end_date' in b and isinstance(b['end_date'], str):
                    b['end_date'] = datetime.strptime(b['end_date'], "%Y-%m-%d").date()
                b.setdefault('package', 'Single Session')
                b.setdefault('status', 'Pending')
                b.setdefault('method', None)
            return data
    return {"students": [], "bookings": []}

def save_data():
    data_to_save = {"students": st.session_state.students, "bookings": []}
    for b in st.session_state.bookings:
        b_copy = b.copy()
        b_copy['start_date'] = str(b_copy['start_date'])
        if 'end_date' in b_copy:
            b_copy['end_date'] = str(b_copy['end_date'])
        data_to_save["bookings"].append(b_copy)
    with open(DATA_FILE, "w") as f:
        json.dump(data_to_save, f, indent=4)

if 'students' not in st.session_state:
    saved = load_data()
    st.session_state.students, st.session_state.bookings = saved["students"], saved["bookings"]
    st.session_state.view_date = datetime.now()
    st.session_state.active_tab_index = 0

if 'selected_student' not in st.session_state:
    st.session_state.selected_student = ""

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
    .scrolling-text-inline {
        display: inline-block;
        padding-left: 100%;
        animation: scroll-left-inline 12s linear infinite;
        font-weight: 600;
        color: #1f77b4;
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
    """, unsafe_allow_html=True)

tab_list = ["📅 Monthly Calendar", "📝 Enrollment & Swimmer", "💰 Payments"]
chosen_tab = st.radio("Nav", tab_list, horizontal=True, label_visibility="collapsed")

if 'active_tab_index' not in st.session_state:
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
                            bg = "" if is_passed else f"background:{b['color']};"
                            html += f"<div class='{style}' style='{bg}'><b>{b['student']}</b><br>{b['time']}</div>"
                    html += "</div>"; st.markdown(html, unsafe_allow_html=True)
                else: st.markdown("<div class='calendar-cell' style='background-color:#fcfcfc;'></div>", unsafe_allow_html=True)

elif chosen_tab == "📝 Enrollment & Swimmer":
    col_manage, col_enroll = st.columns([1.2, 2])
    with col_manage:
        st.subheader("👥 Register Swimmer")
        with st.container(border=True, height=540):
            new_n = st.text_input("Register Name")
            if st.button("Add Student", use_container_width=True):
                if new_n and new_n not in st.session_state.students:
                    st.session_state.students.append(new_n)
                    st.session_state.selected_student = new_n
                    save_data()
                    st.session_state.active_tab_index = 1
                    st.rerun()
            st.divider(); s_list = st.container(height=340)
            for s in sorted(st.session_state.students):
                with s_list:
                    c1, c2, c3 = st.columns([3,1,1])
                    # Always clickable, highlight on selection
                    if c1.button(f"🔵 {s}" if st.session_state.selected_student == s else s, key=f"sel_{s}", use_container_width=True):
                        st.session_state.selected_student = s
                        st.rerun()
                    if c2.button("🗑️", key=f"del_{s}"):
                        st.session_state.students.remove(s)
                        st.session_state.bookings = [b for b in st.session_state.bookings if b['student']!=s]
                        save_data(); st.session_state.active_tab_index = 1; st.rerun()
    with col_enroll:
        st.subheader("📝 Book Your Slot")
        if st.session_state.get("enroll_success"):
            if time.time() - st.session_state.get("enroll_time", 0) < 3:
                st.success("Successfully enrolled!")
            else:
                st.session_state.enroll_success = False
        with st.container(border=True, height=540):
            c1, c2 = st.columns(2)
            st_name = st.session_state.selected_student
            c1.text_input("Select Student*", value=st_name, disabled=True)
            if not st_name:
                st.warning("Select a swimmer from the left panel")
            st_days = c1.multiselect("Class Days*", days_names, default=st.session_state.get("form_days", []), key="form_days")
            st_start = c1.date_input("Start Date", datetime.now(), key="form_start")

            st_package = c2.selectbox("Package", ["Single Session", "Monthly (3/week)", "Custom"], key="form_package")

            st_time = c2.time_input("Start Time", value=dtime(6, 30), key="form_time")

            if st_package == "Custom":
                st_end = c2.date_input("End Date", st_start + timedelta(days=7))
            elif st_package == "Monthly (3/week)":
                # End exactly after 1 month (same date next month)
                next_month = st_start.month % 12 + 1
                year = st_start.year + (st_start.month // 12)
                try:
                    st_end = st_start.replace(year=year, month=next_month)
                except ValueError:
                    # Handle cases like Jan 31 → Feb 28/29
                    last_day = calendar.monthrange(year, next_month)[1]
                    st_end = st_start.replace(year=year, month=next_month, day=last_day)
            else:
                st_end = st_start
            st_people = c2.number_input("Total Persons", 1, 4, 1, key="form_people")
            if st_package == "Single Session":
                base = 750
            elif st_package == "Monthly (3/week)":
                base = 9000
            else:
                base = 0
            final_fee = st.number_input("Final Fee (₹)", value=int(base * st_people), key="form_fee")

            # DUPLICATE PROTECTION
            is_blocked = False
            if st_name and st_days:
                new_start_dt = datetime.combine(datetime.today(), st_time)
                for b in st.session_state.bookings:
                    if b['student'] == st_name:
                        ex_start_dt = datetime.combine(datetime.today(), datetime.strptime(b['time'].split('-')[0], "%I:%M%p").time())
                        st_end = st_end if 'st_end' in locals() else st_start
                        if (
                            set(st_days).intersection(set(b['days'])) and
                            not (st_end < b['start_date'] or st_start > b.get('end_date', st_start)) and
                            new_start_dt < ex_start_dt + timedelta(hours=1) and
                            new_start_dt + timedelta(hours=1) > ex_start_dt
                        ):
                            is_blocked = True
                            break

            if st.button("Confirm Enrollment", disabled=is_blocked or not (st_name and st_days), use_container_width=True):
                end_t = (datetime.combine(datetime.today(), st_time) + timedelta(hours=1)).time()
                st.session_state.bookings.append({
                    "student": st_name,
                    "days": st_days,
                    "start_date": st_start,
                    "end_date": st_end, # Now correctly saves the custom end date
                    "package": st_package,
                    "time": f"{st_time.strftime('%I:%M%p')}-{end_t.strftime('%I:%M%p')}",
                    "color": get_student_color(st_name),
                    "fee": final_fee,
                    "status": "Pending",
                    "method": None
                })
                save_data()

                # Show success message
                st.session_state.enroll_success = True
                st.session_state.enroll_time = time.time()

                # Reset selected student also
                st.session_state.selected_student = ""

                # Safe reset (remove keys so widgets reinitialize)
                for key in ["form_days", "form_start", "form_package", "form_time", "form_people", "form_fee"]:
                    if key in st.session_state:
                        del st.session_state[key]

                st.session_state.active_tab_index = 1
                st.rerun()

# --- TAB 3: PAYMENTS (NEW ALIGNMENT UNDER PRICE) ---
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
                                end_period = b.get('end_date', b['start_date'] + timedelta(days=30))
                                period_str = f"{b['start_date'].strftime('%b %d')} - {end_period.strftime('%b %d, %Y')}"
                                st.markdown(f"""<div class="camp-badge">{cat.upper()}</div><div class="label-text">Training Package</div><div class="student-name">{b['student']}</div><div style="color:#888; font-size:0.85rem; margin-bottom:10px;">📅 Period: <b>{period_str}</b></div><div class="badge-row"><div class="pill">Days: {', '.join(b['days'])}</div><div class="pill">Slot: {b['time']}</div></div>""", unsafe_allow_html=True)
                                
                                # --- PRICE AND METHOD VERTICAL STACK ---
                                st.markdown(f"<div class='price-text'>₹{b['fee']}/-</div>", unsafe_allow_html=True)
                                
                                if b['status'] == "Pending":
                                    pay_m = st.radio("Select Method", ["UPI", "Cash"], key=f"p_{cat}_{r_idx}_{c_idx}", horizontal=True, label_visibility="collapsed")
                                else:
                                    st.markdown(f"<div style='color:#2e7bcf; font-weight:700; font-size:1.1rem; margin-bottom:10px;'>{b['method']}</div>", unsafe_allow_html=True)
                                
                                st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
                                act1, act2 = st.columns([3, 1])
                                if b['status'] == "Pending":
                                    if act1.button("Confirm Payment", key=f"b_{cat}_{r_idx}_{c_idx}", use_container_width=True):
                                        for o in st.session_state.bookings:
                                            if o == b: o['status'] = "Received"; o['method'] = pay_m; save_data(); st.rerun()
                                else:
                                    act1.markdown(f"""<div style="background-color:#f0fff4; color:#22543d; border:1px solid #c6f6d5; padding:8px; border-radius:8px; text-align:center; font-size:0.9rem; font-weight:600; height:38px; display:flex; align-items:center; justify-content:center; width:100%;">Payment Successful ({b['method']})</div>""", unsafe_allow_html=True)
                                if act2.button("Reset", key=f"res_{cat}_{r_idx}_{c_idx}", use_container_width=True):
                                    for o in st.session_state.bookings:
                                        if o == b:
                                            o['status'] = "Pending"
                                            o['method'] = None
                                            save_data()
                                            st.rerun()
