import streamlit as st
from PIL import Image
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
import calendar
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Page Configuration
st.set_page_config(page_title="PTES Multi-Resource Booking", layout="wide")

# Load the PTES Logo
try:
    logo = Image.open('ptes_logo.png')
    st.sidebar.image(logo, use_container_width=True)
except Exception:
    st.sidebar.warning("Logo image 'ptes_logo.png' not found.")

st.title("PUSAT TINGKATAN ENAM SENGKURONG")
st.markdown("## Multi-Resource & Facility Booking Platform")

# 1. Database Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Admin Phone Configuration for Notifications
ADMIN_WA_NUMBER = "6737318186"

# Helper Function: Automated Email Notification to Admin
def send_admin_email(booking_details):
    """Sends an automated HTML email notification to the Admin upon new booking."""
    try:
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_PASSWORD"]
        receiver_email = st.secrets["ADMIN_RECEIVER_EMAIL"]

        subject = f"🔔 New Booking Alert: {booking_details['Room']} ({booking_details['Date']})"
        
        body = f"""
        <html>
            <body>
                <h2>📌 New Room Booking Notification</h2>
                <p>A new reservation has been successfully registered on the PTES Booking Portal:</p>
                <ul>
                    <li><b>Lecturer Name:</b> {booking_details['Name']}</li>
                    <li><b>Department:</b> {booking_details['Department']}</li>
                    <li><b>Facility / Room:</b> {booking_details['Room']}</li>
                    <li><b>Date:</b> {booking_details['Date']}</li>
                    <li><b>Time Slot:</b> {booking_details['Time_Slot']}</li>
                    <li><b>Event Purpose:</b> {booking_details['Event']}</li>
                    <li><b>WhatsApp Contact:</b> {booking_details['WhatsApp']}</li>
                </ul>
                <hr>
                <p><i>This is an automated notification from PTES Booking Portal.</i></p>
            </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        # Send via Gmail SMTP Server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True

    except Exception as e:
        st.warning(f"Booking saved, but background email alert failed: {e}")
        return False

# 2. Sidebar - Admin & Instructions
with st.sidebar:
    st.header("Admin Access")
    admin_password = st.text_input("Enter Password to Delete", type="password")

    st.divider()
    st.info("""
    **📜 Booking Rules:**
    1. Check the schedule before booking.
    2. If an event lasts **more than 1 day**, please submit a separate booking for each day.
    3. Confirmed bookings can only be removed by the Admin.
    """)

# 3. Define Resource Options
room_list = [
    "Lecture Theater One", "Lecture Theater Two", "Multi Purpose Hall", "Multi Media Theater",
    "Admin Lobby Area", "Staff Lounge", "Conference Room", "GREEN Area", "Students' Affair Area", "Canteen Area", "Prayer's Musalla"
]

# Time Slots Mapping
time_slots = {
    "(08:00-09:30) Assembly": "Assembly",
    "(10:00-12:00) Morning": "Morning",
    "(13:30-15:30) Afternoon": "Afternoon",
    "(08:00-12:00) Whole Day": "Whole Day"
}

# 4. Tabs for Navigation
tab1, tab2 = st.tabs(["📝 Make a Booking", "📅 View Schedule"])

# ==========================================
# TAB 1: MAKE A BOOKING
# ==========================================
with tab1:
    st.warning("⚠️ **Reminder:** For multi-day events, please book each day individually.")

    with st.form("booking_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Lecturer Name")
            dept = st.selectbox("Organisation", ["STEAM", "PIBG", "SportHouse", "Mathematics", "ICT Related", "Religious", "Administration", "Sciences", "Assembly", "Others"])
            wa_num = st.text_input("Active WhatsApp Number (e.g. +673...)")
            # NEW: Notification preference selection
            notify_option = st.selectbox("Notify Admin via", ["Email Notification", "WhatsApp Link", "No Notification"])

        with col2:
            event_name = st.text_input("Event Title / Purpose")
            room_choice = st.selectbox("Select Room / Facility", room_list)
            booking_date = st.date_input("Date of Booking", min_value=datetime.today(), format="DD/MM/YYYY")
            slot_choice = st.selectbox("Time Duration", list(time_slots.keys()))

        submit = st.form_submit_button("Confirm Booking")

    if submit:
        if name and event_name and wa_num:
            # Read current data from Google Sheets
            existing_data = conn.read(ttl=0)

            formatted_date = booking_date.strftime("%d/%m/%Y")
            clean_slot_db_value = time_slots[slot_choice]

            # Clash Check Logic
            same_day_room = existing_data[
                (existing_data['Date'].astype(str) == formatted_date) &
                (existing_data['Room'] == room_choice)
            ]

            clash = same_day_room[
                (same_day_room['Time_Slot'] == clean_slot_db_value) |
                (same_day_room['Time_Slot'] == "Whole Day") |
                (clean_slot_db_value == "Whole Day")
            ]

            if not clash.empty:
                st.error(f"❌ CLASH DETECTED: {room_choice} is unavailable on {formatted_date} due to a conflicting reservation.")
            else:
                new_entry = pd.DataFrame([{
                    "Name": name,
                    "Department": dept,
                    "WhatsApp": wa_num,
                    "Event": event_name,
                    "Room": room_choice,
                    "Date": formatted_date, 
                    "Time_Slot": clean_slot_db_value
                }])

                # Append to Google Sheet
                updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                conn.update(data=updated_df)
                
                details_payload = {
                    "Name": name,
                    "Department": dept,
                    "WhatsApp": wa_num,
                    "Event": event_name,
                    "Room": room_choice,
                    "Date": formatted_date,
                    "Time_Slot": clean_slot_db_value
                }

                st.balloons()
                st.success(f"✅ Success! {room_choice} has been reserved for {event_name}.")

                # DYNAMIC NOTIFICATION DISPATCH
                if notify_option == "Email Notification":
                    with st.spinner("Notifying Admin via automated email..."):
                        email_sent = send_admin_email(details_payload)
                    if email_sent:
                        st.info("✉️ Admin notified via automated email.")
                    time.sleep(3)
                    st.rerun()

                elif notify_option == "WhatsApp Link":
                    message_body = (
                        f"📌 *NEW ROOM BOOKING NOTIFICATION*\n\n"
                        f"👤 *Lecturer:* {name}\n"
                        f"🏢 *Department:* {dept}\n"
                        f"🏛️ *Room:* {room_choice}\n"
                        f"📅 *Date:* {formatted_date}\n"
                        f"⏰ *Time Slot:* {clean_slot_db_value}\n"
                        f"📝 *Event:* {event_name}\n"
                        f"📞 *Contact:* {wa_num}"
                    )
                    encoded_msg = urllib.parse.quote(message_body)
                    wa_url = f"https://wa.me/{ADMIN_WA_NUMBER}?text={encoded_msg}"
                    
                    st.markdown(f'👉 [**Click Here to Send WhatsApp Notification to Admin**]({wa_url})')
                    time.sleep(5)
                    st.rerun()

                else:  # No Notification
                    time.sleep(3)
                    st.rerun()
        else:
            st.error("Please fill in all required fields.")

# ==========================================
# TAB 2: INTERACTIVE CALENDAR SCHEDULE VIEW
# ==========================================
with tab2:
    st.subheader("📅 Monthly Interactive Schedule Calendar")
    
    master_data = conn.read(ttl=0)

    # Date / Month Selection Controls
    col_m, col_y = st.columns(2)
    with col_m:
        month_names = list(calendar.month_name)[1:]
        selected_month_str = st.selectbox("Select Month", month_names, index=datetime.today().month - 1)
        selected_month = month_names.index(selected_month_str) + 1
    with col_y:
        selected_year = st.number_input("Select Year", min_value=2024, max_value=2030, value=datetime.today().year)

    # Initialize Active Selected Day in Session State
    if 'selected_calendar_day' not in st.session_state:
        st.session_state.selected_calendar_day = datetime.today().day

    if not master_data.empty:
        display_df = master_data.copy()
        display_df['datetime_obj'] = pd.to_datetime(display_df['Date'], format='%d/%m/%Y', errors='coerce')

        # Filter dataset for selected month & year
        month_data = display_df[
            (display_df['datetime_obj'].dt.month == selected_month) &
            (display_df['datetime_obj'].dt.year == selected_year)
        ]

        # Generate Calendar Matrix (Monday start)
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(selected_year, selected_month)

        # Header
        days_header = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cols = st.columns(7)
        for i, h in enumerate(days_header):
            cols[i].markdown(f"### {h}")

        st.divider()

        # Render Grid Cells
        for week in month_days:
            grid_cols = st.columns(7)
            for i, day in enumerate(week):
                with grid_cols[i]:
                    if day != 0:
                        day_str = f"{day:02d}/{selected_month:02d}/{selected_year}"
                        day_bookings = month_data[month_data['Date'] == day_str]
                        booking_count = len(day_bookings)

                        if booking_count > 0:
                            label = f"🔴 {day:02d} ({booking_count})"
                        else:
                            label = f"⚪ {day:02d}"

                        if st.button(label, key=f"btn_day_{day}_{selected_month}_{selected_year}", use_container_width=True):
                            st.session_state.selected_calendar_day = day

        st.divider()

        # Detailed Day Inspection Table
        active_day = st.session_state.selected_calendar_day
        max_days = calendar.monthrange(selected_year, selected_month)[1]
        if active_day > max_days:
            active_day = max_days

        inspected_date_str = f"{active_day:02d}/{selected_month:02d}/{selected_year}"
        st.write(f"### 🔍 Reservations Summary for **{inspected_date_str}**")

        details_df = month_data[month_data['Date'] == inspected_date_str]

        if not details_df.empty:
            st.success(f"Found {len(details_df)} booking(s) for this date:")
            clean_details = details_df[['Name', 'Department', 'Room', 'Time_Slot', 'Event', 'WhatsApp']]
            st.dataframe(clean_details, hide_index=True, use_container_width=True)
        else:
            st.info(f"No bookings registered for {inspected_date_str}.")

        # Protected Admin Cancellation Section
        try:
            target_password = st.secrets["admin_password"]
        except KeyError:
            target_password = None

        if target_password and admin_password == target_password:  
            st.divider()
            st.write("### 🔑 Admin: Cancel a Booking")
            
            booking_options = []
            for master_idx, row in master_data.iterrows():
                desc = f"{row['Name']} — {row['Room']} on {row['Date']} ({row['Time_Slot']})"
                booking_options.append((desc, master_idx))
            
            if booking_options:
                option_labels = [opt[0] for opt in booking_options]
                selected_label = st.selectbox("Select a Booking to Cancel", options=option_labels)
                selected_master_index = [opt[1] for opt in booking_options if opt[0] == selected_label][0]
                
                if st.button("Delete Selected Booking", type="primary"):
                    updated_master_df = master_data.drop(selected_master_index)
                    conn.update(data=updated_master_df)
                    st.success("Booking deleted successfully.")
                    st.rerun()
    else:
        st.info("No bookings found in database.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; width: 100%;">
        <p style="font-size: 18px; font-weight: bold;">✨ PTES Multi Resource Rooms Booking Portal ✨</p>
    </div>
    """,
    unsafe_allow_html=True
)
