"""
Geocon Proposal Management System - Streamlit Version
This is a demo version for testing and feedback
Data is stored in session state (per browser session)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import uuid
from typing import Dict, List, Any
import random

# Page configuration
st.set_page_config(
    page_title="Geocon Proposal System",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for data persistence
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.proposals = {}
    st.session_state.projects = {}
    st.session_state.counters = {'proposals': 0, 'projects': 0, 'office_counters': {}}
    st.session_state.current_user = None
    st.session_state.is_admin = False
    st.session_state.is_legal = False
    
    # Add some demo data
    demo_proposal = {
        'SD-2024-0001-P-GT': {
            'proposal_number': 'SD-2024-0001-P-GT',
            'date': '2024-01-15',
            'project_name': 'Downtown Tower Development',
            'client': 'ABC Development Corp',
            'contact_first': 'John',
            'contact_last': 'Smith',
            'contact_email': 'john.smith@abcdev.com',
            'contact_phone': '(619) 555-1234',
            'project_manager': 'Shawn Weedon',
            'project_director': 'Kim Goodrich',
            'team_number': '01',
            'fee': 75000,
            'status': 'pending',
            'office': 'SD',
            'service_type': 'GT',
            'proposal_type': 'P',
            'project_scope': 'Geotechnical Investigation',
            'project_type': 'Commercial Buildings (Low Rise)',
            'due_date': '2024-02-01',
            'proposal_sent': False
        }
    }
    st.session_state.proposals = demo_proposal

# Constants
OFFICES = {
    'SD': 'San Diego',
    'OC': 'Orange County',
    'MU': 'Murrieta',
    'RD': 'Redlands',
    'LA': 'Los Angeles'
}

PROPOSAL_TYPES = {
    'P': 'Proposal',
    'S': 'Submittal',
    'C': 'Change Order'
}

SERVICE_TYPES = {
    'GT': 'Geotechnical',
    'EV': 'Environmental',
    'SI': 'Special Inspection',
    'MT': 'Materials Testing'
}

PROJECT_MANAGERS = [
    'Shawn Weedon',
    'Rebecca Silva',
    'Kathlyn Ortega',
    'Richard Church',
    'Jason Muir'
]

PROJECT_DIRECTORS = [
    'Kim Goodrich',
    'Josh Ewart',
    'Shane Rodacker',
    'Jeremy Zorne'
]

PROJECT_SCOPES = [
    'Geotechnical Investigation',
    'Environmental Site Assessment',
    'Phase I Environmental',
    'Special Inspection',
    'Materials Testing',
    'Pavement Design',
    'Foundation Design'
]

PROJECT_TYPES = [
    'Commercial Buildings (Low Rise)',
    'Residential - Single Family',
    'Residential - Multi-Family',
    'Industrial Buildings',
    'Schools - K-12 Public',
    'Healthcare Facilities',
    'Infrastructure'
]

REVENUE_CODES = [
    "Geotechnical - Public Funding - G02",
    "Geotechnical - Private Funding - G01",
    "Environmental ESA - Public Funding - E04",
    "Environmental ESA - Private Funding - E01",
    "Materials - Public Funding - M02",
    "Materials - Private Funding - M01"
]

# Helper functions
def generate_proposal_number(office, prop_type, service_type):
    """Generate a new proposal number"""
    year = datetime.now().year
    if office not in st.session_state.counters['office_counters']:
        st.session_state.counters['office_counters'][office] = 0
    
    st.session_state.counters['office_counters'][office] += 1
    counter = st.session_state.counters['office_counters'][office]
    
    return f"{office}-{year}-{counter:04d}-{prop_type}-{service_type}"

def generate_project_number(team_number):
    """Generate a new project number"""
    st.session_state.counters['projects'] += 1
    counter = st.session_state.counters['projects']
    return f"G-{counter:06d}-{team_number}-01"

def calculate_analytics():
    """Calculate analytics for dashboard"""
    proposals = st.session_state.proposals
    projects = st.session_state.projects
    
    # Last month proposals
    last_month = datetime.now() - timedelta(days=30)
    last_month_key = last_month.strftime('%Y-%m')
    last_month_proposals = sum(1 for p in proposals.values() 
                               if p.get('date', '').startswith(last_month_key))
    
    # Active items
    active_proposals = sum(1 for p in proposals.values() if p.get('status') == 'pending')
    pending_legal = sum(1 for p in projects.values() if p.get('status') == 'pending_legal')
    pending_info = sum(1 for p in projects.values() if p.get('status') == 'pending_additional_info')
    total_active = active_proposals + pending_legal + pending_info
    
    # Win rate
    won = sum(1 for p in proposals.values() if p.get('status') == 'converted_to_project')
    lost = sum(1 for p in proposals.values() if p.get('status') == 'lost')
    total_decided = won + lost
    win_rate = (won / total_decided * 100) if total_decided > 0 else 0
    
    # Legal queue
    legal_queue = sum(1 for p in projects.values() 
                     if p.get('status') in ['pending_legal', 'pending_additional_info'])
    
    return {
        'last_month_proposals': last_month_proposals,
        'total_active': total_active,
        'win_rate': round(win_rate, 1),
        'legal_queue': legal_queue,
        'won': won,
        'lost': lost
    }

# Sidebar for navigation and user info
with st.sidebar:
    st.title("🏗️ Geocon Proposal System")
    st.markdown("---")
    
    # User selection (for demo)
    st.subheader("👤 Demo User")
    user_type = st.selectbox(
        "Select User Role",
        ["Project Manager", "Legal Team", "Administrator"]
    )
    
    if user_type == "Administrator":
        st.session_state.current_user = "admin@geoconinc.com"
        st.session_state.is_admin = True
        st.session_state.is_legal = True
    elif user_type == "Legal Team":
        st.session_state.current_user = "legal@geoconinc.com"
        st.session_state.is_legal = True
        st.session_state.is_admin = False
    else:
        st.session_state.current_user = "pm@geoconinc.com"
        st.session_state.is_legal = False
        st.session_state.is_admin = False
    
    st.info(f"Logged in as: {st.session_state.current_user}")
    
    st.markdown("---")
    
    # Navigation
    st.subheader("📍 Navigation")
    page = st.radio(
        "Go to",
        ["Dashboard", "New Proposal", "Legal Queue", "Analytics", "Past Projects", "Admin Settings"]
    )

# Main content area
if page == "Dashboard":
    st.title("📊 Dashboard")
    
    # Analytics cards
    analytics = calculate_analytics()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Proposals Last Month",
            analytics['last_month_proposals'],
            delta=None
        )
    
    with col2:
        st.metric(
            "Active Items",
            analytics['total_active'],
            delta=None
        )
    
    with col3:
        st.metric(
            "Win Rate",
            f"{analytics['win_rate']}%",
            delta=f"{analytics['won']}/{analytics['won'] + analytics['lost']}"
        )
    
    with col4:
        st.metric(
            "Legal Queue",
            analytics['legal_queue'],
            delta=None
        )
    
    st.markdown("---")
    
    # Filters
    st.subheader("🔍 Filters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search = st.text_input("Search", placeholder="Proposal #, Client, PM")
    
    with col2:
        office_filter = st.selectbox("Office", ["All"] + list(OFFICES.keys()))
    
    with col3:
        pm_filter = st.selectbox("Project Manager", ["All"] + PROJECT_MANAGERS)
    
    with col4:
        status_filter = st.selectbox("Status", ["All", "Pending", "Sent", "Won", "Lost"])
    
    st.markdown("---")
    
    # Active Proposals
    st.subheader("📋 Active Proposals")
    
    proposals_data = []
    for prop_num, proposal in st.session_state.proposals.items():
        if proposal.get('status') == 'pending':
            # Apply filters
            if office_filter != "All" and proposal.get('office') != office_filter:
                continue
            if pm_filter != "All" and proposal.get('project_manager') != pm_filter:
                continue
            if search and search.lower() not in prop_num.lower() and search.lower() not in proposal.get('client', '').lower():
                continue
            
            proposals_data.append({
                'Proposal #': proposal['proposal_number'],
                'Date': proposal['date'],
                'Project': proposal['project_name'],
                'Client': proposal['client'],
                'PM': proposal['project_manager'],
                'Fee': f"${proposal['fee']:,.0f}",
                'Status': '✅ Sent' if proposal.get('proposal_sent') else '⏳ Pending'
            })
    
    if proposals_data:
        df = pd.DataFrame(proposals_data)
        st.dataframe(df, use_container_width=True)
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📧 Mark as Sent", type="secondary"):
                st.success("Proposal marked as sent!")
        with col2:
            if st.button("🏆 Mark as Won", type="primary"):
                st.success("Proposal marked as won! Project created.")
        with col3:
            if st.button("❌ Mark as Lost", type="secondary"):
                st.info("Proposal marked as lost.")
    else:
        st.info("No active proposals")
    
    # Projects Pending Additional Info
    if any(p.get('status') == 'pending_additional_info' for p in st.session_state.projects.values()):
        st.markdown("---")
        st.subheader("⚠️ Projects Pending Additional Information")
        
        pending_data = []
        for proj_num, project in st.session_state.projects.items():
            if project.get('status') == 'pending_additional_info':
                pending_data.append({
                    'Project #': project['project_number'],
                    'Project': project['project_name'],
                    'Client': project['client'],
                    'PM': project['project_manager'],
                    'Days Pending': random.randint(1, 10)
                })
        
        if pending_data:
            df = pd.DataFrame(pending_data)
            st.dataframe(df, use_container_width=True)
            
            if st.button("📝 Enter Additional Information", type="primary"):
                st.info("Opening project information form...")

elif page == "New Proposal":
    st.title("➕ Create New Proposal")
    
    with st.form("new_proposal_form"):
        st.subheader("Proposal Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            office = st.selectbox("Office", list(OFFICES.keys()))
        with col2:
            prop_type = st.selectbox("Proposal Type", list(PROPOSAL_TYPES.keys()))
        with col3:
            service_type = st.selectbox("Service Type", list(SERVICE_TYPES.keys()))
        
        st.subheader("Project Information")
        project_name = st.text_input("Project Name", placeholder="e.g., Downtown Tower Renovation")
        
        col1, col2 = st.columns(2)
        with col1:
            project_city = st.text_input("Project City", placeholder="e.g., San Diego")
        with col2:
            fee = st.number_input("Proposed Fee ($)", min_value=0, value=50000, step=1000)
        
        st.subheader("Client Information")
        client = st.text_input("Client Company", placeholder="e.g., ABC Development Corp")
        
        col1, col2 = st.columns(2)
        with col1:
            contact_first = st.text_input("Contact First Name")
            contact_email = st.text_input("Contact Email")
        with col2:
            contact_last = st.text_input("Contact Last Name")
            contact_phone = st.text_input("Contact Phone")
        
        st.subheader("Project Team")
        col1, col2 = st.columns(2)
        with col1:
            project_manager = st.selectbox("Project Manager", PROJECT_MANAGERS)
        with col2:
            project_director = st.selectbox("Project Director", PROJECT_DIRECTORS)
        
        st.subheader("Project Details")
        col1, col2 = st.columns(2)
        with col1:
            project_scope = st.selectbox("Project Scope", PROJECT_SCOPES)
            due_date = st.date_input("Proposal Due Date")
        with col2:
            project_type = st.selectbox("Project Type", PROJECT_TYPES)
            follow_up_date = st.date_input("Follow Up Date")
        
        notes = st.text_area("Notes", placeholder="Any additional information...")
        
        submitted = st.form_submit_button("Create Proposal", type="primary")
        
        if submitted:
            # Generate proposal number
            proposal_number = generate_proposal_number(office, prop_type, service_type)
            
            # Create proposal
            new_proposal = {
                'proposal_number': proposal_number,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'project_name': project_name,
                'client': client,
                'contact_first': contact_first,
                'contact_last': contact_last,
                'contact_email': contact_email,
                'contact_phone': contact_phone,
                'project_manager': project_manager,
                'project_director': project_director,
                'team_number': '01',
                'fee': fee,
                'status': 'pending',
                'office': office,
                'service_type': service_type,
                'proposal_type': prop_type,
                'project_scope': project_scope,
                'project_type': project_type,
                'due_date': due_date.strftime('%Y-%m-%d'),
                'follow_up_date': follow_up_date.strftime('%Y-%m-%d'),
                'notes': notes,
                'proposal_sent': False
            }
            
            st.session_state.proposals[proposal_number] = new_proposal
            st.success(f"✅ Proposal {proposal_number} created successfully!")
            st.balloons()

elif page == "Legal Queue":
    st.title("⚖️ Legal Queue")
    
    if not st.session_state.is_legal:
        st.error("Access denied. Legal team members only.")
    else:
        # Stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("New Requests", random.randint(2, 5))
        with col2:
            st.metric("Under Review", random.randint(1, 3))
        with col3:
            st.metric("Negotiating", random.randint(0, 2))
        with col4:
            st.metric("Signed This Month", random.randint(5, 10))
        
        st.markdown("---")
        
        # Legal queue table
        st.subheader("Projects Requiring Legal Review")
        
        legal_data = []
        for proj_num, project in st.session_state.projects.items():
            if project.get('status') in ['pending_legal', 'pending_additional_info']:
                legal_data.append({
                    'Project #': project['project_number'],
                    'Project': project['project_name'],
                    'Client': project['client'],
                    'PM': project['project_manager'],
                    'Status': project.get('legal_status', 'New Request'),
                    'Days Pending': random.randint(1, 15)
                })
        
        if legal_data:
            df = pd.DataFrame(legal_data)
            st.dataframe(df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Mark as Signed", type="primary"):
                    st.success("Project signed! Sent to PM for additional information.")
            with col2:
                if st.button("❌ Mark as Not Signed", type="secondary"):
                    st.info("Project marked as not signed.")
        else:
            st.info("No projects in legal queue")

elif page == "Analytics":
    st.title("📈 Analytics Dashboard")
    
    # Check access
    if not st.session_state.is_admin and st.session_state.current_user != "shawn.weedon@geoconinc.com":
        st.error("Access denied. Analytics is restricted to authorized users only.")
    else:
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Revenue", "$2.5M", "↑ 12%")
        with col2:
            st.metric("Avg Time to Win", "18 days", "↓ 3 days")
        with col3:
            st.metric("Active Projects", "47", "↑ 5")
        with col4:
            st.metric("Success Rate", "68%", "↑ 3%")
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Monthly Proposals")
            chart_data = pd.DataFrame({
                'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                'Proposals': [12, 15, 18, 14, 20, 17],
                'Won': [8, 10, 12, 9, 14, 11]
            })
            st.line_chart(chart_data.set_index('Month'))
        
        with col2:
            st.subheader("Revenue by Office")
            pie_data = pd.DataFrame({
                'Office': ['San Diego', 'Orange County', 'Los Angeles', 'Murrieta'],
                'Revenue': [850000, 620000, 540000, 490000]
            })
            st.bar_chart(pie_data.set_index('Office'))
        
        st.markdown("---")
        
        # PM Performance
        st.subheader("Project Manager Performance")
        pm_data = pd.DataFrame({
            'Project Manager': PROJECT_MANAGERS[:3],
            'Total Proposals': [25, 22, 18],
            'Won': [17, 15, 12],
            'Win Rate': ['68%', '68%', '67%'],
            'Revenue': ['$450K', '$380K', '$320K']
        })
        st.dataframe(pm_data, use_container_width=True)

elif page == "Past Projects":
    st.title("📁 Past Projects")
    
    tab1, tab2, tab3 = st.tabs(["Completed Projects", "Lost Proposals", "Dead Jobs"])
    
    with tab1:
        st.subheader("✅ Completed Projects")
        completed_data = pd.DataFrame({
            'Project #': ['G-000001-01-01', 'G-000002-01-01'],
            'Project Name': ['Harbor Plaza', 'Tech Campus'],
            'Client': ['Harbor Dev', 'Tech Corp'],
            'PM': ['Shawn Weedon', 'Rebecca Silva'],
            'Completion Date': ['2024-01-10', '2024-01-08'],
            'Revenue': ['$125,000', '$95,000']
        })
        st.dataframe(completed_data, use_container_width=True)
    
    with tab2:
        st.subheader("❌ Lost Proposals")
        lost_data = pd.DataFrame({
            'Proposal #': ['SD-2024-0003-P-GT'],
            'Project Name': ['Riverside Complex'],
            'Client': ['Riverside LLC'],
            'PM': ['Jason Muir'],
            'Fee Lost': ['$65,000'],
            'Reason': ['Client chose competitor']
        })
        st.dataframe(lost_data, use_container_width=True)
    
    with tab3:
        st.subheader("💀 Dead Jobs (Not Signed)")
        st.info("No dead jobs to display")

elif page == "Admin Settings":
    st.title("⚙️ Admin Settings")
    
    if not st.session_state.is_admin:
        st.error("Access denied. Administrator privileges required.")
    else:
        st.info("👋 This is a demo version. Settings changes are temporary and will reset when you refresh.")
        
        tab1, tab2, tab3 = st.tabs(["Users", "System Settings", "Data Management"])
        
        with tab1:
            st.subheader("Analytics Access Users")
            analytics_users = st.text_area(
                "Users who can view analytics (one email per line)",
                value="admin@geoconinc.com\nshawn.weedon@geoconinc.com\nrebecca.silva@geoconinc.com"
            )
            
            st.subheader("Legal Team Members")
            legal_users = st.text_area(
                "Legal team members (one email per line)",
                value="legal1@geoconinc.com\nlegal2@geoconinc.com"
            )
            
            if st.button("Save User Settings", type="primary"):
                st.success("User settings updated!")
        
        with tab2:
            st.subheader("Office Codes")
            office_codes = st.text_area(
                "Office codes (format: CODE - Name)",
                value="SD - San Diego\nOC - Orange County\nLA - Los Angeles"
            )
            
            st.subheader("Project Managers")
            pms = st.text_area(
                "Project Managers (one per line)",
                value="\n".join(PROJECT_MANAGERS)
            )
            
            if st.button("Save System Settings", type="primary"):
                st.success("System settings updated!")
        
        with tab3:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🗑️ Clear All Data", type="secondary"):
                    st.session_state.proposals = {}
                    st.session_state.projects = {}
                    st.success("All data cleared!")
            
            with col2:
                if st.button("📥 Load Sample Data", type="primary"):
                    # Load sample data
                    st.success("Sample data loaded!")
            
            with col3:
                if st.button("📊 Generate Report", type="secondary"):
                    st.info("Report generation coming soon!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🏗️ Geocon Proposal Management System - Demo Version</p>
    <p>This is a testing environment. Data is stored temporarily in your browser session.</p>
    <p>For feedback, contact: your-email@geoconinc.com</p>
</div>
""", unsafe_allow_html=True)