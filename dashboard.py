import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. APP CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Falkenherz HR Dashboard", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 5px solid #2E86C1;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #ffffff;
        border-radius: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. ROBUST DATA LOADER
# -----------------------------------------------------------------------------
@st.cache_data
def load_all_data():
    data = {
        "active": pd.DataFrame(),
        "inactive": pd.DataFrame(),
        "recruitment": pd.DataFrame(),
        "performance": pd.DataFrame(),
        "leave": pd.DataFrame()
    }
    
    master_file = "Employee Master Sheet - Lahore Office.xlsx"
    
    if os.path.exists(master_file):
        try:
            # --- A. ACTIVE STAFF ---
            # Smart Search for Header Row
            df_temp = pd.read_excel(master_file, sheet_name="Active Staff", header=None, nrows=15)
            header_idx = None
            for i, row in df_temp.iterrows():
                row_str = row.astype(str).values.tolist()
                if "Employee Number" in row_str and "Name" in row_str:
                    header_idx = i
                    break
            
            if header_idx is not None:
                df_act = pd.read_excel(master_file, sheet_name="Active Staff", header=header_idx)
                # Cleaning
                df_act = df_act[df_act['Name'].notna()]
                df_act = df_act[df_act['Employee Number'] != 'Employee Number']
                
                # Normalize Columns
                if 'Business Unit' in df_act.columns: 
                    df_act['Business Unit'] = df_act['Business Unit'].fillna('Unassigned')
                if 'Reporting To' in df_act.columns: 
                    df_act['Reporting To'] = df_act['Reporting To'].fillna('Direct to CEO')
                if 'Joining Date' in df_act.columns: 
                    df_act['Joining Date'] = pd.to_datetime(df_act['Joining Date'], errors='coerce')
                
                data["active"] = df_act

            # --- B. INACTIVE STAFF ---
            df_inact = pd.read_excel(master_file, sheet_name="Inactive Staff", header=0)
            if 'Exit Date' in df_inact.columns: 
                df_inact['Exit Date'] = pd.to_datetime(df_inact['Exit Date'], errors='coerce')
            data["inactive"] = df_inact
            
        except Exception as e:
            st.error(f"Error loading Master File: {e}")

    # --- C. RECRUITMENT ---
    rec_file = "Hirings Requests UAE & PK.xlsx"
    if os.path.exists(rec_file):
        try:
            df_rec = pd.read_excel(rec_file, sheet_name="Progress")
            # Funnel Logic
            def get_stage(status_text):
                text = str(status_text).lower()
                if "join" in text or "hired" in text: return "Hired"
                if "offer" in text: return "Offer Extended"
                if "interview" in text: return "Interview"
                if "shortlist" in text: return "Shortlisted"
                return "Applied/In Process"
            
            if 'Standing' in df_rec.columns:
                df_rec['Funnel Stage'] = df_rec['Standing'].apply(get_stage)
            data["recruitment"] = df_rec
        except: pass

    # --- D. PERFORMANCE ---
    perf_file = "Increment - Lahore Office _ Apr - Sep 25.xlsx"
    if os.path.exists(perf_file):
        try:
            df_perf = pd.read_excel(perf_file, sheet_name="Evaluation Data")
            score_col = 'Total Points (Out of 100)'
            if score_col in df_perf.columns:
                df_perf[score_col] = pd.to_numeric(df_perf[score_col], errors='coerce')
                def classify(score):
                    if pd.isna(score): return "Pending"
                    if score >= 85: return "High Performer"
                    elif score < 70: return "Low Performer"
                    else: return "Average"
                df_perf['Category'] = df_perf[score_col].apply(classify)
                data["performance"] = df_perf
        except: pass

    # --- E. LEAVE MANAGEMENT ---
    leave_file = "Leave Record - 2025.xlsx"
    if os.path.exists(leave_file):
        try:
            # Multi-header logic
            df_leave = pd.read_excel(leave_file, sheet_name="Summary", header=1)
            
            if 'Employee Name' not in df_leave.columns:
                df_leave.rename(columns={df_leave.columns[1]: 'Employee Name'}, inplace=True)
            
            df_leave = df_leave[df_leave['Employee Name'].notna()]

            # Calculate Total Availed (look for columns ending in .1 which signify Availed in this format)
            availed_cols = [c for c in df_leave.columns if str(c).endswith('.1')]
            if availed_cols:
                df_leave['Total Availed'] = df_leave[availed_cols].apply(pd.to_numeric, errors='coerce').sum(axis=1)
            else:
                df_leave['Total Availed'] = 0
            
            data["leave"] = df_leave
        except: pass

    return data

