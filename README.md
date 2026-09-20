# 🌧️ Civic Grievance & Flood-Risk Early-Warning System

An AI-powered platform for triaging civic complaints and detecting early flood risk across Indian cities. Built for the **1M1B AI for Sustainability Virtual Internship** by IBM SkillsBuild & AICTE.

**SDG 11** · Sustainable Cities and Communities
**SDG 13** · Climate Action

---

## 🎯 Problem & Solution

**Problem:** Municipal departments receive hundreds of civic complaints daily with no systematic triage, and early flood warning systems are absent or manual.

**Solution:** An AI assistant that:

* Classifies complaints instantly (text + photo)
* Routes to correct department automatically
* Scores flood risk per ward in real-time
* Detects hazardous situations (fire, electrical, injury) as HIGH priority
* Suggests user location automatically

---

## ✨ Key Features

### 1️⃣ Intelligent Hazard Detection

* Fire, electrical, or injury-related complaints → **HIGH priority** immediately
* Life-threatening keywords trigger urgent routing
* Rule-based + LLM-backed classification

### 2️⃣ Auto-Location Detection

* IP-based geolocation on app load
* Maps to nearest city + ward
* Manual override always available

### 3️⃣ Dynamic Location Search

* **Google Maps autocomplete** for location finding
* Real-time suggestions (like Zomato/Uber)
* City-scoped results only
* Fallback to local dataset if API unavailable

### 4️⃣ Multimodal Classification

* Text complaint + optional photo
* Gemini Vision for image analysis
* Hybrid LLM (Gemini → Groq → rule-based)

### 5️⃣ Live Flood-Risk Dashboard

* Ward-level risk scoring
* Complaint density + rainfall combined
* Explainable scoring (shows calculation)
* Real-time updates as complaints arrive

### 6️⃣ Department Alert System

* Instant routing with priority tags
* Timestamp logging
* High-risk warnings
* Ready for SMS/email integration

---

## 🚀 Quick Start

### Prerequisites

```bash
python 3.8+
pip
```

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd civic-flood-ai-final

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.env` file in project root:

```env
# Required for location search
GOOGLE_API_KEY=your_google_maps_places_api_key

# Optional: for photo classification (multimodal)
GOOGLE_API_KEY=your_gemini_api_key

# Optional: alternative LLM backend
GROQ_API_KEY=your_groq_api_key
```

### Run the App

```bash
streamlit run app.py
```

The app will:

1. Auto-detect your location (city + ward)
2. Open in browser at `http://localhost:8501`
3. Show 4 interactive tabs

---

## 📊 Interface Overview

### Tab 1: 📝 Submit Complaint

* Auto-detected city & ward
* Google Places search for precise location
* Text description + photo upload
* Instant classification & routing
* Alert logged automatically

### Tab 2: 🗺️ Flood-Risk Dashboard

* Real-time ward risk ranking
* Risk score visualization
* Complaint history
* City filter
* High-risk warnings

### Tab 3: 🔔 Department Alerts

* Live alert log (timestamped)
* Priority indicators
* Department assignment tracking
* High-priority counter

### Tab 4: ℹ️ About & Responsible AI

* Problem statement & SDG alignment
* Fairness & transparency notes
* Privacy & ethics considerations
* Expected impact

---

## 🗂️ Project Structure

```text
civic-flood-ai-final/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Dependencies
├── README.md                   # This file
├── IMPLEMENTATION_SUMMARY.md   # Detailed implementation docs
├── .env                        # API keys (NOT in git)
├── data/
│   ├── complaints.csv          # 34 seed complaints (8 cities)
│   └── rainfall.csv            # Synthetic rainfall data
└── utils/
    ├── classifier.py           # Text/image classification + hazard detection
    ├── data_loader.py          # CSV caching & loading
    ├── geolocation.py          # IP-based city/ward detection
    ├── google_places.py        # Google Places API + fallback
    ├── llm_helper.py           # LLM config (Gemini/Groq)
    ├── risk_scorer.py          # Flood-risk calculation
    └── __init__.py             # Package init
```

---

## 🔧 How It Works

### Complaint Classification

```text
User Input (text + optional photo)
    ↓
Hazard Check (fire/electric/injury?)
    ↓
    YES → Urgency = HIGH ✓
    NO  → Continue to category check
    ↓
LLM Classification (Gemini/Groq/rule-based)
    ↓
Output: Category, Urgency, Department, Reasoning
```

### Location Detection

```text
App Load
    ↓
IP Geolocation (ipapi.co / fallback: ip-api.com)
    ↓
Find Nearest City (Euclidean distance)
    ↓
Find Nearest Ward (within city)
    ↓
Show in UI with ✅ badge
```

### Flood-Risk Scoring

```text
Complaints by Ward + Recent Rainfall
    ↓
Risk Score = (complaint_density + rainfall_score) / 2
    ↓
Categorize: High (>0.7), Medium (0.4-0.7), Low (<0.4)
    ↓
Rank wards + Show warnings
```

### Dynamic Search

```text
User types location name (3+ characters)
    ↓
Query Google Places API (city-biased)
    ↓
IF API returns results → Show top 8
IF API fails or zero results → Use local dataset
    ↓
User selects → Ward field populates
```

---

## 🛡️ Error Handling

| Feature            | Primary       | Fallback                |
| ------------------ | ------------- | ----------------------- |
| Location Detection | ipapi.co      | ip-api.com, then manual |
| LLM Classification | Gemini        | Groq, then rule-based   |
| Location Search    | Google Places | Local dataset           |
| Text Encoding      | UTF-8         | Windows console fix     |

