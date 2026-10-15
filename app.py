from __future__ import annotations

import math
import random
import zlib
from datetime import date
from html import escape
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

# ----------------------------------------------------------------------------
# Constants & reference data
# ----------------------------------------------------------------------------
APP_NAME = "Agrisphere AI"
ACRES_PER_HECTARE = 2.471
HA_PER_ACRE = 0.4047

PAGES = [
    "🏠 Home",
    "🌾 Crop & Seed Recommendation",
    "🧪 Soil Intelligence",
    "🔄 Crop Rotation Planner",
    "🏛️ Government Schemes",
    "📈 Market Intelligence",
    "🏬 Storage Connect",
    "📍 Nearby Agri Services",
    "🔬 Plant Health Scanner",
]

CITIES = {
    "Indore, MP": (22.7196, 75.8577),
    "Bhopal, MP": (23.2599, 77.4126),
    "Ujjain, MP": (23.1765, 75.7885),
    "Jabalpur, MP": (23.1815, 79.9864),
    "Nagpur, MH": (21.1458, 79.0882),
    "Pune, MH": (18.5204, 73.8567),
    "Ahmedabad, GJ": (23.0225, 72.5714),
    "Jaipur, RJ": (26.9124, 75.7873),
    "Lucknow, UP": (26.8467, 80.9462),
    "Patna, BR": (25.5941, 85.1376),
    "Ludhiana, PB": (30.9010, 75.8573),
    "Hyderabad, TS": (17.3850, 78.4867),
    "Custom coordinates": None,
}

# Ideal ranges: N, P, K = available nutrients (kg/ha); pH; T = temperature (°C);
# H = relative humidity (%); R = seasonal rainfall (mm); dose = N:P2O5:K2O (kg/ha).
CROPS = {
    "Rice (Paddy)": dict(icon="🌾", cat="Cereal", seasons=["Kharif"], N=(280, 560), P=(10, 30), K=(108, 280),
        pH=(5.5, 7.5), T=(22, 35), H=(65, 90), R=(600, 1500), dose=(120, 60, 40),
        seeds="Pusa Basmati 1121, IR-64, MTU-1010 (choose by local advisory)", rate="8–10 kg/acre (nursery)",
        window="Jun–Jul (transplant 25–30 days later)", note="Needs standing water; suits heavy, water-retentive soils."),
    "Wheat": dict(icon="🌿", cat="Cereal", seasons=["Rabi"], N=(280, 560), P=(10, 30), K=(108, 280),
        pH=(6.0, 7.5), T=(10, 25), H=(40, 70), R=(250, 500), dose=(120, 60, 40),
        seeds="HI 1544, GW 322, Lok-1, HD 2967 (choose by local advisory)", rate="40–50 kg/acre",
        window="Late Oct–Nov (timely sowing)", note="Cool growing season with a warm, dry ripening period."),
    "Maize": dict(icon="🌽", cat="Cereal", seasons=["Kharif", "Zaid"], N=(280, 560), P=(10, 30), K=(108, 280),
        pH=(5.8, 7.5), T=(21, 32), H=(50, 80), R=(500, 900), dose=(120, 60, 40),
        seeds="Certified hybrids suited to your zone (ask KVK / seed dealer)", rate="8 kg/acre",
        window="Jun–Jul (Kharif); Feb–Mar (Zaid)", note="Sensitive to waterlogging; needs good drainage."),
    "Soybean": dict(icon="🫘", cat="Legume", seasons=["Kharif"], N=(140, 400), P=(10, 30), K=(108, 280),
        pH=(6.0, 7.5), T=(22, 32), H=(55, 80), R=(450, 900), dose=(20, 60, 40),
        seeds="JS 9560, JS 2034, RVS 2001-4 (choose by local advisory)", rate="30 kg/acre",
        window="Late Jun–early Jul with monsoon onset", note="Fixes nitrogen; treat seed with Rhizobium culture."),
    "Chickpea (Chana)": dict(icon="🟤", cat="Legume", seasons=["Rabi"], N=(140, 350), P=(10, 30), K=(108, 280),
        pH=(6.0, 8.0), T=(15, 28), H=(30, 60), R=(300, 500), dose=(20, 40, 20),
        seeds="JG 14, JG 63, JAKI 9218 (choose by local advisory)", rate="30–35 kg/acre",
        window="Mid Oct–mid Nov", note="Thrives on residual moisture; avoid excess irrigation."),
    "Mustard": dict(icon="🌼", cat="Oilseed", seasons=["Rabi"], N=(250, 480), P=(10, 30), K=(108, 280),
        pH=(6.0, 7.8), T=(10, 25), H=(35, 65), R=(250, 500), dose=(80, 40, 40),
        seeds="Pusa Bold, RH 749, NRCHB 101 (choose by local advisory)", rate="1.5–2 kg/acre",
        window="Early–mid Oct", note="Cool, dry weather; responds well to sulphur."),
    "Cotton": dict(icon="☁️", cat="Cash", seasons=["Kharif"], N=(250, 500), P=(10, 30), K=(108, 300),
        pH=(6.0, 8.0), T=(21, 35), H=(45, 75), R=(500, 1000), dose=(120, 60, 60),
        seeds="Approved Bt hybrids for your region (ask KVK / state agri dept.)", rate="1–1.5 kg/acre",
        window="May–Jun (irrigated) / with monsoon (rainfed)", note="Deep black soils retain moisture well."),
    "Sugarcane": dict(icon="🎋", cat="Cash", seasons=["Kharif", "Rabi", "Zaid"], N=(350, 600), P=(10, 30), K=(150, 300),
        pH=(6.0, 8.0), T=(20, 35), H=(60, 85), R=(1000, 1800), dose=(250, 85, 115),
        seeds="Co 0238, Co 86032 and region-approved varieties", rate="3–4 tonnes setts/acre",
        window="Feb–Mar (spring) or Oct (autumn)", note="Long-duration, water-hungry crop (10–18 months).", perennial=True),
    "Groundnut": dict(icon="🥜", cat="Oilseed", seasons=["Kharif", "Zaid"], N=(140, 350), P=(10, 30), K=(108, 280),
        pH=(6.0, 7.0), T=(22, 32), H=(50, 75), R=(500, 900), dose=(25, 50, 75),
        seeds="GG 20, TAG 24, Kadiri-6 (choose by local advisory)", rate="35–40 kg kernels/acre",
        window="Jun–Jul (Kharif); Jan–Feb (Zaid)", note="Light, well-drained sandy loam is best; add gypsum at pegging."),
    "Pigeon pea (Tur)": dict(icon="🫛", cat="Legume", seasons=["Kharif"], N=(140, 350), P=(10, 30), K=(108, 280),
        pH=(5.5, 7.5), T=(20, 32), H=(50, 75), R=(600, 1000), dose=(20, 50, 20),
        seeds="ICPL 87, Pusa 992, Asha (choose by local advisory)", rate="6–8 kg/acre",
        window="Jun–Jul", note="Deep-rooted, drought-tolerant; good for intercropping."),
    "Pearl millet (Bajra)": dict(icon="🌾", cat="Millet", seasons=["Kharif", "Zaid"], N=(140, 400), P=(8, 25), K=(100, 280),
        pH=(6.0, 8.0), T=(25, 35), H=(30, 65), R=(250, 600), dose=(80, 40, 0),
        seeds="HHB 67 Improved, regional hybrids (ask KVK)", rate="2 kg/acre",
        window="Jul (Kharif)", note="Very hardy; suits low-rainfall, light soils."),
    "Potato": dict(icon="🥔", cat="Vegetable/Tuber", seasons=["Rabi"], N=(300, 560), P=(12, 35), K=(150, 300),
        pH=(5.2, 6.5), T=(12, 24), H=(55, 80), R=(400, 700), dose=(180, 80, 100),
        seeds="Kufri Jyoti, Kufri Pukhraj, Kufri Bahar (certified seed tubers)", rate="800–1000 kg tubers/acre",
        window="Mid Oct–Nov", note="Needs cool nights, loose well-drained soil and uniform moisture."),
    "Moong (Green gram)": dict(icon="🟢", cat="Legume", seasons=["Zaid", "Kharif"], N=(140, 300), P=(10, 25), K=(108, 280),
        pH=(6.0, 7.5), T=(25, 35), H=(50, 75), R=(300, 600), dose=(20, 40, 20),
        seeds="IPM 02-3, Pusa Vishal, SML 668 (choose by local advisory)", rate="8–10 kg/acre",
        window="Mar–Apr (summer) or Jul (Kharif)", note="Short duration (60–65 days); excellent soil-builder after wheat."),
}