# Load Data Once
datasets = load_all_data()
df_active = datasets["active"]
df_inactive = datasets["inactive"]
df_rec = datasets["recruitment"]
df_perf = datasets["performance"]
df_leave = datasets["leave"]

# -----------------------------------------------------------------------------
# 3. SIDEBAR BRANDING & NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    # --- BRANDING SECTION ---
    # Replace these URLs with local file paths (e.g., "logo.png")
    st.image("FHZ-Logo-2.png", use_container_width=True)
    
    st.markdown("### Ventures")
    c1, c2, c3 = st.columns(3)
    c1.image("vertical-logo-light-background.png", caption="Voltro")
    c2.image("Untitled-2-01 - Copy - Copy-1 (2).png", caption="FAMS")
    c3.image("logo final-01-01 - Copy.png", caption="JetClass")
    
    st.markdown("---")
    
    # --- NAVIGATION MENU ---
    menu = st.radio("Main Menu", [
        "Dashboard Overview", 
        "Leave Management",
        "Organization Structure",
        "Employee Movement",
        "Recruitment Tracking",
        "Performance Management",
        "Employee Master File",
        "Policies & Documentation"
    ])
    
    st.markdown("---")
    st.caption("Falkenherz Group • HR Dept")

# -----------------------------------------------------------------------------
# 4. MODULE: DASHBOARD OVERVIEW (Req 1-4)
# -----------------------------------------------------------------------------
if menu == "Dashboard Overview":
    st.title("📊 HR Executive Overview")
    
    if not df_active.empty:
        # Metrics
        total = len(df_active) + len(df_inactive)
        active = len(df_active)
        retention = (active / total * 100) if total > 0 else 0
        
        probation = 0
        if 'Employment Status' in df_active.columns:
            probation = df_active['Employment Status'].astype(str).str.contains('Probation', case=False).sum()

        # Scorecards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Headcount", total)
        c2.metric("Active Employees", active)
        c3.metric("Retention Rate", f"{retention:.1f}%")
        c4.metric("On Probation", probation, delta="Action Req", delta_color="inverse")
        
        st.markdown("---")
        
        # Charts
        c_left, c_right = st.columns(2)
        with c_left:
            st.subheader("Headcount by Business Unit")
            if 'Business Unit' in df_active.columns:
                bu_counts = df_active['Business Unit'].value_counts().reset_index()
                bu_counts.columns = ['Business Unit', 'Count']
                fig = px.bar(bu_counts, x='Business Unit', y='Count', color='Business Unit', text='Count')
                st.plotly_chart(fig, use_container_width=True)
        
        with c_right:
            st.subheader("Leave Utilization (Top 5)")
            if not df_leave.empty and 'Total Availed' in df_leave.columns:
                top_leaves = df_leave.sort_values('Total Availed', ascending=False).head(5)
                fig_leave = px.bar(top_leaves, x='Total Availed', y='Employee Name', orientation='h')
                st.plotly_chart(fig_leave, use_container_width=True)
    else:
        st.warning("Data not loaded. Please ensure Excel files are in the folder.")

# -----------------------------------------------------------------------------
# 5. MODULE: LEAVE MANAGEMENT (Req 14)
# -----------------------------------------------------------------------------
elif menu == "Leave Management":
    st.title("📅 Leave Management System")
    
    if not df_leave.empty:
        total_leaves = df_leave['Total Availed'].sum()
        avg_leaves = df_leave['Total Availed'].mean()
        
        m1, m2 = st.columns(2)
        m1.metric("Total Leaves Availed (YTD)", f"{total_leaves:.0f}")
        m2.metric("Avg Leaves per Employee", f"{avg_leaves:.1f}")
        
        st.markdown("---")
        
        # Balance Table Logic
        st.subheader("Employee Leave Balances")
        # Identify balance columns (ending in .2)
        balance_map = {}
        for col in df_leave.columns:
            if str(col).endswith('.2'):
                clean_name = str(col).replace('.2', '') + " (Bal)"
                balance_map[col] = clean_name
        
        base_cols = ['Employee Name', 'Designation', 'Total Availed']
        valid_base = [c for c in base_cols if c in df_leave.columns]
        cols_to_show = valid_base + list(balance_map.keys())
        
        df_disp = df_leave[cols_to_show].rename(columns=balance_map)
        
        # Search
        search = st.text_input("Search Employee:", placeholder="Name...")
        if search:
            mask = df_disp.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df_disp = df_disp[mask]
            
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
        
        # Leave Type Pie Chart
        st.markdown("### Leave Type Breakdown")
        type_sums = {}
        for col in df_leave.columns:
            if str(col).endswith('.1'): # .1 signifies 'Availed' in summary sheet
                l_type = str(col).replace('.1', '')
                type_sums[l_type] = df_leave[col].apply(pd.to_numeric, errors='coerce').sum()
        
        if type_sums:
            df_types = pd.DataFrame(list(type_sums.items()), columns=['Type', 'Count'])
            fig_types = px.pie(df_types, values='Count', names='Type', hole=0.4)
            st.plotly_chart(fig_types, use_container_width=True)
    else:
        st.warning("Leave data not found.")

