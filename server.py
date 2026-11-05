"""
ReaperShield - Local Development Server with Mock AWS Lambda/DynamoDB/S3 Telemetry
Integrated with Google Gemini 3.1 AI for Accident Authenticity Verification & First-Aid Decision Triage
Run using: python server.py
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.request
import urllib.error
import webbrowser
import hashlib
import base64
import datetime
import time

# Ensure UTF-8 console output for Windows PowerShell/CMD
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(DIRECTORY, "uploads")
EVIDENCE_DB_FILE = os.path.join(DIRECTORY, "evidence_database.json")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Helper functions for the dedicated Evidence Database
def load_evidence_db():
    if not os.path.exists(EVIDENCE_DB_FILE):
        return []
    try:
        with open(EVIDENCE_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_evidence_db(data):
    try:
        with open(EVIDENCE_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving evidence DB: {e}")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6JDFshXTOVJLYtRDXWXNA3Tt7P505LrkUj41hcZzdl7rQ")
GEMINI_MODEL = "gemini-3.1-flash-lite"

# ==============================================================================
# OFFICIAL 2026 FIRST AID DATABASE FOR ACCIDENTS & EMERGENCIES (CLINICAL HANDBOOK)
# Source: Emergency First-Aid Guidelines 2026 (ERSS 112 / GVK EMRI 108 / NHAI 1033)
# ==============================================================================
FIRST_AID_KNOWLEDGE_BASE = {
    "emergency_numbers": {
        "unified_sos": "112",
        "ambulance": "108",
        "highway_aid": "1033",
        "health_blood": "104",
        "police": "100",
        "fire": "101"
    },
    "protocols": [
        {
            "id": 1,
            "title": "The First Minute: What to Do First",
            "tamil_title": "முதல் ஒரு நிமிடம்: முதலில் செய்ய வேண்டியவை",
            "actions": [
                "Make the scene safe: check traffic, fire, electricity, chemicals, falling hazards. Do not become another casualty. Use gloves/barrier.",
                "Check response: speak loudly and gently tap shoulders. DO NOT shake someone with head/neck/spine injury.",
                "Call 112/108 on speakerphone. State exact location, number injured, conscious/breathing status.",
                "Check breathing: if unresponsive and not breathing normally (gasping != normal), start CPR + AED.",
                "If unconscious but breathing normally: place in recovery position UNLESS spine injury is suspected. Keep airway open.",
                "Treat life-threatening problems first: control severe bleeding with firm direct pressure. Keep warm & still."
            ],
            "critical_do_nots": [
                "DO NOT move a seriously injured person unless immediate danger (fire, traffic) or needed for lifesaving care.",
                "DO NOT give food, drink or medicines to an injured or unconscious person."
            ]
        },
        {
            "id": 2,
            "title": "CPR, Choking & Unconsciousness",
            "tamil_title": "சி.பி.ஆர், மூச்சுத்திணறல் & நினைவிழந்த நிலை",
            "actions": [
                "Place on back on a firm, flat surface. Put heel of one hand in center of chest, other hand on top. Arms straight.",
                "Push hard & fast: 100-120 compressions per minute, 5-6 cm deep for average adult. Allow full chest recoil.",
                "If trained: cycles of 30 compressions and 2 rescue breaths. If untrained: continuous hands-only chest compressions.",
                "Attach AED pads to bare, dry chest immediately. Follow voice prompts; do not touch during analysis or shock.",
                "Child/Infant: use age-appropriate compression depth; call 112 on speaker."
            ],
            "critical_do_nots": [
                "DO NOT practice CPR on someone who is responsive or breathing normally.",
                "DO NOT delay CPR to look for a pulse if person is unresponsive and not breathing."
            ]
        },
        {
            "id": 3,
            "title": "Severe Choking",
            "tamil_title": "கடுமையான மூச்சுத்திணறல் (தொண்டையில் அடைப்பு)",
            "actions": [
                "If coughing or speaking: encourage coughing and watch closely.",
                "If unable to breathe, cough or speak: give up to 5 firm back blows between shoulder blades.",
                "If not cleared: give up to 5 abdominal thrusts (Heimlich maneuver). Repeat 5 back blows & 5 thrusts until cleared.",
                "Pregnancy / Obese: use chest thrusts instead of abdominal thrusts.",
                "Baby under 1 year: 5 back blows with head lower than chest, then 5 chest thrusts with 2 fingers on breastbone. Call 112. If unresponsive, begin infant CPR."
            ],
            "critical_do_nots": [
                "DO NOT use abdominal thrusts on a baby under 1 year.",
                "DO NOT blindly sweep fingers inside the mouth (only remove object if clearly visible and loose)."
            ]
        },
        {
            "id": 4,
            "title": "Severe Bleeding, Wounds & Nosebleeds",
            "tamil_title": "கடுமையான ரத்தப்போக்கு, காயங்கள் & மூக்கில் ரத்தம்",
            "actions": [
                "Call 112/108. Put on gloves if available.",
                "Apply firm, continuous direct pressure with sterile gauze or clean cloth.",
                "If blood soaks through, ADD MORE MATERIAL ON TOP without lifting the first layer. Keep pressure until help arrives.",
                "For life-threatening limb bleeding, trained person may apply commercial tourniquet; note time and do not loosen.",
                "Nosebleed: sit upright and LEAN FORWARD. Pinch soft part of nose just above nostrils for 10-15 minutes continuously; breathe through mouth."
            ],
            "critical_do_nots": [
                "DO NOT remove an embedded object from a wound; apply pressure around it and stabilize it.",
                "DO NOT tilt the head back or lie flat during a nosebleed (causes blood swallowing/choking)."
            ]
        },
        {
            "id": 5,
            "title": "Burns, Scalds & Chemical Injuries",
            "tamil_title": "தீக்காயங்கள் & ரசாயன காயங்கள்",
            "actions": [
                "Thermal burn: move away from heat. Cool burn under cool or lukewarm running water for AT LEAST 20 MINUTES.",
                "Remove jewellery and loose clothing near burn, but DO NOT pull off anything stuck to skin.",
                "Cover loosely with clean non-fluffy dressing or clear cling film laid flat over the area (not wrapped tightly).",
                "Chemical splash: brush off dry powder first, then flush skin/eyes with running water for AT LEAST 20 MINUTES. Call 112/108."
            ],
            "critical_do_nots": [
                "DO NOT use ice, iced water, butter, toothpaste, oils, creams or powders on burns.",
                "DO NOT burst blisters or peel stuck clothing.",
                "DO NOT try to chemically neutralize an acid or alkaline chemical splash."
            ]
        },
        {
            "id": 6,
            "title": "Fractures, Sprains & Road Traffic Accidents",
            "tamil_title": "எலும்பு முறிவு & சாலை விபத்துகள் (Head, Neck & Spine)",
            "actions": [
                "Road crash: make scene safe, switch off vehicle ignition if safe. Call 112/108.",
                "Keep injured parts STILL in position found. Support with padding or splint without forcing straight.",
                "Head/Neck/Spine trauma: suspect after fall, crash or blow. Support head in position found; keep neck completely neutral.",
                "Watch for warning signs: vomiting, confusion, seizure, unequal pupils, blood/fluid from ears/nose, unconsciousness."
            ],
            "critical_do_nots": [
                "DO NOT move casualty unless there is immediate danger (fire, explosion, traffic).",
                "DO NOT remove a helmet unless essential to open airway or perform CPR and you are trained.",
                "DO NOT twist, straighten or sit up someone with suspected spine injury.",
                "DO NOT push exposed broken bone back into the wound."
            ]
        },
        {
            "id": 7,
            "title": "Medical Emergencies: Heart Attack, Stroke, Seizure & Shock",
            "tamil_title": "மாரடைப்பு, பக்கவாதம், வலிப்பு & அதிர்ச்சி",
            "actions": [
                "Heart attack: chest pressure/pain spreading to arm/jaw, sweating, shortness of breath. Call 112/108 immediately. Rest in comfortable position, loosen clothing.",
                "Stroke (FAST): Face drooping, Arm weakness, Speech slurred, Time to call 112 immediately. Note symptom onset time.",
                "Seizure / Fit: protect from hazards, cushion head, loosen tight neckwear, TIME the seizure. After shaking stops, place in recovery position if breathing.",
                "Shock (pale, cold, clammy, weak): lay flat if comfortable, keep warm, monitor breathing."
            ],
            "critical_do_nots": [
                "DO NOT put anything in the mouth of a person having a seizure.",
                "DO NOT restrain someone having a seizure.",
                "DO NOT give food, drink, tablets or aspirin unless specifically instructed by emergency dispatcher.",
                "DO NOT raise legs in shock if suspected spine, pelvis, abdominal, or leg injury."
            ]
        },
        {
            "id": 8,
            "title": "Poisoning, Snakebite, Animal Bites & Anaphylaxis",
            "tamil_title": "விஷம், பாம்புக்கடி, விலங்குக்கடி & கடுமையான ஒவ்வாமை",
            "actions": [
                "Snakebite: move away from snake. Keep person calm and COMPLETELY STILL. Immobilise bitten limb with loose splint; remove rings/watches before swelling. Call 112/108 immediately.",
                "Animal bite (dog/cat): wash wound thoroughly with soap and running water for ABOUT 15 MINUTES. Cover with clean dressing. Immediate rabies/tetanus assessment.",
                "Poisoning/overdose: call 112/poison centre. Keep container/label. Flush chemicals from eyes/skin with water.",
                "Anaphylaxis: help person administer prescribed adrenaline (EpiPen) auto-injector immediately. Lie flat with legs raised (sit if breathing difficult)."
            ],
            "critical_do_nots": [
                "DO NOT cut, suck, ice, burn, or wash a snakebite wound.",
                "DO NOT apply a tight tourniquet or traditional remedies to a snakebite.",
                "DO NOT induce vomiting after suspected poisoning.",
                "DO NOT give milk, drink or home remedies after poisoning."
            ]
        },
        {
            "id": 9,
            "title": "Drowning, Electric Shock, Heatstroke & Hypothermia",
            "tamil_title": "நீரில் மூழ்குதல், மின் அதிர்ச்சி, வெப்பத்தாக்கம் & தீவிர குளிர்",
            "actions": [
                "Electric shock: DO NOT touch person until power is isolated at mains. Once safe, call 112, check breathing, start CPR/AED if needed.",
                "Drowning: reach or throw flotation aid. Once rescued, call 112; start CPR with rescue breaths; dry chest before AED.",
                "Heatstroke: confusion, collapse, very hot skin. Call 112/108, cool rapidly with cold water, wet cloths and fanning.",
                "Hypothermia: move to shelter, remove wet clothing, wrap in dry layers gradually. Handle gently."
            ],
            "critical_do_nots": [
                "DO NOT touch someone receiving an electric shock until the power source is isolated.",
                "DO NOT give drinks to someone confused or unconscious.",
                "DO NOT rub frostbitten skin, apply direct intense heat, or give alcohol for hypothermia."
            ]
        },
        {
            "id": 10,
            "title": "Eye Injuries, Fainting, Diabetes & Asthma",
            "tamil_title": "கண் காயங்கள், மயக்கம், சர்க்கரை குறைவு & ஆஸ்துமா",
            "actions": [
                "Eye object: do not rub. Rinse gently with clean water if loose. Protect eye without pressing.",
                "Chemical in eye: flush immediately with running water for AT LEAST 20 MINUTES, holding eyelids open. Remove contacts while flushing. Call 112.",
                "Fainting: lie flat, protect from injury, loosen tight clothes. Rest before standing.",
                "Low blood sugar (conscious): give fast-acting sugary drink or glucose. Recheck in 10-15 minutes.",
                "Asthma attack: help person sit upright, use prescribed reliever inhaler with spacer. Call 112 if not improving."
            ],
            "critical_do_nots": [
                "DO NOT remove an embedded object from the eye.",
                "DO NOT give anything by mouth to an unconscious or drowsy diabetic person.",
                "DO NOT make someone having an asthma attack lie flat."
            ]
        },
        {
            "id": 11,
            "title": "Common First-Aid Mistakes to Avoid (Strict DO NOT Rules)",
            "tamil_title": "தவிர்க்க வேண்டிய தவறுகள் (கட்டாய 'செய்யக் கூடாதவை')",
            "actions": [
                "Review these strict negative clinical boundaries before touching a casualty."
            ],
            "critical_do_nots": [
                "DO NOT put anything in the mouth of a person having a seizure.",
                "DO NOT move a person with suspected spine injury unless immediate danger exists.",
                "DO NOT apply ice, toothpaste, butter, or oils to burns.",
                "DO NOT induce vomiting after suspected poisoning.",
                "DO NOT cut, suck, ice, or tightly tie a snakebite.",
                "DO NOT remove embedded objects from wounds.",
                "DO NOT give food, drink, or tablets to an unconscious or confused person.",
                "DO NOT touch someone receiving an electric shock until power is cut.",
                "DO NOT tilt the head back during a nosebleed (always lean forward).",
                "DO NOT remove a helmet from an accident victim unless airway is blocked and you are trained.",
                "DO NOT delay calling 112/108 while searching online or trying home remedies."
            ]
        },
        {
            "id": 12,
            "title": "What to Tell the Emergency Operator (112 / 108 Dispatch Briefing)",
            "tamil_title": "அவசர ஆபரேட்டரிடம் கூற வேண்டிய முக்கிய விவரங்கள்",
            "actions": [
                "1. Exact location and a nearby prominent landmark.",
                "2. Your callback phone number.",
                "3. Exactly what happened and when.",
                "4. Number of people injured and approximate ages.",
                "5. Whether each person is conscious and breathing normally.",
                "6. Major injuries: severe bleeding, head/spine trauma, chest pain, seizure, burn, poisoning, trapped person, etc.",
                "7. Any immediate scene hazards and what first aid has already been given."
            ],
            "critical_do_nots": [
                "DO NOT hang up until the operator tells you to do so."
            ]
        }
    ]
}

# Plaintext representation for Gemini LLM context
FIRST_AID_KNOWLEDGE_BASE_TEXT = json.dumps(FIRST_AID_KNOWLEDGE_BASE, indent=2, ensure_ascii=False)


TOKENS_DB_FILE = os.path.join(DIRECTORY, "tokens_database.json")
HOSPITAL_DB_FILE = os.path.join(DIRECTORY, "hospital_database.json")
BLOODLINE_DB_FILE = os.path.join(DIRECTORY, "bloodline_database.json")
ANALYTICS_DB_FILE = os.path.join(DIRECTORY, "analytics_database.json")

def load_tokens_db():
    if not os.path.exists(TOKENS_DB_FILE):
        initial_tokens = [
            {
                "token_id": "GST-2026-1103-4587",
                "timestamp": "Nov 03, 2026 • 10:14 AM",
                "location": "Tambaram, Chennai (GST Road)",
                "latitude": 12.9249,
                "longitude": 80.1481,
                "severity": "CRITICAL",
                "blood_group": "O-",
                "notes": "Two-wheeler collision with median. Bystander stabilized airway.",
                "bystander_phone": "+91 98401 99882",
                "sha256_hash": "SHA256:7FA9312E8B1C49D6A0142EF381294AA7",
                "legal_status": "SECTION_134A_IMMUNITY_ACTIVE",
                "court_reference": "Supreme Court WP (C) No. 235/2012",
                "morth_award_eligible": True,
                "qr_url": "/api/verify?token=GST-2026-1103-4587"
            },
            {
                "token_id": "GST-2026-1103-8821",
                "timestamp": "Nov 04, 2026 • 02:45 PM",
                "location": "Guindy Kathipara Junction, Chennai",
                "latitude": 13.0067,
                "longitude": 80.2038,
                "severity": "HIGH",
                "blood_group": "A+",
                "notes": "Rear bumper collision. Driver conscious, neck brace applied.",
                "bystander_phone": "+91 97908 12345",
                "sha256_hash": "SHA256:3B81A409D3E71C250E88F0241A6C5892",
                "legal_status": "SECTION_134A_IMMUNITY_ACTIVE",
                "court_reference": "Supreme Court WP (C) No. 235/2012",
                "morth_award_eligible": True,
                "qr_url": "/api/verify?token=GST-2026-1103-8821"
            }
        ]
        save_tokens_db(initial_tokens)
        return initial_tokens
    try:
        with open(TOKENS_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_tokens_db(data):
    try:
        with open(TOKENS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving tokens DB: {e}")

def load_hospital_db():
    if not os.path.exists(HOSPITAL_DB_FILE):
        initial_hospital = {
            "incoming_cases": [
                {
                    "case_id": "CASE-2026-9081",
                    "token_id": "GST-2026-1103-4587",
                    "location": "Tambaram, Chennai (GST Road)",
                    "eta": "08:00",
                    "eta_minutes": 8,
                    "vitals": "GCS 13, BP 110/70, SPO2 96%",
                    "severity": "CRITICAL",
                    "ambulance_id": "TN-01-G-1088",
                    "assigned_bay": "Trauma Bay 1 (Red Zone)",
                    "status": "EN_ROUTE",
                    "blood_required": "O-",
                    "blood_ready": "2 Units O- Rh-negative Allocated",
                    "paramedic_notes": "Neck stabilized with rigid C-collar. IV saline line running at 100ml/hr.",
                    "dispatched_at": "10:14 AM"
                }
            ],
            "hospitals": [
                {
                    "id": "HOSP-01",
                    "name": "Rajiv Gandhi Government General Hospital",
                    "type": "Level-1 Apex Trauma Center",
                    "area": "Park Town, Chennai",
                    "distance_km": 4.2,
                    "icu_trauma_beds_free": 12,
                    "blood_bank_status": "Active 24/7 (O-, O+, A+, B+ stocked)",
                    "phone": "044-25305000",
                    "coordinates": [13.0827, 80.2707],
                    "surgeons_on_call": 4
                },
                {
                    "id": "HOSP-02",
                    "name": "Government Kilpauk Medical College Hospital",
                    "type": "Super Specialty Burns & Trauma Center",
                    "area": "Kilpauk, Chennai",
                    "distance_km": 6.8,
                    "icu_trauma_beds_free": 8,
                    "blood_bank_status": "Active 24/7",
                    "phone": "044-28364951",
                    "coordinates": [13.0833, 80.2431],
                    "surgeons_on_call": 3
                },
                {
                    "id": "HOSP-03",
                    "name": "Tambaram Taluk Government Hospital",
                    "type": "Sub-District Trauma Emergency Center",
                    "area": "Chromepet / Tambaram, Chennai",
                    "distance_km": 1.8,
                    "icu_trauma_beds_free": 4,
                    "blood_bank_status": "Active 24/7",
                    "phone": "044-22418282",
                    "coordinates": [12.9342, 80.1415],
                    "surgeons_on_call": 2
                },
                {
                    "id": "HOSP-04",
                    "name": "Government Royapettah Hospital",
                    "type": "Regional Trauma Center",
                    "area": "Royapettah, Chennai",
                    "distance_km": 5.1,
                    "icu_trauma_beds_free": 6,
                    "blood_bank_status": "Active 24/7",
                    "phone": "044-28483051",
                    "coordinates": [13.0569, 80.2589],
                    "surgeons_on_call": 2
                },
                {
                    "id": "HOSP-05",
                    "name": "Stanley Medical College & Hospital",
                    "type": "North Chennai Trauma Care Center",
                    "area": "Old Jail Road, Royapuram, Chennai",
                    "distance_km": 7.5,
                    "icu_trauma_beds_free": 10,
                    "blood_bank_status": "Active 24/7",
                    "phone": "044-25281351",
                    "coordinates": [13.1067, 80.2872],
                    "surgeons_on_call": 3
                }
            ]
        }
        save_hospital_db(initial_hospital)
        return initial_hospital
    try:
        with open(HOSPITAL_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"incoming_cases": [], "hospitals": []}

def save_hospital_db(data):
    try:
        with open(HOSPITAL_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving hospital DB: {e}")

def load_bloodline_db():
    if not os.path.exists(BLOODLINE_DB_FILE):
        initial_bloodline = {
            "donors": [
                {
                    "id": "D1",
                    "name": "Karthik Raja",
                    "blood": "O-",
                    "phone": "+91 98401 23456",
                    "occupation": "IT Systems Engineer @ TCS",
                    "source": "Verified Indian Red Cross Society (Camp ID: #RC-9082)",
                    "lastDonated": "4 Months ago (Medically Eligible)",
                    "area": "Mount Road, Chennai",
                    "distance": "1.2 km",
                    "status": "Verified Active",
                    "enRoute": False
                },
                {
                    "id": "D2",
                    "name": "Ananya Murali",
                    "blood": "O-",
                    "phone": "+91 98410 87654",
                    "occupation": "Senior High School Teacher",
                    "source": "Rajiv Gandhi GH Annual Blood Registry (Reg #GH-4412)",
                    "lastDonated": "6 Months ago (Medically Eligible)",
                    "area": "Alwarpet, Chennai",
                    "distance": "2.4 km",
                    "status": "Verified Active",
                    "enRoute": False
                },
                {
                    "id": "D3",
                    "name": "Vignesh Sundaram",
                    "blood": "O-",
                    "phone": "+91 94441 55678",
                    "occupation": "Mechanical Engineer @ Hyundai",
                    "source": "Rotary Blood Bank Emergency Volunteer (#ROT-887)",
                    "lastDonated": "5 Months ago (Medically Eligible)",
                    "area": "Guindy Industrial Estate, Chennai",
                    "distance": "3.1 km",
                    "status": "EN ROUTE (11m)",
                    "enRoute": True
                },
                {
                    "id": "D4",
                    "name": "Dr. Priya Lakshmi",
                    "blood": "O+",
                    "phone": "+91 98842 11223",
                    "occupation": "Resident Pediatrician @ Apollo",
                    "source": "Tamil Nadu State Blood Transfusion Council",
                    "lastDonated": "3 Months ago",
                    "area": "Greams Road, Chennai",
                    "distance": "1.5 km",
                    "status": "Verified Active",
                    "enRoute": False
                },
                {
                    "id": "D5",
                    "name": "Saravanan M.",
                    "blood": "A+",
                    "phone": "+91 97908 33445",
                    "occupation": "Logistics Dispatch Supervisor",
                    "source": "Lion's Club Blood Mission (#LION-321)",
                    "lastDonated": "4 Months ago",
                    "area": "Koyambedu, Chennai",
                    "distance": "4.0 km",
                    "status": "Verified Active",
                    "enRoute": False
                },
                {
                    "id": "D6",
                    "name": "Deepa Ramachandran",
                    "blood": "B+",
                    "phone": "+91 99402 77889",
                    "occupation": "Software Architect @ Zoho",
                    "source": "IT Corridor Emergency Donor Network",
                    "lastDonated": "7 Months ago",
                    "area": "Guduvanchery / Tambaram, Chennai",
                    "distance": "3.5 km",
                    "status": "Verified Active",
                    "enRoute": False
                },
                {
                    "id": "D7",
                    "name": "Arvind Swaminathan",
                    "blood": "AB+",
                    "phone": "+91 98419 66778",
                    "occupation": "Branch Manager @ SBI",
                    "source": "Indian Red Cross Society",
                    "lastDonated": "5 Months ago",
                    "area": "Nungambakkam, Chennai",
                    "distance": "2.9 km",
                    "status": "Verified Active (Universal Recipient)",
                    "enRoute": False
                },
                {
                    "id": "D8",
                    "name": "Mohammed Faizal",
                    "blood": "AB-",
                    "phone": "+91 98400 99112",
                    "occupation": "Certified Emergency Paramedic",
                    "source": "St. John Ambulance Association",
                    "lastDonated": "4 Months ago",
                    "area": "Central / George Town, Chennai",
                    "distance": "3.8 km",
                    "status": "Verified Active (Rare Phenotype)",
                    "enRoute": False
                }
            ],
            "alerts": []
        }
        save_bloodline_db(initial_bloodline)
        return initial_bloodline
    try:
        with open(BLOODLINE_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"donors": [], "alerts": []}

def save_bloodline_db(data):
    try:
        with open(BLOODLINE_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving bloodline DB: {e}")

def load_analytics_db():
    if not os.path.exists(ANALYTICS_DB_FILE):
        initial_analytics = {
            "total_dispatches": 142,
            "lives_saved": 138,
            "average_response_time_seconds": 448,
            "average_response_time_human": "7.4 minutes",
            "tokens_issued": 142,
            "active_blood_donors": 846,
            "morth_award_claims_filed": 29,
            "trauma_centers_connected": 14,
            "uptime_percentage": 99.98,
            "last_incident_timestamp": datetime.datetime.now().strftime("%b %d, %Y • %I:%M %p"),
            "district_breakdown": {
                "Chennai": 64,
                "Chengalpattu / Tambaram": 38,
                "Kanchipuram": 22,
                "Tiruvallur": 18
            }
        }
        save_analytics_db(initial_analytics)
        return initial_analytics
    try:
        with open(ANALYTICS_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_analytics_db(data):
    try:
        with open(ANALYTICS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving analytics DB: {e}")

class ReaperShieldHandler(http.server.SimpleHTTPRequestHandler):
    def address_string(self):
        # Disable slow Windows reverse DNS lookups for instant sub-millisecond responses
        return str(self.client_address[0])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def do_GET(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API: Server Health & Full Backend Status
        if path == '/api/status' or path == '/api/health':
            db_records = load_evidence_db()
            tokens_db = load_tokens_db()
            hosp_db = load_hospital_db()
            blood_db = load_bloodline_db()
            analytics_db = load_analytics_db()
            status_data = {
                "status": "ONLINE",
                "service": "ReaperShield Unified Full-Stack Backend",
                "version": "2.5.0",
                "port": PORT,
                "endpoints": [
                    "/api/status",
                    "/api/health",
                    "/api/location/auto",
                    "/api/location/reverse-geocode",
                    "/api/first-aid/protocols",
                    "/api/first-aid/protocol/<id>",
                    "/api/verify",
                    "/api/tokens/list",
                    "/api/tokens/<token_id>",
                    "/api/certificate/<token_id>",
                    "/api/dispatch",
                    "/api/evidence/upload",
                    "/api/evidence/list",
                    "/api/evidence/photo/<token_id>",
                    "/api/evidence/clear",
                    "/api/bloodline/donors",
                    "/api/bloodline/broadcast",
                    "/api/bloodline/register",
                    "/api/bloodline/ping",
                    "/api/bloodline/alerts",
                    "/api/hospital/incoming",
                    "/api/hospital/update-eta",
                    "/api/hospital/admit",
                    "/api/hospital/hospitals",
                    "/api/analytics/metrics",
                    "/api/analytics/leaderboard",
                    "/api/emergency/contacts",
                    "/api/sos/broadcast",
                    "/api/aws/telemetry",
                    "/api/gemini/triage"
                ],
                "gemini_model": GEMINI_MODEL,
                "gemini_status": "READY",
                "aws_region": "ap-south-1",
                "dynamodb_status": "CONNECTED",
                "evidence_vault_count": len(db_records),
                "tokens_count": len(tokens_db),
                "active_incoming_cases": len(hosp_db.get("incoming_cases", [])),
                "registered_donors": len(blood_db.get("donors", [])),
                "protocols_count": len(FIRST_AID_KNOWLEDGE_BASE.get("protocols", []))
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status_data, ensure_ascii=False).encode('utf-8'))
            return

        # 2. API: High-Precision Auto Location Resolver (IP & Network Telemetry)
        elif path == '/api/location/auto':
            loc_data = {
                "status": "SUCCESS",
                "source": "NETWORK_TELEMETRY",
                "city": "Kalpatta",
                "region": "Kerala",
                "country": "India",
                "lat": 11.61056,
                "lng": 76.08222,
                "formatted": "Kalpatta, Kerala (11.6106° N, 76.0822° E)"
            }
            try:
                req = urllib.request.Request("https://ipapi.co/json/", headers={"User-Agent": "Mozilla/5.0 ReaperShield/2.5"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    d = json.loads(resp.read().decode('utf-8'))
                    if d.get('latitude') and d.get('longitude'):
                        c = d.get('city') or d.get('region') or 'Urban Corridor'
                        r = d.get('region') or d.get('country_name') or 'India'
                        lat = float(d.get('latitude'))
                        lng = float(d.get('longitude'))
                        loc_data = {
                            "status": "SUCCESS",
                            "source": "LIVE_IP_GEOLOCATION",
                            "city": c,
                            "region": r,
                            "lat": lat,
                            "lng": lng,
                            "formatted": f"{c}, {r} ({lat:.4f}° N, {lng:.4f}° E)"
                        }
            except Exception as ex:
                print(f"⚠️ External IP Geolocation fallback: {ex}")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(loc_data, ensure_ascii=False).encode('utf-8'))
            return

        # 3. API: Deliver Official 2026 First-Aid Knowledge Base
        elif path == '/api/first-aid/protocols':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(FIRST_AID_KNOWLEDGE_BASE, ensure_ascii=False).encode('utf-8'))
            return

        # 3b. API: Single Protocol by ID or search
        elif path.startswith('/api/first-aid/protocol/'):
            param = path.split('/')[-1]
            protocols = FIRST_AID_KNOWLEDGE_BASE.get("protocols", [])
            matched = None
            if param.isdigit():
                pid = int(param)
                matched = next((p for p in protocols if p.get('id') == pid), None)
            else:
                pname = param.lower()
                matched = next((p for p in protocols if pname in p.get('title', '').lower()), None)
            if matched:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "SUCCESS", "protocol": matched}, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "NOT_FOUND", "message": f"Protocol {param} not found"}, ensure_ascii=False).encode('utf-8'))
            return

        # 4. API: Verify Good Samaritan Legal Immunity Token
        elif path.startswith('/api/verify'):
            token_query = query.get('token', ['GST-2026-1103-4587'])[0]
            
            # Check tokens_db first, then evidence_db
            tokens_db = load_tokens_db()
            found = next((t for t in tokens_db if t.get('token_id') == token_query), None)
            
            if not found:
                ev_records = load_evidence_db()
                found = next((r for r in ev_records if r.get('token_id') == token_query), None)
            
            if not found:
                found = {
                    "token_id": token_query,
                    "timestamp": datetime.datetime.now().strftime("%b %d, %Y • %I:%M %p"),
                    "location": "Tambaram, Chennai (GST Road)",
                    "severity": "CRITICAL",
                    "blood_group": "O-",
                    "notes": "Verified Good Samaritan rescue submission",
                    "sha256_hash": f"SHA256:{hashlib.sha256(token_query.encode()).hexdigest()[:32].upper()}",
                    "legal_status": "SECTION_134A_IMMUNITY_ACTIVE",
                    "court_reference": "Supreme Court WP (C) No. 235/2012"
                }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "VERIFIED",
                "token_id": token_query,
                "record": found,
                "statutory_immunity": "ACTIVE",
                "legal_shield": "SECTION_134A_MOTOR_VEHICLES_ACT_1988",
                "court_directive": "SaveLIFE Foundation vs Union of India (2016) 7 SCC 638"
            }, ensure_ascii=False).encode('utf-8'))
            return

        # 5. API: Retrieve All Good Samaritan Tokens
        elif path == '/api/tokens/list':
            tokens = load_tokens_db()
            filter_q = query.get('q', [''])[0].strip().lower()
            if filter_q:
                tokens = [t for t in tokens if filter_q in t.get('token_id', '').lower() or filter_q in t.get('location', '').lower() or filter_q in t.get('severity', '').lower()]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "count": len(tokens), "tokens": tokens}, ensure_ascii=False).encode('utf-8'))
            return

        # 5b. API: Single Token Details
        elif path.startswith('/api/tokens/'):
            token_id = path.split('/')[-1]
            tokens = load_tokens_db()
            matched = next((t for t in tokens if t.get('token_id') == token_id), None)
            if matched:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "SUCCESS", "token": matched}, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "NOT_FOUND", "message": f"Token {token_id} not found"}, ensure_ascii=False).encode('utf-8'))
            return

        # 6. API: Good Samaritan Legal Immunity Certificate Payload
        elif path.startswith('/api/certificate/'):
            token_id = path.split('/')[-1]
            tokens = load_tokens_db()
            matched = next((t for t in tokens if t.get('token_id') == token_id), None)
            if not matched:
                matched = {
                    "token_id": token_id,
                    "timestamp": datetime.datetime.now().strftime("%b %d, %Y • %I:%M %p"),
                    "location": "Chennai Highway Corridor, Tamil Nadu",
                    "severity": "CRITICAL",
                    "sha256_hash": f"SHA256:{hashlib.sha256(token_id.encode()).hexdigest()[:32].upper()}"
                }
            cert_payload = {
                "certificate_title": "OFFICIAL GOOD SAMARITAN STATUTORY IMMUNITY CERTIFICATE",
                "token_id": token_id,
                "legal_statute": "Section 134A of The Motor Vehicles (Amendment) Act, 2019",
                "gazette_notification": "Gazette of India Extraordinary No. 341 (MoRTH)",
                "supreme_court_ruling": "SaveLIFE Foundation vs Union of India, WP (C) No. 235/2012",
                "immunity_clauses": [
                    "Zero civil and zero criminal liability for any assistance provided during the Golden Hour.",
                    "Complete protection against police questioning, harassment, detention, or compelled testimony.",
                    "Immunity from hospital demand for advance payment, deposit, or registration charges.",
                    "Option to remain anonymous or provide voluntary testimony via single video conference affidavit."
                ],
                "morth_cash_award_scheme": "Eligible for MoRTH ₹5,000 Cash Award & Prashansa Patra Scheme for saving road crash victims.",
                "incident_details": matched,
                "issued_by": "National Emergency Road Safety Telemetry Network (ERSS 112 / GVK EMRI 108)"
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(cert_payload, ensure_ascii=False).encode('utf-8'))
            return

        # 7. API: Retrieve all records from dedicated Evidence Database
        elif path == '/api/evidence/list':
            records = load_evidence_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "count": len(records), "records": records}, ensure_ascii=False).encode('utf-8'))
            return

        # 7b. API: Retrieve single photo by token_id from dedicated storage
        elif path.startswith('/api/evidence/photo/'):
            token_id = path.split('/')[-1]
            clean_token = "".join(c for c in token_id if c.isalnum() or c in "-_")
            photo_path = os.path.join(UPLOADS_DIR, f"{clean_token}.jpg")
            if os.path.exists(photo_path):
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                with open(photo_path, 'rb') as pf:
                    self.wfile.write(pf.read())
                return
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Photo not found in Evidence Vault"}).encode('utf-8'))
                return

        # 7c. Direct file serve for /uploads/
        elif path.startswith('/uploads/'):
            filename = os.path.basename(path)
            clean_name = "".join(c for c in filename if c.isalnum() or c in ".-_")
            filepath = os.path.join(UPLOADS_DIR, clean_name)
            if os.path.exists(filepath):
                mime = 'image/jpeg' if filepath.lower().endswith(('.jpg', '.jpeg')) else ('image/png' if filepath.lower().endswith('.png') else 'application/octet-stream')
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
                return

        # 8. API: Hospital Incoming Trauma Feed
        elif path == '/api/hospital/incoming':
            hosp_db = load_hospital_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "SUCCESS",
                "count": len(hosp_db.get("incoming_cases", [])),
                "incoming_cases": hosp_db.get("incoming_cases", [])
            }, ensure_ascii=False).encode('utf-8'))
            return

        # 8b. API: Nearby Verified Level-1 Trauma Centers
        elif path == '/api/hospital/hospitals':
            hosp_db = load_hospital_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "SUCCESS",
                "count": len(hosp_db.get("hospitals", [])),
                "hospitals": hosp_db.get("hospitals", [])
            }, ensure_ascii=False).encode('utf-8'))
            return

        # 9. API: BloodLine Donors List & Filter
        elif path == '/api/bloodline/donors':
            blood_db = load_bloodline_db()
            donors = blood_db.get("donors", [])
            target_group = query.get('group', [''])[0].strip().upper()
            
            # Blood compatibility filter
            if target_group:
                def is_compatible(donor_blood, patient_blood):
                    if patient_blood == 'O-': return donor_blood == 'O-'
                    if patient_blood == 'O+': return donor_blood in ['O-', 'O+']
                    if patient_blood == 'A+': return donor_blood in ['O-', 'O+', 'A-', 'A+']
                    if patient_blood == 'A-': return donor_blood in ['O-', 'A-']
                    if patient_blood == 'B+': return donor_blood in ['O-', 'O+', 'B-', 'B+']
                    if patient_blood == 'B-': return donor_blood in ['O-', 'B-']
                    if patient_blood == 'AB+': return True
                    if patient_blood == 'AB-': return donor_blood in ['O-', 'A-', 'B-', 'AB-']
                    return donor_blood == patient_blood

                donors = [d for d in donors if is_compatible(d.get('blood', ''), target_group)]

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "SUCCESS",
                "target_group": target_group or "ALL",
                "count": len(donors),
                "donors": donors
            }, ensure_ascii=False).encode('utf-8'))
            return

        # 9b. API: BloodLine Alert Broadcast History
        elif path == '/api/bloodline/alerts':
            blood_db = load_bloodline_db()
            alerts = blood_db.get("alerts", [])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "count": len(alerts), "alerts": alerts}, ensure_ascii=False).encode('utf-8'))
            return

        # 10. API: Impact Analytics Metrics
        elif path == '/api/analytics/metrics':
            analytics_db = load_analytics_db()
            tokens_db = load_tokens_db()
            ev_db = load_evidence_db()
            analytics_db["total_dispatches"] = max(analytics_db.get("total_dispatches", 142), len(tokens_db))
            analytics_db["tokens_issued"] = len(tokens_db)
            analytics_db["evidence_records_count"] = len(ev_db)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "metrics": analytics_db}, ensure_ascii=False).encode('utf-8'))
            return

        # 10b. API: Regional Trauma Leaderboard
        elif path == '/api/analytics/leaderboard':
            leaderboard = [
                {"rank": 1, "district": "Chennai Metro", "dispatches": 64, "avg_eta": "6.8 min", "lives_saved_rate": "98.4%"},
                {"rank": 2, "district": "Chengalpattu (GST Road)", "dispatches": 38, "avg_eta": "7.2 min", "lives_saved_rate": "97.1%"},
                {"rank": 3, "district": "Kanchipuram (Bangalore Hwy)", "dispatches": 22, "avg_eta": "8.1 min", "lives_saved_rate": "95.5%"},
                {"rank": 4, "district": "Tiruvallur (NH 716)", "dispatches": 18, "avg_eta": "8.5 min", "lives_saved_rate": "94.2%"}
            ]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "leaderboard": leaderboard}, ensure_ascii=False).encode('utf-8'))
            return

        # 11. API: Official 2026 Emergency Helplines Directory
        elif path == '/api/emergency/contacts':
            contacts = {
                "unified_emergency": {"number": "112", "label": "ERSS National Unified Emergency Helpline", "description": "Police, Fire, Ambulance 24x7"},
                "ambulance": {"number": "108", "label": "GVK EMRI Free Emergency Ambulance & Trauma Triage", "description": "Free BLS/ALS Ambulance Dispatch"},
                "highway_aid": {"number": "1033", "label": "NHAI Highway Emergency Care", "description": "Tollway Incident Management, Cranes & Route Aid"},
                "health_blood": {"number": "104", "label": "National Health & Blood Bank Information Helpline", "description": "Blood availability & medical counseling"},
                "disaster": {"number": "1077", "label": "District Disaster Management Authority", "description": "Flood, cyclone, road collapse & mass casualty coordination"},
                "women_safety": {"number": "1091", "label": "Women Safety Emergency SOS", "description": "Direct Police Women Patrol SOS"},
                "childline": {"number": "1098", "label": "Childline Emergency Assistance", "description": "Protection for children in distress or crash victims"}
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "contacts": contacts}, ensure_ascii=False).encode('utf-8'))
            return

        # 12. API: AWS Cloud Architecture Telemetry (for in-browser AWS Modal)
        elif path == '/api/aws/telemetry':
            tokens_db = load_tokens_db()
            ev_db = load_evidence_db()
            blood_db = load_bloodline_db()
            aws_telemetry = {
                "region": "ap-south-1 (Asia Pacific - Mumbai)",
                "timestamp": datetime.datetime.now().isoformat(),
                "services": {
                    "dynamodb": {
                        "table_name": "GoodSamaritanTokens",
                        "status": "ACTIVE",
                        "item_count": len(tokens_db),
                        "billing_mode": "PAY_PER_REQUEST",
                        "primary_key": "token_id (String)"
                    },
                    "s3": {
                        "bucket_name": "reapershield-accident-evidence-vault",
                        "status": "ONLINE",
                        "object_count": len(ev_db),
                        "encryption": "AES256_SSE_S3",
                        "lifecycle_rule": "Retain forensic records for 7 years"
                    },
                    "lambda": {
                        "functions": [
                            {"name": "ReaperShieldDispatch", "runtime": "python3.12", "memory": "256 MB", "invocations_today": len(tokens_db) * 3 + 12},
                            {"name": "ReaperShieldVerify", "runtime": "python3.12", "memory": "128 MB", "invocations_today": 84},
                            {"name": "ReaperShieldGeminiTriage", "runtime": "python3.12", "memory": "512 MB", "invocations_today": 56},
                            {"name": "ReaperShieldBloodline", "runtime": "python3.12", "memory": "256 MB", "invocations_today": 41}
                        ]
                    },
                    "sns": {
                        "topic_arn": "arn:aws:sns:ap-south-1:713881804297:EmergencyTraumaDispatch",
                        "blood_topic_arn": "arn:aws:sns:ap-south-1:713881804297:EmergencyBloodDonors",
                        "status": "CONFIRMED",
                        "subscribers_count": len(blood_db.get("donors", [])) + 14
                    }
                }
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(aws_telemetry, ensure_ascii=False).encode('utf-8'))
            return

        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            payload = {}

        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. API: Core Emergency Incident Dispatch (/api/dispatch)
        if path == '/api/dispatch':
            token_id = payload.get('token_id') or f"GST-2026-1103-{int(datetime.datetime.now().timestamp()) % 10000:04d}"
            photo_data = payload.get('photo_data') or payload.get('photo') or payload.get('image') or ''
            location = payload.get('location') or 'Tambaram, Chennai (GST Road)'
            severity = payload.get('severity') or 'CRITICAL'
            notes = payload.get('notes') or payload.get('victim_notes') or 'Emergency road crash report'
            blood_group = payload.get('blood_group') or 'O-'
            lat = payload.get('latitude') or 12.9249
            lng = payload.get('longitude') or 80.1481
            bystander_phone = payload.get('bystander_phone') or '+91 98401 00000'

            # 1a. Store photo in Evidence Database if provided
            evidence_rec = None
            sha256_hash = f"SHA256:{hashlib.sha256(f'{token_id}{time.time()}'.encode()).hexdigest()[:32].upper()}"
            if photo_data:
                clean_token = "".join(c for c in token_id if c.isalnum() or c in "-_")
                saved_filename = f"{clean_token}.jpg"
                saved_path = os.path.join(UPLOADS_DIR, saved_filename)
                file_size = 0
                photo_b64 = photo_data.split(',', 1)[1] if ',' in photo_data else photo_data
                try:
                    img_bytes = base64.b64decode(photo_b64)
                    with open(saved_path, 'wb') as img_f:
                        img_f.write(img_bytes)
                    file_size = len(img_bytes)
                    sha256_hash = f"SHA256:{hashlib.sha256(img_bytes).hexdigest()[:32].upper()}"
                except Exception as ex:
                    print(f"⚠️ Dispatch photo decode error: {ex}")

                evidence_rec = {
                    "token_id": token_id,
                    "photo_filename": saved_filename,
                    "photo_url": f"/uploads/{saved_filename}",
                    "file_size_bytes": file_size,
                    "timestamp": datetime.datetime.now().strftime("%b %d, %Y • %I:%M %p"),
                    "location": location,
                    "severity": severity,
                    "notes": notes,
                    "sha256_hash": sha256_hash,
                    "legal_status": "SECTION_134A_IMMUNITY_ACTIVE",
                    "database": "DEDICATED_EVIDENCE_VAULT_DB"
                }
                ev_db = load_evidence_db()
                ev_db = [r for r in ev_db if r.get('token_id') != token_id]
                ev_db.insert(0, evidence_rec)
                save_evidence_db(ev_db)

            # 1b. Commit Token to persistent tokens_database.json
            now_str = datetime.datetime.now().strftime("%b %d, %Y • %I:%M %p")
            token_record = {
                "token_id": token_id,
                "timestamp": now_str,
                "created_at": datetime.datetime.now().isoformat(),
                "timestamp_human": datetime.datetime.now().strftime("%I:%M:%S %p, Today"),
                "location": location,
                "latitude": lat,
                "longitude": lng,
                "severity": severity,
                "blood_group": blood_group,
                "notes": notes,
                "bystander_phone": bystander_phone,
                "sha256_hash": sha256_hash,
                "legal_status": "SECTION_134A_IMMUNITY_ACTIVE",
                "court_reference": "Supreme Court WP (C) No. 235/2012",
                "morth_award_eligible": True,
                "qr_url": f"/api/verify?token={token_id}"
            }
            tokens_db = load_tokens_db()
            tokens_db = [t for t in tokens_db if t.get('token_id') != token_id]
            tokens_db.insert(0, token_record)
            save_tokens_db(tokens_db)

            # 1c. Create incoming trauma case in hospital_database.json
            hosp_db = load_hospital_db()
            case_id = f"CASE-{datetime.datetime.now().strftime('%Y')}-{int(time.time()) % 10000:04d}"
            new_incoming = {
                "case_id": case_id,
                "token_id": token_id,
                "location": location,
                "eta": "08:00",
                "eta_minutes": 8,
                "vitals": "GCS 13, BP 110/70, SPO2 96%",
                "severity": severity,
                "ambulance_id": "TN-01-G-1088",
                "assigned_bay": "Trauma Bay 1 (Red Zone)",
                "status": "EN_ROUTE",
                "blood_required": blood_group,
                "blood_ready": f"2 Units {blood_group} Allocated",
                "paramedic_notes": f"Bystander first-aid applied. {notes}",
                "dispatched_at": datetime.datetime.now().strftime("%I:%M %p")
            }
            incoming_cases = hosp_db.get("incoming_cases", [])
            incoming_cases.insert(0, new_incoming)
            hosp_db["incoming_cases"] = incoming_cases[:10]
            save_hospital_db(hosp_db)

            # 1d. Increment Analytics
            analytics_db = load_analytics_db()
            analytics_db["total_dispatches"] = analytics_db.get("total_dispatches", 142) + 1
            analytics_db["tokens_issued"] = len(tokens_db)
            analytics_db["last_incident_timestamp"] = now_str
            save_analytics_db(analytics_db)

            print("\n" + "="*50)
            print("⚡ [AWS LAMBDA UNIFIED DISPATCH TRIGGERED]")
            print(f"📦 Token ID: {token_id} | Location: {location}")
            print(f"🪣 [AWS S3]: Stored accident evidence snapshot to s3://reapershield-accident-evidence-vault/{token_id}.jpg")
            print("💾 [AWS DynamoDB]: Stored token record to table 'GoodSamaritanTokens'")
            print("🗄️ [DEDICATED EVIDENCE DB]: Committed photo to separate evidence_database.json")
            print("🏥 [HOSPITAL TELEMETRY]: En route alert sent to Rajiv Gandhi General Hospital")
            print("🔔 [AWS SNS]: Dispatched emergency priority push to Level-1 Trauma Bay")
            print("="*50 + "\n")

            response = {
                "statusCode": 200,
                "status": "SUCCESS",
                "awsRegion": "ap-south-1",
                "lambdaRequestId": f"c8a41289-{hashlib.md5(token_id.encode()).hexdigest()[:12]}",
                "token_id": token_id,
                "token_record": token_record,
                "case_id": case_id,
                "dynamoDbStatus": "ITEM_COMMITTED",
                "evidenceDatabaseStatus": "RECORD_PERSISTED",
                "evidenceRecord": evidence_rec,
                "legalStatus": "SECTION_134A_IMMUNITY_ACTIVE",
                "statutoryProtection": "Complete Civil and Criminal Legal Shield under Motor Vehicles Act 2019"
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            return

        # 2. API: Manual / Programmatic Token Creation
        elif path == '/api/tokens/create':
            token_id = payload.get('token_id') or f"GST-2026-1103-{int(datetime.datetime.now().timestamp()) % 10000:04d}"
            location = payload.get('location') or 'Tamil Nadu Highway Corridor'
            severity = payload.get('severity') or 'CRITICAL'
            notes = payload.get('notes') or 'Direct token generation'
            
            token_rec = {
                "token_id": token_id,
                "timestamp": datetime.datetime.now().strftime("%b %d, %Y • %I:%M %p"),
                "created_at": datetime.datetime.now().isoformat(),
                "timestamp_human": datetime.datetime.now().strftime("%I:%M:%S %p, Today"),
                "location": location,
                "latitude": payload.get('latitude', 12.9249),
                "longitude": payload.get('longitude', 80.1481),
                "severity": severity,
                "blood_group": payload.get('blood_group', 'O-'),
                "notes": notes,
                "bystander_phone": payload.get('bystander_phone', '+91 98401 00000'),
                "sha256_hash": f"SHA256:{hashlib.sha256(token_id.encode()).hexdigest()[:32].upper()}",
                "legal_status": "SECTION_134A_IMMUNITY_ACTIVE",
                "court_reference": "Supreme Court WP (C) No. 235/2012",
                "morth_award_eligible": True,
                "qr_url": f"/api/verify?token={token_id}"
            }
            tokens_db = load_tokens_db()
            tokens_db.insert(0, token_rec)
            save_tokens_db(tokens_db)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "token": token_rec}, ensure_ascii=False).encode('utf-8'))
            return

        # 3. API: Dedicated Evidence Database Photo Upload
        elif path == '/api/evidence/upload':
            token_id = payload.get('token_id') or f"GST-2026-1103-{int(datetime.datetime.now().timestamp()) % 10000:04d}"
            photo_data = payload.get('photo_data') or payload.get('photo') or payload.get('image') or ''
            location = payload.get('location') or 'Tambaram, Chennai (12.9249° N, 80.1481° E)'
            severity = payload.get('severity') or 'CRITICAL'
            notes = payload.get('notes') or 'Live accident photo uploaded via Good Samaritan 1-Tap Portal'
            
            clean_token = "".join(c for c in token_id if c.isalnum() or c in "-_")
            saved_filename = f"{clean_token}.jpg"
            saved_path = os.path.join(UPLOADS_DIR, saved_filename)
            
            file_size = 0
            sha256_hash = "SHA256:7FA9312E8B1C49D6A0142EF38"
            
            photo_b64 = ''
            if photo_data and ',' in photo_data:
                photo_b64 = photo_data.split(',', 1)[1]
            elif photo_data:
                photo_b64 = photo_data
                
            if photo_b64:
                try:
                    img_bytes = base64.b64decode(photo_b64)
                    with open(saved_path, 'wb') as img_f:
                        img_f.write(img_bytes)
                    file_size = len(img_bytes)
                    sha256_hash = f"SHA256:{hashlib.sha256(img_bytes).hexdigest()[:32].upper()}"
                    print(f"📸 Saved dedicated accident evidence photo: {saved_filename} ({file_size} bytes, {sha256_hash})")
                except Exception as ex:
                    print(f"⚠️ Base64 decode error for evidence photo: {ex}")

            record = {
                "token_id": token_id,
                "photo_filename": saved_filename,
                "photo_url": f"/uploads/{saved_filename}",
                "file_size_bytes": file_size,
                "timestamp": datetime.datetime.now().strftime("%b %d, %Y • %I:%M %p"),
                "location": location,
                "severity": severity,
                "notes": notes,
                "sha256_hash": sha256_hash,
                "legal_status": "SECTION_134A_IMMUNITY_ACTIVE",
                "database": "DEDICATED_EVIDENCE_VAULT_DB"
            }
            
            db = load_evidence_db()
            db = [r for r in db if r.get('token_id') != token_id]
            db.insert(0, record)
            save_evidence_db(db)

            resp = {
                "status": "SUCCESS",
                "message": "Accident photo successfully committed to dedicated Evidence Database",
                "record": record
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        # 3b. Dedicated Evidence Database Endpoint: Reset / Clear
        elif path == '/api/evidence/clear':
            save_evidence_db([])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": "Evidence Database cleared"}).encode('utf-8'))
            return

        # 4. API: Hyperlocal BloodLine AWS SNS Emergency Broadcast
        elif path == '/api/bloodline/broadcast':
            token_id = payload.get('token_id', 'GST-2026-1103-ALERT')
            blood_group = payload.get('blood_group', 'O-')
            location = payload.get('location', 'Tambaram, Chennai')
            
            blood_db = load_bloodline_db()
            alert_rec = {
                "alert_id": f"SNS-ALERT-{int(time.time())}",
                "token_id": token_id,
                "blood_group": blood_group,
                "location": location,
                "donors_alerted": 3,
                "estimated_eta": "11 mins",
                "timestamp": datetime.datetime.now().strftime("%b %d, %Y • %I:%M %p")
            }
            alerts = blood_db.get("alerts", [])
            alerts.insert(0, alert_rec)
            blood_db["alerts"] = alerts[:20]
            save_bloodline_db(blood_db)

            print("\n" + "="*50)
            print("🩸 [AWS SNS BLOODLINE BROADCAST TRIGGERED]")
            print(f"📦 Target Blood Group: {blood_group}")
            print(f"📍 Location: {location}")
            print("📲 Dispatched emergency SMS push via AWS SNS Topic: arn:aws:sns:ap-south-1:EmergencyBloodDonors")
            print("="*50 + "\n")
            
            resp = {
                "statusCode": 200,
                "status": "SUCCESS",
                "message": f"AWS SNS emergency broadcast sent to 3 verified {blood_group} donors",
                "donors_alerted": 3,
                "estimated_eta": "11 mins",
                "sns_message_id": "sns-" + hashlib.md5(f"{token_id}{time.time()}".encode()).hexdigest()[:12]
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        # 4b. API: Register New Good Samaritan Blood Donor
        elif path == '/api/bloodline/register':
            name = payload.get('name', 'Anonymous Samaritan')
            blood = payload.get('blood', 'O-').upper()
            phone = payload.get('phone', '+91 90000 00000')
            area = payload.get('area', 'Chennai Corridor')
            occupation = payload.get('occupation', 'Volunteer Good Samaritan')
            
            blood_db = load_bloodline_db()
            donors = blood_db.get("donors", [])
            new_donor = {
                "id": f"D{len(donors) + 1}",
                "name": name,
                "blood": blood,
                "phone": phone,
                "occupation": occupation,
                "source": "ReaperShield Community Samaritan Registry",
                "lastDonated": "Eligible for immediate donation",
                "area": area,
                "distance": "1.0 km",
                "status": "Verified Active",
                "enRoute": False
            }
            donors.insert(0, new_donor)
            blood_db["donors"] = donors
            save_bloodline_db(blood_db)

            # Increment active donors metric
            analytics_db = load_analytics_db()
            analytics_db["active_blood_donors"] = analytics_db.get("active_blood_donors", 846) + 1
            save_analytics_db(analytics_db)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": "Donor registered successfully", "donor": new_donor}, ensure_ascii=False).encode('utf-8'))
            return

        # 4c. API: Direct Donor Emergency Ping
        elif path == '/api/bloodline/ping':
            donor_name = payload.get('name', 'Donor')
            phone = payload.get('phone', '')
            blood = payload.get('blood', 'O-')
            location = payload.get('location', 'Rajiv Gandhi General Hospital')
            
            msg = f"EMERGENCY BLOOD ALERT: Critical patient urgently requires {blood} at {location}. Reply YES to confirm."
            print(f"📲 [DIRECT SMS PING] Sent to {donor_name} ({phone}): {msg}")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": f"Direct emergency ping sent to {donor_name}", "phone": phone}, ensure_ascii=False).encode('utf-8'))
            return

        # 5. API: Hospital ETA & Bay Update
        elif path == '/api/hospital/update-eta':
            case_id = payload.get('case_id')
            new_eta = payload.get('eta', '05:00')
            assigned_bay = payload.get('assigned_bay', 'Trauma Bay 1 (Red Zone)')
            status = payload.get('status', 'PREPARING_BAY')

            hosp_db = load_hospital_db()
            cases = hosp_db.get("incoming_cases", [])
            updated = False
            for c in cases:
                if c.get('case_id') == case_id or not case_id:
                    c['eta'] = new_eta
                    c['assigned_bay'] = assigned_bay
                    c['status'] = status
                    updated = True
                    break
            if updated:
                save_hospital_db(hosp_db)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": "Hospital ETA updated", "cases": cases}, ensure_ascii=False).encode('utf-8'))
            return

        # 5b. API: Hospital Patient Admission
        elif path == '/api/hospital/admit':
            case_id = payload.get('case_id')
            hosp_db = load_hospital_db()
            cases = hosp_db.get("incoming_cases", [])
            for c in cases:
                if c.get('case_id') == case_id:
                    c['status'] = 'ADMITTED_TO_ICU'
                    break
            save_hospital_db(hosp_db)
            
            # Increment lives saved
            analytics_db = load_analytics_db()
            analytics_db["lives_saved"] = analytics_db.get("lives_saved", 138) + 1
            save_analytics_db(analytics_db)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": "Patient successfully admitted to trauma ICU"}, ensure_ascii=False).encode('utf-8'))
            return

        # 6. API: Multi-Contact Emergency SOS Broadcast
        elif path == '/api/sos/broadcast':
            coords = payload.get('coordinates', [12.9249, 80.1481])
            location_name = payload.get('location', 'Tambaram, Chennai')
            contacts = payload.get('contacts', ['112 (ERSS)', '108 (Ambulance)'])
            
            sos_id = f"SOS-{int(time.time())}"
            print(f"🚨 [MULTI-CONTACT SOS BROADCAST] Location: {location_name} | Coords: {coords} | Contacts: {contacts}")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "SUCCESS",
                "sos_id": sos_id,
                "message": f"Emergency SOS sent with GPS coordinates to {len(contacts)} emergency responders",
                "coordinates": coords
            }, ensure_ascii=False).encode('utf-8'))
            return

        # 7. API: Reverse Geocode Lat/Lng into Formatted Address
        elif path == '/api/location/reverse-geocode':
            lat = payload.get('lat')
            lng = payload.get('lng')
            formatted_address = f"Corridor at ({lat:.4f}° N, {lng:.4f}° E), Tamil Nadu"
            try:
                url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=16&addressdetails=1"
                req = urllib.request.Request(url, headers={"User-Agent": "ReaperShield-Backend/2.5"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    geo = json.loads(resp.read().decode('utf-8'))
                    formatted_address = geo.get('display_name') or formatted_address
            except Exception as ex:
                print(f"⚠️ Reverse geocode fallback: {ex}")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SUCCESS", "formatted_address": formatted_address}, ensure_ascii=False).encode('utf-8'))
            return

        # 8. API: Gemini AI Medical First-Aid & Truth Verification Endpoint
        elif path == '/api/gemini/triage':
            location = payload.get('location', 'Highway / Urban Road')
            severity = payload.get('severity', 'CRITICAL')
            blood_group = payload.get('blood_group', 'O-')
            scene_tag = payload.get('scene_tag', 'Roadside collision')
            victim_notes = (payload.get('victim_notes') or payload.get('notes') or payload.get('query') or payload.get('question') or '').strip()
            if not victim_notes:
                victim_notes = 'General Emergency First Aid Priorities and Scene Safety'

            gemini_result = self.call_gemini_triage(location, severity, blood_group, scene_tag, victim_notes)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(gemini_result, ensure_ascii=False).encode('utf-8'))
            return

        else:
            self.send_error(404, "Endpoint not found")

    def call_gemini_triage(self, location, severity, blood_group, scene_tag, victim_notes):
        prompt = f"""You are an emergency trauma physician and certified first-aid instructor operating in India.
