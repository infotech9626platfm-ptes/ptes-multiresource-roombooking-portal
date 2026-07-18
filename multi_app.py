import streamlit as st
from PIL import Image
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

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

# Time Slots Mapping
time_slots = {
    "(08:00-09:30) Assembly": "Assembly",
    "(10:00-12:00) Morning": "Morning",
    "(13:30-15:30) Afternoon": "Afternoon",
    "(08:00-12:00) Whole Day": "Whole Day"
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
            booking_date = st.date_input("Date of Booking", min_value=datetime.today(), format="DD/MM/YYYY")
            slot_choice = st.selectbox("Time Duration", list(time_slots.keys()))

        submit = st.form_submit_button("Confirm Booking")

    if submit:
        if name and event_name and wa_num:
            # Load existing data from Google Sheet
            existing_data = conn.read(ttl=0)

            # Format selected date object into string representation
            formatted_date = booking_date.strftime("%d/%m/%Y")
            clean_slot_db_value = time_slots[slot_choice]

            # Filter existing data for identical date and room choice
            same_day_room = existing_data[
                (existing_data['Date'].astype(str) == formatted_date) &
                (existing_data['Room'] == room_choice)
            ]

            # Strict Clash Logic (Whole day locks everything; matching slots lock each other)
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

                # Append and upload data structure to cloud
                updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                conn.update(data=updated_df)
                
                # Success visual feedback animations
                st.balloons()
                st.success(f"✅ Success! {room_choice} has been reserved for {event_name}.")
                st.rerun()
        else:
            st.error("Please fill in all required fields.")

with tab2:
    st.subheader("Current Booking Schedule")
    
    # Load master copy from Google Sheets
    master_data = conn.read(ttl=0)

    if not master_data.empty:
        # Create a working copy for processing filters and sorting layouts
        display_df = master_data.copy()

        # --- UPDATED: 14-15 DAY HISTORICAL FILTER ---
        # 1. Convert string date entries to true datetime objects temporarily
        display_df['datetime_obj'] = pd.to_datetime(display_df['Date'], format='%d/%m/%Y', errors='coerce')
        
        # 2. Calculate the exact cutoff point (15 days ago from the current actual date)
        past_cutoff = datetime.today() - timedelta(days=15)
        
        # 3. Filter out rows older than 15 days ago from today (keeps today, future, and recent past)
        display_df = display_df[display_df['datetime_obj'] >= past_cutoff]
        
        # 4. Sort chronologically in descending order (Latest/Future dates at the top)
        display_df = display_df.sort_values(by='datetime_obj', ascending=False)
        
        # 5. Clean up temporary tracking column before rendering
        display_df = display_df.drop(columns=['datetime_obj'])

        # Filter/Search implementation over the processed data frame
        search_query = st.text_input("Search by Room or Lecturer Name")
        if search_query:
            display_df = display_df[
                display_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

        # Render the clean sorted table to screen
        st.dataframe(display_df, hide_index=True, use_container_width=True)

        # Retrieve Environment Secret Variable safely
        try:
            target_password = st.secrets["admin_password"]
        except KeyError:
            target_password = None
            st.sidebar.error("Secrets Configuration Missing: 'admin_password' not found.")

        # Protected administrative dropdown deletion logic
        if target_password and admin_password == target_password:  
            st.divider()
            st.write("### Admin: Cancel a Booking")
            
            # Build choice strings using display_df layout order while tracking master index keys
            booking_options = []
            for master_idx, row in display_df.iterrows():
                description = f"{row['Name']} — {row['Room']} on {row['Date']} ({row['Time_Slot']})"
                booking_options.append((description, master_idx))
            
            if booking_options:
                option_labels = [opt[0] for opt in booking_options]
                selected_label = st.selectbox("Select a Booking to Cancel", options=option_labels)
                
                # Map selected label back to its absolute row location index in the master spreadsheet
                selected_master_index = [opt[1] for opt in booking_options if opt[0] == selected_label][0]
                
                if st.button("Delete Selected Booking", type="primary"):
                    # Drop the row directly via its unique master row pointer
                    updated_master_df = master_data.drop(selected_master_index)
                    conn.update(data=updated_master_df)
                    st.success("Booking deleted successfully.")
                    st.rerun()
            else:
                st.info("No active current bookings available to cancel.")
    else:
        st.info("No bookings found.")

# --- FOOTER ---
st.markdown("---")
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
        <div style="color: gray; font-size: 14px; margin-top: 10px;">
            Creator: Miss Hajah Nurul Haziqah HN (PTES CS Tutor)
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