# -----------------------------------------------------------------------------
# 6. MODULE: ORGANIZATION STRUCTURE (Req 13)
# -----------------------------------------------------------------------------
elif menu == "Organization Structure":
    st.title("🏢 Organization Hierarchy")
    
    if not df_active.empty:
        st.subheader("Interactive Hierarchy")
        # Path: BU -> Dept -> Designation
        path = []
        if 'Business Unit' in df_active.columns: path.append('Business Unit')
        if 'Department' in df_active.columns: path.append('Department')
        if 'Designation' in df_active.columns: path.append('Designation')
        
        if path:
            df_tree = df_active.groupby(path).size().reset_index(name='Count')
            fig = px.sunburst(df_tree, path=path, values='Count', height=600)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### Reporting Matrix")
        # Safe column selection
        cols = ['Name', 'Designation', 'Business Unit', 'Reporting To']
        valid = [c for c in cols if c in df_active.columns]
        
        bu_filter = st.multiselect("Filter by Business Unit", options=df_active['Business Unit'].unique())
        df_show = df_active[valid]
        if bu_filter:
            df_show = df_show[df_show['Business Unit'].isin(bu_filter)]
            
        st.dataframe(df_show.sort_values('Reporting To'), use_container_width=True)

# -----------------------------------------------------------------------------
# 7. MODULE: EMPLOYEE MOVEMENT (Req 11-12)
# -----------------------------------------------------------------------------
elif menu == "Employee Movement":
    st.title("🔄 Employee Movement")
    
    if not df_active.empty:
        # New Joiners Logic
        max_date = df_active['Joining Date'].max()
        if pd.notnull(max_date):
            curr_month = max_date.strftime("%B %Y")
            new_joiners = df_active[
                (df_active['Joining Date'].dt.month == max_date.month) & 
                (df_active['Joining Date'].dt.year == max_date.year)
            ]
        else:
            new_joiners = pd.DataFrame()
            curr_month = "N/A"
            
        m1, m2 = st.columns(2)
        m1.metric(f"New Joiners ({curr_month})", len(new_joiners), delta="Growth")
        m2.metric("Total Attrition", len(df_inactive), delta="Exits", delta_color="inverse")
        
        st.markdown("---")
        
        t1, t2 = st.tabs(["📉 Attrition Analysis", "🆕 New Joiners"])
        
        with t1:
            if not df_inactive.empty:
                c1, c2 = st.columns(2)
                with c1: 
                    if 'Reason' in df_inactive.columns:
                        fig = px.pie(df_inactive, names='Reason', title="Exit Reasons")
                        st.plotly_chart(fig, use_container_width=True)
                with c2:
                    # Safe select
                    e_cols = ['Name', 'Designation', 'Exit Date', 'Reason']
                    v_e = [c for c in e_cols if c in df_inactive.columns]
                    st.dataframe(df_inactive[v_e])
                    
        with t2:
            # Safe select for joiners
            j_cols = ['Name', 'Designation', 'Department', 'Joining Date', 'Reporting To']
            v_j = [c for c in j_cols if c in new_joiners.columns]
            st.dataframe(new_joiners[v_j], use_container_width=True)

