import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go
from shapely.geometry import Polygon, Point
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib import colors
import io

# --------------------------
# تنظیمات سیستم و داده‌های طبقه‌بندی خاک
# --------------------------
class AppConfig:
    THEMES = {
        "light": {
            "primary": "#FFFFFF",
            "secondary": "#F5F5F5",
            "accent": "#006699",
            "text": "#333333",
            "map_style": "mapbox://styles/mapbox/light-v10"
        },
        "dark": {
            "primary": "#1F2937",
            "secondary": "#374151",
            "accent": "#3B82F6",
            "text": "#F9FAFB",
            "map_style": "mapbox://styles/mapbox/dark-v10"
        }
    }
    
    SOIL_TAXONOMY = {
        "لوم": {
            "class": "Loam",
            "brief": "ترکیب متعادل ماسه، سیلت و رس با زهکشی مناسب و حاصلخیزی عالی",
            "details": """• دامنه pH ایده‌آل: 6.0-7.0
• ظرفیت نگهداری آب: متوسط
• تهویه: بسیار خوب
• مناسب برای بیشتر محصولات کشاورزی"""
        },
        "رسی": {
            "class": "Clay",
            "brief": "ذرات ریز با ظرفیت بالای نگهداری آب و مواد مغذی",
            "details": """• دامنه pH معمول: 5.5-7.5
• چسبندگی بالا هنگام مرطوب بودن
• تهویه ضعیف
• نیاز به زهکشی مناسب"""
        },
        "شنی": {
            "class": "Sandy",
            "brief": "زهکشی سریع با ظرفیت کم نگهداری مواد مغذی",
            "details": """• دامنه pH معمول: 6.5-8.0
• نیاز مکرر به آبیاری
• تهویه عالی
• مناسب برای گیاهان مقاوم به خشکی"""
        },
        "لوم سیلتی": {
            "class": "Silt Loam",
            "brief": "ترکیب با سیلت غالب و بافت نرم",
            "details": """• دامنه pH معمول: 6.0-7.5
• نگهداری آب بالا
• مستعد فشردگی
• نیاز به مدیریت آبیاری دقیق"""
        },
        "لوم شنی": {
            "class": "Sandy Loam",
            "brief": "ترکیب با ماسه غالب و زهکشی خوب",
            "details": """• دامنه pH معمول: 6.5-7.5
• زهکشی سریع
• نیاز به کوددهی مکرر
• مناسب برای سبزیجات ریشه‌ای"""
        },
        "رسی لومی": {
            "class": "Clay Loam",
            "brief": "ترکیبی با رس غالب و کاربردپذیری محدود",
            "details": """• دامنه pH معمول: 6.0-7.0
• چسبندگی متوسط
• نیاز به اصلاح خاک
• مناسب برای غلات"""
        }
    }

    SOIL_COLORS = {
        "لوم": "#8D704B",
        "رسی": "#B74A4A",
        "شنی": "#E3D888",
        "لوم سیلتی": "#A89B8C",
        "لوم شنی": "#C2B280",
        "رسی لومی": "#7E4E4E"
    }

# --------------------------
# تولید داده‌های واقعی‌تر با طبقه‌بندی صحیح
# --------------------------
def generate_soil_data(num=100):
    data = []
    for _ in range(num):
        # تولید درصدهای واقعی با جمع 100
        sand = np.random.randint(0, 100)
        silt = np.random.randint(0, 100 - sand)
        clay = 100 - sand - silt
        
        # تعیین نوع خاک بر اساس مثلث بافت USDA
        soil_type = determine_soil_type(sand, silt, clay)
        
        lat = 35.8400 + np.random.uniform(-0.15, 0.15)
        lon = 50.9391 + np.random.uniform(-0.15, 0.15)
        
        data.append({
            "lat": lat,
            "lon": lon,
            "نوع خاک": soil_type,
            "رنگ": AppConfig.SOIL_COLORS[soil_type],
            "میزان اسیدیته": round(np.random.uniform(5.5, 8.5), 1),
            "هدایت الکتریکی": f"{np.random.uniform(0.5, 4.5):.1f} dS/m",
            "عمق خاک": f"{np.random.randint(30, 150)} cm",
            "ماسه (%)": sand,
            "سیلت (%)": silt,
            "رس (%)": clay
        })
    return pd.DataFrame(data)