CROP_WEIGHTS = {"N": 1.0, "P": 1.0, "K": 1.0, "pH": 1.3, "T": 1.5, "H": 0.8, "R": 1.5}
PARAM_LABEL = {"N": "Nitrogen (kg/ha)", "P": "Phosphorus (kg/ha)", "K": "Potassium (kg/ha)",
               "pH": "Soil pH", "T": "Temperature (°C)", "H": "Humidity (%)", "R": "Rainfall (mm)"}
PARAM_ADVICE = {
    ("N", "Low"): "Add nitrogen (urea / FYM / compost); split into 2–3 doses.",
    ("N", "High"): "Reduce nitrogen to avoid lodging and pest build-up.",
    ("P", "Low"): "Apply DAP / SSP at sowing; consider phosphate-solubilising bacteria.",
    ("P", "High"): "Skip or cut basal phosphorus this season.",
    ("K", "Low"): "Apply muriate of potash (MOP) or potassium sulphate.",
    ("K", "High"): "No extra potash needed this season.",
    ("pH", "Low"): "Soil is acidic: apply agricultural lime based on a lab recommendation.",
    ("pH", "High"): "Soil is alkaline: use gypsum / organic matter; prefer tolerant varieties.",
    ("T", "Low"): "Cooler than ideal: adjust sowing date or choose a cold-tolerant variety.",
    ("T", "High"): "Hotter than ideal: shift sowing date, mulch, and irrigate in cooler hours.",
    ("H", "Low"): "Dry air: mulching and light, frequent irrigation can help.",
    ("H", "High"): "High humidity: watch for fungal disease; keep spacing and airflow good.",
    ("R", "Low"): "Rainfall is short: plan irrigation or water-conserving practices.",
    ("R", "High"): "Excess rain: ensure drainage and avoid waterlogging.",
}

CAT_NEXT = {
    "Cereal": ["Legume", "Oilseed"], "Millet": ["Legume", "Oilseed"],
    "Legume": ["Cereal", "Vegetable/Tuber", "Millet"], "Oilseed": ["Cereal", "Legume"],
    "Cash": ["Legume", "Cereal"], "Vegetable/Tuber": ["Legume", "Cereal"],
}
CAT_REASON = {
    "Legume": "Legumes fix atmospheric nitrogen and reduce the fertiliser need of the next crop.",
    "Cereal": "Cereals use residual nitrogen and break the pest/disease cycle of legumes and oilseeds.",
    "Oilseed": "Different root depth and pest spectrum help break disease cycles.",
    "Vegetable/Tuber": "Different nutrient demand and pest complex; diversifies income.",
    "Millet": "Hardy, low-input crop that uses residual moisture and nutrients.",
    "Cash": "High-value crop; follow it with a soil-building legume.",
}

SCHEMES = [
    dict(name="PM-KISAN Samman Nidhi", tags=["Income"], small_only=False,
         benefit="₹6,000 per year as direct income support, paid in three instalments of ₹2,000 every four months via DBT.",
         eligibility="Landholding farmer families (certain high-income / institutional categories are excluded). e-KYC and Aadhaar-linked bank account required.",
         docs="Aadhaar, land records, bank passbook, mobile number", portal="https://pmkisan.gov.in",
         keywords="income support money 6000 financial cash kisan samman nidhi installment"),
    dict(name="Pradhan Mantri Fasal Bima Yojana (PMFBY)", tags=["Insurance"], small_only=False,
         benefit="Crop insurance against yield loss from natural calamities, pests and disease. Farmer premium: 2% (Kharif food/oilseed crops), 1.5% (Rabi), 5% (commercial/horticultural).",
         eligibility="Farmers growing notified crops in notified areas; enrol before the cut-off date (usually via bank/CSC/portal). Report localised losses within 72 hours (helpline 14447).",
         docs="Land/sowing certificate, bank account, Aadhaar", portal="https://pmfby.gov.in",
         keywords="insurance claim damage loss flood drought hail fasal bima crop failure compensation"),
    dict(name="Kisan Credit Card (KCC)", tags=["Credit"], small_only=False,
         benefit="Short-term crop credit at concessional interest (effective ~4% with interest subvention and prompt-repayment incentive on eligible limits). Collateral-free limit is ₹2 lakh under current RBI norms.",
         eligibility="Farmers, tenant farmers, sharecroppers and allied-activity farmers (dairy, fisheries) through banks and cooperatives.",
         docs="Aadhaar, land records / tenancy proof, photo, bank KYC", portal="https://www.pmkisan.gov.in",
         keywords="credit loan card kcc bank interest finance working capital"),
    dict(name="PM-KUSUM (Solar for Agriculture)", tags=["Energy", "Irrigation"], small_only=False,
         benefit="Support for standalone solar pumps and solarisation of grid-connected pumps; typically ~30% central + ~30% state subsidy (farmer pays ~40%, loans available). Surplus power can be sold to the grid under Component C.",
         eligibility="Individual farmers, groups and cooperatives; rollout, subsidy share and validity vary by state - confirm current status with your state nodal agency.",
         docs="Land records, Aadhaar, bank account, electricity connection details (if applicable)", portal="https://pmkusum.mnre.gov.in",
         keywords="solar pump kusum electricity diesel power energy"),
    dict(name="PM Krishi Sinchayee Yojana - Per Drop More Crop", tags=["Irrigation"], small_only=False,
         benefit="Subsidy on drip and sprinkler systems: around 55% for small & marginal farmers and 45% for other farmers (central + state share). Can cut water use substantially.",
         eligibility="Farmers with their own water source; apply through the state horticulture / agriculture department.",
         docs="Land records, Aadhaar, bank account, water-source proof", portal="https://pmksy.gov.in",
         keywords="drip irrigation sprinkler water micro irrigation sinchayee per drop"),
    dict(name="Soil Health Card Scheme", tags=["Soil"], small_only=False,
         benefit="Free soil testing and a card with crop-wise nutrient and fertiliser recommendations, refreshed on a 2-year cycle.",
         eligibility="All farmers. Contact your block agriculture office or KVK for sample collection.",
         docs="Land / survey number, contact details", portal="https://soilhealth.dac.gov.in",
         keywords="soil health card testing nutrient fertilizer recommendation lab"),
    dict(name="Agriculture Infrastructure Fund (AIF)", tags=["Infrastructure", "Storage"], small_only=False,
         benefit="Medium-long-term loans with 3% interest subvention (up to ₹2 crore) and credit guarantee for post-harvest infrastructure such as cold storage, warehouses, grading and packing units.",
         eligibility="Farmers, FPOs, cooperatives, agri-entrepreneurs and start-ups.",
         docs="Project report, KYC, land/lease documents", portal="https://agriinfra.dac.gov.in",
         keywords="cold storage warehouse godown infrastructure post harvest loan processing"),
    dict(name="e-NAM (National Agriculture Market)", tags=["Market"], small_only=False,
         benefit="Online trading platform linking mandis for transparent price discovery and access to buyers beyond the local mandi.",
         eligibility="Farmers register at an e-NAM-integrated mandi (or online) with KYC.",
         docs="Aadhaar, bank account, mobile number", portal="https://enam.gov.in",
         keywords="mandi market price selling trading online buyers apmc enam"),
    dict(name="Sub-Mission on Agricultural Mechanization (SMAM)", tags=["Mechanization"], small_only=False,
         benefit="Financial assistance (commonly ~40–50% depending on category and machine) for farm machinery and custom hiring centres; drones for spraying are supported under related guidelines.",
         eligibility="Individual farmers, FPOs, cooperatives; state-specific procedures apply.",
         docs="Land records, Aadhaar, bank account, quotation", portal="https://agrimachinery.nic.in",
         keywords="tractor machinery equipment subsidy custom hiring drone harvester mechanization"),
    dict(name="Paramparagat Krishi Vikas Yojana (PKVY)", tags=["Organic"], small_only=False,
         benefit="Cluster-based support for organic farming and certification, with part of the assistance directly to farmers for organic inputs.",
         eligibility="Farmer groups forming clusters (typically 20 ha); apply via state agriculture department.",
         docs="Land records, group formation documents, Aadhaar", portal="https://pgsindia-ncof.gov.in",
         keywords="organic farming natural certification clusters"),
    dict(name="PM Kisan Maandhan Yojana", tags=["Pension"], small_only=True,
         benefit="₹3,000 monthly pension after age 60 against a small monthly contribution (based on entry age 18–40).",
         eligibility="Small and marginal farmers (up to 2 ha) aged 18–40, not covered by other pension schemes.",
         docs="Aadhaar, bank account, land records", portal="https://maandhan.in",
         keywords="pension old age retirement maandhan"),
]