# -----------------------------------------------------------------------------
# 8. MODULE: RECRUITMENT TRACKING (Req 10)
# -----------------------------------------------------------------------------
elif menu == "Recruitment Tracking":
    st.title("📢 Recruitment Tracker")
    
    if not df_rec.empty:
        closed = df_rec[df_rec['Funnel Stage'] == 'Hired'].shape[0]
        open_pos = len(df_rec) - closed
        
        st.metric("Open Positions", open_pos)
        
        c1, c2 = st.columns(2)
        with c1:
            counts = df_rec['Funnel Stage'].value_counts().reset_index()
            counts.columns = ['Stage', 'Count']
            order = ['Applied/In Process', 'Shortlisted', 'Interview', 'Offer Extended', 'Hired']
            counts['Stage'] = pd.Categorical(counts['Stage'], categories=order, ordered=True)
            counts = counts.sort_values('Stage')
            fig = px.funnel(counts, x='Count', y='Stage', title="Hiring Funnel")
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            if 'BU' in df_rec.columns:
                fig_bu = px.histogram(df_rec[df_rec['Funnel Stage']!='Hired'], y='BU', title="Openings by Dept")
                st.plotly_chart(fig_bu, use_container_width=True)

        st.dataframe(df_rec[['BU', 'Position', 'Status', 'Funnel Stage']], use_container_width=True)
    else:
        st.warning("Recruitment data not found.")

# -----------------------------------------------------------------------------
# 9. MODULE: PERFORMANCE MANAGEMENT (Req 7-9)
# -----------------------------------------------------------------------------
elif menu == "Performance Management":
    st.title("🚀 Performance Appraisals")
    
    if not df_perf.empty:
        avg = df_perf['Total Points (Out of 100)'].mean()
        high = len(df_perf[df_perf['Category'] == 'High Performer'])
        
        col1, col2 = st.columns(2)
        col1.metric("Avg Score", f"{avg:.1f}")
        col2.metric("High Performers", high)
        
        st.markdown("### Appraisal Data")
        cat = st.selectbox("Filter Category", ["All", "High Performer", "Average", "Low Performer"])
        df_show = df_perf
        if cat != "All":
            df_show = df_show[df_show['Category'] == cat]
            
        # Safe Select
        p_cols = ['Name', 'Total Points (Out of 100)', 'Category', 'Evaluated By']
        v_p = [c for c in p_cols if c in df_perf.columns]
        st.dataframe(df_show[v_p], use_container_width=True)
    else:
        st.warning("Performance data not found.")

# -----------------------------------------------------------------------------
# 10. MODULE: EMPLOYEE MASTER FILE (Req 5-6)
# -----------------------------------------------------------------------------
elif menu == "Employee Master File":
    st.title("📂 Employee Master Database")
    
    if not df_active.empty:
        t1, t2 = st.tabs(["Search", "Probation"])
        
        with t1:
            q = st.text_input("Search Name/ID")
            # Safe Select
            m_cols = ['Employee Number', 'Name', 'Designation', 'Department', 'Business Unit', 'Reporting To', 'Joining Date', 'Profiles']
            v_m = [c for c in m_cols if c in df_active.columns]
            
            df_d = df_active[v_m].copy()
            if 'Profiles' in df_d.columns: 
                df_d.rename(columns={'Profiles': 'CV Link'}, inplace=True)
            
            if q:
                df_d = df_d[df_d.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)]
            
            st.dataframe(
                df_d, 
                use_container_width=True,
                column_config={"CV Link": st.column_config.LinkColumn("CV Link", display_text="View CV")}
            )
            
        with t2:
            if 'Employment Status' in df_active.columns:
                prob = df_active[df_active['Employment Status'].str.contains('Probation', case=False, na=False)]
                st.error(f"{len(prob)} Employees on Probation")
                st.dataframe(prob)

# -----------------------------------------------------------------------------
# 11. MODULE: POLICIES (Req 9)
# -----------------------------------------------------------------------------
elif menu == "Policies & Documentation":
    st.title("📜 Policies")
    t1, t2 = st.tabs(["Approved", "Drafts"])
    
    with t1:
        st.info("Effective immediately")
        with st.expander("Annual Increment Policy"): st.write("Eligibility: 12 Months service.")
        with st.expander("Recruitment Policy"): st.write("KPI: Time to hire < 30 days.")
        with st.expander("Leave Policy"): st.write("WFH: Allowed once a week.")
        with st.expander("Code of Conduct"): st.write("Zero Tolerance Policy.")
    
    with t2:
        st.warning("Under Review")
        st.write("- AI Usage Policy")
        st.write("- Wellness Program")