---

## 🌍 Supported Cities

* **Kolkata** (Girih Park, Park Circus, Salt Lake, etc.)
* **Mumbai** (Kurla, Andheri, etc.)
* **Delhi** (Karol Bagh, Rohini, etc.)
* **Bengaluru** (Whitefield, Koramangala, etc.)
* **Chennai** (T. Nagar, Velachery, etc.)
* **Hyderabad** (Secunderabad, LB Nagar, etc.)
* **Pune** (Kothrud, Hadapsar, etc.)
* **Guwahati** (Fancy Bazar, Six Mile, etc.)

Each city has multiple wards with street-level coordinate mapping.

---

## 🤖 LLM Integration

### Classification Priority

1. **Gemini** (best multimodal, via GOOGLE_API_KEY)
2. **Groq** (fast, via GROQ_API_KEY)
3. **Rule-Based** (always available, transparent)

### Rule-Based Fallback

When no LLM is configured, the system uses transparent keyword matching:

* **HIGH PRIORITY:** fire, electric, wire, shock, injury, bleeding, accident, gas leak, chemical, collapse, death
* **WATERLOGGING:** water, flooding, drain, overflow, stagnation
* **DRAINAGE:** blocked, choked, sewage, clogged
* **STREET LIGHTING:** light, dark, streetlight, electricity
* **ROAD DAMAGE:** pothole, damage, cave-in, road, crack

---

## 📈 Sample Output

### Complaint Submission Result

```text
Category: Electrical Hazard
Urgency: High ⚠️
Flood-related?: No
Location: Girih Park, Kolkata
Routed to: Electrical Department
Reasoning: High-priority hazard detected (keyword: electric wire)
```

### Risk Dashboard

```text
Ward                 | Flood Complaints | Peak Rainfall | Risk Score | Risk Level
Girih Park, Kolkata  | 1                | 45mm          | 0.68       | 🟡 Medium
Park Circus, Kolkata | 2                | 52mm          | 0.82       | 🔴 High
Salt Lake, Kolkata   | 1                | 38mm          | 0.55       | 🟡 Medium
```

---

## 🔐 Privacy & Security

* **No secrets in code:** All API keys in `.env` (git-ignored)
* **Synthetic data:** Seed dataset is fully synthetic
* **No external data sharing:** Location queries stay within 50km city radius
* **Session-scoped:** Live data persists only in current session

---

## 📝 Responsible AI

### Fairness

Risk scores combine complaint density + rainfall to avoid volume-only bias (wealthier areas may over-report).

### Transparency

Every risk score displays exact calculation:

```text
Risk Score = (Flood Complaints: 2 + Rainfall: 52mm) / 2 = 0.82 → High Risk
```

### Privacy

In real deployment, anonymize complaint data & photos before using for analysis.

### Ethics

Alerts are decision aids for municipal staff, not autonomous actions. Final authority remains with departments.

### Scope Honesty

* In-app alerts only (SMS/email is future scope)
* Photo classification requires Gemini API key
* These boundaries are explicit, not hidden

---

## 🚀 Future Scope

* [ ] Real SMS/email alerts to departments
* [ ] Multi-language support (Hindi, local languages)
* [ ] Mobile app (React Native / Flutter)
* [ ] Historical trend analysis (seasonal patterns)
* [ ] Predictive flood modeling
* [ ] Integration with municipal CMS
* [ ] Public API for third-party integration
* [ ] Dashboard for municipal admin
* [ ] Citizen feedback loop & resolution tracking

---

## 📊 Data

### Complaints (34 entries)

Real-world scenarios across 8 Indian cities:

* Waterlogging & drainage issues
* Street lighting problems
* Road damage
* Electrical hazards
* Garbage collection
* etc.

### Rainfall

Synthetic ward-level rainfall data (Sep 14-17, 2026) for demo purposes.

---

## 🛠️ Technologies

* **Frontend:** Streamlit (Python web framework)
* **Backend:** Python 3.8+
* **LLM:** Google Gemini / Groq
* **APIs:** Google Maps Places Autocomplete
* **Data:** Pandas, CSV
* **Geolocation:** ipapi.co / ip-api.com

---

## 📋 Requirements

See `requirements.txt`:

* streamlit
* pandas
* python-dotenv
* google-generativeai
* groq
* Pillow
* googlemaps
* requests

---

## 🤝 Contributing

Improvements welcome! Areas for contribution:

* Additional cities & wards
* Improved LLM prompts
* UI/UX enhancements
* Performance optimization
* Test coverage

---

## 📄 License

This project is built for the 1M1B AI for Sustainability program.

---

## 👤 Author

**Aritra Dey** · BTech CSE
*1M1B AI for Sustainability Virtual Internship (2026)*

---

## 📞 Support

For issues or questions:

1. Check `IMPLEMENTATION_SUMMARY.md` for detailed docs
2. Review error logs in console
3. Verify `.env` configuration
4. Check API key validity

---

## 🎯 Key Milestones

* ✅ Hazard detection (HIGH priority)
* ✅ Auto-geolocation (city + ward)
* ✅ Google Places API integration
* ✅ Dynamic location search
* ✅ Multimodal classification
* ✅ Flood-risk dashboard
* ✅ Department alerts
* ✅ Responsible AI framework

---

**Ready for deployment & GitHub push!**

---

*Last Updated: Sep 19, 2026*
*Deadline: Sep 21, 2026*
