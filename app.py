import os
import re
import json
import time
import requests
import streamlit as st
import pandas as pd
from io import BytesIO

# ==================== إعدادات المنصة والبراند القديم ====================
st.set_page_config(page_title="Montgk Empire Platform", page_icon="🥷", layout="wide")

# 🔒 التوكن الأصلي بتاعك شغال فوري
BOT_TOKEN = "8685178390:AAEgzrKz2yHW2oeflsZyZMeSN1Nw0da3vvI" 

EXCEL_FILE = "Montgk_Live_Products.xlsx"

# قاعدة بيانات المستوردين (المصنع الأساسي)
IMPORTERS = {
    "BAGH": {"name": "البغدادي للأدوات المنزلية", "margin": 1.25},
    "SHAH": {"name": "الشهاب ستور للاكسسوارات", "margin": 1.20},
    "KANZ": {"name": "الكنز للجملة", "margin": 1.30}
}

def load_excel_data():
    if os.path.exists(EXCEL_FILE):
        try: return pd.read_excel(EXCEL_FILE).to_dict(orient="records")
        except: return []
    return []

def save_to_excel(data_list):
    df = pd.DataFrame(data_list)
    df.to_excel(EXCEL_FILE, index=False)

# ==================== واجهة الويب الشيك ====================
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .brand-header {
        background: linear-gradient(135deg, #111115 0%, #ff4b4b 100%);
        padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 25px;
    }
    .brand-title { color: white; font-size: 36px; font-weight: bold; }
    .brand-sub { color: #e0e0e0; font-size: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="brand-header">
        <div class="brand-title">🥷 Mr:- Bo0 Empire</div>
        <div class="brand-sub">🚀 مـنتـجكـ - Montgk Unified Factory</div>
    </div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📦 مستودع المنتجات", "📋 دفتر المستوردين"])

with tab1:
    st.subheader("📦 جدول المنتجات الكلية")
    products_list = load_excel_data()
    if products_list:
        df_display = pd.DataFrame(products_list)
        st.dataframe(df_display, use_container_width=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_display.to_excel(writer, index=False, sheet_name='Montgk_Products')
        st.download_button(
            label="📥 تحميل شيت الإكسيل",
            data=output.getvalue(),
            file_name="Montgk_Empire_Products.xlsx"
        )
    else:
        st.info("📭 المستودع فاضي حالياً. ابعت الروابط للبوت عشان يسحبها فوري!")

with tab2:
    st.subheader("📋 دفتر أكواد ونسب المستوردين المسجلين")
    df_importers = pd.DataFrame([
        {"كود المستورد": k, "اسم البراند": v["name"], "نسبة الربح المضافة": f"{(v['margin']-1)*100:.0f}%"}
        for k, v in IMPORTERS.items()
    ])
    st.table(df_importers)
    st.success("⚙️ معادلات السحب التلقائي شغالة وزي الفل!")