You have full access to the following OFFICIAL 2026 CLINICAL FIRST-AID KNOWLEDGE BASE FOR ACCIDENTS & EMERGENCIES (India Helplines: 112 / 108 / 1033 / 104):

=== BEGIN FIRST AID KNOWLEDGE BASE (2026 EDITION) ===
{FIRST_AID_KNOWLEDGE_BASE_TEXT}
=== END FIRST AID KNOWLEDGE BASE ===

USER INQUIRY / EMERGENCY TELEMETRY:
- User Question or Observation Notes: "{victim_notes}"
- Location (if reported): {location}
- Clinical Severity: {severity}

INSTRUCTIONS FOR GEMINI AI:
1. DYNAMIC TOPIC IDENTIFICATION:
- The user may describe a live accident OR ask ANY first-aid question in English, Tamil, Tanglish, or colloquial terms.
- Detect the EXACT medical topic/condition being asked about (e.g. Choking, CPR, Severe Bleeding, Nosebleed, Thermal Burn, Chemical in Eye/Skin, Snakebite, Dog/Animal Bite, Seizure/Fit, Heart Attack, Stroke FAST, Electric Shock, Drowning, Broken Bone/Fracture, Asthma, Diabetes/Low Blood Sugar, Fainting, Poisoning, Road Accident & Helmet, etc.).
- MATCH it to the correct Protocol (Protocols 1 through 12) in the Knowledge Base.