# name -> (base price Rs/quintal, volatility %, kind)  [SAMPLE values for demonstration]
MARKET_BASE = {
    "Wheat": (2550, 1.0, "grain"), "Paddy (Rice)": (2400, 1.0, "grain"), "Maize": (2250, 1.4, "grain"),
    "Soybean": (4800, 1.6, "grain"), "Chickpea (Chana)": (5700, 1.4, "grain"), "Mustard": (6000, 1.3, "grain"),
    "Pigeon pea (Tur)": (7500, 1.5, "grain"), "Moong": (8000, 1.5, "grain"), "Groundnut": (6500, 1.4, "grain"),
    "Cotton": (7300, 1.2, "grain"), "Pearl millet (Bajra)": (2600, 1.2, "grain"),
    "Potato": (1300, 3.0, "cold"), "Onion": (1600, 3.5, "cold"),
}

SERVICE_TYPES = {
    "🌱 Seed & fertiliser dealers": ("Beej & Khad Bhandar", "seed fertilizer dealer"),
    "🧪 Soil testing labs": ("Soil Testing Laboratory", "soil testing laboratory"),
    "🏛️ KVK & agriculture offices": ("Krishi Vigyan Kendra / Agri Office", "krishi vigyan kendra agriculture office"),
    "🚜 Equipment & custom hiring": ("Custom Hiring Centre", "tractor custom hiring centre"),
    "🛩️ Drone spraying": ("Agri Drone Services", "agriculture drone spraying"),
    "🐄 Veterinary & dairy": ("Veterinary Dispensary", "veterinary hospital"),
    "🏦 Banks & KCC desks": ("Bank / Cooperative Society", "bank kisan credit card"),
    "🏪 Mandi / APMC yards": ("Krishi Upaj Mandi", "krishi upaj mandi apmc"),
}
NAME_PREFIX = ["Shree", "Kisan", "Gramin", "Annapurna", "Bharat", "Sagar", "Navdeep", "Krishak", "Hariyali", "Sunrise"]
ZONES = ["North", "East", "South", "West", "Central"]

STORAGE_TYPES = {
    "Cold storage (vegetables)": dict(kind="cold", rate=(18, 30), temp="2–4 °C", crops="Onion, potato, vegetables"),
    "Cold storage (potato)": dict(kind="cold", rate=(20, 32), temp="2–4 °C", crops="Potato"),
    "WDRA-registered warehouse": dict(kind="grain", rate=(6, 12), temp="Ambient, fumigated", crops="Wheat, rice, pulses, oilseeds"),
    "Grain godown / silo": dict(kind="grain", rate=(4, 9), temp="Ambient", crops="Wheat, rice, maize, millets"),
}


# ----------------------------------------------------------------------------
# Pure logic (no Streamlit calls) - easy to test and to swap for real APIs
# ----------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def offset_point(lat: float, lon: float, km: float, bearing_deg: float) -> tuple[float, float]:
    b = math.radians(bearing_deg)
    dlat = km * math.cos(b) / 111.0
    dlon = km * math.sin(b) / (111.0 * max(math.cos(math.radians(lat)), 0.2))
    return lat + dlat, lon + dlon


def farmer_category(acres: float) -> str:
    ha = acres * HA_PER_ACRE
    if ha < 1:
        return "Marginal (< 1 ha)"
    if ha <= 2:
        return "Small (1–2 ha)"
    return "Other (> 2 ha)"


def range_score(value: float, lo: float, hi: float) -> float:
    if lo <= value <= hi:
        # inside the ideal band: 1.0 at the centre, easing to 0.8 at the edges (breaks ties between crops)
        half = max((hi - lo) / 2, 1e-6)
        return 1.0 - 0.2 * abs(value - (lo + hi) / 2) / half
    tol = max((hi - lo) * 0.6, 1e-6)
    dist = lo - value if value < lo else value - hi
    return max(0.0, 1 - dist / tol)


def param_status(key: str, value: float, crop: dict) -> str:
    lo, hi = crop[key]
    return "Low" if value < lo else "High" if value > hi else "Ideal"


def score_crops(values: dict, season: str, irrigated: bool) -> pd.DataFrame:
    rows = []
    for name, c in CROPS.items():
        if season != "Any" and season not in c["seasons"]:
            continue
        total = wsum = 0.0
        for key, w in CROP_WEIGHTS.items():
            if key == "R" and irrigated:
                w *= 0.5
            total += w * range_score(values[key], *c[key])
            wsum += w
        rows.append({"Crop": name, "Score": round(100 * total / wsum, 1)})
    return pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)


def nutrient_rating(n: float, p: float, k: float) -> dict:
    """Standard Indian soil-test ratings: N 280/560, P(Olsen) 10/25, K 108/280 kg/ha."""
    return {
        "N": "Low" if n < 280 else "Medium" if n <= 560 else "High",
        "P": "Low" if p < 10 else "Medium" if p <= 25 else "High",
        "K": "Low" if k < 108 else "Medium" if k <= 280 else "High",
    }


def fertiliser_plan(crop: str, n: float, p: float, k: float, acres: float) -> dict:
    rating = nutrient_rating(n, p, k)
    factor = {"Low": 1.25, "Medium": 1.0, "High": 0.75}
    base = CROPS[crop]["dose"]
    dose = [round(b * factor[rating[x]]) for b, x in zip(base, "NPK")]  # kg nutrient / ha
    dap = dose[1] / 0.46
    urea = max(0.0, dose[0] - dap * 0.18) / 0.46
    mop = dose[2] / 0.60
    per_acre = {"Urea": urea / ACRES_PER_HECTARE, "DAP": dap / ACRES_PER_HECTARE, "MOP": mop / ACRES_PER_HECTARE}
    bag = {"Urea": 45, "DAP": 50, "MOP": 50}
    rows = [{"Fertiliser": f, "Per acre (kg)": round(q, 1), f"For {acres:g} acres (kg)": round(q * acres, 1),
             "Bags": round(q * acres / bag[f], 1)} for f, q in per_acre.items()]
    return {"dose": dose, "rating": rating, "table": pd.DataFrame(rows)}


def soil_health(n, p, k, ph, oc, ec) -> tuple[int, dict]:
    pts = {"Low": 40, "Medium": 75, "High": 100}
    rating = nutrient_rating(n, p, k)
    ph_s = 100 if 6.5 <= ph <= 7.5 else 80 if 6.0 <= ph <= 8.0 else 55 if 5.5 <= ph <= 8.5 else 30
    oc_s = 40 if oc < 0.5 else 75 if oc <= 0.75 else 100
    ec_s = 100 if ec < 1 else 70 if ec <= 2 else 40
    score = (0.2 * pts[rating["N"]] + 0.15 * pts[rating["P"]] + 0.15 * pts[rating["K"]]
             + 0.2 * ph_s + 0.2 * oc_s + 0.1 * ec_s)
    parts = {"Nitrogen": pts[rating["N"]], "Phosphorus": pts[rating["P"]], "Potassium": pts[rating["K"]],
             "pH balance": ph_s, "Organic carbon": oc_s, "Salinity (EC)": ec_s}
    return round(score), {"rating": rating, "parts": parts}


