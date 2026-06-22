import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
        .block-container { max-width: 98% !important; padding-left: 1rem !important; padding-right: 1rem !important; }
        .header-container {
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 2rem; border-radius: 15px; margin-bottom: 2rem; color: white;
            box-shadow: 0 4px 15px rgba(30, 58, 138, 0.2); display: flex; flex-direction: column; gap: 0.5rem;
        }
        .header-text h1 { margin: 0; font-size: clamp(1.2rem, 4vw, 2rem) !important; font-weight: 800; letter-spacing: -0.5px; }
        .header-text p { margin: 0; font-size: clamp(0.8rem, 2vw, 1rem); opacity: 0.9; }
        div[data-testid="metric-container"] {
            background-color: white; padding: 1.2rem !important; border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important; border-bottom: 5px solid #FFCC00 !important;
        }
        /* Style untuk st.container(border=True) agar menjadi Card Premium */
        div[data-testid="stElementContainer"] > div[style*="border"] {
            background-color: white !important;
            padding: 1.5rem !important;
            border-radius: 15px !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
            border: 1px solid #e2e8f0 !important;
            margin-bottom: 1rem !important;
        }
        div[data-testid="stMetricValue"] { color: #1e3a8a !important; font-size: clamp(1.8rem, 5vw, 2.8rem) !important; font-weight: 800 !important; line-height: 1.1; }
        div[data-testid="stMetricLabel"] { font-size: 0.9rem !important; text-transform: uppercase; font-weight: 700; color: #64748b !important; letter-spacing: 0.5px; }
        /* PROFESSIONAL LIGHT SIDEBAR */
        section[data-testid="stSidebar"] {
            background-color: #ffffff !important; /* Pure White */
            border-right: 1px solid #e2e8f0 !important;
        }
        
        /* FLEXBOX SIDEBAR TO POSITION BUTTON AT BOTTOM */
        [data-testid="stSidebarContent"] {
            display: flex !important;
            flex-direction: column !important;
            height: 100vh !important;
        }
        
        /* Make wrappers transparent to layout so elements become direct flex items */
        [data-testid="stSidebarUserContent"],
        [data-testid="stSidebarUserContent"] > div[data-testid="stVerticalBlock"] {
            display: contents !important;
        }

        /* Default order 1 for custom elements at the top (Logo, Header) */
        [data-testid="stSidebarContent"] div[data-testid="stElementContainer"] {
            order: 1 !important;
        }

        /* Navigation menu in the middle (order 2) */
        [data-testid="stSidebarNav"] {
            order: 2 !important;
            background-color: transparent !important;
        }

        /* Update button pushed to the bottom (order 3) */
        [data-testid="stSidebarContent"] div[data-testid="stElementContainer"]:has(div.stButton) {
            order: 3 !important;
            margin-top: auto !important;
            padding: 16px 8px !important;
            border-top: 1px solid #e2e8f0 !important;
            background-color: #ffffff !important;
        }

        /* Styling for the Logo/Button Container */
        .sidebar-top-container {
            padding: 24px 16px 10px 16px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        /* Sidebar Header Subtitle Styling */
        .sidebar-header-text {
            text-align: center;
            margin-top: -5px;
            margin-bottom: 5px;
        }
        .sidebar-header-text h3 {
            font-size: 1.05rem !important;
            color: #1e3a8a !important; /* Navy Blue */
            font-weight: 800 !important;
            margin: 0 !important;
            letter-spacing: 1px;
            font-family: 'Inter', sans-serif;
        }
        .sidebar-header-text p {
            font-size: 0.72rem !important;
            color: #64748b !important; /* Muted Slate */
            margin: 0 !important;
            font-family: 'Inter', sans-serif;
        }

        /* Navigation Items Styling */
        div[data-testid="stSidebarNavItems"] {
            padding: 0 8px;
        }
        
        div[data-testid="stSidebarNavItems"] li {
            margin-bottom: 6px !important;
        }

        div[data-testid="stSidebarNavItems"] a {
            border-radius: 10px !important;
            padding: 10px 16px !important;
            color: #475569 !important; /* Dark Gray */
            font-weight: 500 !important;
            text-decoration: none !important;
            transition: all 0.2s ease-in-out !important;
        }

        div[data-testid="stSidebarNavItems"] a:hover {
            background-color: #f1f5f9 !important; /* Very light gray */
            color: #1e3a8a !important; /* Navy Blue */
        }

        /* Active state */
        div[data-testid="stSidebarNavItems"] a[aria-current="page"] {
            background-color: #e2e8f0 !important; /* Light Active Background */
            color: #1e3a8a !important; /* Navy Blue */
            font-weight: 600 !important;
            border-left: 4px solid #FFCC00 !important; /* Gold Indicator */
        }

        /* Global Button Style (e.g. Reset Filter) */
        .stButton button {
            width: 100% !important;
            border-radius: 10px !important;
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 1px solid #cbd5e1 !important;
            padding: 8px 16px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        
        .stButton button:hover {
            background-color: #f1f5f9 !important;
            border-color: #94a3b8 !important;
            color: #0f172a !important;
        }

        /* Sidebar Specific Button (Update Data) */
        section[data-testid="stSidebar"] .stButton button {
            width: 100% !important;
            border-radius: 10px !important;
            background-color: #ffffff !important;
            color: #1e3a8a !important;
            border: 1px solid #cbd5e1 !important;
            padding: 10px 16px !important;
            font-weight: 600 !important;
            box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05) !important;
            transition: all 0.2s ease !important;
        }
        
        section[data-testid="stSidebar"] .stButton button:hover {
            background-color: #f1f5f9 !important;
            color: #1d4ed8 !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 2px 4px 0 rgba(0,0,0,0.08) !important;
        }

        /* IMPROVED FILTER & INPUT WIDGETS */
        div[data-testid="stExpander"] {
            background-color: white !important;
            border-radius: 15px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
            margin-bottom: 1.5rem !important;
        }
        
        div[data-testid="stExpander"] > details > summary {
            font-weight: 700 !important;
            color: #1e3a8a !important;
            padding: 10px 15px !important;
        }

        /* Styling for Multiselect & Inputs to make them "Pop" */
        div[data-baseweb="select"] > div {
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
            background-color: #ffffff !important;
        }
        
        div[data-baseweb="select"]:hover > div {
            border-color: #3b82f6 !important;
        }

        .stMultiSelect label, .stTextInput label, .stSelectbox label {
            color: #475569 !important;
            font-weight: 600 !important;
            margin-bottom: 8px !important;
            text-transform: uppercase;
            font-size: 0.8rem !important;
            letter-spacing: 0.3px;
        }

        /* Chart & Container Styling */
        .chart-title { color: #1e3a8a; font-weight: 700; margin-bottom: 1.5rem; border-left: 5px solid #FFCC00; padding-left: 15px; font-size: clamp(1rem, 2vw, 1.2rem); }
        .stDataFrame { border: 1px solid #e2e8f0; border-radius: 12px; }

        /* CUSTOM PREMIUM METRIC CARDS */
        .metric-card {
            display: flex;
            align-items: center;
            background-color: white;
            padding: 1.25rem;
            border-radius: 16px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.04);
            border: 1px solid #e2e8f0;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            gap: 1rem;
            position: relative;
            overflow: hidden;
            margin-bottom: 1rem;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(30, 58, 138, 0.08);
        }
        
        /* Card Theme Colors */
        .card-blue { border-bottom: 5px solid #3b82f6; }
        .card-blue:hover { border-color: #1d4ed8; }
        
        .card-green { border-bottom: 5px solid #10b981; }
        .card-green:hover { border-color: #047857; }
        
        .card-purple { border-bottom: 5px solid #8b5cf6; }
        .card-purple:hover { border-color: #6d28d9; }
        
        .card-amber { border-bottom: 5px solid #f59e0b; }
        .card-amber:hover { border-color: #b45309; }
        
        .metric-icon-container {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 48px;
            height: 48px;
            border-radius: 12px;
            color: white;
            flex-shrink: 0;
            box-shadow: 0 4px 10px rgba(0,0,0,0.08);
        }
        
        .metric-info {
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
            width: 100%;
        }
        
        .metric-label {
            font-size: 0.75rem !important;
            font-weight: 700;
            color: #64748b !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0;
        }
        
        .metric-value-wrapper {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.5rem;
            width: 100%;
        }
        
        .metric-value {
            font-size: clamp(1.2rem, 2.2vw, 1.6rem) !important;
            font-weight: 800;
            color: #1e3a8a !important;
            line-height: 1.2;
            margin: 0;
        }
        
        .metric-delta {
            font-size: 0.75rem;
            font-weight: 700;
            color: #047857;
            background-color: #ecfdf5;
            padding: 0.25rem 0.5rem;
            border-radius: 20px;
            display: inline-flex;
            align-items: center;
            border: 1px solid #a7f3d0;
            line-height: 1;
        }
        .progress-bar-container {
            width: 100%;
            height: 6px;
            background-color: #e2e8f0;
            border-radius: 3px;
            margin-top: 0.5rem;
            overflow: hidden;
        }
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            border-radius: 3px;
            transition: width 0.5s ease-in-out;
        }
        </style>
        """, unsafe_allow_html=True)

def get_header_html():
    return '<div class="header-container"><div class="header-text"><h1>MONITORING E-PURCHASING TA.2026</h1><p>Konsolidasi Data Nasional (Inaproc) &amp; Sistem Internal Monitoring (BP2JK / Iemon)</p></div></div>'
