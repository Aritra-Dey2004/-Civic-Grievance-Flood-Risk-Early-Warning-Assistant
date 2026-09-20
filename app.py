import io
from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image

from utils.data_loader import load_complaints, load_rainfall
from utils.classifier import classify_complaint
from utils.risk_scorer import score_wards
from utils.llm_helper import llm_is_configured
from utils.geolocation import detect_and_set_location
from utils.google_places import get_place_autocomplete

st.set_page_config(page_title="Civic Grievance & Flood-Risk Assistant", page_icon="🌧️", layout="wide")

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
h1, h2, h3, h4 {
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
}

.hero-banner {
    background: linear-gradient(135deg, #0B5563 0%, #14848C 55%, #2E8B57 100%);
    padding: 2.1rem 2rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 1.4rem;
    box-shadow: 0 10px 28px rgba(11, 85, 99, 0.28);
}
.hero-banner h1 {
    color: white;
    margin: 0 0 0.35rem 0;
    font-size: 1.85rem;
}
.hero-banner p {
    color: rgba(255,255,255,0.92);
    margin: 0;
    font-size: 0.95rem;
}
.hero-badges { margin-top: 0.9rem; }
.hero-badge {
    display: inline-block;
    background: rgba(255,255,255,0.16);
    padding: 0.3rem 0.85rem;
    border-radius: 999px;
    font-size: 0.76rem;
    margin-right: 0.5rem;
    border: 1px solid rgba(255,255,255,0.35);
}

div.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    padding: 0.55rem 1.3rem;
    border: none;
    background: linear-gradient(135deg, #0B5563, #14848C);
    color: white;
    transition: all 0.15s ease;
}
div.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(11, 85, 99, 0.35);
    color: white;
}

.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    font-weight: 500;
    padding: 0.5rem 1rem;
}

section[data-testid="stSidebar"] {
    background-color: transparent;
}

div[data-testid="stMetric"] {
    background: #F7FAFA;
    border: 1px solid #E1E8E8;
    border-radius: 12px;
    padding: 0.9rem 0.6rem;
}