def soil_actions(n, p, k, ph, oc, ec) -> list[str]:
    r = nutrient_rating(n, p, k)
    out = []
    if ph < 5.5:
        out.append("**Acidic soil:** apply agricultural lime (dose from a lab test) and prefer acid-tolerant crops.")
    elif ph < 6.0:
        out.append("**Slightly acidic:** light liming or organic matter helps; monitor pH each season.")
    elif ph > 8.5:
        out.append("**Strongly alkaline / sodic risk:** apply gypsum, add organic matter, use good-quality irrigation water.")
    elif ph > 8.0:
        out.append("**Alkaline:** add organic matter / green manure; prefer ammonium-based nitrogen sources.")
    if oc < 0.5:
        out.append("**Low organic carbon:** add 4–5 t/ha FYM or compost, use green manure and retain crop residue.")
    elif oc <= 0.75:
        out.append("**Medium organic carbon:** keep adding compost/FYM to move towards > 0.75%.")
    if ec > 2:
        out.append("**High salinity:** improve drainage, leach with good water, choose salt-tolerant crops.")
    if r["N"] == "Low":
        out.append("**Low nitrogen:** use split urea doses, add compost, and include legumes in rotation.")
    if r["P"] == "Low":
        out.append("**Low phosphorus:** apply DAP/SSP at sowing; consider phosphate-solubilising bacteria (PSB).")
    if r["K"] == "Low":
        out.append("**Low potassium:** apply MOP; especially important for potato, cotton and sugarcane.")
    if not out:
        out.append("**Soil looks well balanced.** Maintain with regular organic matter and a soil test every 2 years.")
    return out


def pick_next_crop(prev: str, season: str, used: list[str]) -> tuple[str, str]:
    prev_cat = CROPS[prev]["cat"]
    prefer = CAT_NEXT.get(prev_cat, ["Legume", "Cereal"])
    cands = [c for c, d in CROPS.items() if season in d["seasons"] and c != prev and not d.get("perennial")]
    if not cands:
        cands = [c for c in CROPS if c != prev and not CROPS[c].get("perennial")]

    def rank(c: str) -> tuple:
        cat = CROPS[c]["cat"]
        return (c in used[-2:], prefer.index(cat) if cat in prefer else 9, list(CROPS).index(c))

    best = min(cands, key=rank)
    return best, CAT_REASON[CROPS[best]["cat"]]


def next_season(season: str, include_zaid: bool) -> str:
    cycle = ["Kharif", "Rabi", "Zaid"] if include_zaid else ["Kharif", "Rabi"]
    return cycle[(cycle.index(season) + 1) % len(cycle)] if season in cycle else cycle[0]


def rotation_plan(prev: str, season: str, include_zaid: bool, n: int = 4) -> pd.DataFrame:
    rows, used = [], [prev]
    cur, s = prev, season
    for _ in range(n):
        s = next_season(s, include_zaid)
        crop, why = pick_next_crop(cur, s, used)
        rows.append({"Season": s, "Crop": f"{CROPS[crop]['icon']} {crop}", "Type": CROPS[crop]["cat"], "Why": why})
        used.append(crop)
        cur = crop
    return pd.DataFrame(rows)


def market_series(crop: str) -> pd.Series:
    """Deterministic SAMPLE 30-day price series (replace with Agmarknet / e-NAM data)."""
    base, vol, _ = MARKET_BASE[crop]
    rng = random.Random(zlib.crc32(f"{crop}-{date.today().isocalendar()[:2]}".encode()))
    drift = rng.uniform(-0.15, 0.25) * vol / 30
    price, vals = base * rng.uniform(0.94, 1.0), []
    for _ in range(30):
        price *= 1 + drift + rng.uniform(-vol, vol) / 100 * 0.6
        vals.append(price)
    idx = pd.date_range(end=pd.Timestamp(date.today()), periods=30)
    return pd.Series([round(v) for v in vals], index=idx)


def market_table() -> pd.DataFrame:
    rows = []
    for crop, (_, _, kind) in MARKET_BASE.items():
        s = market_series(crop)
        ch7 = (s.iloc[-1] / s.iloc[-8] - 1) * 100
        signal = "📈 Rising: consider holding" if ch7 >= 2 else "📉 Falling: consider selling" if ch7 <= -2 else "➖ Stable"
        rows.append({"Crop": crop, "Modal price (₹/qtl)": int(s.iloc[-1]), "7-day change (%)": round(ch7, 1),
                     "30-day trend": s.tolist(), "Signal": signal, "Storage type": "Cold storage" if kind == "cold" else "Warehouse / godown"})
    return pd.DataFrame(rows)


def sell_vs_store(qty, price_now, price_later, months, storage_rate, transport, loss_pct, interest_pct) -> dict:
    sell_now = qty * price_now - transport * qty
    revenue_later = qty * (1 - loss_pct / 100) * price_later
    storage_cost = qty * storage_rate * months
    interest = qty * price_now * (interest_pct / 100) * (months / 12)
    store = revenue_later - storage_cost - interest - transport * qty
    return {"sell_now": sell_now, "store": store, "gain": store - sell_now,
            "storage_cost": storage_cost, "interest": interest, "shrink": qty * price_later * loss_pct / 100}


def gen_services(lat: float, lon: float) -> pd.DataFrame:
    rows = []
    for label, (noun, _) in SERVICE_TYPES.items():
        rng = random.Random(f"{round(lat, 2)}|{round(lon, 2)}|{label}")
        for d in sorted(rng.uniform(1.5, 42) for _ in range(3)):
            plat, plon = offset_point(lat, lon, d, rng.uniform(0, 360))
            rows.append({"Category": label, "Name": f"{rng.choice(NAME_PREFIX)} {noun} ({rng.choice(ZONES)})",
                         "Distance (km)": round(haversine_km(lat, lon, plat, plon), 1),
                         "lat": plat, "lon": plon, "Open": rng.choice(["Mon–Sat, 9 am–6 pm", "Daily, 8 am–7 pm", "Mon–Fri, 10 am–5 pm"])})
    return pd.DataFrame(rows).sort_values("Distance (km)").reset_index(drop=True)


def gen_storage(lat: float, lon: float) -> pd.DataFrame:
    rows = []
    for label, spec in STORAGE_TYPES.items():
        rng = random.Random(f"S|{round(lat, 2)}|{round(lon, 2)}|{label}")
        for _ in range(3):
            d = rng.uniform(2, 45)
            plat, plon = offset_point(lat, lon, d, rng.uniform(0, 360))
            cap = rng.choice([500, 1000, 2000, 3000, 5000])
            rows.append({"Facility": f"{rng.choice(NAME_PREFIX)} {label.split(' (')[0]} {rng.choice(ZONES)}",
                         "Type": label, "kind": spec["kind"], "Distance (km)": round(haversine_km(lat, lon, plat, plon), 1),
                         "Free capacity (MT)": int(cap * rng.uniform(0.1, 0.6)),
                         "Rate (₹/qtl/month)": rng.randint(*spec["rate"]), "Temperature": spec["temp"], "Suitable for": spec["crops"],
                         "lat": plat, "lon": plon})
    return pd.DataFrame(rows).sort_values("Distance (km)").reset_index(drop=True)


