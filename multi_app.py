import streamlit as st
from PIL import Image

# Load the PTES Logo
logo = Image.open('ptes_logo.png')

# Display logo at the top of the Sidebar
st.sidebar.image(logo, use_container_width=True)

# OR Display logo at the top of the Main Page
# st.image(logo, width=100)

from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="PTES Multi-Resource Booking", layout="wide")

st.title("PUSAT TINGKATAN ENAM SENGKURONG")
st.markdown("## Multi-Resource & Facility Booking Platform")

# 1. Database Connection
conn = st.connection("gsheets", type=GSheetsConnection)

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
    "Admin Lobby Area", "Staff Lounge", "Conference Room", "Prayer's Hall / Musalla",
]

time_slots = {
    "Morning (08:00 - 11:30)": "Morning",
    "Afternoon (13:00 - 16:30)": "Afternoon",
    "Whole Day (08:00 - 15:30)": "Whole Day"
}

# 4. Tabs for Navigation
tab1, tab2 = st.tabs(["📝 Make a Booking", "📅 View Schedule"])

with tab1:
    st.warning("⚠️ **Reminder:** For multi-day events, please book each day individually.")

    with st.form("booking_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Lecturer Name")
            dept = st.selectbox("Position / Department", ["Arts&Design&Media", "Science", "Humanities", "Mathematics", "Languages", "Religious Studies","Administration", "Others"])
            wa_num = st.text_input("Active WhatsApp Number (e.g. +673...)")

        with col2:
            event_name = st.text_input("Event Name / Purpose")
            room_choice = st.selectbox("Select Room / Facility", room_list)
            booking_date = st.date_input("Date of Booking", min_value=datetime.today())
            slot_choice = st.selectbox("Time Duration", list(time_slots.keys()))

        submit = st.form_submit_button("Confirm Booking")

    if submit:
        if name and event_name and wa_num:
            # Load existing data to check for clashes
            existing_data = conn.read(ttl=0)

            # Formulate the check
            formatted_date = booking_date.strftime("%d/%m/%Y")

            # 1. Filter existing data for the SAME date and SAME room
            same_day_room = existing_data[
                (existing_data['Date'] == formatted_date) &
                (existing_data['Room'] == room_choice)
                ]

            # 2. Smart Clash Logic: Find ANY overlap
            # A clash occurs if:
            # - Any existing booking is "Whole Day"
            # - OR the NEW booking is "Whole Day"
            # - OR the time slots match exactly
            clash = same_day_room[
                (same_day_room['Time_Slot'].str.contains("Whole Day", na=False)) |
                ("Whole Day" in slot_choice) |
                (same_day_room['Time_Slot'] == slot_choice)
                ]

            if not clash.empty:
                st.error(f"❌ CLASH DETECTED: {room_choice} is already booked for {slot_choice} on {formatted_date}.")
            else:
                # Add new booking
                new_entry = pd.DataFrame([{
                    "Name": name,
                    "Department": dept,
                    "WhatsApp": wa_num,
                    "Event": event_name,
                    "Room": room_choice,
                    "Date": formatted_date,
                    "Time_Slot": slot_choice
                }])

                updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"✅ Success! {room_choice} has been reserved for {event_name}.")
                st.balloons()
        else:
            st.error("Please fill in all required fields.")

with tab2:
    st.subheader("Current Booking Schedule")
    # Read data
    schedule_data = conn.read(ttl=0)

    if not schedule_data.empty:
        # Filter/Search feature
        search_query = st.text_input("Search by Room or Lecturer Name")
        if search_query:
            schedule_data = schedule_data[
                schedule_data.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

        # st.dataframe(schedule_data, use_container_width=True)
        st.dataframe(schedule_data, hide_index=True, use_container_width=True)
        # st.dataframe(df, hide_index=True)

        # Admin Delete Logic
        if admin_password == "admin123":  # Change this to your preferred password
            st.divider()
            st.write("### Admin: Cancel a Booking")
            row_to_delete = st.number_input("Enter Row Index to Delete", min_value=0, max_value=len(schedule_data) - 1,
                                            step=1)
            if st.button("Delete Selected Booking"):
                schedule_data = schedule_data.drop(schedule_data.index[row_to_delete])
                conn.update(data=schedule_data)
                st.success("Booking deleted successfully.")
                st.rerun()
    else:
        st.info("No bookings found.")

# --- FOOTER ---
st.markdown("---")

# Using a single container with centered alignment
st.markdown(
    """
    <div style="text-align: center; width: 100%;">
        <p style="font-size: 20px; font-weight: bold; margin-bottom: 5px;">
            ✨ PTES Multi Resource Rooms Booking Portal ✨
        </p>
        <p style="font-size: 16px; font-weight: bold; letter-spacing: 0.5px;">
            <span style="color: #FF0000;">🔴 By providing</span> | 
            <span style="color: #FFD700;">🟡 Equal Opportunity</span> | 
            <span style="color: #0070FF;">🔵 Quality Education</span> | 
            <span style="color: #28A745;">🟢 Equipping 21st century Skills</span>
        </p>
        <p style="color: gray; font-size: 14px; margin-top: 10px;">
            Creator: Miss Hajah Nurul Haziqah HN (PTES CS Tutor)
        </p>
    </div>
    """,
    unsafe_allow_html=True
)