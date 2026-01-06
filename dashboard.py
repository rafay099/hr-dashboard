import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import requests
from datetime import datetime

# ==============================================================================
# 1. APP CONFIGURATION & THEME
# ==============================================================================
st.set_page_config(
    page_title="Falkenherz HR Dashboard", 
    layout="wide", 
    page_icon="FHZ-Logo-2.png",
    initial_sidebar_state="expanded"
)

# --- COLOR PALETTE ---
PRIMARY = "#2E86C1"    # Falkenherz Blue
SECONDARY = "#2ECC71"  # Success Green
DANGER = "#E74C3C"     # Red for Exits
TEXT_COLOR = "#1F2937" 
CARD_BG = "#FFFFFF"
BG_COLOR = "#F4F6F9"

# --- LOTTIE ANIMATION LOADER ---
try:
    from streamlit_lottie import st_lottie
    @st.cache_data(ttl=86400) 
    def load_lottieurl(url: str):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: return None
            return r.json()
        except: return None
except ImportError:
    def st_lottie(animation_json, height=200, key=None):
        pass 
    def load_lottieurl(url): return None

lottie_hr = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_5tl1xxnz.json") 
lottie_hiring = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_w51pcehl.json") 
lottie_move = load_lottieurl("https://assets2.lottiefiles.com/packages/lf20_hX7y8C.json") 