def analyze_leaf(img: Image.Image) -> dict:
    """Colour-based screening of a leaf photo. NOT a disease diagnosis."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((640, 640))
    hsv = np.array(img.convert("HSV")).astype(np.int16)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    coloured = (s > 45) & (v > 40)
    green = coloured & (h >= 45) & (h <= 125)
    yellow = coloured & (h >= 26) & (h < 45) & (s > 70)
    brown = coloured & (h >= 5) & (h < 26) & (v < 235)
    plant = green | yellow | brown
    total_px, plant_px = h.size, int(plant.sum())
    if plant_px < 0.03 * total_px:
        return {"ok": False, "img": img}
    pct = {"green": green.sum() / plant_px * 100, "yellow": yellow.sum() / plant_px * 100,
           "brown": brown.sum() / plant_px * 100}
    # spatial spread of brown areas on an 8x8 grid
    H, W = h.shape
    gh, gw, affected, with_plant = H // 8, W // 8, 0, 0
    for i in range(8):
        for j in range(8):
            sl = (slice(i * gh, (i + 1) * gh), slice(j * gw, (j + 1) * gw))
            pc = plant[sl].sum()
            if pc > 0.02 * gh * gw:
                with_plant += 1
                affected += brown[sl].sum() / pc > 0.10
    spread = affected / with_plant * 100 if with_plant else 0.0
    out = np.array(img).astype(np.float32)
    for mask, colour in ((yellow, (255, 193, 7)), (brown, (229, 57, 53))):
        out[mask] = out[mask] * 0.35 + np.array(colour, dtype=np.float32) * 0.65
    overlay = Image.fromarray(out.astype(np.uint8))
    affected_pct = pct["yellow"] + pct["brown"]
    severity = ("Minimal" if affected_pct < 8 else "Mild" if affected_pct < 25
                else "Moderate" if affected_pct < 50 else "Severe")
    findings = []
    if pct["yellow"] > 15:
        findings.append(("Yellowing (chlorosis)", "Possible nitrogen / iron / magnesium deficiency, waterlogging, root stress or a viral / sucking-pest problem."))
    if pct["brown"] > 8:
        findings.append(("Brown or dead patches", "Possible fungal or bacterial leaf spot / blight, leaf scorch from heat or salts, or nutrient burn."
                         + (" Lesions are widely scattered across the leaf." if spread > 40 else "")))
    if not findings:
        findings.append(("No strong visible stress pattern", "Colour distribution looks mostly healthy. Keep monitoring; photos cannot detect early or hidden problems."))
    return {"ok": True, "img": img, "overlay": overlay, "pct": pct, "spread": spread,
            "severity": severity, "findings": findings}


# ----------------------------------------------------------------------------
# Styling & UI helpers
# ----------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
.stApp, .stMarkdown, .stButton button, .stTextInput input, .stSelectbox, .stRadio, .stTabs, [data-testid="stMetric"] {
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 4.5rem; padding-bottom: 3rem; max-width: 1240px; }
.hero { background: linear-gradient(120deg, #0F3D2E 0%, #1B5E3A 55%, #2E7D4F 100%); color: #fff; border-radius: 20px;
  padding: 2.2rem 2.4rem; margin-bottom: 1.4rem; position: relative; overflow: hidden; }
.hero:after { content: "🌾"; position: absolute; right: 2rem; bottom: -1.2rem; font-size: 8rem; opacity: .12; }
.hero-badge { display: inline-block; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28);
  padding: .28rem .8rem; border-radius: 999px; font-size: .78rem; font-weight: 600; margin-bottom: .8rem; }
.hero-title { font-size: 2.5rem; font-weight: 800; line-height: 1.1; margin: 0 0 .55rem 0; letter-spacing: -.02em; }
.hero-sub { font-size: 1.02rem; max-width: 760px; opacity: .92; line-height: 1.55; margin: 0; }
.page-head { display: flex; gap: .9rem; align-items: center; margin-bottom: .3rem; }
.page-icon { font-size: 1.7rem; width: 3rem; height: 3rem; display: flex; align-items: center; justify-content: center;
  background: rgba(46,125,79,.14); border-radius: 14px; }
.page-title { font-size: 1.65rem; font-weight: 800; margin: 0; letter-spacing: -.01em; line-height: 1.15; }
.page-sub { margin: .15rem 0 0 0; opacity: .72; font-size: .95rem; }
.card { border: 1px solid rgba(128,128,128,.25); background: rgba(128,128,128,.06); border-radius: 16px;
  padding: 1.05rem 1.15rem; height: 100%; }
.card-icon { font-size: 1.6rem; margin-bottom: .3rem; }
.card-title { font-weight: 700; font-size: 1.02rem; margin-bottom: .2rem; }
.card-text { font-size: .88rem; opacity: .75; line-height: 1.45; }
.rec { border: 1px solid rgba(128,128,128,.28); border-radius: 16px; padding: 1rem 1.15rem; height: 100%;
  background: rgba(128,128,128,.05); }
.rec.top { border: 2px solid #2E7D4F; background: rgba(46,125,79,.09); }
.rec-rank { font-size: .78rem; font-weight: 700; color: #2E7D4F; }
.rec-name { font-size: 1.2rem; font-weight: 800; margin: .15rem 0 .5rem 0; }
.rec-score { font-size: 1.9rem; font-weight: 800; line-height: 1; }
.bar { height: 8px; border-radius: 99px; background: rgba(128,128,128,.22); overflow: hidden; margin: .45rem 0 .6rem 0; }
.bar > div { height: 100%; border-radius: 99px; background: linear-gradient(90deg, #E0A526, #2E7D4F); }
.chip { display: inline-block; font-size: .74rem; font-weight: 600; padding: .15rem .6rem; border-radius: 99px;
  background: rgba(46,125,79,.16); color: #2E7D4F; margin: 0 .3rem .3rem 0; }
.chip.warn { background: rgba(224,165,38,.2); color: #B07A00; }
.note { border-left: 4px solid #E0A526; background: rgba(224,165,38,.10); padding: .7rem .95rem; border-radius: 8px;
  font-size: .88rem; margin: .6rem 0 1rem 0; }
.brand { font-size: 1.35rem; font-weight: 800; letter-spacing: -.01em; }
.brand-sub { font-size: .78rem; opacity: .65; margin-bottom: .4rem; }
div[data-testid="stMetric"] { border: 1px solid rgba(128,128,128,.22); border-radius: 14px; padding: .8rem 1rem;
  background: rgba(128,128,128,.05); }
button[kind="primary"], button[data-testid="stBaseButton-primary"], div[data-testid="stFormSubmitButton"] button {
  background: #2E7D4F !important; border-color: #2E7D4F !important; color: #fff !important; font-weight: 600; border-radius: 10px; }
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover { background: #1B5E3A !important; }
</style>
"""


def card(icon: str, title: str, text: str) -> str:
    return (f'<div class="card"><div class="card-icon">{icon}</div><div class="card-title">{escape(title)}</div>'
            f'<div class="card-text">{escape(text)}</div></div>')


def page_header(icon: str, title: str, sub: str) -> None:
    st.markdown(f'<div class="page-head"><div class="page-icon">{icon}</div><div><div class="page-title">{escape(title)}</div>'
                f'<p class="page-sub">{escape(sub)}</p></div></div>', unsafe_allow_html=True)
    st.write("")


def note(text: str) -> None:
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def go(page: str) -> None:
    st.session_state["nav"] = page


def maps_link(query: str, lat: float, lon: float) -> str:
    return f"https://www.google.com/maps/search/{quote_plus(query)}/@{lat:.5f},{lon:.5f},12z"


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
def sidebar() -> dict:
    st.session_state.setdefault("nav", PAGES[0])
    with st.sidebar:
        st.markdown(f'<div class="brand">🌾 {APP_NAME}</div><div class="brand-sub">Your farming sahayak, in one place</div>',
                    unsafe_allow_html=True)
        st.radio("Navigate", PAGES, key="nav", label_visibility="collapsed")
        st.divider()
        st.markdown("**👤 Farm profile**")
        loc = st.selectbox("Location", list(CITIES), key="loc")
        if CITIES[loc] is None:
            lat = st.number_input("Latitude", -90.0, 90.0, 22.7196, step=0.01, format="%.4f", key="lat")
            lon = st.number_input("Longitude", -180.0, 180.0, 75.8577, step=0.01, format="%.4f", key="lon")
        else:
            lat, lon = CITIES[loc]
        acres = st.number_input("Land holding (acres)", 0.1, 500.0, 5.0, step=0.5, key="acres")
        cat = farmer_category(acres)
        st.caption(f"Category: **{cat}** · {acres * HA_PER_ACRE:.2f} ha")
        st.divider()
        st.caption("Advisory output is for guidance only. Confirm decisions with your local KVK or agriculture officer.")
    return {"loc": loc, "lat": lat, "lon": lon, "acres": acres, "cat": cat}


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page_home(profile: dict) -> None:
    st.markdown(
        '<div class="hero"><div class="hero-badge">AI-powered agricultural intermediary platform</div>'
        f'<div class="hero-title">{APP_NAME}</div>'
        '<p class="hero-sub">Personalised crop and seed advice, soil intelligence, rotation planning, government-scheme discovery, '
        'market and storage connectivity, nearby services and plant-health screening, through a single interface.</p></div>',
        unsafe_allow_html=True)

    soil, crop_res = st.session_state.get("soil"), st.session_state.get("crop_result")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Farm location", profile["loc"].split(",")[0] if profile["loc"] != "Custom coordinates" else "Custom")
    c2.metric("Land holding", f"{profile['acres']:g} acres")
    c3.metric("Soil health score", f"{soil['score']}/100" if soil else "Not tested")
    c4.metric("Top crop match", crop_res["top"] if crop_res else "Not run")
    st.write("")
    st.markdown("#### What would you like to do today?")

    items = [
        (PAGES[1], "🌾", "Crop & seed advice", "Best-fit crops, seed varieties, sowing window and fertiliser plan."),
        (PAGES[2], "🧪", "Soil intelligence", "Soil health score, nutrient ratings and corrective actions."),
        (PAGES[3], "🔄", "Crop rotation", "A multi-season plan that protects soil and breaks pest cycles."),
        (PAGES[4], "🏛️", "Government schemes", "Find subsidies, insurance, credit and how to apply."),
        (PAGES[5], "📈", "Market intelligence", "Price board, trends and a sell-vs-store calculator."),
        (PAGES[6], "🏬", "Storage connect", "Cold storage and warehouses nearby, with booking requests."),
        (PAGES[7], "📍", "Nearby services", "Dealers, labs, KVKs, equipment, banks and mandis around you."),
        (PAGES[8], "🔬", "Plant health scanner", "Upload a leaf photo for a visible-symptom screening."),
    ]
    for row in (items[:4], items[4:]):
        cols = st.columns(4)
        for col, (page, icon, title, text) in zip(cols, row):
            with col:
                st.markdown(card(icon, title, text), unsafe_allow_html=True)
                st.button("Open →", key=f"open_{page}", on_click=go, args=(page,))
        st.write("")

    note("<b>How this works:</b> advice comes from transparent agronomic rules and reference ranges. Market, storage and "
         "service listings shown here are <b>sample data</b> until connected to live sources (Agmarknet / e-NAM, Google Places).")


