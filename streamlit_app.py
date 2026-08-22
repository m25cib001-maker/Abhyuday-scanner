# ============================================================
# ABHYUDAY 2026 - CLOUD QR SCANNER
# ============================================================

import streamlit as st
import pandas as pd
import jwt
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time
import re

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Abhyuday 2026 - QR Scanner",
    page_icon="🎟️",
    layout="wide"
)

# ============================================
# SECRET KEY (Same as Colab)
# ============================================
SECRET_KEY = "Abhyuday2026_IITJ_SecureKey_DoNotShare"

# ============================================
# GOOGLE SHEETS CONNECTION
# ============================================
def connect_to_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        creds_dict = {
            "type": st.secrets["type"],
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets["private_key_id"],
            "private_key": st.secrets["private_key"],
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets["client_x509_cert_url"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet_url = st.secrets["sheet_url"]
        sheet = client.open_by_url(sheet_url)
        return sheet.get_worksheet(0)
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None

# ============================================
# SESSION STATE
# ============================================
if 'scanned' not in st.session_state:
    st.session_state.scanned = False
if 'result' not in st.session_state:
    st.session_state.result = None

# ============================================
# VALIDATE SCAN
# ============================================
def validate_scan(token, worksheet):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        roll_no = payload.get('roll_no')
        name = payload.get('name')
        
        records = worksheet.get_all_records()
        for record in records:
            if str(record.get('Roll_No', '')) == str(roll_no):
                if record.get('Status') == 'IN HOUSE':
                    return {
                        'success': False,
                        'message': f'❌ {name} is already checked in!',
                        'name': name,
                        'duplicate': True
                    }
        
        cell = worksheet.find(str(roll_no))
        if cell:
            row_num = cell.row
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            worksheet.update(f'G{row_num}', 'IN HOUSE')
            worksheet.update(f'H{row_num}', current_time)
            
            return {
                'success': True,
                'name': name,
                'roll_no': roll_no,
                'time': current_time,
                'message': f'✅ {name} checked in!'
            }
        else:
            return {
                'success': False,
                'message': '❌ Student not found in database',
                'name': name
            }
            
    except jwt.ExpiredSignatureError:
        return {
            'success': False,
            'message': '❌ QR expired! Please refresh.',
            'name': 'Unknown'
        }
    except jwt.InvalidTokenError:
        return {
            'success': False,
            'message': '❌ Invalid QR! Contact organizers.',
            'name': 'Unknown'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'❌ Error: {str(e)}',
            'name': 'Unknown'
        }

# ============================================
# UI
# ============================================
st.markdown("""
<style>
    .big-title { text-align: center; font-size: 3rem; color: #ffd700; }
    .stats { display: flex; gap: 2rem; justify-content: center; margin: 2rem 0; }
    .stat-box { background: #1a1a4e; padding: 1.5rem; border-radius: 12px; text-align: center; min-width: 150px; }
    .stat-num { font-size: 2.5rem; font-weight: bold; color: #ffd700; }
    .stat-label { color: #aaa; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="big-title">🎟️ Abhyuday 2026</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #aaa;">Freshers QR Scanner & Entry Validation</p>', unsafe_allow_html=True)

# Connect to sheet
worksheet = connect_to_sheet()

if not worksheet:
    st.error("❌ Could not connect to Google Sheets. Please check credentials.")
    st.stop()

# Dashboard
records = worksheet.get_all_records()
total = len(records)
checked_in = sum(1 for r in records if r.get('Status') == 'IN HOUSE')

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total Freshers", total)
with col2:
    st.metric("✅ Checked In", checked_in)
with col3:
    st.metric("⏳ Remaining", total - checked_in)

# Scanner
st.divider()
st.subheader("📷 Scan QR Code")

qr_input = st.text_input(
    "Paste QR token here (or scan via camera)",
    placeholder="Paste the token from QR code...",
    key="qr_input"
)

col_scan, col_clear = st.columns(2)
with col_scan:
    if st.button("🔍 Validate", type="primary", use_container_width=True):
        if qr_input:
            result = validate_scan(qr_input, worksheet)
            st.session_state.result = result
            st.session_state.scanned = True
        else:
            st.warning("Please enter a QR token")

with col_clear:
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.scanned = False
        st.session_state.result = None
        st.rerun()

if st.session_state.scanned and st.session_state.result:
    result = st.session_state.result
    if result.get('success'):
        st.success(f"✅ {result['message']}")
        st.balloons()
    elif result.get('duplicate'):
        st.warning(result['message'])
    else:
        st.error(result['message'])

# Recent check-ins
st.divider()
st.subheader("📋 Recent Check-ins")

checkins = [r for r in records if r.get('Status') == 'IN HOUSE']
checkins = checkins[-10:][::-1]

if checkins:
    for c in checkins:
        st.text(f"✅ {c.get('Name')} ({c.get('Roll_No')}) - {c.get('Check-in Time', '')}")
else:
    st.info("No check-ins yet")

# Export
st.divider()
if st.button("📥 Download Attendance Excel"):
    df = pd.DataFrame(records)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="abhyuday_attendance.csv",
        mime="text/csv"
    )

with st.expander("📖 Instructions for Volunteers"):
    st.markdown("""
    1. **Fresher shows QR on their phone**
    2. **Paste the QR token in the box above**
    3. **Click Validate**
    4. **If valid → Student is marked "IN HOUSE"**
    5. **QR expires in 30 seconds!**
    
    **Duplicate Prevention:**
    - Once scanned, the student can't scan again
    - You'll see "Already checked in" warning
    """)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #666;'>Abhyuday 2026 - SWC Team, IIT Jodhpur</p>", unsafe_allow_html=True)