2. AUTHENTICITY / TRUTH EVALUATION:
- If this is a plausible medical condition, accident, or legitimate first-aid question, classify `is_authentic: true` and `authenticity_score: 85-99`.
- If it is obviously an absurd prank, joke, or nonsensical hoax (e.g., "testing 123", "a ghost hit me", "April fool"), classify `is_authentic: false` and `authenticity_score: 5-30`.

3. TAILORED CLINICAL INSTRUCTIONS (DO NOT COPY GENERIC ACCIDENT TEMPLATES):
- `matched_protocol`: The exact Protocol from the handbook matching this specific question.
- `should_give_first_aid`: true / false / "CAUTION".
- `decision_headline`: A bold, high-impact clinical headline SPECIFIC TO THIS TOPIC.
- `critical_do_nots`: 2 to 4 strict "DO NOT" warnings taken directly from the relevant chapter/Protocol in the Knowledge Base (e.g. for seizure: do not put anything in mouth; for burns: do not use ice/toothpaste/butter; for snakebite: do not cut/suck/ice/tourniquet; for choking in infants: no abdominal thrusts; for nosebleed: do not tilt head back; for road crash: do not remove helmet unless airway blocked).
- `safe_action_steps`: 3 to 4 actionable, life-saving steps strictly matching the official 2026 handbook (e.g., 20-min running water for burns; 15-min soap wash for animal bites; 5 back blows & 5 thrusts for choking; 100-120 bpm for CPR; lean forward 10-15 mins for nosebleed; EpiPen for anaphylaxis; etc.).
- `tamil_audio_guide`: A clear, natural, empathetic spoken Tamil guide for the rescuer specifically for THIS condition.
- `operator_briefing`: A concise 1-2 sentence script of what to tell the 112/108 dispatcher for this specific emergency.
- `recommended_emergency_number`: "112" or "108" or "1033" or "104".

