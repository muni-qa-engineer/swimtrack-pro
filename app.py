import streamlit as st
import pandas as pd
import calendar
import hashlib
import json
import os
from datetime import datetime, time as dtime, timedelta

st.set_page_config(page_title="SwimTrack Pro", layout="wide")
DATA_FILE = "swim_data.json"

# ---------- DATA ----------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                data = json.load(f)
            except:
                return {"students": [], "bookings": []}

            for b in data.get("bookings", []):
                b['start_date'] = datetime.strptime(b['start_date'], "%Y-%m-%d").date()
                if 'end_date' in b:
                    b['end_date'] = datetime.strptime(b['end_date'], "%Y-%m-%d").date()
            return data
    return {"students": [], "bookings": []}


def save_data():
    data = {"students": st.session_state.students, "bookings": []}
    for b in st.session_state.bookings:
        b_copy = b.copy()
        b_copy['start_date'] = str(b_copy['start_date'])
        if 'end_date' in b_copy:
            b_copy['end_date'] = str(b_copy['end_date'])
        data["bookings"].append(b_copy)

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


if 'students' not in st.session_state:
    saved = load_data()
    st.session_state.students = saved["students"]
    st.session_state.bookings = saved["bookings"]
    st.session_state.view_date = datetime.now()

if 'selected_student' not in st.session_state:
    st.session_state.selected_student = ""


def get_color(name):
    return f"#{hashlib.md5(name.encode()).hexdigest()[:6]}"


days_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# ---------- UI ----------
st.title("🏊 SwimTrack Pro")

tab = st.radio("", ["📅 Calendar","📝 Enrollment & Swimmer","💰 Payments"], horizontal=True)

# ---------- CALENDAR ----------
if tab == "📅 Calendar":

    cal = calendar.monthcalendar(datetime.now().year, datetime.now().month)

    for week in cal:
        cols = st.columns(7)
        for i, d in enumerate(week):
            with cols[i]:
                if d:
                    curr = datetime.now().replace(day=d).date()
                    st.markdown(f"**{d}**")

                    for b in st.session_state.bookings:
                        if days_names[i] in b['days'] and b['start_date'] <= curr <= b.get('end_date', curr):
                            st.markdown(f"""
                            <div style="background:{b['color']};color:white;padding:5px;border-radius:5px;">
                            {b['student']}<br>{b['time']}
                            </div>
                            """, unsafe_allow_html=True)