def determine_soil_type(sand, silt, clay):
    # طبقه‌بندی بر اساس سیستم USDA
    if (sand > 85 and silt + 1.5*clay < 15):
        return "شنی"
    elif (sand >= 70 and sand <= 85 and silt + 1.5*clay < 15):
        return "لوم شنی"
    elif (clay >= 40 and sand <= 45 and silt <= 40):
        return "رسی"
    elif (clay >= 27 and clay < 40 and sand <= 20):
        return "رسی لومی"
    elif (sand < 50 and silt >= 28 and silt < 50 and clay < 27):
        return "لوم سیلتی"
    elif (sand >= 23 and sand < 52 and silt >= 28 and silt < 50 and clay >= 7 and clay < 27):
        return "لوم"
    else:
        return "لوم"

# --------------------------
# سیستم تحلیل پلی‌گون
# --------------------------
class PolygonAnalyzer:
    @staticmethod
    def points_in_polygon(points, polygon_coords):
        polygon = Polygon(polygon_coords)
        return [Point(p).within(polygon) for p in zip(points.lat, points.lon)]

# --------------------------
# تولید گزارش PDF پیشرفته
# --------------------------
def generate_pdf_report(data, selected_area_data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # استایل‌ها
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]
    
    # هدر گزارش
    title = Paragraph("<para align=center>گزارش کامل تحلیل خاک</para>", title_style)
    title.wrapOn(c, width-100, height)
    title.drawOn(c, 50, height-50)
    
    # اطلاعات کلی
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height-100, f"تعداد نمونه‌ها: {len(selected_area_data)}")
    c.drawString(50, height-120, f"محدوده جغرافیایی: عرض {data['lat'].mean():.4f} - طول {data['lon'].mean():.4f}")
    
    # جدول داده‌ها
    table_data = [["نوع خاک", "میانگین pH", "میانگین EC (dS/m)", "میانگین عمق (cm)"]]
    for soil_type in selected_area_data["نوع خاک"].unique():
        subset = selected_area_data[selected_area_data["نوع خاک"] == soil_type]
        table_data.append([
            soil_type,
            f"{subset['میزان اسیدیته'].mean():.1f}",
            f"{subset['هدایت الکتریکی'].str.extract(r'(\d+\.\d+)')[0].astype(float).mean():.1f}",
            f"{subset['عمق خاک'].str.extract(r'(\d+)')[0].astype(int).mean():.0f}"
        ])
    
    t = Table(table_data, colWidths=[100, 80, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (-1,-1), 'CENTER')
    ]))
    t.wrapOn(c, width-100, height)
    t.drawOn(c, 50, height-250)
    
    # توضیحات خاک‌ها
    y_pos = height-300
    for soil_type in selected_area_data["نوع خاک"].unique():
        desc = AppConfig.SOIL_TAXONOMY.get(soil_type, {})
        text = f"<b>{soil_type}</b> ({desc.get('class', '')}): {desc.get('brief', '')}"
        p = Paragraph(text, body_style)
        p.wrap(width-100, 50)
        p.drawOn(c, 50, y_pos)
        y_pos -= 60
        
    c.save()
    buffer.seek(0)
    return buffer

