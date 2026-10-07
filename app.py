import os
import json
from PIL import Image
import pandas as pd
import streamlit as st
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv
from typing import Literal

from database import init_db, insert_scanned_record, fetch_all_records

load_dotenv()

# Initialize Database Schema
init_db()

# Pydantic Schema for Strict Extraction
class ReceiptExtraction(BaseModel):
    merchant_name: str = Field(description="Name of vendor, store, or issuer")
    document_type: Literal["Receipt", "Invoice", "Bill", "Ticket", "Other"] = Field(
        description="Categorize the document accurately. If it is not a receipt, invoice, bill, or ticket, you MUST select 'Other'."
    )
    document_date: str = Field(description="DD-MM-YYYY or readable transaction date")
    total_amount: float = Field(description="Total monetary value charged")
    tax_amount: float = Field(default=0.0, description="Tax or VAT amount charged")
    currency: str = Field(default="USD", description="Currency symbol or code (USD, NGN, EUR, etc.)")
    payment_method: str = Field(default="Unknown", description="Cash, Credit Card, Transfer, etc.")
    category: str = Field(description="Meals, Travel, Utilities, Office Supplies, etc.")
    raw_summary: str = Field(description="Brief itemized summary of key lines purchased")


def extract_receipt_data(image: Image.Image) -> ReceiptExtraction:
    """Send image bytes to Google Gemini API for structured OCR parsing."""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        st.error("Missing GEMINI_API_KEY. Add it to your .env file.")
        st.stop()

    client = genai.Client(api_key=gemini_api_key)

    prompt = (
        "You are an expert document extraction engine. "
        "Analyze this image and extract its metadata strictly into the requested JSON schema. "
        "CRITICAL: Evaluate the image type carefully. If the image is a standard text document, "
        "ID card, random photo, or anything that is NOT a financial receipt, invoice, or bill, "
        "you MUST classify 'document_type' as 'Other'."
    )

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[image, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ReceiptExtraction,
            temperature=0.1,
        ),
    )
    return ReceiptExtraction.model_validate_json(response.text)


# Streamlit Layout
st.set_page_config(page_title="SESA: Smart Document & Receipt Scanner", page_icon="🧾", layout="wide")

st.title("🧾 SESA: Smart Document & Receipt Scanner")
st.caption("AI-Powered Information Extraction with Neon PostgreSQL Persistence")

tab1, tab2 = st.tabs(["📤 Scan & Upload", "📊 Online Database Records"])

with tab1:
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("1. Upload Receipt / Document")
        uploaded_file = st.file_uploader(
            "Choose a receipt image (PNG, JPG, JPEG)",
            type=["png", "jpg", "jpeg"]
        )

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Document Preview", use_container_width=True)

            if st.button("⚡ Extract Information with AI", type="primary", use_container_width=True):
                with st.spinner("AI is scanning, parsing, and structuring document text..."):
                    try:
                        extracted: ReceiptExtraction = extract_receipt_data(image)
                        st.session_state["extracted_data"] = extracted.model_dump()
                        st.success("Extraction complete! Verify details on the right.")
                    except Exception as err:
                        st.error(f"Extraction failed: {err}")

    with col_right:
        st.subheader("2. Review & Commit to Database")

        if "extracted_data" in st.session_state:
            data = st.session_state["extracted_data"]

            with st.form("verify_and_save_form"):
                merchant = st.text_input("Merchant / Company", value=data.get("merchant_name", ""))
                doc_options = ["Receipt", "Invoice", "Bill", "Ticket", "Other"]
                extracted_type = data.get("document_type", "Other")
                default_idx = doc_options.index(extracted_type) if extracted_type in doc_options else 4
                
                doc_type = st.selectbox(
                    "Document Type",
                    doc_options,
                    index=default_idx
                )
                doc_date = st.text_input("Document Date", value=data.get("document_date", ""))
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    total = st.number_input("Total Amount", value=float(data.get("total_amount", 0.0)))
                with c2:
                    tax = st.number_input("Tax / VAT", value=float(data.get("tax_amount", 0.0)))
                with c3:
                    curr = st.text_input("Currency", value=data.get("currency", "USD"))

                c4, c5 = st.columns(2)
                with c4:
                    pay_method = st.text_input("Payment Method", value=data.get("payment_method", "Cash"))
                with c5:
                    cat = st.text_input("Category", value=data.get("category", "General"))

                summary = st.text_area("Itemized Summary", value=data.get("raw_summary", ""), height=100)

                submit_btn = st.form_submit_button("🚀 Send to Neon Database", use_container_width=True)

                if submit_btn:
                    payload = {
                        "merchant_name": merchant,
                        "document_type": doc_type,
                        "document_date": doc_date,
                        "total_amount": total,
                        "tax_amount": tax,
                        "currency": curr,
                        "payment_method": pay_method,
                        "category": cat,
                        "raw_summary": summary,
                    }
                    try:
                        rec_id = insert_scanned_record(payload)
                        st.success(f"Record #{rec_id} successfully stored in Neon PostgreSQL!")
                        del st.session_state["extracted_data"]
                    except Exception as exc:
                        st.error(f"Database insertion failed: {exc}")
        else:
            st.info("Upload an image on the left and click **'Extract Information with AI'** to populate this form.")

with tab2:
    st.subheader("Live Neon Database View")
    if st.button("🔄 Refresh Data"):
        st.rerun()

    try:
        df_records = fetch_all_records()
        if not df_records.empty:
            st.dataframe(df_records, use_container_width=True, hide_index=True)
            
            st.markdown("### 📈 Database Insights")
            
            # 1. Top-Level Metrics
            m1, m2 = st.columns(2)
            m1.metric("Total Documents Processed", len(df_records))
            m2.metric("Top Category", df_records['category'].mode()[0] if not df_records['category'].empty else "N/A")
            
            # 2. Dynamic Currency Totals
            st.markdown("#### Total Value by Currency")
            currency_totals = df_records.groupby("currency")["total_amount"].sum()
            
            if not currency_totals.empty:
                # Create a dynamic number of columns based on how many currencies exist
                metric_cols = st.columns(len(currency_totals))
                for col, (currency, total) in zip(metric_cols, currency_totals.items()):
                    col.metric(label=f"Total ({currency})", value=f"{total:,.2f}")
        else:
            st.info("No records in Neon database yet. Upload a receipt to start!")
    except Exception as exc:
        st.error(f"Could not load records from Neon DB: {exc}")