.section-label {
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    color: #0B5563;
    margin-bottom: 0.4rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero-banner">
        <h1>🌧️ Civic Grievance &amp; Flood-Risk Early-Warning Assistant</h1>
        <p>AI-powered complaint triage and ward-level flood early warning for Indian cities.</p>
        <div class="hero-badges">
            <span class="hero-badge">SDG 11 · Sustainable Cities</span>
            <span class="hero-badge">SDG 13 · Climate Action</span>
            <span class="hero-badge">1M1B x IBM SkillsBuild x AICTE</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if llm_is_configured():
    st.success("LLM classification is active (Gemini/Groq key detected).", icon="🤖")
else:
    st.info(
        "No LLM API key configured — running on the transparent rule-based classifier for text. "
        "Image classification requires a Gemini key. Add GOOGLE_API_KEY or GROQ_API_KEY to .env "
        "to switch on LLM-based classification.",
        icon="⚙️",
    )

complaints_df = load_complaints()
rainfall_df = load_rainfall()

# Initialize session state for geolocation detection
if "location_initialized" not in st.session_state:
    detect_and_set_location(complaints_df)
    st.session_state["location_initialized"] = True

# Initialize session state for geolocation detection
if "location_initialized" not in st.session_state:
    detect_and_set_location(complaints_df)
    st.session_state["location_initialized"] = True


def combined_location(city: str, ward: str) -> str:
    return f"{city} - {ward}"


@st.cache_data(show_spinner=False)
def classify_seed_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Classify the seed/history dataset once and cache it — this is the
    'complaints that already exist' baseline the live dashboard builds on."""
    rows = []
    for _, row in df.iterrows():
        result = classify_complaint(description=row["description"])
        rows.append(
            {
                "complaint_id": row["complaint_id"],
                "city": row["city"],
                "ward": combined_location(row["city"], row["ward"]),
                "description": row["description"],
                "category": result["category"],
                "urgency": result["urgency"],
                "is_flood_related": result.get("is_flood_related", False),
                "department": result["department"],
                "origin": "seed",
            }
        )
    return pd.DataFrame(rows)


if "live_complaints" not in st.session_state:
    st.session_state["live_complaints"] = []
if "alert_log" not in st.session_state:
    st.session_state["alert_log"] = []


def log_alert(city, ward, department, category, urgency, source_note):
    st.session_state["alert_log"].append(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "city": city,
            "ward": ward,
            "department": department,
            "category": category,
            "urgency": urgency,
            "note": source_note,
        }
    )


CITY_WARDS = complaints_df[["city", "ward"]].drop_duplicates().sort_values(["city", "ward"])

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🌱 Project Snapshot")
    st.caption("AI-Powered Civic Grievance Triage & Flood-Risk Early-Warning System")
    st.markdown("**SDG 11** · Sustainable Cities  \n**SDG 13** · Climate Action")
    st.divider()
    st.markdown("### 📊 This Session")
    s1, s2 = st.columns(2)
    s1.metric("Live submissions", len(st.session_state["live_complaints"]))
    s2.metric("Alerts raised", len(st.session_state["alert_log"]))
    st.divider()
    st.caption(
        "Hybrid classification: Gemini/Groq when configured, transparent rule-based fallback otherwise. "
        "Built with Streamlit."
    )
    st.caption("Author: Aritra Dey · BTech CSE")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📝 Submit Complaint", "🗺️ Flood-Risk Dashboard (live)", "🔔 Department Alerts", "ℹ️ About & Responsible AI"]
)

# ---------------------------------------------------------------------------
# TAB 1: Submit a complaint — text, photo, or both — instant classification,
# and it immediately feeds the live risk dashboard.
# ---------------------------------------------------------------------------
with tab1:
    st.markdown('<div class="section-label">Report a civic issue</div>', unsafe_allow_html=True)
    st.write(
        "Describe the issue, upload a photo of it, or both. The assistant classifies it instantly, "
        "routes it to the correct department, raises an alert, and updates the flood-risk dashboard live."
    )

    cities = sorted(CITY_WARDS["city"].unique())

    # Show auto-detection status
    detected_city = st.session_state.get("detected_city")
    detected_ward = st.session_state.get("detected_ward")
    auto_detected = st.session_state.get("auto_detected", False)

    if auto_detected and detected_city and detected_ward:
        st.success(f"📍 Your location detected: **{detected_city}** → **{detected_ward}**. Type to search or confirm below.", icon="✅")
    elif auto_detected is False and detected_city is None:
        st.info("📍 Location auto-detection unavailable. Search for your city and ward below.", icon="ℹ️")

    col_city, col_ward = st.columns(2)
    with col_city:
        # City search with autocomplete
        default_city_idx = cities.index(detected_city) if detected_city in cities else 0
        city = st.selectbox("Search City", cities, index=default_city_idx, help="Start typing to search cities", key="city_select")

    # Initialize ward search session state when city changes
    if "current_city" not in st.session_state:
        st.session_state.current_city = city

    if st.session_state.current_city != city:
        st.session_state.current_city = city
        st.session_state.ward_search_input = ""  # Reset search when city changes

    with col_ward:
        st.markdown("**🗺️ Search Location (Google Maps)**")

        # Ward search input with Google Places Autocomplete
        ward_search = st.text_input(
            "Search Ward / Street / Area",
            placeholder="Type location name (e.g., Girih Park, AJC Bose Road)...",
            help="Search with Google Maps",
            key="ward_search"
        )

        # Get suggestions from Google Places API (with fallback to local dataset)
        suggestions = []
        if ward_search and len(ward_search) > 2:
            suggestions = get_place_autocomplete(ward_search, city, CITY_WARDS)

        # Show suggestions
        if suggestions:
            st.write(f"**Suggestions (top results):**")

            # Create a list of formatted suggestions
            suggestion_texts = [f"{s['main_text']} - {s['secondary_text']}" for s in suggestions]

            selected_suggestion = st.selectbox(
                "Select a location",
                range(len(suggestions)),
                format_func=lambda i: suggestion_texts[i],
                label_visibility="collapsed",
                key="place_suggestions"
            )

            if selected_suggestion is not None:
                selected = suggestions[selected_suggestion]
                ward = selected['main_text']
                st.success(f"✓ Selected: {selected['description']}")
        elif ward_search and len(ward_search) > 2:
            st.info("🔍 No suggestions found. Try a different search term.")

            # Fallback to dataset search
            wards_in_city = sorted(CITY_WARDS[CITY_WARDS["city"] == city]["ward"].unique())
            filtered_wards = [w for w in wards_in_city if ward_search.lower() in w.lower()]

            if filtered_wards:
                st.write(f"**Matches in {city} dataset:**")
                ward = st.selectbox(
                    "Select from dataset",
                    filtered_wards,
                    label_visibility="collapsed",
                    key="ward_fallback"
                )
            else:
                st.write(f"**Available locations in {city}:**")
                wards_in_city = sorted(CITY_WARDS[CITY_WARDS["city"] == city]["ward"].unique())
                ward = st.selectbox(
                    "Select location",
                    wards_in_city,
                    label_visibility="collapsed",
                    key="ward_all"
                )
        else:
            # No search - show all wards
            wards_in_city = sorted(CITY_WARDS[CITY_WARDS["city"] == city]["ward"].unique())
            if detected_ward and detected_ward in wards_in_city:
                default_ward_idx = list(wards_in_city).index(detected_ward)
            else:
                default_ward_idx = 0
            ward = st.selectbox(
                "Select Ward / Area",
                wards_in_city,
                index=default_ward_idx,
                label_visibility="collapsed",
                key="ward_select"
            )

    description = st.text_area(
        "Describe the issue (optional)",
        placeholder="e.g. Water has been standing outside my building since last night, it's entering the ground floor shops.",
        height=90,
        help="Can be left empty if you upload a photo"
    )
    uploaded_image = st.file_uploader("Upload a photo (optional)", type=["jpg", "jpeg", "png"],
                                       help="Can be left empty if you describe the issue")

    image_preview = None
    if uploaded_image is not None:
        image_preview = Image.open(io.BytesIO(uploaded_image.getvalue()))
        st.image(image_preview, caption="Uploaded photo", width=280)

    if st.button("Classify, Route & Alert", type="primary"):
        if not description.strip() and image_preview is None:
            st.warning("⚠️ Please either describe the issue OR upload a photo (or both).")
        else:
            with st.spinner("Analyzing and routing..."):
                result = classify_complaint(description=description, image=image_preview)

            if result.get("is_valid_complaint") is False:
                st.warning(
                    "⚠️ This image does not look like a civic complaint. Please upload a photo related to a city issue such as drainage, garbage, road damage, water supply, streetlight, or public safety.",
                    icon="🧭",
                )
                st.caption(result.get("reason", "Image is unrelated to a civic complaint."))
            elif result["source"] == "unavailable":
                st.error(f"❌ {result['reason']}", icon="🚫")
            else:
                with st.container(border=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Category", result["category"])
                    c2.metric("Urgency", result["urgency"])
                    c3.metric("Flood-related?", "Yes" if result.get("is_flood_related") else "No")
                    st.write(f"**Location:** {ward}, {city}")
                    st.write(f"**Routed to:** {result['department']}")
                    st.caption(f"Reasoning ({result.get('source', 'n/a')}): {result.get('reason', '')}")

                st.session_state["live_complaints"].append(
                    {
                        "complaint_id": f"LIVE-{len(st.session_state['live_complaints']) + 1}",
                        "city": city,
                        "ward": combined_location(city, ward),
                        "description": description or "(submitted as photo)",
                        "category": result["category"],
                        "urgency": result["urgency"],
                        "is_flood_related": result.get("is_flood_related", False),
                        "department": result["department"],
                        "origin": "live",
                    }
                )
                log_alert(
                    city, ward, result["department"], result["category"], result["urgency"],
                    source_note=("photo-based" if image_preview is not None else "text-based"),
                )
                st.success(
                    f"📨 Alert logged for {result['department']} — priority: {result['urgency']}. "
                    "This submission is now included in the live Flood-Risk Dashboard.",
                    icon="✅",
                )

# ---------------------------------------------------------------------------
# TAB 2: Flood-risk dashboard — recomputes live on every view.
# ---------------------------------------------------------------------------
with tab2:
    st.markdown('<div class="section-label">Ward-level flood risk — live</div>', unsafe_allow_html=True)
    st.write(
        "Updates instantly as complaints come in from the Submit tab, combined with existing complaint "
        "history and recent rainfall per ward. No manual refresh needed."
    )

    with st.spinner("Loading complaint history..."):
        seed_df = classify_seed_dataset(complaints_df)

    live_df = pd.DataFrame(st.session_state["live_complaints"])
    combined_df = pd.concat([seed_df, live_df], ignore_index=True) if not live_df.empty else seed_df

    if st.session_state["live_complaints"]:
        st.caption(f"Includes {len(st.session_state['live_complaints'])} live submission(s) from this session.")

    city_filter = st.multiselect("Filter by city (optional)", sorted(complaints_df["city"].unique()))
    if city_filter:
        combined_df = combined_df[combined_df["city"].isin(city_filter)]

    rainfall_combined = rainfall_df.copy()
    rainfall_combined["ward"] = rainfall_combined.apply(lambda r: combined_location(r["city"], r["ward"]), axis=1)
    if city_filter:
        rainfall_combined = rainfall_combined[rainfall_combined["city"].isin(city_filter)]

    risk_df = score_wards(combined_df, rainfall_combined)
    high_risk = risk_df[risk_df["risk_level"] == "High"]

    display_df = risk_df.copy()
    level_emoji = {"High": "🔴 High", "Medium": "🟡 Medium", "Low": "🟢 Low"}
    display_df["risk_level"] = display_df["risk_level"].map(level_emoji)

    st.markdown('<div class="section-label">Ward risk ranking</div>', unsafe_allow_html=True)
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ward": st.column_config.TextColumn("Ward"),
            "flood_complaint_count": st.column_config.NumberColumn("Flood Complaints"),
            "recent_max_rainfall_mm": st.column_config.NumberColumn("Peak Rainfall (mm)"),
            "risk_score": st.column_config.ProgressColumn("Risk Score", min_value=0, max_value=1, format="%.2f"),
            "risk_level": st.column_config.TextColumn("Risk Level"),
            "explanation": st.column_config.TextColumn("Why", width="large"),
        },
    )

    st.markdown('<div class="section-label">Risk score by ward</div>', unsafe_allow_html=True)
    st.bar_chart(risk_df.set_index("ward")["risk_score"], color="#14848C")

    if not high_risk.empty:
        st.warning("⚠️ High flood risk flagged for: " + ", ".join(high_risk["ward"].tolist()), icon="🚨")

    with st.expander("See all classified complaints (history + live)"):
        st.dataframe(combined_df, use_container_width=True, hide_index=True)

    if st.session_state["live_complaints"]:
        if st.button("Reset live submissions for this session"):
            st.session_state["live_complaints"] = []
            st.session_state["alert_log"] = []
            st.rerun()

# ---------------------------------------------------------------------------
# TAB 3: Department alerts log (simulated in-app notification system)
# ---------------------------------------------------------------------------
with tab3:
    st.markdown('<div class="section-label">Department alerts</div>', unsafe_allow_html=True)
    st.caption(
        "This is a live, in-app alert log — every complaint classified in the Submit tab raises a "
        "timestamped, priority-tagged alert here, as if picked up by the relevant department's queue."
    )

    if st.session_state["alert_log"]:
        alerts_df = pd.DataFrame(st.session_state["alert_log"]).sort_values("timestamp", ascending=False)

        # Display alerts with action status
        st.markdown("### 📋 Active Alerts")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        high_count = (alerts_df["urgency"] == "High").sum()
        medium_count = (alerts_df["urgency"] == "Medium").sum()
        low_count = (alerts_df["urgency"] == "Low").sum()

        col1.metric("🔴 High Priority", int(high_count))
        col2.metric("🟡 Medium Priority", int(medium_count))
        col3.metric("🟢 Low Priority", int(low_count))
        col4.metric("📊 Total Alerts", len(alerts_df))

        st.divider()

        # Department breakdown
        st.markdown("### 🏢 By Department")
        dept_counts = alerts_df["department"].value_counts()
        st.bar_chart(dept_counts)

        st.divider()

        # Full alert table with action buttons
        st.markdown("### 📝 Alert Details")
        st.dataframe(alerts_df, use_container_width=True, hide_index=True)

        # High priority warning
        if high_count:
            st.warning(f"🚨 {int(high_count)} High-priority alert(s) require immediate action!", icon="⚠️")

        # Department action recommendations
        st.markdown("### ✅ Recommended Actions")
        col1, col2, col3 = st.columns(3)

        with col1:
            if high_count > 0:
                st.info(f"**{int(high_count)} HIGH** alerts\n→ Dispatch immediately")

        with col2:
            if medium_count > 0:
                st.info(f"**{int(medium_count)} MEDIUM** alerts\n→ Schedule within 24h")

        with col3:
            if low_count > 0:
                st.info(f"**{int(low_count)} LOW** alerts\n→ Routine response")

        st.divider()

        # Reset option
        if st.button("🔄 Clear all alerts (test only)", help="Clears all alerts for testing"):
            st.session_state["alert_log"] = []
            st.rerun()
    else:
        st.caption("No alerts yet — submit a complaint in the first tab to see one appear here.")

# ---------------------------------------------------------------------------
# TAB 4: About / SDG / Responsible AI
# ---------------------------------------------------------------------------
with tab4:
    with st.container(border=True):
        st.markdown('<div class="section-label">Project overview</div>', unsafe_allow_html=True)
        st.markdown(
            """
**Problem statement:** How might we use AI to triage civic complaints and detect early flood/waterlogging
risk, so that city departments respond faster and residents get advance warning before an area floods?

**SDG alignment:** Primary — SDG 11 (Sustainable Cities and Communities). Secondary — SDG 13 (Climate Action).

**Who is affected:** Residents of low-lying, drainage-poor wards across Indian cities, and municipal
departments that currently sort complaints manually with no early-warning capability.

**Why AI is needed:** Individually, complaint text, photos, and rainfall numbers are just noise. AI
classifies and routes complaints instantly — from text or a photo — and a cluster of waterlogging
complaints combined with rising rainfall in one ward is an early flood signal no single complaint reveals
on its own.

**How data flows in this prototype:** the dashboard's starting point is a seed dataset standing in for
complaint history that would naturally exist in a live deployment. Every complaint submitted through this
app during your session is classified instantly and merges into that same live view.
            """
        )

    with st.container(border=True):
        st.markdown('<div class="section-label">Responsible AI considerations</div>', unsafe_allow_html=True)
        st.markdown(
            """
- **Fairness:** Risk scores are not based on complaint volume alone, since wealthier or more vocal wards
  may over-report relative to their actual risk — a known limitation of citizen-reported signals.
- **Transparency:** Every risk score shown in the dashboard displays exactly which numbers produced it
  (complaint count + rainfall figure) rather than hiding behind a black-box model.
- **Privacy:** The seed dataset is fully synthetic. In a real deployment, complaint data and photos would
  be anonymized before being used for ward-level analysis — no personal identifiers feed the risk model.
- **Ethics / human-in-the-loop:** This tool supports municipal decision-makers, it does not replace them.
  The alert log is a routing aid; final action on any flagged complaint stays with the department.
- **Scope honesty:** Alerts shown here are logged in-app for demonstration, not sent as real SMS/email;
  photo classification depends on a configured Gemini key. Both are explicit boundaries, not hidden ones.
            """
        )

    with st.container(border=True):
        st.markdown('<div class="section-label">Expected impact</div>', unsafe_allow_html=True)
        st.markdown(
            """
Faster resolution of everyday civic complaints, and a low-cost early-warning layer for flood-prone wards
across multiple cities where none currently exists — reducing response time to both routine issues and
climate-driven flood risk.
            """
        )