# --------------------------
# رابط کاربری
# --------------------------
def main():
    st.set_page_config(
        page_title="سامانه تحلیل خاک WSS",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # تنظیم تم و داده‌ها
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    if "drawing_data" not in st.session_state:
        st.session_state.drawing_data = None
    
    current_theme = AppConfig.THEMES[st.session_state.theme]
    df = generate_soil_data(150)

    # استایل سفارشی
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazir:wght@400;700&display=swap');
        * {{ 
            font-family: 'Vazir' !important; 
            direction: rtl !important;
        }}
        .stApp {{ 
            background: {current_theme['primary']};
            color: {current_theme['text']};
        }}
        .header {{
            background: {current_theme['accent']};
            padding: 1.5rem;
            border-radius: 0 0 25px 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .card {{
            background: {current_theme['secondary']};
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }}
    </style>
    """, unsafe_allow_html=True)

    # نوار کناری
    with st.sidebar:
        st.markdown("## تنظیمات")
        st.selectbox("تم", ["light", "dark"], key="theme")
        
        with st.expander("📚 راهنمای استفاده"):
            st.markdown("""
            ### راهنمای سامانه:
            1. **ترسیم پلیگون**: با ابزار کشیدن روی نقشه محدوده مورد نظر را انتخاب کنید
            2. **جدول داده‌ها**: نمونه‌های داخل پلیگون به صورت خودکار آپدیت می‌شود
            3. **مثلث بافت**: ترکیب خاک انتخاب شده را در نمودار مثلثی مشاهده کنید
            4. **گزارش‌گیری**: از بخش تنظیمات گزارش PDF دریافت نمایید
            """)

    # هدر
    st.markdown(f"""
    <div class="header">
        <h1 style="color:{current_theme['primary']}; margin:0; text-align:center">
            🌱 سامانه تحلیل خاک پیشرفته WSS
        </h1>
    </div>
    """, unsafe_allow_html=True)

    # بخش اصلی
    col1, col2 = st.columns([2, 1])

    with col1:
        # نقشه تعاملی
        st.markdown("### نقشه نمونه‌های خاک")
        view_state = pdk.ViewState(
            latitude=35.8400,
            longitude=50.9391,
            zoom=10,
            pitch=45
        )
        
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["lon", "lat"],
            get_radius=150,
            get_fill_color="رنگ",
            pickable=True
        )
        
        polygon_layer = pdk.Layer(
            "PolygonLayer",
            data=[],
            get_polygon="-",
            get_fill_color=[255, 140, 0, 100],
            pickable=False
        )
        
        deck = pdk.Deck(
            map_style=current_theme["map_style"],
            initial_view_state=view_state,
            layers=[layer, polygon_layer],
            tooltip={
                "html": """
                <div style="
                    background: {primary};
                    color: {text};
                    padding: 1rem;
                    border-radius: 5px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                ">
                    <b>نوع خاک:</b> {{نوع خاک}}<br>
                    <b>اسیدیته:</b> {{میزان اسیدیته}}<br>
                    <b>EC:</b> {{هدایت الکتریکی}}<br>
                    <b>عمق:</b> {{عمق خاک}}<br>
                    <b>ترکیب:</b> {{ماسه (%)}}% ماسه, {{سیلت (%)}}% سیلت, {{رس (%)}}% رس
                </div>
                """.format(primary=current_theme["primary"], text=current_theme["text"])
            }
        )
        
        # دریافت داده‌های ترسیم
        selected_data = st.pydeck_chart(deck, key="map")
        
        # تحلیل پلیگون
        if st.session_state.get("map") and "last_active_drawing" in st.session_state.map:
            polygon_coords = st.session_state.map["last_active_drawing"]["geometry"]["coordinates"][0]
            df["در محدوده"] = PolygonAnalyzer.points_in_polygon(df, polygon_coords)
            filtered_df = df[df["در محدوده"]]
            
            st.markdown("### نمونه‌های داخل پلیگون")
            st.dataframe(
                filtered_df[["نوع خاک", "میزان اسیدیته", "هدایت الکتریکی", "عمق خاک"]],
                height=300
            )
            
            # گزارش‌گیری PDF
            if st.button("ایجاد گزارش PDF"):
                pdf_buffer = generate_pdf_report(df, filtered_df)
                st.download_button(
                    label="دانلود گزارش کامل",
                    data=pdf_buffer,
                    file_name="soil_analysis_report.pdf",
                    mime="application/pdf"
                )

    with col2:
        # مثلث بافت خاک با اطلاعات طبقه‌بندی
        st.markdown("### تحلیل مثلث بافت خاک")
        selected_point = st.selectbox(
            "انتخاب نمونه", 
            df.index,
            format_func=lambda x: f"نمونه {x+1} - {df.iloc[x]['نوع خاک']}"
        )
        
        # اطلاعات طبقه‌بندی
        soil_info = AppConfig.SOIL_TAXONOMY.get(df.iloc[selected_point]["نوع خاک"], {})
        
        st.markdown(f"""
        <div class="card">
            <h4>طبقه‌بندی USDA:</h4>
            <p>{soil_info.get('class', '')} - {df.iloc[selected_point]['نوع خاک']}</p>
            
            <h4>ویژگی‌های کلیدی:</h4>
            <p>{soil_info.get('brief', '')}</p>
            
            <h4>خصوصیات شیمیایی:</h4>
            <pre>{soil_info.get('details', '')}</pre>
        </div>
        """, unsafe_allow_html=True)
        
        # نمودار مثلث بافت
        fig = go.Figure(go.Scatterternary({
            'mode': 'markers',
            'a': [df.iloc[selected_point]["ماسه (%)"]],
            'b': [df.iloc[selected_point]["سیلت (%)"]],
            'c': [df.iloc[selected_point]["رس (%)"]],
            'marker': {
                'color': df.iloc[selected_point]["رنگ"],
                'size': 20
            }
        }))
        
        fig.update_layout({
            'ternary': {
                'sum': 100,
                'aaxis': {'title': 'ماسه (%)'},
                'baxis': {'title': 'سیلت (%)'},
                'caxis': {'title': 'رس (%)'}
            },
            'paper_bgcolor': current_theme["primary"],
            'plot_bgcolor': current_theme["secondary"]
        })
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()