# ---------- ENROLL ----------
elif tab == "📝 Enrollment & Swimmer":

    col1, col2 = st.columns([1,2])

    # ---------- REGISTER ----------
    with col1:
        st.subheader("Register Swimmer")
        name = st.text_input("Name")

        if st.button("Add Student"):
            if name and name not in st.session_state.students:
                st.session_state.students.append(name)
                st.session_state.selected_student = name
                save_data()
                st.rerun()

        st.divider()

        for s in st.session_state.students:
            cols = st.columns([3,1])

            if cols[0].button(
                f"🔵 {s}" if st.session_state.selected_student == s else s,
                key=s,
                use_container_width=True
            ):
                st.session_state.selected_student = s

            if cols[1].button("❌", key=f"del{s}"):
                st.session_state.students.remove(s)
                st.session_state.bookings = [b for b in st.session_state.bookings if b['student'] != s]
                save_data()
                st.rerun()

    # ---------- BOOK ----------
    with col2:
        st.subheader("Book Slot")

        st.text_input("Select Student", value=st.session_state.selected_student, disabled=True)

        days = st.multiselect("Days", days_names)
        start = st.date_input("Start Date")

        package = st.selectbox("Package", ["Single Session","Monthly (3/week)","Custom"])

        time_val = st.time_input("Start Time", value=dtime(6,30))

        if package == "Monthly (3/week)":
            next_month = start.month % 12 + 1
            year = start.year + (start.month // 12)
            try:
                end = start.replace(year=year, month=next_month)
            except:
                end = start + timedelta(days=30)
        elif package == "Custom":
            end = st.date_input("End Date", start + timedelta(days=7))
        else:
            end = start

        fee = st.number_input("Fee", value=750)

        if st.button("Confirm") and st.session_state.selected_student:
            end_time = (datetime.combine(datetime.today(), time_val) + timedelta(hours=1)).time()

            st.session_state.bookings.append({
                "student": st.session_state.selected_student,
                "days": days,
                "start_date": start,
                "end_date": end,
                "time": f"{time_val.strftime('%I:%M%p')}-{end_time.strftime('%I:%M%p')}",
                "color": get_color(st.session_state.selected_student),
                "fee": fee,
                "status": "Pending"
            })

            save_data()
            st.rerun()

# ---------- PAYMENTS ----------
elif tab == "💰 Payments":

    for b in st.session_state.bookings:
        st.markdown(f"### {b['student']}")
        st.write(f"₹ {b['fee']}")
        st.write(f"{b['start_date']} → {b.get('end_date')}")

        if b['status'] == "Pending":
            if st.button("Pay", key=b['student']):
                b['status'] = "Paid"
                save_data()
                st.rerun()
        else:
            st.success("Paid")st.session_state.active_tab_index = tab_list.index(chosen_tab)

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
                        if days_names[i] in b['days'] and curr_d >= b['start_date']:
                            is_passed = (curr_d < today_date) or (curr_d == today_date and current_time > datetime.strptime(b['time'].split('-')[0], "%I:%M%p").time())
                            style = "completed-tile" if is_passed else "student-tile"
                            bg = "" if is_passed else f"background:{b['color']};"
                            html += f"<div class='{style}' style='{bg}'><b>{b['student']}</b><br>{b['time']}</div>"
                    html += "</div>"; st.markdown(html, unsafe_allow_html=True)
                else: st.markdown("<div class='calendar-cell' style='background-color:#fcfcfc;'></div>", unsafe_allow_html=True)

elif chosen_tab == "📝 Enrollment & Students":
    col_manage, col_enroll = st.columns([1.2, 2])
    with col_manage:
        st.subheader("👥 Students")
        with st.container(border=True, height=540):
            new_n = st.text_input("Register Name")
            if st.button("Add Student", use_container_width=True):
                if new_n and new_n not in st.session_state.students:
                    st.session_state.students.append(new_n); save_data(); st.session_state.active_tab_index = 1; st.rerun()
            st.divider(); s_list = st.container(height=340)
            for s in sorted(st.session_state.students):
                with s_list:
                    c1, c2 = st.columns([4, 1]); c1.text(f"• {s}")
                    if c2.button("🗑️", key=f"del_{s}"):
                        st.session_state.students.remove(s)
                        st.session_state.bookings = [b for b in st.session_state.bookings if b['student']!=s]
                        save_data(); st.session_state.active_tab_index = 1; st.rerun()
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
                new_start = datetime.combine(datetime.today(), st_time)
                for b in st.session_state.bookings:
                    if b['student'] == st_name:
                        ex_start = datetime.strptime(b['time'].split('-')[0], "%I:%M%p")
                        if set(st_days).intersection(set(b['days'])) and (new_start.time() < (ex_start + timedelta(hours=1)).time() and (new_start + timedelta(hours=1)).time() > ex_start.time()):
                            is_blocked = True; break
            if st.button("Confirm Enrollment", disabled=is_blocked or not (st_name and st_days), use_container_width=True):
                end_t = (datetime.combine(datetime.today(), st_time) + timedelta(hours=1)).time()
                st.session_state.bookings.append({"student": st_name, "days": st_days, "start_date": st_start, "package": st_package, "time": f"{st_time.strftime('%I:%M%p')}-{end_t.strftime('%I:%M%p')}", "color": get_student_color(st_name), "fee": final_fee, "status": "Pending", "method": None})
                save_data(); st.session_state.active_tab_index = 1; st.rerun()

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
                                end_period = b['start_date'] + timedelta(days=30)
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
                                        if o == b: o['status'] = "Pending"; save_data(); st.rerun()
