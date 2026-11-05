# 🎃 ReaperShield | Zero-Liability Good Samaritan & Emergency Escort System
> **"Beating the Reaper. Shielding the Savior."**  
> *A lifesaving civic-tech & emergency trauma coordination system designed to eliminate bystander fear of police harassment & hospital billing liability during the critical Golden Hour of road accidents in India.*

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Legal Compliance](https://img.shields.io/badge/Legal%20Act-Section%20134A%20MVA%201988-amber.svg)](https://morth.nic.in)
[![Supreme Court](https://img.shields.io/badge/Supreme%20Court-WP(C)%20235%2F2012%20Certified-emerald.svg)](https://main.sci.gov.in)
[![AI Engine](https://img.shields.io/badge/AI%20Triage-Google%20Gemini%203.1-cyan.svg)](https://ai.google.dev)
[![AWS Serverless](https://img.shields.io/badge/Backend-AWS%20Serverless%20Architecture-orange.svg)](aws-backend/)

---

## 🚨 The Critical Real-World Challenge
In India, over **150,000 lives are lost annually in road collisions**. Medical statistics prove that **80% of fatalities during the Golden Hour** could be prevented with immediate bystander intervention. However, 84% of bystanders hesitate or flee the scene due to two profound fears:
1. **Fear of Police Interrogation & Legal Entanglement:** Bystanders fear being treated as accused, forced into police interrogation, or repeatedly summoned to criminal court.
2. **Fear of Hospital Billing Demands:** Private and public emergency rooms often pressure the rescuer for immediate cash deposits before treating the unconscious casualty.

> **The Law:** Under **Section 134A of the Motor Vehicles Act, 1988** and the landmark **Supreme Court ruling in WP(C) 235/2012**, Good Samaritans enjoy **100% complete civil and criminal immunity**, cannot be detained, and cannot be forced to pay admission fees. **ReaperShield operationalizes this law directly onto every citizen's smartphone.**

---

## ⚡ Key Features

- **🛡️ 1-Tap Accident Reporting & Beacon Broadcast:**  
  Instantly captures GPS coordinates, clinical severity, and transmits high-priority telemetry to the nearest trauma bay with one tap.

- **📜 Cryptographic Legal Immunity Token (Section 134A):**  
  Generates an official verifiable digital token (`GST-2026-XXXX`) and **Pure Vector SVG QR Code** that police and hospital authorities can scan to verify statutory bystander immunity.

- **🗺️ Interactive Google Maps Swiping Carousel:**  
  Hardware-accelerated horizontal touch-swipe corridor:
  - **Slide 1:** Live Google Maps Driving Route from Tambaram to RGGGH via GST Road & Anna Salai with real road names and navigation.
  - **Slide 2:** High-resolution Google Satellite imagery with aerial corridor overview.
  - **Slide 3:** Rajiv Gandhi Government General Hospital (RGGGH) Trauma Bay 4 entry gate zoom.
  - **Maps App Button:** Direct one-tap launch into the native Google Maps app for voice turn-by-turn navigation.

- **🤖 Google Gemini 3.1 AI Medical Triage Engine:**  
  Integrates with Gemini 3.1 Flash-Lite AI with the **Official 2026 Emergency Clinical First-Aid Knowledge Base (ERSS 112 / GVK EMRI 108 / NHAI 1033)** across 18 trauma scenarios (Adult CPR, Severe Bleeding, Head/Spine/Helmet management, Choking, Thermal Burns, Fractures, etc.).

- **🔊 Tamil & English TTS Audio Guidance:**  
  Synthesizes lifelike emergency Tamil audio instructions so bystanders can administer lifesaving stabilization without reading text.

- **🩸 Hyperlocal BloodLine Broadcast:**  
  Pushes priority O-negative blood donor availability to nearby donor banks and hospital trauma centers.

---

## 🏛️ System Architecture

```
[ Citizen / Rescuer Mobile ]               [ Level-1 Trauma Command Center ]
            │                                             │
            ├───────────────► [ API Gateway ] ◄───────────┤
            │                        │
            ▼                        ▼
[ Client-Side Engine ]       [ AWS Serverless ]
  • Offline SVG QR Code       • Lambda Dispatch Handler
  • Google Maps Carousel      • DynamoDB (GoodSamaritanTokens)
  • Web Speech Audio API      • S3 (Accident Scene Evidence)
  • 12 Clinical Protocols     • SNS (Emergency Physician Push)
                              • Gemini 3.1 AI Triage Engine
```

---

## 🚀 Quick Start (Local Run in 5 Seconds)

No complex build tools or npm installation required. ReaperShield runs on pure Python 3.8+:

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/reaper-shield.git
cd reaper-shield

# 2. Start the local server
python server.py
```

Open your browser:
- **On PC / Laptop:** [http://localhost:8000/](http://localhost:8000/)
- **On Mobile Phone (Same Wi-Fi):** `http://<your-pc-ip>:8000/`

---

## 🌐 Deploy to GitHub Pages (100% Free Hosting)

You can host this entire web application live on GitHub Pages with 1 click:

1. Push this repository to GitHub.
2. Go to **Settings** ➔ **Pages** (under Code and automation).
3. Under **Branch**, select `main` and folder `/ (root)`.
4. Click **Save**!
5. Your live global HTTPS site will be available at:  
   `https://<your-username>.github.io/reaper-shield/`

---

## ☁️ Deploy AWS Cloud Backend

Inside the [`aws-backend/`](aws-backend/) folder:

1. **Option 1 (1-Click AWS Console):**  
   Upload [`template.json`](aws-backend/template.json) or [`template.yaml`](aws-backend/template.yaml) directly to **AWS CloudFormation Console (Mumbai `ap-south-1`)**.

2. **Option 2 (Automated Script):**  
   Run:
   ```bash
   cd aws-backend
   python deploy_aws.py
   ```

---

## 📄 License
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

*Dedicated to zero-liability Good Samaritans saving lives across India.*
