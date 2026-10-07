# SESA - Smart Receipt Scanner

SESA is an AI-powered multimodal document extraction application. It leverages a Streamlit web interface, Google Gemini Vision for structured optical character recognition (OCR), and a Neon Serverless PostgreSQL database for data persistence.

This project allows users to upload images of financial documents, automatically extract key metadata (Merchant, Total, Tax, Currency, Category, etc.) using AI, verify the data, and securely store it in a remote database.

## 🏗 System Architecture

![SESA - Smart Receipt Scanner: System Architecture](sesa_svg.drawio.svg)


The SESA system operates through a streamlined flow connecting the client browser, a Dockerized application, and external cloud services:

1. **End User (Web Browser):** Initiates a browser session to upload images, review extracted data forms, and view the metrics dashboard.
2. **Docker Container (`sesa-app`):** The application runs internally on port 8501 and consists of four main components:
   * **Streamlit Web App (`app.py`):** Provides the Upload UI, Review Form, and Dashboard Tab.
   * **Pydantic Schema (`ReceiptExtraction`):** Enforces strict, typed validation on the AI's output.
   * **SQLAlchemy ORM (`database.py`):** Maps data to the `ScannedDocument` model.
   * **Runtime Secrets (`.env`):** Injects the `GEMINI_API_KEY` and `DATABASE_URL` securely at runtime.
3. **Google Gemini API:** The application sends the uploaded image and an extraction prompt to the `gemini-3.8-flash` Vision model, which returns structured JSON containing fields like merchant, amount, tax, and category.
4. **Neon Serverless PostgreSQL:** The SQLAlchemy ORM performs secure SSL INSERT and SELECT operations into the `scanned_documents` table.

**Workflow:**
1. **Frontend:** User uploads a receipt image via the Streamlit UI.
2. **AI Processing:** The image is sent to the Google Gemini Vision API with strict instructions to return a validated JSON schema (Pydantic).
3. **Validation & Editing:** The user reviews the extracted data in the Streamlit form and makes corrections if necessary.
4. **Storage:** The confirmed data is committed to a Neon Serverless PostgreSQL database using SQLAlchemy.
5. **Deployment:** The app is containerized using Docker and hosted on an AWS EC2 instance.

## ✨ Features
- **Multimodal AI Extraction:** Uses `gemini-3.8-flash` to read and parse text directly from images.
- **Strict JSON Enforcement:** Utilizes Pydantic schemas to ensure the AI always returns structured, predictable data.
- **Document Categorization:** Automatically rejects non-financial documents (classifies as "Other").
- **Dynamic Database Insights:** Live view of scanned records with dynamic total calculations grouped by currency.
- **Dockerized & Cloud-Ready:** Easily deployable to AWS EC2 or any Docker-compatible hosting platform.

## 🛠 Tech Stack
- **Frontend/UI:** Streamlit
- **AI/LLM:** Google GenAI SDK (Gemini Vision)
- **Database:** Neon Serverless PostgreSQL
- **ORM:** SQLAlchemy & Psycopg 3
- **Data Handling:** Pandas, Pydantic
- **Containerization:** Docker

## 📂 Folder Structure

```text
.
├── .env                  # Runtime secrets (Not committed to git)
├── .gitignore            # Git exclusion rules
├── Dockerfile            # Container build instructions
├── requirements.txt      # App dependencies
├── database.py           # SQLAlchemy ORM and Neon DB connection logic
├── app.py                # Streamlit Web App and Gemini API integration
└── sesa_svg.drawio.svg   # Architecture diagram
```

## 🚀 Local Setup & Development

### 1. Prerequisites
- Python 3.11+
- A Google AI Studio API Key
- A Neon PostgreSQL Database URL

### 2. Environment Variables
Create a `.env` file in the root of the project. **Do not use quotation marks** around the values, as this ensures compatibility with Docker.

```env
GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
DATABASE_URL=postgresql://user:password@ep-sample-pool.region.aws.neon.tech/neondb?sslmode=require
```

### 3. Run Locally (Virtual Environment)
```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py
```

### 4. Run Locally (Docker)
```bash
# Build the image
docker build -t receipt-scanner .

# Run the container (passing the .env file)
docker run -p 8501:8501 --env-file .env receipt-scanner
```
Access the app at `http://localhost:8501`.

## ☁️ AWS EC2 Deployment Guide

Follow these steps to deploy the application on an AWS EC2 instance.

### 1. EC2 Provisioning
- Launch an **Ubuntu 24.04 LTS** instance (`t3.small` recommended).
- **Security Group:** Allow inbound traffic on:
  - Port `22` (SSH) from your IP.
  - Port `8501` (Custom TCP) from anywhere (`0.0.0.0/0`).

### 2. Server Configuration
SSH into your instance and run the following commands:

```bash
# Update packages and install Docker & Git
sudo apt-get update -y
sudo apt-get install -y docker.io git

# Enable Docker and add current user to docker group
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu
newgrp docker
```

### 3. Clone & Configure
```bash
# Clone this repository
git clone https://github.com/lteTraveller/sesa-receipt-scanner.git
cd sesa-receipt-scanner

# Create the .env file on the server
nano .env
```
*Paste your `GEMINI_API_KEY` and `DATABASE_URL` (without quotes) and save.*

### 4. Build & Run
```bash
# Build the Docker image
docker build -t receipt-scanner .

# Run the container in detached mode with auto-restart
docker run -d --name receipt-scanner-app -p 8501:8501 --env-file .env --restart always receipt-scanner
```

Your app is now live at `http://<ec2-public-ip>:8501`!

## 🐛 Troubleshooting Common Issues


* **`SQLAlchemy URL ArgumentError`**: Remove quotation marks (`"`) from the variables in your `.env` file when using Docker `--env-file`.
* **`429 RESOURCE_EXHAUSTED (Gemini)`**: You have hit the Free Tier rate limit (usually 20 requests/minute). Wait 30 seconds and try again, or add a billing account in Google AI Studio to increase your limits.