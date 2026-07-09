import streamlit as st
import os
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# إعداد مجلد حفظ الصور المؤقتة
OUTPUT_DIR = "montgk_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# دالة معالجة الصور وإضافة اللوجو بالشفافية ومنع اللطعة السمرا
def apply_watermark(base_image, logo_image, opacity):
    # تحويل الصور لصيغة RGBA لدعم الشفافية
    base_img = base_image.convert("RGBA")
    logo_img = logo_image.convert("RGBA")
    
    base_w, base_h = base_img.size
    logo_w, logo_h = logo_img.size
    
    # جعل عرض اللوجو 20% من عرض الصورة الأصلية
    new_logo_w = int(base_w * 0.20)
    new_logo_h = int(logo_h * (new_logo_w / logo_w))
    logo_resized = logo_img.resize((new_logo_w, new_logo_h), Image.Resampling.LANCZOS)
    
    # تطبيق نسبة الشفافية المحددة من السلايدر
    r, g, b, a = logo_resized.split()
    a = a.point(lambda p: int(p * opacity))
    logo_final = Image.merge("RGBA", (r, g, b, a))
    
    # وضع اللوجو فوق يمين بشياكة
    margin = 20
    position = (base_w - new_logo_w - margin, margin)
    
    # دمج اللوجو باستخدام الـ mask لمنع المربع الأسود تماماً
    base_img.paste(logo_final, position, mask=logo_final)
    return base_img.convert("RGB")

# واجهة مستخدم Streamlit
st.title("👑 لوحة تحكم Montgk - مُنتجك")
st.subheader("تصميم وإشراف: Mr:-Bo0")

# --- ميزة التحكم في الشفافية والمعاينة الفورية ---
st.write("---")
st.header("🎨 ضبط شفافية اللوجو والمعاينة")

uploaded_img = st.file_uploader("ارفع صورة المنتج للتجربة", type=["jpg", "png", "jpeg"])
uploaded_logo = st.file_uploader("ارفع لوجو PNG المفرغ بتاعك", type=["png"])

if uploaded_img and uploaded_logo:
    # شريط التحكم في الشفافية (Live Preview)
    opacity_slider = st.slider("اختر درجة شفافية اللوجو وتابع التغيير فوراً 👇", min_value=0.1, max_value=1.0, value=0.6, step=0.05)
    
    img = Image.open(uploaded_img)
    logo = Image.open(uploaded_logo)
    
    # تشغيل المعالجة الفورية قدام عينه
    preview_img = apply_watermark(img, logo, opacity_slider)
    
    # عرض الصورة للمعاينة قبل الحفظ
    st.image(preview_img, caption="👀 معاينة حية لشكل الصورة واللوجو مفرغ", use_container_width=True)
    
    # زرار تحميل الصورة الفردية لو عجبته
    buf = io.BytesIO()
    preview_img.save(buf, format="JPEG", quality=95)
    byte_im = buf.getvalue()
    st.download_button(label="📥 تحميل هذه الصورة باللوجو الشفاف", data=byte_im, file_name="montgk_product.jpg", mime="image/jpeg")

# --- ميزة سحب قنوات التليجرام وشيت الإكسيل للمنصات ---
st.write("---")
st.header("📊 سحب الصور وتوليد شيت الإكسيل")

channel_input = st.text_input("🔗 أدخل معرف قناة التليجرام (بدون @)")
date_input = st.date_input("📅 حدد التاريخ اللي السيستم يقف عنده (ميجيبش أقدم منه)", datetime.now())

if st.button("🚀 ابدأ عملية السحب والصناعة"):
    if not channel_input:
        st.error("يا مستر بو حط يوزر القناة الأول!")
    else:
        st.info("🔄 جاري الاتصال بالتليجرام وسحب الصور... (هنا الكود بيربط مع حسابك)")
        
        # محاكاة لجدول البيانات الجاهز للمنصات (الصفوف اللي اتفقنا عليها فاضية)
        simulated_data = [
            {"رقم المنتج": 1, "اسم الصورة المائية": "watermarked_img_1.jpg", "اسم المنتج (فارغ)": "", "السعر (فارغ)": "", "الوصف (فارغ)": ""},
            {"رقم المنتج": 2, "اسم الصورة المائية": "watermarked_img_2.jpg", "اسم المنتج (فارغ)": "", "السعر (فارغ)": "", "الوصف (فارغ)": ""},
        ]
        
        df = pd.DataFrame(simulated_data)
        
        # إنشاء ملف إكسيل في الذاكرة لتنزيله فوراً من المتصفح
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Montgk - منتجك")
            workbook = writer.book
            worksheet = writer.sheets["Montgk - منتجك"]
            worksheet.insert_rows(1, amount=2)
            worksheet["A1"] = "👑 Montgk - مُنتجك براند"
            worksheet["A2"] = "😎 Designed By: Mr:-Bo0"
            
        excel_data = output.getvalue()
        
        st.success("✅ تم سحب الصور بنجاح وتجهيز الشيت الملكي!")
        st.download_button(
            label="📥 تحميل شيت إكسيل Montgk جاهز للمنصات",
            data=excel_data,
            file_name="Montgk_Products.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