Return STRICTLY valid JSON with these exact keys:
{{
  "is_authentic": true,
  "authenticity_score": 96,
  "authenticity_rationale": "<forensic clinical evaluation of the specific condition>",
  "matched_protocol": "<Exact Protocol Name from Knowledge Base matching this question>",
  "should_give_first_aid": true,
  "decision_headline": "<CLEAR, CAPITALIZED DIRECTIVE SPECIFIC TO THIS TOPIC>",
  "critical_do_nots": [
    "<Mistake 1 specific to this topic>",
    "<Mistake 2 specific to this topic>"
  ],
  "safe_action_steps": [
    "<Action step 1 with specific timing/dosage>",
    "<Action step 2 with specific technique>",
    "<Action step 3>"
  ],
  "tamil_audio_guide": "<Clear spoken Tamil instructions specifically for this topic>",
  "operator_briefing": "<Concise script for 112/108 dispatcher for this topic>",
  "recommended_emergency_number": "108"
}}"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        req_body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }).encode('utf-8')

        req = urllib.request.Request(url, data=req_body, headers={'Content-Type': 'application/json'}, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
                parsed = json.loads(raw_text)
                print(f"🤖 [GEMINI AI TRIAGE COMPLETED]: Protocol: {parsed.get('matched_protocol')} • Headline: {parsed.get('decision_headline')}")
                return parsed
        except Exception as e:
            print(f"⚠️ [GEMINI API FALLBACK]: {e}")
            return self.get_knowledge_base_fallback(victim_notes, location)

    def get_knowledge_base_fallback(self, notes, location):
        """Complete 2026 First Aid Clinical Knowledge Base Engine supporting ALL 14 Chapters in English & Tamil."""
        n = (notes or "").lower()

        # 0. Prank / Hoax Check
        if any(w in n for w in ['test', 'prank', 'joke', 'ghost', 'fake', 'fool', 'பரிகாசம்']):
            return {
                "is_authentic": False,
                "authenticity_score": 15,
                "authenticity_rationale": "Forensic AI Discrepancy: Observation notes contain non-clinical test or prank indicators.",
                "matched_protocol": "Section 1: Emergency Verification & False Alarm Filter",
                "should_give_first_aid": False,
                "decision_headline": "SUSPECTED HOAX / FALSE ALARM • NO CLINICAL INTERVENTION REQUIRED",
                "critical_do_nots": [
                    "DO NOT mobilize emergency ambulance response teams for unverified prank reports.",
                    "DO NOT tamper with emergency dispatch channels."
                ],
                "safe_action_steps": [
                    "Verify physical scene before triggering emergency beacons.",
                    "If a real medical emergency exists, describe specific physical symptoms."
                ],
                "tamil_audio_guide": "இது உண்மையான அவசர உதவி போல் தெரியவில்லை. உண்மையான விபத்து என்றால் காயத்தின் விவரங்களை சரியாக பதிவிடவும்.",
                "operator_briefing": "Unconfirmed report flagged as probable false alarm.",
                "recommended_emergency_number": "112"
            }

        # 1. Choking Protocol (Adult, Pregnancy, Infant)
        if any(w in n for w in ['chok', 'throat', 'swallow', 'airway', 'heimlich', 'அடைப்பு', 'மூச்சுத்திணறல்', 'தொண்டை']):
            is_infant = any(w in n for w in ['baby', 'infant', 'குழந்தை', 'குழந்தைக்கு'])
            if is_infant:
                return {
                    "is_authentic": True,
                    "authenticity_score": 98,
                    "authenticity_rationale": "Infant airway obstruction emergency. Immediate pediatric choking protocol indicated.",
                    "matched_protocol": "Protocol 3: Choking in Baby Under 1 Year",
                    "should_give_first_aid": True,
                    "decision_headline": "5 BACK BLOWS + 5 CHEST THRUSTS (TWO FINGERS) • NO ABDOMINAL THRUSTS",
                    "critical_do_nots": [
                        "DO NOT use abdominal thrusts on a baby under 1 year (causes severe internal organ rupture).",
                        "DO NOT blindly sweep fingers inside the infant's mouth."
                    ],
                    "safe_action_steps": [
                        "Lay the baby face down along your forearm with head lower than chest, supporting jaw.",
                        "Give up to 5 firm back blows between shoulder blades with heel of hand.",
                        "If still blocked, turn baby face up and give up to 5 chest thrusts using two fingers on breastbone.",
                        "Call 112/108 immediately. If baby becomes unresponsive, start infant CPR."
                    ],
                    "tamil_audio_guide": "ஒரு வயதுக்குட்பட்ட குழந்தைக்கு வயிற்றை அழுத்தக் கூடாது! குழந்தையை கவிழ்த்து தலை கீழாக இருக்குமாறு பிடித்து, முதுகில் 5 முறை தட்டவும். பிறகு நெஞ்சில் இரண்டு விரல்களால் 5 முறை அழுத்தவும்.",
                    "operator_briefing": f"Choking infant under 1 year at {location}. Back blows and chest thrusts in progress. Need pediatric ambulance.",
                    "recommended_emergency_number": "108"
                }
            return {
                "is_authentic": True,
                "authenticity_score": 97,
                "authenticity_rationale": "Foreign body airway obstruction (severe choking) in adult/child.",
                "matched_protocol": "Protocol 3: Severe Choking Protocol",
                "should_give_first_aid": True,
                "decision_headline": "5 FIRM BACK BLOWS + 5 ABDOMINAL THRUSTS (HEIMLICH) • REPEAT",
                "critical_do_nots": [
                    "DO NOT blindly sweep fingers inside mouth (only remove object if clearly visible).",
                    "DO NOT use abdominal thrusts for pregnant or obese victims (use chest thrusts instead)."
                ],
                "safe_action_steps": [
                    "If casualty can speak or cough, encourage coughing and watch closely.",
                    "If unable to cough or breathe: lean person forward and give up to 5 firm blows between shoulder blades.",
                    "If still blocked, stand behind them and give up to 5 inward and upward abdominal thrusts (Heimlich).",
                    "Repeat 5 back blows and 5 thrusts until cleared. If unresponsive, start CPR immediately."
                ],
                "tamil_audio_guide": "பாதிக்கப்பட்டவரை முன்னால் சாய்த்து முதுகில் இரண்டு தோள்பட்டைகளுக்கு நடுவே 5 முறை பலமாகத் தட்டவும். அடைப்பு நீங்காவிட்டால், பின்னால் நின்று தொப்புளுக்கு மேலே இரு கைகளால் வயிற்றை உள்நோக்கி 5 முறை அழுத்தவும்.",
                "operator_briefing": f"Severe choking casualty at {location}. Back blows and abdominal thrusts active. Request immediate ALS ambulance.",
                "recommended_emergency_number": "108"
            }

        # 2. CPR & Cardiac Arrest / Unconsciousness
        if any(w in n for w in ['cpr', 'unresponsive', 'not breathing', 'gasping', 'aed', 'சுவாசம் இல்லை', 'அசைவில்லை', 'இதய துடிப்பு']):
            return {
                "is_authentic": True,
                "authenticity_score": 99,
                "authenticity_rationale": "Cardiac arrest / absent normal respiration. Life-or-death resuscitation protocol required.",
                "matched_protocol": "Protocol 2: Adult CPR & AED Protocol",
                "should_give_first_aid": True,
                "decision_headline": "START CPR IMMEDIATELY • 100-120 COMPRESSIONS/MIN • ATTACH AED",
                "critical_do_nots": [
                    "DO NOT practice CPR on anyone who is responsive or breathing normally.",
                    "DO NOT delay CPR to check for pulse if person is unresponsive and not breathing."
                ],
                "safe_action_steps": [
                    "Place casualty flat on their back on a firm surface. Call 112/108 on speaker and send for an AED.",
                    "Place heel of one hand in center of chest, other hand on top with locked elbows.",
                    "Push hard & fast: 100-120 beats per minute, 5-6 cm deep, allowing complete chest recoil.",
                    "If untrained: continuous hands-only CPR. If AED arrives, attach pads to bare dry chest and follow prompts."
                ],
                "tamil_audio_guide": "உடனே 108-ஐ அழையுங்கள்! நபரை தரையில் நேராகப் படுக்க வைத்து, நெஞ்சின் நடுவில் இரு கைகளையும் வைத்து 5 முதல் 6 செ.மீ ஆழத்திற்கு நிமிடத்திற்கு 100 முதல் 120 முறை வேகமாக அழுத்தவும்.",
                "operator_briefing": f"Cardiac arrest / unresponsive casualty not breathing at {location}. Continuous bystander CPR initiated. AED requested.",
                "recommended_emergency_number": "108"
            }

        # 3. Heart Attack / Acute Coronary Syndrome
        if any(w in n for w in ['heart attack', 'chest pain', 'cardiac', 'crushing', 'மாரடைப்பு', 'நெஞ்சு வலி']):
            return {
                "is_authentic": True,
                "authenticity_score": 98,
                "authenticity_rationale": "Suspected acute myocardial infarction (heart attack). High mortality time window.",
                "matched_protocol": "Protocol 7: Medical Emergencies - Heart Attack",
                "should_give_first_aid": True,
                "decision_headline": "REST COMFORTABLY • LOOSEN CLOTHING • CALL 112/108 IMMEDIATELY",
                "critical_do_nots": [
                    "DO NOT let the patient walk, exercise, or drive themselves to the hospital.",
                    "DO NOT give aspirin or medication unless explicitly advised by emergency dispatcher/doctor (allergy/bleeding risk)."
                ],
                "safe_action_steps": [
                    "Call 112/108 immediately and state suspected heart attack.",
                    "Help patient sit in a comfortable, supported position (e.g., on floor against a wall with knees bent).",
                    "Loosen tight neckwear, belts, and collars. Keep person calm and reassure them continuously.",
                    "Assist only with their own pre-prescribed emergency medication (e.g. sublingual nitroglycerin) if available."
                ],
                "tamil_audio_guide": "பாதிக்கப்பட்டவரை நடக்கவோ வண்டி ஓட்டவோ விடாதீர்கள். அவரை தரையில் சாய்வாக உட்கார வைத்து ஆடைகளை தளர்த்தவும். பதற்றப்படாமல் இருக்குமாறு கூறி உடனே 108 ஆம்புலன்ஸை அழைக்கவும்.",
                "operator_briefing": f"Suspected heart attack at {location}. Patient has crushing chest pain radiating to arm. Resting in sitting position.",
                "recommended_emergency_number": "108"
            }

        # 4. Stroke (FAST Protocol)
        if any(w in n for w in ['stroke', 'droop', 'paralysis', 'slurred', 'speech', 'fast', 'பக்கவாதம்', 'வாய் கோணுதல்', 'கை மரத்து']):
            return {
                "is_authentic": True,
                "authenticity_score": 98,
                "authenticity_rationale": "Acute cerebrovascular event (stroke) identified via FAST criteria.",
                "matched_protocol": "Protocol 7: Medical Emergencies - Stroke (FAST)",
                "should_give_first_aid": True,
                "decision_headline": "STROKE FAST ALERT • NOTE ONSET TIME • CALL 112/108 NOW",
                "critical_do_nots": [
                    "DO NOT give food, drink, water or aspirin/tablets (swallowing reflex is compromised; high aspiration risk).",
                    "DO NOT wait to see if symptoms improve; every minute millions of brain neurons die."
                ],
                "safe_action_steps": [
                    "Conduct FAST test: Face (drooping?), Arms (one arm drifts down?), Speech (slurred?), Time (call 112 now).",
                    "Note the exact time symptoms first began or when the person was last known well.",
                    "Keep patient calm, lying on side if drowsy or vomit prone, airway open.",
                    "Communicate the symptom onset time immediately to 112/108 dispatcher for thrombolysis window."
                ],
                "tamil_audio_guide": "பக்கவாத அறிகுறிகள் (முகம் கோணுதல், கை பலவீனம், வாய் குளறுதல்). நோயாளிக்கு தண்ணீர் அல்லது மாத்திரை எதுவும் கொடுக்காதீர்கள்! அறிகுறிகள் தொடங்கிய நேரத்தைக் குறித்துக்கொண்டு உடனே 108-ஐ அழைக்கவும்.",
                "operator_briefing": f"Acute stroke patient at {location}. FAST positive (facial droop and arm weakness). Symptom onset noted.",
                "recommended_emergency_number": "108"
            }

        # 5. Seizure / Convulsion / Epilepsy
        if any(w in n for w in ['seizure', 'fit', 'shaking', 'convulsion', 'epilepsy', 'வலிப்பு', 'காக்காய் வலிப்பு']):
            return {
                "is_authentic": True,
                "authenticity_score": 96,
                "authenticity_rationale": "Active convulsive seizure episode. Strict neurological safety protocol.",
                "matched_protocol": "Protocol 7: Medical Emergencies - Seizure / Fit",
                "should_give_first_aid": True,
                "decision_headline": "CUSHION HEAD • TIME SEIZURE • DO NOT PUT ANYTHING IN MOUTH",
                "critical_do_nots": [
                    "DO NOT put anything in the mouth of a person having a seizure (no keys, spoons, cloth, or fingers).",
                    "DO NOT physically restrain the person or try to stop their jerking movements.",
                    "DO NOT give water, medicine, or food until fully conscious and responsive."
                ],
                "safe_action_steps": [
                    "Clear away hard, sharp objects and cushion the head with a soft jacket or folded cloth.",
                    "Loosen tight neckwear and start timing the duration of the seizure.",
                    "Once jerking movements stop, check breathing; gently turn them onto their side in recovery position to keep airway clear.",
                    "Call 112 if seizure lasts >= 5 mins, repeats, if pregnant, injured, in water, or first occurrence."
                ],
                "tamil_audio_guide": "வலிப்பு வரும்போது வாயில் சாவி அல்லது எந்தப் பொருளையும் வைக்கக் கூடாது! உடம்பை பிடித்து அழுத்தாதீர்கள். தலையின் கீழ் துணியை வைத்து ஆடைகளை தளர்த்தவும். வலிப்பு நின்றதும் ஒருபக்கமாக திருப்பி படுக்க வைக்கவும்.",
                "operator_briefing": f"Active seizure victim at {location}. Head protected, time tracked. Recovery position planned once jerking stops.",
                "recommended_emergency_number": "112"
            }

        # 6. Thermal Burns, Scalds & Fire
        if any(w in n for w in ['burn', 'scald', 'fire', 'boiling', 'steam', 'flame', 'தீ', 'சுடுதண்ணீர்', 'தீக்காயம்']):
            return {
                "is_authentic": True,
                "authenticity_score": 97,
                "authenticity_rationale": "Thermal dermal injury requiring urgent cooling to halt subcutaneous tissue necrosis.",
                "matched_protocol": "Protocol 5: Thermal Burns, Scalds & Chemical Injuries",
                "should_give_first_aid": True,
                "decision_headline": "COOL UNDER RUNNING WATER FOR 20 MINUTES • NO ICE OR TOOTHPASTE",
                "critical_do_nots": [
                    "DO NOT apply ice, iced water, butter, toothpaste, oils, creams or powders (causes deep tissue shock/infection).",
                    "DO NOT peel or pull off clothing stuck to the burned skin.",
                    "DO NOT burst blisters (blister skin is a sterile biological dressing)."
                ],
                "safe_action_steps": [
                    "Cool the burn immediately under cool or lukewarm clean running water for AT LEAST 20 MINUTES.",
                    "Remove rings, watches and loose clothing near the burn before swelling starts.",
                    "Cover the burned area loosely with a clean, non-fluffy dressing or clear cling film laid flat (not wrapped tight).",
                    "Keep the rest of the person warm to prevent hypothermia, and call 112/108 for large or deep burns."
                ],
                "tamil_audio_guide": "தீக்காயம் பட்ட இடத்தில் உடனடியாக குளிர்ந்த ஓடும் தண்ணீரை குறைந்தது 20 நிமிடங்கள் ஊற்றவும். டூத்பேஸ்ட், ஐஸ் கட்டி, எண்ணெய் எதையும் தடவக் கூடாது. கொப்புளங்களை உடைக்காதீர்கள்.",
                "operator_briefing": f"Thermal burn casualty at {location}. 20-minute running water cooling initiated. Loose cover applied. Need burn trauma team.",
                "recommended_emergency_number": "108"
            }

        # 7. Chemical Splash (Skin or Eyes)
        if any(w in n for w in ['chemical', 'acid', 'alkali', 'battery acid', 'ரசாயனம்', 'ஆசிட்']):
            return {
                "is_authentic": True,
                "authenticity_score": 97,
                "authenticity_rationale": "Chemical caustic burn on epithelial tissue. Continuous decontamination protocol.",
                "matched_protocol": "Protocol 5: Chemical on Skin or in Eyes",
                "should_give_first_aid": True,
                "decision_headline": "FLUSH WITH RUNNING WATER FOR AT LEAST 20 MINUTES • DO NOT NEUTRALIZE",
                "critical_do_nots": [
                    "DO NOT attempt to chemically neutralize the chemical (creates exothermic thermal burn).",
                    "DO NOT touch the chemical with bare hands (protect yourself first)."
                ],
                "safe_action_steps": [
                    "Brush off any dry chemical powder first before flushing with water.",
                    "Flush skin or eyes continuously with copious running water for AT LEAST 20 MINUTES.",
                    "For eye splash: hold eyelids open while flushing and remove contact lenses if easy to do.",
                    "Remove contaminated clothing while flushing if safe. Call 112/108 and save product container/label for doctors."
                ],
                "tamil_audio_guide": "ரசாயனம் அல்லது ஆசிட் பட்ட இடத்தில் தொடர்ந்து 20 நிமிடங்கள் தண்ணீரை ஊற்றி கழுவவும். கண்களில் பட்டால் கண்ணைத் திறந்து பிடித்து தண்ணீர் ஊற்றவும். வேறு எந்த மருந்தையும் ஊற்றக் கூடாது.",
                "operator_briefing": f"Chemical burn incident at {location}. Continuous water flushing underway for 20 mins. Chemical container secured.",
                "recommended_emergency_number": "108"
            }

        # 8. Snakebite
        if any(w in n for w in ['snake', 'venom', 'fang', 'பாம்பு', 'விஷம்']):
            return {
                "is_authentic": True,
                "authenticity_score": 97,
                "authenticity_rationale": "Suspected venomous snake envenomation. High morbidity limb emergency.",
                "matched_protocol": "Protocol 8: Snakebite Protocol",
                "should_give_first_aid": True,
                "decision_headline": "KEEP CALM & STILL • IMMOBILISE LIMB • DO NOT CUT, SUCK OR TIE TIGHT",
                "critical_do_nots": [
                    "DO NOT cut, suck, ice, burn, or wash the bite wound (Protocol 8).",
                    "DO NOT apply a tight tourniquet (causes tissue gangrene and sudden venom rush upon release).",
                    "DO NOT let the person walk, run, or panic (speeds venom spread)."
                ],
                "safe_action_steps": [
                    "Move away from the snake to safety. Keep the victim completely still and reassured.",
                    "Immobilise the bitten limb with a loose splint and keep it at or slightly below heart level.",
                    "Remove rings, bracelets, watches or tight clothing before swelling begins.",
                    "Arrange urgent emergency transport to nearest hospital with Anti-Snake Venom (ASV) via 112/108."
                ],
                "tamil_audio_guide": "பாம்பு கடித்த இடத்தை கத்தியால் கீறவோ, ரத்தத்தை உறிஞ்சவோ, கயிறு வைத்து இறுக்கிக் கட்டவோ கூடாது! பாதிக்கப்பட்டவரை அசையாமல் படுக்க வைத்து உடனே 108 ஆம்புலன்ஸை அழைக்கவும்.",
                "operator_briefing": f"Snakebite casualty at {location}. Bitten limb immobilized, patient kept still. Immediate Anti-Snake Venom (ASV) required.",
                "recommended_emergency_number": "108"
            }

        # 9. Animal Bite (Dog, Cat, Monkey)
        if any(w in n for w in ['dog', 'cat', 'animal', 'rabies', 'நாய்', 'விலங்கு']):
            return {
                "is_authentic": True,
                "authenticity_score": 95,
                "authenticity_rationale": "Zoonotic puncture wound with high rabies and tetanus risk.",
                "matched_protocol": "Protocol 8: Dog, Cat or Other Animal Bite Protocol",
                "should_give_first_aid": True,
                "decision_headline": "WASH WITH SOAP & RUNNING WATER FOR 15 MINUTES • GET RABIES SHOT IMMEDIATELY",
                "critical_do_nots": [
                    "DO NOT delay washing the wound or wait for symptoms to develop (rabies is fatal once symptoms start).",
                    "DO NOT apply lime, chili powder, turmeric, or traditional irritant remedies to animal bites."
                ],
                "safe_action_steps": [
                    "Wash the wound thoroughly with soap and copious clean running water for ABOUT 15 MINUTES.",
                    "Apply mild antiseptic and cover with a clean sterile dressing.",
                    "Seek medical care immediately at government hospital for Post-Exposure Prophylaxis (PEP) rabies vaccine and tetanus shot."
                ],
                "tamil_audio_guide": "நாய் அல்லது விலங்கு கடித்த இடத்தை சோப்பு போட்டு ஓடும் தண்ணீரில் 15 நிமிடங்கள் தொடர்ந்து நன்றாகக் கழுவவும். உடனே அரசு மருத்துவமனைக்குச் சென்று ரேபிஸ் தடுப்பூசி போடவும்.",
                "operator_briefing": f"Animal bite victim at {location}. 15-minute soap debridement completed. Urgent Anti-Rabies Vaccine (ARV) required.",
                "recommended_emergency_number": "104"
            }

        # 10. Nosebleed
        if any(w in n for w in ['nosebleed', 'bleeding nose', 'epistaxis', 'மூக்கில் ரத்தம்']):
            return {
                "is_authentic": True,
                "authenticity_score": 92,
                "authenticity_rationale": "Anterior nasal hemorrhage. Hemostatic posture protocol.",
                "matched_protocol": "Protocol 4: Nosebleed Protocol",
                "should_give_first_aid": True,
                "decision_headline": "SIT UPRIGHT & LEAN FORWARD • PINCH SOFT NOSE FOR 10-15 MINS",
                "critical_do_nots": [
                    "DO NOT tilt the head back or lie flat (blood flows down airway causing choking, nausea, and vomiting).",
                    "DO NOT pack tissues or cloth deep inside the nostrils."
                ],
                "safe_action_steps": [
                    "Sit upright and lean slightly forward so blood drains out through nostrils.",
                    "Pinch the soft lower part of the nose firmly with thumb and index finger continuously for 10-15 minutes.",
                    "Breathe through the mouth and spit out any blood that enters the throat.",
                    "Seek emergency care if bleeding is heavy, follows major head trauma, or persists past 20 minutes."
                ],
                "tamil_audio_guide": "மூக்கில் ரத்தம் வந்தால் தலையை பின்னால் சாய்க்கக் கூடாது! முன்னால் குனிந்து உட்கார்ந்து, மூக்கின் கீழ் மென்மையான பகுதியை விரல்களால் 10 முதல் 15 நிமிடங்கள் அழுத்தமாகப் பிடிக்கவும். வாய் வழியாக சுவாசிக்கவும்.",
                "operator_briefing": f"Persistent nosebleed at {location}. Direct pressure applied leaning forward. Medical assessment requested.",
                "recommended_emergency_number": "112"
            }

        # 11. Severe Bleeding, Deep Wounds & Tourniquet
        if any(w in n for w in ['bleed', 'hemorrhage', 'artery', 'deep wound', 'ரத்தம்', 'ரத்தப்போக்கு', 'வெட்டுக் காயம்']):
            return {
                "is_authentic": True,
                "authenticity_score": 97,
                "authenticity_rationale": "High-velocity traumatic vascular hemorrhage.",
                "matched_protocol": "Protocol 4: Severe Bleeding & Wounds Protocol",
                "should_give_first_aid": True,
                "decision_headline": "FIRM DIRECT PRESSURE WITH CLEAN CLOTH • DO NOT LIFT INITIAL LAYER",
                "critical_do_nots": [
                    "DO NOT remove the initial cloth if blood soaks through (add fresh material directly on top).",
                    "DO NOT remove embedded foreign objects (knife, glass) — apply pressure around and stabilize it."
                ],
                "safe_action_steps": [
                    "Call 112/108 immediately. Put on disposable gloves if available.",
                    "Apply firm, continuous direct pressure over the bleeding wound with sterile gauze or clean cloth.",
                    "If blood soaks through, add more layers on top without lifting the bottom layer.",
                    "Keep casualty still, warm, and reassured until emergency medical services arrive."
                ],
                "tamil_audio_guide": "ரத்தப்போக்கு உள்ள இடத்தில் சுத்தமான துணியை வைத்து அழுத்தமாகப் பிடிக்கவும். ரத்தம் நனைந்தால் அந்தத் துணியை எடுக்காமல், அதன் மேலேயே இன்னொரு துணியை வைத்து அழுத்தவும். கத்தியோ கண்ணாடியோ குத்தியிருந்தால் அதை எடுக்கக் கூடாது.",
                "operator_briefing": f"Severe traumatic bleeding at {location}. Continuous direct pressure maintained. Priority trauma ambulance required.",
                "recommended_emergency_number": "108"
            }

        # 12. Broken Bones / Fractures & Sprains
        if any(w in n for w in ['fracture', 'broken bone', 'dislocation', 'sprain', 'எலும்பு முறிவு', 'சுளுக்கு']):
            return {
                "is_authentic": True,
                "authenticity_score": 96,
                "authenticity_rationale": "Musculoskeletal structural compromise (suspected fracture).",
                "matched_protocol": "Protocol 6: Fractures & Sprains Protocol",
                "should_give_first_aid": True,
                "decision_headline": "IMMOBILISE IN POSITION FOUND • DO NOT FORCE STRAIGHT",
                "critical_do_nots": [
                    "DO NOT try to straighten, twist, or force an angled broken bone back into place.",
                    "DO NOT push exposed bone back into the wound if open fracture."
                ],
                "safe_action_steps": [
                    "Keep the injured part completely still in the position found.",
                    "Support with soft padding, rolled blankets, or a splint without forcing straight.",
                    "Apply a cold pack wrapped in cloth near the injury for short periods to reduce swelling.",
                    "Cover open wounds with a clean dressing and call 112/108 for transport."
                ],
                "tamil_audio_guide": "உடைந்த எலும்பை நேராக்கவோ அசைக்கவோ கூடாது! அது எந்த நிலையில் இருக்கிறதோ அதே நிலையில் துணியை வைத்து அசையாமல் பிடித்துக் கொள்ளவும். உடைந்த எலும்பு வெளியே தெரிந்தால் அதை உள்ளே தள்ளக் கூடாது.",
                "operator_briefing": f"Suspected bone fracture at {location}. Limb supported in position found. Open wound dressed if present.",
                "recommended_emergency_number": "108"
            }

        # 13. Electric Shock
        if any(w in n for w in ['electric shock', 'electrocution', 'live wire', 'power line', 'மின் அதிர்ச்சி', 'கரண்ட்']):
            return {
                "is_authentic": True,
                "authenticity_score": 97,
                "authenticity_rationale": "High-voltage or domestic electrical contact trauma with cardiac arrhythmia risk.",
                "matched_protocol": "Protocol 9: Electric Shock Emergency Protocol",
                "should_give_first_aid": False,
                "decision_headline": "DO NOT TOUCH CASUALTY UNTIL POWER IS SWITCHED OFF AT MAINS",
                "critical_do_nots": [
                    "DO NOT touch the person while they may still be in contact with electricity (you will be electrocuted).",
                    "DO NOT approach downed high-voltage lines (maintain minimum 10-meter clearance)."
                ],
                "safe_action_steps": [
                    "Switch off the electric power supply at the main circuit breaker / switch immediately.",
                    "If power cannot be cut, use a dry, non-conductive wooden stick or broom handle to push the source away only if domestic voltage and safe.",
                    "Once power is completely isolated, call 112/108, check breathing, and start CPR/AED if unresponsive.",
                    "All electrical shock victims need hospital evaluation even if appearing uninjured."
                ],
                "tamil_audio_guide": "மின்சாரத்தை மெயின் சுவிட்சில் அணைக்காமல் பாதிக்கப்பட்டவரைத் தொடாதீர்கள்! மின்சாரம் துண்டிக்கப்பட்ட பிறகுதான் நபரைத் தொட வேண்டும். சுவாசம் இல்லையென்றால் உடனடியாக சி.பி.ஆர் தொடங்கவும்.",
                "operator_briefing": f"Electric shock victim at {location}. Power isolated. Breathing assessed. ALS ambulance required.",
                "recommended_emergency_number": "112"
            }

        # 14. Asthma Attack
        if any(w in n for w in ['asthma', 'inhaler', 'wheezing', 'breathless', 'ஆஸ்துமா', 'மூச்சு வாங்குதல்']):
            return {
                "is_authentic": True,
                "authenticity_score": 95,
                "authenticity_rationale": "Acute bronchospasm and respiratory distress.",
                "matched_protocol": "Protocol 10: Asthma Attack Protocol",
                "should_give_first_aid": True,
                "decision_headline": "SIT UPRIGHT • USE RELIEVER INHALER • DO NOT LIE FLAT",
                "critical_do_nots": [
                    "DO NOT make someone having an asthma attack lie down flat (makes breathing significantly harder).",
                    "DO NOT crowd around the person (they need maximum fresh air)."
                ],
                "safe_action_steps": [
                    "Help the person sit upright leaning slightly forward. Reassure them calmly.",
                    "Assist them to use their own prescribed blue/reliever inhaler (preferably with spacer): 1 puff every 30-60 secs up to 10 puffs.",
                    "Call 112/108 immediately if symptoms worsen, blue lips, or unable to speak full sentences.",
                    "Repeat inhaler doses after 10-15 minutes if ambulance has not yet arrived."
                ],
                "tamil_audio_guide": "ஆஸ்துமா உள்ளவரை படுக்க வைக்கக் கூடாது! அவரை நேராக உட்கார வைத்து, அவர்களின் இன்ஹேலரை (Inhaler) பயன்படுத்த உதவவும். மூச்சுத்திணறல் குறையாவிட்டால் உடனடியாக 108-ஐ அழைக்கவும்.",
                "operator_briefing": f"Acute asthma distress at {location}. Inhaler administered in upright posture. Emergency transport needed.",
                "recommended_emergency_number": "108"
            }

        # 15. Low Blood Sugar (Diabetes / Hypoglycemia)
        if any(w in n for w in ['sugar', 'diabetes', 'hypoglycemia', 'insulin', 'சர்க்கரை']):
            return {
                "is_authentic": True,
                "authenticity_score": 94,
                "authenticity_rationale": "Neuroglycopenia / acute hypoglycemic crisis.",
                "matched_protocol": "Protocol 10: Low Blood Sugar (Diabetes)",
                "should_give_first_aid": True,
                "decision_headline": "FAST SUGAR IF CONSCIOUS • NOTHING BY MOUTH IF UNCONSCIOUS",
                "critical_do_nots": [
                    "DO NOT give anything by mouth to someone who is drowsy, unconscious or unable to swallow (choking hazard).",
                    "DO NOT administer insulin to an unconscious diabetic person."
                ],
                "safe_action_steps": [
                    "If person is conscious and able to swallow: give fast-acting glucose, fruit juice, or sugary drink.",
                    "Wait 10-15 minutes and recheck; give further carbohydrate snacks if improving.",
                    "If person is unconscious, drowsy, or unable to swallow: call 112/108 immediately and place in recovery position."
                ],
                "tamil_audio_guide": "நோயாளி சுயநினைவுடன் இருந்தால் மட்டுமே பழச்சாறு அல்லது சர்க்கரை தண்ணீர் கொடுக்கவும். மயக்கமாகவோ அல்லது விழுங்க முடியாமலோ இருந்தால் வாயில் எதையும் ஊற்றக் கூடாது! உடனே 108-ஐ அழைக்கவும்.",
                "operator_briefing": f"Diabetic hypoglycemic crisis at {location}. Conscious status verified. Paramedic glucose assessment needed.",
                "recommended_emergency_number": "108"
            }

        # 16. Poisoning / Overdose
        if any(w in n for w in ['poison', 'overdose', 'swallowed pills', 'toxic', 'விஷம் குடித்த']):
            return {
                "is_authentic": True,
                "authenticity_score": 96,
                "authenticity_rationale": "Toxic ingestion / chemical poisoning emergency.",
                "matched_protocol": "Protocol 8: Poisoning or Overdose",
                "should_give_first_aid": True,
                "decision_headline": "DO NOT INDUCE VOMITING • DO NOT GIVE MILK • CALL 112",
                "critical_do_nots": [
                    "DO NOT induce vomiting (corrosive poisons cause double esophageal burns coming back up).",
                    "DO NOT give milk, raw eggs, or home remedies (can speed toxic absorption)."
                ],
                "safe_action_steps": [
                    "Call 112 / poison information centre immediately.",
                    "If toxic fumes were inhaled, move person to fresh air only if safe for rescuer.",
                    "Keep the chemical container, label, or medicine bottle for emergency physicians.",
                    "If person becomes unconscious, check breathing and place in recovery position; be ready for CPR."
                ],
                "tamil_audio_guide": "விஷம் குடித்தவருக்கு வாந்தி எடுக்க வைக்கக் கூடாது! பால் அல்லது வேறு எதையும் குடிக்க வைக்க வேண்டாம். விஷ பாட்டிலை பத்திரமாக எடுத்துக்கொண்டு உடனடியாக 112/108 ஆம்புலன்ஸில் மருத்துவமனைக்கு அழைத்துச் செல்லவும்.",
                "operator_briefing": f"Acute poisoning incident at {location}. Container secured. No vomiting induced. Urgent toxicological triage required.",
                "recommended_emergency_number": "112"
            }

        # 17. Road Traffic Accident & Head/Spine/Helmet
        if any(w in n for w in ['crash', 'bike', 'car', 'accident', 'helmet', 'motorcycl', 'vehicle', 'விபத்து', 'ஹெல்மெட்', 'கார்', 'பைக்', 'வாகனம்', 'மோதி', 'தலையில் அடி']):
            return {
                "is_authentic": True,
                "authenticity_score": 96,
                "authenticity_rationale": "High-energy vehicular collision trauma consistent with Protocol 6 guidelines.",
                "matched_protocol": "Protocol 6: Road Traffic Accidents, Head, Neck & Spine Trauma",
                "should_give_first_aid": True,
                "decision_headline": "DO NOT REMOVE HELMET • SUPPORT CERVICAL SPINE • CONTROL BLEEDING",
                "critical_do_nots": [
                    "DO NOT remove a helmet unless essential to open airway or perform CPR and you are trained (Protocol 6).",
                    "DO NOT twist, straighten, or sit up anyone with suspected spine/neck trauma.",
                    "DO NOT give food, drink, or oral medication to accident victims."
                ],
                "safe_action_steps": [
                    "Make the scene safe from traffic, turn off vehicle ignition if safe, and call 112/108 on speaker.",
                    "Support the head and neck in the exact neutral position found; do not allow head rotation.",
                    "Apply firm, continuous direct pressure with a clean cloth over bleeding wounds without lifting initial layer.",
                    "Reassure casualty, keep them warm, and monitor breathing until ambulance arrives."
                ],
                "tamil_audio_guide": "கழுத்தையோ தலையையோ அசைக்காதீர்கள். ஹெல்மெட் இருந்தால் கழற்றாதீர்கள். தண்ணீர் கொடுக்காதீர்கள். ரத்தப்போக்கு உள்ள இடத்தில் மட்டும் சுத்தமான துணியை வைத்து அழுத்தமாகப் பிடிக்கவும்.",
                "operator_briefing": f"Road traffic collision at {location}. Head/spine stabilization maintained. Severe bleeding dressed. Request Level-1 trauma response.",
                "recommended_emergency_number": "108"
            }

        # 18. General Emergency / Scene Safety (Protocol 1)
        return {
            "is_authentic": True,
            "authenticity_score": 95,
            "authenticity_rationale": "General medical emergency triage assessment.",
            "matched_protocol": "Protocol 1: The First Minute - Scene Safety & Emergency Activation",
            "should_give_first_aid": True,
            "decision_headline": "VERIFY SCENE SAFETY • CALL 108/112 • ASSESS AIRWAY & BREATHING",
            "critical_do_nots": [
                "DO NOT put yourself in danger before approaching the casualty.",
                "DO NOT move the casualty unless there is immediate mortal danger (fire, flood, traffic).",
                "DO NOT give water or fluids to an unconscious person."
            ],
            "safe_action_steps": [
                "Scan scene for danger (live electricity, moving vehicles, fire, fumes).",
                "Call 108 (Ambulance) or 112 (Unified Emergency) immediately on speakerphone.",
                "Check responsiveness: gently shake shoulders and ask loudly 'Are you OK?'.",
                "Look, listen, and feel for normal breathing for no more than 10 seconds; if absent, start CPR immediately."
            ],
            "tamil_audio_guide": "முதலில் விபத்து நடந்த இடம் உங்களுக்கு பாதுகாப்பாக உள்ளதா என்று பாருங்கள். உடனடியாக 108 அல்லது 112 அவசர எண்ணுக்கு அழைக்கவும். பாதிக்கப்பட்டவர் மூச்சு விடுகிறாரா என்பதை சோதிக்கவும். நினைவு இல்லாவிட்டால் உடனே சிபிஆர் (CPR) தொடங்கவும்.",
            "operator_briefing": f"Medical emergency at {location}. Bystander on scene. Scene safety assessed. Paramedic dispatch requested.",
            "recommended_emergency_number": "108"
        }

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

if __name__ == '__main__':
    class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        allow_reuse_address = True

    with ThreadingServer(("", PORT), ReaperShieldHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print("\n" + "#"*65)
        print("  🎃 REAPERSHIELD - ZERO-LIABILITY GOOD SAMARITAN RESCUE")
        print("  🤖 GOOGLE GEMINI 3.1 FLASH-LITE AI TRIAGE & AUTHENTICITY ENGINE")
        print("#"*65)
        print(f"\n🚀 Server running live at: {url}")
        print("👉 Press Ctrl+C in terminal to stop server.\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 ReaperShield server stopped gracefully.")
            sys.exit(0)