def page_crop(profile: dict) -> None:
    page_header("🌾", "Crop & Seed Recommendation", "Enter your soil and climate details to rank the best-fit crops for your field.")
    soil = st.session_state.get("soil", {})
    if soil:
        st.success("Soil values pre-filled from your Soil Intelligence report.")

    with st.form("crop_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Soil nutrients**")
            n = st.number_input("Available nitrogen, N (kg/ha)", 0, 1000, int(soil.get("N", 300)), step=10)
            p = st.number_input("Available phosphorus, P (kg/ha)", 0, 200, int(soil.get("P", 15)), step=1)
            k = st.number_input("Available potassium, K (kg/ha)", 0, 800, int(soil.get("K", 150)), step=10)
            ph = st.number_input("Soil pH", 3.0, 10.0, float(soil.get("pH", 6.8)), step=0.1, format="%.1f")
        with c2:
            st.markdown("**Climate**")
            temp = st.number_input("Average temperature (°C)", 0.0, 50.0, 26.0, step=0.5)
            hum = st.number_input("Relative humidity (%)", 5.0, 100.0, 65.0, step=1.0)
            rain = st.number_input("Seasonal rainfall (mm)", 0.0, 3000.0, 600.0, step=25.0)
        with c3:
            st.markdown("**Farm context**")
            season_label = st.selectbox("Season", ["Any season", "Kharif (Jun–Oct)", "Rabi (Nov–Mar)", "Zaid (Mar–Jun)"])
            irrigated = st.radio("Assured irrigation?", ["Yes", "No (rainfed)"], horizontal=True) == "Yes"
            st.caption("With irrigation, rainfall carries less weight in the match score.")
        submitted = st.form_submit_button("Analyse my field", type="primary")

    if submitted:
        season = "Any" if season_label.startswith("Any") else season_label.split()[0]
        vals = {"N": n, "P": p, "K": k, "pH": ph, "T": temp, "H": hum, "R": rain}
        ranked = score_crops(vals, season, irrigated)
        st.session_state["crop_result"] = {"vals": vals, "season": season, "ranked": ranked, "top": ranked.iloc[0]["Crop"]}

    res = st.session_state.get("crop_result")
    if not res:
        note("Fill in the form and press <b>Analyse my field</b> to see your ranked crop recommendations.")
        return

    ranked, vals = res["ranked"], res["vals"]
    st.markdown(f"#### Top matches ({'all seasons' if res['season'] == 'Any' else res['season']})")
    cols = st.columns(3)
    for i, col in enumerate(cols[: min(3, len(ranked))]):
        r = ranked.iloc[i]
        c = CROPS[r["Crop"]]
        with col:
            st.markdown(
                f'<div class="rec {"top" if i == 0 else ""}"><div class="rec-rank">{"Best match" if i == 0 else f"#{i + 1} match"}</div>'
                f'<div class="rec-name">{c["icon"]} {escape(r["Crop"])}</div><div class="rec-score">{r["Score"]:.0f}%</div>'
                f'<div class="bar"><div style="width:{r["Score"]:.0f}%"></div></div>'
                f'<span class="chip">{c["cat"]}</span><span class="chip">{" / ".join(c["seasons"])}</span>'
                f'<div class="card-text" style="margin-top:.4rem">{escape(c["note"])}</div></div>', unsafe_allow_html=True)

    st.write("")
    choice = st.selectbox("Explore details for", ranked["Crop"].tolist(), index=0)
    crop = CROPS[choice]
    t1, t2, t3 = st.tabs(["Why this crop", "🌱 Seed guidance", "🧴 Fertiliser plan"])

    with t1:
        rows = []
        for key in CROP_WEIGHTS:
            status = param_status(key, vals[key], crop)
            lo, hi = crop[key]
            rows.append({"Factor": PARAM_LABEL[key], "Your value": vals[key], "Ideal range": f"{lo:g} – {hi:g}",
                         "Status": {"Ideal": "✅ Ideal", "Low": "⬇️ Low", "High": "⬆️ High"}[status],
                         "What to do": PARAM_ADVICE.get((key, status), "No action needed.")})
        st.dataframe(pd.DataFrame(rows), hide_index=True)

    with t2:
        a, b, c = st.columns(3)
        a.metric("Seed rate", crop["rate"])
        b.metric("Sowing window", crop["window"].split("(")[0].strip())
        c.metric("Season", " / ".join(crop["seasons"]))
        st.markdown(f"**Commonly used varieties:** {crop['seeds']}")
        st.caption("Sowing windows are indicative for central/north India. Always use certified seed and confirm varieties "
                   "and dates with your KVK or state seed corporation.")

    with t3:
        plan = fertiliser_plan(choice, vals["N"], vals["P"], vals["K"], profile["acres"])
        d = plan["dose"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Nitrogen (N)", f"{d[0]} kg/ha", plan["rating"]["N"] + " soil level")
        m2.metric("Phosphorus (P₂O₅)", f"{d[1]} kg/ha", plan["rating"]["P"] + " soil level")
        m3.metric("Potash (K₂O)", f"{d[2]} kg/ha", plan["rating"]["K"] + " soil level")
        st.dataframe(plan["table"], hide_index=True)
        st.caption("Dose is the crop's standard recommendation, raised 25% for low-testing nutrients and cut 25% for high-testing "
                   "ones, then converted to Urea (46% N, 45 kg bag), DAP (18-46-0) and MOP (60% K₂O). Apply N in split doses; "
                   "follow your Soil Health Card where available.")


def page_soil(profile: dict) -> None:
    page_header("🧪", "Soil Intelligence", "Turn a soil test report into a health score and a clear list of corrective actions.")
    prev = st.session_state.get("soil", {})
    with st.form("soil_form"):
        c1, c2 = st.columns(2)
        with c1:
            n = st.number_input("Available nitrogen, N (kg/ha)", 0, 1000, int(prev.get("N", 300)), step=10)
            p = st.number_input("Available phosphorus, P (kg/ha)", 0, 200, int(prev.get("P", 15)), step=1)
            k = st.number_input("Available potassium, K (kg/ha)", 0, 800, int(prev.get("K", 150)), step=10)
        with c2:
            ph = st.number_input("Soil pH", 3.0, 10.0, float(prev.get("pH", 6.8)), step=0.1, format="%.1f")
            oc = st.number_input("Organic carbon (%)", 0.0, 3.0, float(prev.get("OC", 0.6)), step=0.05, format="%.2f")
            ec = st.number_input("Electrical conductivity, EC (dS/m)", 0.0, 10.0, float(prev.get("EC", 0.5)), step=0.1, format="%.1f")
        sub = st.form_submit_button("Analyse soil", type="primary")

    if sub:
        score, info = soil_health(n, p, k, ph, oc, ec)
        st.session_state["soil"] = {"N": n, "P": p, "K": k, "pH": ph, "OC": oc, "EC": ec, "score": score,
                                    "info": info, "actions": soil_actions(n, p, k, ph, oc, ec)}
    soil = st.session_state.get("soil")
    if not soil:
        note("Enter values from your Soil Health Card or lab report. If you have no test yet, the "
             "<b>Government Schemes</b> page explains how to get a free one.")
        return

    score = soil["score"]
    label = "Excellent" if score >= 80 else "Good" if score >= 65 else "Fair" if score >= 50 else "Needs attention"
    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric("Soil health score", f"{score} / 100", label)
        st.progress(score / 100)
        r = soil["info"]["rating"]
        st.markdown(f"**N** {r['N']} · **P** {r['P']} · **K** {r['K']}")
    with c2:
        parts = pd.DataFrame({"Parameter": list(soil["info"]["parts"]), "Score": list(soil["info"]["parts"].values())}).set_index("Parameter")
        if _supports_horizontal():
            st.bar_chart(parts, horizontal=True, height=250)
        else:
            st.bar_chart(parts, height=250)
    st.markdown("#### Recommended actions")
    for a in soil["actions"]:
        st.markdown(f"- {a}")
    st.success("Saved. The Crop Recommendation page will use these values automatically.")
    st.caption("Ratings follow standard Indian soil-test classes (N 280/560, P 10/25, K 108/280 kg/ha).")


def _supports_horizontal() -> bool:
    try:
        import inspect
        return "horizontal" in inspect.signature(st.bar_chart).parameters
    except Exception:
        return False


def page_rotation(profile: dict) -> None:
    page_header("🔄", "Crop Rotation Planner", "Plan the next seasons so each crop leaves your soil better than it found it.")
    rotatable = [c for c in CROPS if not CROPS[c].get("perennial")]
    c1, c2, c3 = st.columns(3)
    prev = c1.selectbox("Last crop grown", rotatable, index=rotatable.index("Wheat"))
    season = c2.selectbox("Season just completed", ["Kharif", "Rabi", "Zaid"], index=1)
    zaid = c3.toggle("Include summer (Zaid) crop", value=False)
    plan = rotation_plan(prev, season, zaid, n=4 if not zaid else 6)
    st.markdown("#### Suggested sequence")
    st.dataframe(plan, hide_index=True)

    cat = CROPS[prev]["cat"]
    a, b = st.columns(2)
    with a:
        st.markdown("**Why rotate?**")
        st.markdown("- Breaks pest and disease cycles\n- Balances nutrient demand across seasons\n- Legumes add nitrogen naturally\n- Improves soil structure and organic matter")
    with b:
        st.markdown("**Avoid**")
        st.markdown(f"- Growing **{prev}** again right after itself\n- Two crops of the same type ({cat.lower()}) back-to-back where possible\n"
                    "- Leaving fields bare - use green manure or a short legume where water allows")
    note("Rotation is a starting point. Local water availability, market demand and your recommended-crop scores should guide the final choice.")


def _set_scheme_query(term: str) -> None:
    st.session_state["scheme_text"] = term


def page_schemes(profile: dict) -> None:
    page_header("🏛️", "Government Scheme Discovery", "Search central schemes by need, see what you may qualify for, and how to apply.")
    all_tags = sorted({t for s in SCHEMES for t in s["tags"]})
    c1, c2 = st.columns([2, 3])
    q = c1.text_input("Search (e.g. solar pump, insurance, loan, cold storage)", key="scheme_text",
                      placeholder="What do you need help with?")
    tags = c2.multiselect("Filter by need", all_tags)

    st.caption("Quick searches")
    pc = st.columns(5)
    presets = [("☀️ Solar pump", "solar pump"), ("💧 Drip", "drip irrigation"), ("🛡️ Insurance", "insurance"),
               ("💰 Income support", "income support"), ("💳 Credit", "credit")]
    for col, (label, term) in zip(pc, presets):
        col.button(label, key=f"preset_{term}", on_click=_set_scheme_query, args=(term,))

    def relevance(s: dict) -> int:
        if not q:
            return 1
        hay = (s["name"] + " " + s["benefit"] + " " + s["keywords"] + " " + " ".join(s["tags"])).lower()
        return sum(1 for w in q.lower().split() if w in hay)

    results = [(relevance(s), s) for s in SCHEMES if (not tags or set(tags) & set(s["tags"]))]
    results = [r for r in results if r[0] > 0]
    results.sort(key=lambda r: -r[0])

    if not results:
        st.warning("No scheme matched. Try a simpler word, or visit your nearest KVK / Krishi Bhawan for guidance.")
        return
    st.markdown(f"**{len(results)} scheme(s) found** · your category: **{profile['cat']}**")
    for _, s in results:
        small = profile["cat"] != "Other (> 2 ha)"
        flag = ""
        if s["small_only"]:
            flag = "✅ Likely applicable (small/marginal)" if small else "⚠️ Meant for small & marginal farmers"
        with st.expander(f"{s['name']}", expanded=len(results) <= 2):
            st.markdown("".join(f'<span class="chip">{t}</span>' for t in s["tags"]) + (f'<span class="chip warn">{flag}</span>' if flag else ""),
                        unsafe_allow_html=True)
            if s["name"].startswith("PM Krishi Sinchayee"):
                rate = "55%" if small else "45%"
                st.markdown(f"**Subsidy for your category:** about **{rate}**")
            st.markdown(f"**Benefit:** {s['benefit']}")
            st.markdown(f"**Eligibility:** {s['eligibility']}")
            st.markdown(f"**Documents:** {s['docs']}")
            st.link_button("Official portal ↗", s["portal"])
    note("Scheme terms, subsidy shares and validity change and vary by state. Treat this as a guide and confirm on the "
         "official portal or at your Krishi Bhawan before applying. Kisan Call Centre: <b>1800-180-1551</b>.")


def page_market(profile: dict) -> None:
    page_header("📈", "Market Intelligence", "Compare prices, read the trend, and decide whether to sell now or store.")
    note("<b>Sample data:</b> prices below are illustrative to demonstrate the workflow. Connect Agmarknet / e-NAM "
         "to show live mandi prices (replace <code>market_series()</code>).")
    t1, t2, t3 = st.tabs(["Price board", "Trend chart", "Sell vs store"])
    tbl = market_table()

    with t1:
        st.dataframe(tbl, hide_index=True, column_config={
            "30-day trend": st.column_config.LineChartColumn("30-day trend"),
            "Modal price (₹/qtl)": st.column_config.NumberColumn(format="₹%d"),
            "7-day change (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        })
    with t2:
        picks = st.multiselect("Compare crops", list(MARKET_BASE), default=["Wheat", "Soybean"])
        if picks:
            df = pd.DataFrame({c: market_series(c) for c in picks})
            st.line_chart(df)
            st.caption("₹ per quintal, last 30 days (sample series).")
        else:
            st.info("Select at least one crop.")
    with t3:
        crop = st.selectbox("Crop", list(MARKET_BASE), key="sv_crop")
        s = market_series(crop)
        kind = MARKET_BASE[crop][2]
        c1, c2, c3 = st.columns(3)
        qty = c1.number_input("Quantity (quintals)", 1.0, 100000.0, 100.0, step=10.0)
        price_now = c2.number_input("Price today (₹/qtl)", 100, 100000, int(s.iloc[-1]), step=50)
        change = c3.slider("Expected price change by selling time (%)", -20, 40, 6)
        c4, c5, c6, c7 = st.columns(4)
        months = c4.slider("Storage duration (months)", 1, 10, 3)
        rate = c5.number_input("Storage rate (₹/qtl/month)", 0.0, 100.0, 22.0 if kind == "cold" else 8.0, step=1.0)
        transport = c6.number_input("Transport (₹/qtl)", 0.0, 500.0, 40.0, step=5.0)
        loss = c7.slider("Storage loss / shrinkage (%)", 0.0, 15.0, 3.0 if kind == "cold" else 1.5, step=0.5)
        interest = st.slider("Cost of money / loan interest (% per year)", 0, 24, 8)
        r = sell_vs_store(qty, price_now, price_now * (1 + change / 100), months, rate, transport, loss, interest)
        m1, m2, m3 = st.columns(3)
        m1.metric("Sell today (net)", f"₹{r['sell_now']:,.0f}")
        m2.metric(f"Store {months} mo. (net)", f"₹{r['store']:,.0f}")
        m3.metric("Difference", f"₹{r['gain']:,.0f}", "Storing pays" if r["gain"] > 0 else "Selling now is better")
        st.caption(f"Storing costs ₹{r['storage_cost']:,.0f} rent, ₹{r['interest']:,.0f} interest and ₹{r['shrink']:,.0f} shrinkage. "
                   "The result depends on your expected price change, which is uncertain - test a few scenarios.")


def page_storage(profile: dict) -> None:
    page_header("🏬", "Storage Connect", "Find cold storage and warehouses near you and send a booking request.")
    note("<b>Sample listings.</b> Replace <code>gen_storage()</code> with your partner/WDRA directory API. "
         "Tip: pledging produce against an e-NWR receipt can unlock warehouse-receipt finance.")
    df = gen_storage(profile["lat"], profile["lon"])
    c1, c2, c3 = st.columns(3)
    commodity = c1.selectbox("What are you storing?", list(MARKET_BASE))
    radius = c2.slider("Search radius (km)", 5, 50, 30)
    sort = c3.selectbox("Sort by", ["Distance", "Rate (low to high)", "Free capacity"])
    kind = MARKET_BASE[commodity][2]
    if commodity == "Potato":
        df = df[df["Type"].isin(["Cold storage (potato)", "Cold storage (vegetables)"])]
    else:
        df = df[df["kind"] == kind]
    df = df[df["Distance (km)"] <= radius]
    df = df.sort_values({"Distance": "Distance (km)", "Rate (low to high)": "Rate (₹/qtl/month)",
                         "Free capacity": "Free capacity (MT)"}[sort], ascending=sort != "Free capacity")
    if df.empty:
        st.warning("No facilities in this radius. Increase the search radius.")
        return
    show = df[["Facility", "Type", "Distance (km)", "Free capacity (MT)", "Rate (₹/qtl/month)", "Temperature"]]
    st.dataframe(show, hide_index=True)
    me = pd.DataFrame({"lat": [profile["lat"]], "lon": [profile["lon"]]})
    st.map(pd.concat([df[["lat", "lon"]], me], ignore_index=True))
    st.caption("Map shows facilities and your selected location.")

    st.markdown("#### Request a booking")
    with st.form("book_form", clear_on_submit=True):
        f1, f2 = st.columns(2)
        fac = f1.selectbox("Facility", df["Facility"].tolist())
        qty = f2.number_input("Quantity (quintals)", 1.0, 100000.0, 100.0, step=10.0)
        g1, g2, g3 = st.columns(3)
        months = g1.slider("Duration (months)", 1, 10, 3)
        name = g2.text_input("Your name")
        phone = g3.text_input("Mobile number", max_chars=10)
        ok = st.form_submit_button("Send booking request", type="primary")
    if ok:
        if not name.strip() or not (phone.isdigit() and len(phone) == 10):
            st.error("Please enter your name and a valid 10-digit mobile number.")
        else:
            rate = int(df.loc[df["Facility"] == fac, "Rate (₹/qtl/month)"].iloc[0])
            rid = f"AS-{zlib.crc32((fac + name + phone).encode()) % 100000:05d}"
            st.session_state.setdefault("bookings", []).append(
                {"Request ID": rid, "Facility": fac, "Qty (qtl)": qty, "Months": months, "Est. rent (₹)": round(qty * rate * months)})
            st.success(f"Request **{rid}** recorded (demo). In production this would notify the facility and SMS you.")
    if st.session_state.get("bookings"):
        st.markdown("**Your requests this session**")
        st.dataframe(pd.DataFrame(st.session_state["bookings"]), hide_index=True)


def page_services(profile: dict) -> None:
    page_header("📍", "Nearby Agri Services", "Discover seed dealers, labs, equipment, banks and mandis around your location.")
    cats = list(SERVICE_TYPES)
    c1, c2 = st.columns([3, 2])
    chosen = c1.multiselect("Service types", cats, default=cats[:4])
    radius = c2.slider("Radius (km)", 5, 50, 25)
    if not chosen:
        st.info("Select at least one service type.")
        return

    st.markdown("**Find real, current listings on Google Maps**")
    cols = st.columns(min(len(chosen), 4))
    for i, cat in enumerate(chosen):
        cols[i % len(cols)].link_button(cat, maps_link(SERVICE_TYPES[cat][1], profile["lat"], profile["lon"]))

    df = gen_services(profile["lat"], profile["lon"])
    df = df[df["Category"].isin(chosen) & (df["Distance (km)"] <= radius)]
    st.markdown(f"#### Sample directory near {profile['loc'] if profile['loc'] != 'Custom coordinates' else 'your coordinates'}")
    note("Entries below are <b>sample data</b> to demonstrate the experience. Use the Google Maps buttons above for verified "
         "listings, or connect a Places API to replace <code>gen_services()</code>.")
    if df.empty:
        st.warning("Nothing in this radius. Increase the radius.")
        return
    st.dataframe(df[["Category", "Name", "Distance (km)", "Open"]], hide_index=True)
    me = pd.DataFrame({"lat": [profile["lat"]], "lon": [profile["lon"]]})
    st.map(pd.concat([df[["lat", "lon"]], me], ignore_index=True))


def page_scanner(profile: dict) -> None:
    page_header("🔬", "Plant Health Scanner", "Upload a clear leaf photo to screen for visible yellowing and brown or dead patches.")
    note("<b>Screening aid, not a diagnosis.</b> This tool measures leaf colour patterns only. It cannot confirm a disease, "
         "pest or deficiency, and can miss early, hidden or white-coloured symptoms. For a confirmed diagnosis, contact your KVK, "
         "plant clinic or Kisan Call Centre (1800-180-1551).")
    t1, t2 = st.tabs(["📁 Upload photo", "📷 Use camera"])
    with t1:
        f1 = st.file_uploader("Leaf photo", type=["jpg", "jpeg", "png", "webp"], key="leaf_up")
    with t2:
        f2 = st.camera_input("Take a photo of the leaf", key="leaf_cam")
    file = f1 or f2
    crop = st.selectbox("Crop (optional)", ["Not sure"] + list(CROPS), key="scan_crop")
    st.caption("Tips: one leaf, daylight, plain background, in focus, no flash glare.")
    if file is None:
        return

    try:
        img = Image.open(file)
        img.load()
    except Exception:
        st.error("Could not read that image. Please upload a JPG, PNG or WebP photo.")
        return
    with st.spinner("Analysing leaf colour patterns..."):
        res = analyze_leaf(img)
    if not res["ok"]:
        st.warning("I couldn't find enough leaf area in this photo. Retake it closer, in good light, filling the frame with the leaf.")
        return

    pct = res["pct"]
    a, b = st.columns(2)
    a.image(res["img"], caption="Your photo")
    b.image(res["overlay"], caption="Highlighted: amber = yellowing, red = brown/dead")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Healthy green", f"{pct['green']:.0f}%")
    m2.metric("Yellowing", f"{pct['yellow']:.0f}%")
    m3.metric("Brown / dead", f"{pct['brown']:.0f}%")
    m4.metric("Visible stress", res["severity"])

    st.markdown("#### What the image suggests")
    for title, text in res["findings"]:
        st.markdown(f"**{title}.** {text}")
    st.markdown("#### Sensible next steps")
    st.markdown("- Check the underside of leaves and stems for insects, webbing or spots.\n"
                "- Note the pattern: whole field vs a few plants, old vs new leaves, after rain or irrigation.\n"
                "- Remove and bag badly affected leaves; avoid overhead irrigation late in the day.\n"
                "- Take a soil test if yellowing is widespread (see Soil Intelligence).\n"
                f"- Show the photo{' of ' + crop if crop != 'Not sure' else ''} to your KVK or plant clinic before spraying anything; "
                "follow label doses and safety instructions.")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title=f"{APP_NAME}", page_icon="🌾", layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    profile = sidebar()
    page = st.session_state["nav"]
    dispatch = {
        PAGES[0]: page_home, PAGES[1]: page_crop, PAGES[2]: page_soil, PAGES[3]: page_rotation,
        PAGES[4]: page_schemes, PAGES[5]: page_market, PAGES[6]: page_storage,
        PAGES[7]: page_services, PAGES[8]: page_scanner,
    }
    dispatch[page](profile)
    st.divider()
    st.caption(f"© {date.today().year} {APP_NAME} · Decision-support only. Verify with local agricultural experts before acting.")


if __name__ == "__main__":
    main()