# --- ADVANCED CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {BG_COLOR}; font-family: 'Inter', sans-serif; }}
    h1, h2, h3, h4, h5, p, span, div, label {{ color: {TEXT_COLOR} !important; }}
    
    header[data-testid="stHeader"] {{
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #E5E7EB;
    }}
    
    div[data-testid="metric-container"] {{
        background-color: {CARD_BG};
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 5px solid {PRIMARY};
    }}
    div[data-testid="stMetricValue"] {{ color: {PRIMARY} !important; }}
    
    .chart-box {{
        background-color: {CARD_BG};
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        margin-bottom: 20px;
        border: 1px solid #E5E7EB;
    }}
    
    [data-testid="stSidebar"] {{
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. DATA ENGINE
# ==============================================================================
@st.cache_data
def load_data():
    data = {
        "active": pd.DataFrame(), "inactive": pd.DataFrame(),
        "recruitment": pd.DataFrame(), "performance": pd.DataFrame(), "leave": pd.DataFrame()
    }
    
    master_file = "Employee Master Sheet - Lahore Office.xlsx"
    if os.path.exists(master_file):
        try:
            # Active Staff
            df_temp = pd.read_excel(master_file, sheet_name="Active Staff", header=None, nrows=15)
            header_idx = None
            for i, row in df_temp.iterrows():
                if "Employee Number" in row.astype(str).values.tolist() and "Name" in row.astype(str).values.tolist():
                    header_idx = i; break
            
            if header_idx is not None:
                df_act = pd.read_excel(master_file, sheet_name="Active Staff", header=header_idx)
                df_act = df_act[df_act['Name'].notna()]
                df_act = df_act[df_act['Employee Number'] != 'Employee Number']
                if 'Business Unit' in df_act.columns: df_act['Business Unit'].fillna('Unassigned', inplace=True)
                if 'Reporting To' in df_act.columns: df_act['Reporting To'].fillna('Direct to CEO', inplace=True)
                if 'Joining Date' in df_act.columns: df_act['Joining Date'] = pd.to_datetime(df_act['Joining Date'], errors='coerce')
                data["active"] = df_act

            # Inactive Staff
            df_inact = pd.read_excel(master_file, sheet_name="Inactive Staff", header=0)
            if 'Exit Date' in df_inact.columns: df_inact['Exit Date'] = pd.to_datetime(df_inact['Exit Date'], errors='coerce')
            data["inactive"] = df_inact
        except: pass

    # Recruitment
    rec_file = "Hirings Requests UAE & PK.xlsx"
    if os.path.exists(rec_file):
        try:
            df_rec = pd.read_excel(rec_file, sheet_name="Progress")
            def get_stage(x):
                s = str(x).lower()
                if "join" in s or "hired" in s: return "Hired"
                if "offer" in s: return "Offer Extended"
                if "interview" in s: return "Interview"
                if "shortlist" in s: return "Shortlisted"
                return "Applied"
            if 'Standing' in df_rec.columns: df_rec['Funnel Stage'] = df_rec['Standing'].apply(get_stage)
            data["recruitment"] = df_rec
        except: pass

    # Performance
    perf_file = "Increment - Lahore Office _ Apr - Sep 25.xlsx"
    if os.path.exists(perf_file):
        try:
            df_perf = pd.read_excel(perf_file, sheet_name="Evaluation Data")
            if 'Total Points (Out of 100)' in df_perf.columns:
                df_perf['Total Points (Out of 100)'] = pd.to_numeric(df_perf['Total Points (Out of 100)'], errors='coerce')
                df_perf['Category'] = df_perf['Total Points (Out of 100)'].apply(lambda x: "High Performer" if x>=85 else ("Low Performer" if x<70 else "Average"))
                data["performance"] = df_perf
        except: pass

    # Leave
    leave_file = "Leave Record - 2025.xlsx"
    if os.path.exists(leave_file):
        try:
            df_leave = pd.read_excel(leave_file, sheet_name="Summary", header=1)
            if 'Employee Name' not in df_leave.columns: df_leave.rename(columns={df_leave.columns[1]: 'Employee Name'}, inplace=True)
            df_leave = df_leave[df_leave['Employee Name'].notna()]
            availed_cols = [c for c in df_leave.columns if str(c).endswith('.1')]
            df_leave['Total Availed'] = df_leave[availed_cols].apply(pd.to_numeric, errors='coerce').sum(axis=1) if availed_cols else 0
            data["leave"] = df_leave
        except: pass

    return data

datasets = load_data()
df_active, df_inactive = datasets["active"], datasets["inactive"]
df_rec, df_perf, df_leave = datasets["recruitment"], datasets["performance"], datasets["leave"]

# ==============================================================================
# 3. SIDEBAR BRANDING
# ==============================================================================
with st.sidebar:
    st.image("FHZ-Logo-2.png", use_container_width=True)
    st.markdown("### Executive Dashboard")
    menu = st.radio("Navigate", [
        "Overview",
        "Recruitment Pipeline",
        "Employee Movement", 
        "Organization Structure",
        "Performance & Leave",
        "Policies & Docs"
    ])
    st.markdown("---")
    st.caption("Ventures")
    c1, c2, c3 = st.columns(3)
    with c1: st.image("logo final-01-01 - Copy.png", use_container_width=True)
    with c2: st.image("vertical-logo-light-background.png", use_container_width=True)
    with c3: st.image("Untitled-2-01 - Copy - Copy-1 (2).png", use_container_width=True)

# ==============================================================================
# 4. MODULES
# ==============================================================================

# --- OVERVIEW ---
if menu == "Overview":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("Dashboard Overview")
    with c2: 
        if lottie_hr: st_lottie(lottie_hr, height=100, key="hr")
    
    if not df_active.empty:
        total = len(df_active) + len(df_inactive)
        active = len(df_active)
        retention = (active / total * 100) if total else 0
        probation = df_active['Employment Status'].str.contains('Probation', case=False).sum() if 'Employment Status' in df_active.columns else 0
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Headcount", total)
        k2.metric("Active Employees", active, delta=f"{len(df_inactive)} Exited", delta_color="inverse")
        k3.metric("Retention Rate", f"{retention:.1f}%")
        k4.metric("On Probation", probation, delta="Review", delta_color="inverse")
        
        st.markdown("---")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.subheader("Headcount by Venture")
            if 'Business Unit' in df_active.columns:
                bu_counts = df_active['Business Unit'].value_counts().reset_index()
                bu_counts.columns = ['Business Unit', 'Count']
                fig = px.bar(bu_counts, x='Business Unit', y='Count', color='Business Unit', text='Count', 
                             color_discrete_sequence=px.colors.qualitative.Prism)
                fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", font=dict(color=TEXT_COLOR), showlegend=False)
                
                selected = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
                
                if selected and selected['selection']['points']:
                    clicked = selected['selection']['points'][0]['x']
                    st.success(f"Drilling down: **{clicked}**")
                    st.dataframe(df_active[df_active['Business Unit'] == clicked][['Name', 'Designation', 'Reporting To']], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.subheader("Performance Pulse")
            if not df_perf.empty:
                cat_counts = df_perf['Category'].value_counts().reset_index()
                cat_counts.columns = ['Category', 'Count']
                fig = px.pie(cat_counts, names='Category', values='Count', hole=0.6,
                             color='Category', color_discrete_map={'High Performer': '#2ECC71', 'Average': '#F1C40F', 'Low Performer': '#E74C3C'})
                fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", font=dict(color=TEXT_COLOR), margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# --- RECRUITMENT ---
elif menu == "Recruitment Pipeline":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("Talent Acquisition")
    with c2: 
        if lottie_hiring: st_lottie(lottie_hiring, height=90, key="hire")
    
    if not df_rec.empty:
        open_pos = len(df_rec) - df_rec[df_rec['Funnel Stage'] == 'Hired'].shape[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Open Requisitions", open_pos)
        c2.metric("Total Pipeline", len(df_rec))
        c3.metric("Closed/Hired", len(df_rec) - open_pos)
        
        st.markdown("---")
        st.subheader("Interactive Hiring Funnel")
        
        counts = df_rec['Funnel Stage'].value_counts().reset_index()
        counts.columns = ['Stage', 'Count']
        order = ['Applied', 'Shortlisted', 'Interview', 'Offer Extended', 'Hired']
        counts['Stage'] = pd.Categorical(counts['Stage'], categories=order, ordered=True)
        counts = counts.sort_values('Stage')
        
        fig = px.funnel(counts, x='Count', y='Stage', color='Stage', color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", font=dict(color=TEXT_COLOR))
        
        sel = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
        
        stage = None
        if sel and sel['selection']['points']:
            stage = sel['selection']['points'][0]['y']
            
        st.markdown("### 📋 Candidate Details")
        if stage:
            st.info(f"Showing details for: **{stage}**")
            st.dataframe(df_rec[df_rec['Funnel Stage'] == stage][['BU', 'Position', 'Request by', 'Status']], use_container_width=True)
        else:
            st.dataframe(df_rec[['BU', 'Position', 'Funnel Stage', 'Status']], use_container_width=True)

# --- EMPLOYEE MOVEMENT (SCROLLABLE & INTERACTIVE) ---
elif menu == "Employee Movement":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("Workforce Dynamics")
    with c2: 
        if lottie_move: st_lottie(lottie_move, height=100, key="move")

    # 1. DATA PREP
    now = datetime.now()
    
    # A. New Joiners (Current Month)
    joiners_df = pd.DataFrame()
    if not df_active.empty and 'Joining Date' in df_active.columns:
        joiners_df = df_active[
            (df_active['Joining Date'].dt.month == now.month) & 
            (df_active['Joining Date'].dt.year == now.year)
        ].copy()
        joiners_df['count'] = 1

    # B. Leavers (ALL records)
    leavers_df = df_inactive.copy() if not df_inactive.empty else pd.DataFrame()
    if not leavers_df.empty: 
        leavers_df['count'] = 1
        leavers_df = leavers_df.sort_values('Exit Date', ascending=False) # Recent first

    # C. Trend Data (Monthly Summary)
    trend_df = pd.DataFrame()
    if not df_inactive.empty and 'Exit Date' in df_inactive.columns:
        df_inactive['ExitMonth'] = df_inactive['Exit Date'].dt.strftime('%Y-%m')
        trend_df = df_inactive.groupby('ExitMonth').size().reset_index(name='Exits')
        trend_df = trend_df.sort_values('ExitMonth')

    # 2. KPI METRICS
    k1, k2 = st.columns(2)
    k1.metric(f"New Joiners ({now.strftime('%B')})", len(joiners_df), delta="Monthly Inflow")
    k2.metric("Total Attrition (YTD)", len(df_inactive), delta="Total Exits", delta_color="inverse")

    st.markdown("---")

    # 3. INTERACTIVE SECTION WITH SCROLLABLE CHARTS
    col_left, col_right = st.columns([1, 1])

    # === LEFT: NEW JOINERS ===
    with col_left:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.subheader(f"✨ New Joiners ({len(joiners_df)})")
        
        # POP-UP / DETAIL AREA FOR JOINERS (Place ABOVE the scrollable chart for visibility)
        st.markdown("### 🔍 Details")
        detail_placeholder_join = st.empty()
        detail_placeholder_join.caption("👈 Click on a name below to see their Join Date & Manager")

        st.markdown("---") # Separator

        # SCROLLABLE CHART CONTAINER
        with st.container(height=400):
            if not joiners_df.empty:
                # Dynamic Height: 40px per person so it scrolls
                h_join = max(300, len(joiners_df) * 40)
                
                fig_join = px.bar(joiners_df, x='count', y='Name', orientation='h', 
                                  text='Name', color_discrete_sequence=[SECONDARY])
                fig_join.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white", 
                    font=dict(color=TEXT_COLOR),
                    yaxis={'visible': True, 'showticklabels': False, 'title': ''},
                    xaxis={'visible': False},
                    showlegend=False,
                    height=h_join,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                fig_join.update_traces(textposition='inside', insidetextanchor='start')
                
                # INTERACTIVITY
                sel_join = st.plotly_chart(fig_join, use_container_width=True, on_select="rerun")
                
                # UPDATE POP-UP
                if sel_join and sel_join['selection']['points']:
                    clicked_name = sel_join['selection']['points'][0]['y']
                    person = joiners_df[joiners_df['Name'] == clicked_name].iloc[0]
                    with detail_placeholder_join.container():
                        st.info(f"👤 **{clicked_name}**")
                        st.write(f"📅 Joined: **{person['Joining Date'].strftime('%d %b %Y')}**")
                        st.write(f"👔 Reports To: **{person.get('Reporting To', 'N/A')}**")
            else:
                st.info("No new joiners this month.")
        st.markdown('</div>', unsafe_allow_html=True)

    # === RIGHT: LEAVING EMPLOYEES (ALL) ===
    with col_right:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.subheader(f"👋 Leaving Employees ({len(leavers_df)})")
        
        # POP-UP / DETAIL AREA FOR LEAVERS
        st.markdown("### 🔍 Details")
        detail_placeholder_leave = st.empty()
        detail_placeholder_leave.caption("👈 Click on a name below to reveal the reason")

        st.markdown("---") # Separator

        # SCROLLABLE CHART CONTAINER
        with st.container(height=400):
            if not leavers_df.empty:
                # Dynamic Height: Ensure ALL names fit by calculating height per person
                h_leave = max(300, len(leavers_df) * 40)
                
                fig_leave = px.bar(leavers_df, x='count', y='Name', orientation='h',
                                   text='Name', color_discrete_sequence=[DANGER])
                fig_leave.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white", 
                    font=dict(color=TEXT_COLOR),
                    yaxis={'visible': True, 'showticklabels': False, 'title': ''}, # Hide Y axis text to save width
                    xaxis={'visible': False},
                    showlegend=False,
                    height=h_leave, # TALL HEIGHT to fit everyone
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                fig_leave.update_traces(textposition='inside', insidetextanchor='start')
                
                # INTERACTIVITY
                sel_leave = st.plotly_chart(fig_leave, use_container_width=True, on_select="rerun")
                
                # UPDATE POP-UP
                if sel_leave and sel_leave['selection']['points']:
                    clicked_leaver = sel_leave['selection']['points'][0]['y']
                    leaver = leavers_df[leavers_df['Name'] == clicked_leaver].iloc[0]
                    with detail_placeholder_leave.container():
                        st.error(f"👤 **{clicked_leaver}**")
                        reason = leaver.get('Reason', 'Not Mentioned')
                        st.write(f"❓ Reason: **{reason}**")
                        exit_d = leaver.get('Exit Date', pd.NaT)
                        d_str = exit_d.strftime('%d %b %Y') if pd.notnull(exit_d) else "N/A"
                        st.write(f"📅 Exit Date: **{d_str}**")
            else:
                st.success("No attrition records found.")
        st.markdown('</div>', unsafe_allow_html=True)

    # === BOTTOM: SUMMARY CHART ===
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.subheader("📉 Attrition Overview (Monthly Trend)")
    if not trend_df.empty:
        fig_trend = px.area(trend_df, x='ExitMonth', y='Exits', title="Monthly Exits", markers=True)
        fig_trend.update_traces(line_color=DANGER, fillcolor="rgba(231, 76, 60, 0.2)")
        fig_trend.update_layout(plot_bgcolor="white", paper_bgcolor="white", font=dict(color=TEXT_COLOR))
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Not enough data for trend analysis.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- ORG STRUCTURE ---
elif menu == "Organization Structure":
    st.title("🏢 Interactive Hierarchy")
    if not df_active.empty:
        st.info("Click segments to drill down.")
        path = []
        if 'Business Unit' in df_active.columns: path.append('Business Unit')
        if 'Department' in df_active.columns: path.append('Department')
        if 'Designation' in df_active.columns: path.append('Designation')
        
        if path:
            df_tree = df_active.groupby(path).size().reset_index(name='Count')
            fig = px.sunburst(df_tree, path=path, values='Count', color='Business Unit', height=600)
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", font=dict(color=TEXT_COLOR))
            st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            
            st.subheader("Reporting Matrix")
            cols = ['Name', 'Designation', 'Business Unit', 'Reporting To']
            valid = [c for c in cols if c in df_active.columns]
            st.dataframe(df_active[valid].sort_values('Reporting To'), use_container_width=True)

# --- PERFORMANCE & LEAVE ---
elif menu == "Performance & Leave":
    st.title("🚀 Performance & Leave Analytics")
    t1, t2 = st.tabs(["Performance", "Leave"])
    
    with t1:
        if not df_perf.empty:
            avg = df_perf['Total Points (Out of 100)'].mean()
            c1, c2 = st.columns(2)
            c1.metric("Avg Score", f"{avg:.1f}")
            c2.metric("High Performers", len(df_perf[df_perf['Category'] == 'High Performer']))
            
            st.subheader("Performance Distribution")
            cat_counts = df_perf['Category'].value_counts().reset_index()
            cat_counts.columns = ['Category', 'Count']
            fig = px.bar(cat_counts, x='Category', y='Count', color='Category', 
                         color_discrete_map={'High Performer': '#2ECC71', 'Average': '#F1C40F', 'Low Performer': '#E74C3C'})
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", font=dict(color=TEXT_COLOR))
            
            sel = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            
            cat = None
            if sel and sel['selection']['points']:
                cat = sel['selection']['points'][0]['x']
                
            if cat:
                st.dataframe(df_perf[df_perf['Category'] == cat], use_container_width=True)
            else:
                st.dataframe(df_perf, use_container_width=True)

    with t2:
        if not df_leave.empty:
            st.metric("Total Leaves (YTD)", f"{df_leave['Total Availed'].sum():.0f}")
            
            st.subheader("Leave Balances")
            bal_cols = [c for c in df_leave.columns if str(c).endswith('.2')]
            valid = ['Employee Name', 'Total Availed'] + bal_cols
            st.dataframe(df_leave[[c for c in valid if c in df_leave.columns]], use_container_width=True)

# --- POLICIES ---
elif menu == "Policies & Docs":
    st.title("📜 Corporate Policies")
    with st.expander("📄 Annual Increment Policy"):
        st.info("Eligibility: Min 12 months service | Criteria: KPI & Profitability")
    with st.expander("📄 Recruitment Policy"):
        st.info("SLA: 30 Days to Hire | Process: Requisition > Panel > Offer")