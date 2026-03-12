import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="全能资产助手", page_icon="💰", layout="wide")

# --- 2. 连接与数据读取逻辑 ---
# 从 Secrets 获取 URL
sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
sheet_base_url = sheet_url.split("/edit")[0].split("/view")[0]

def get_data(worksheet_name):
    """通过 CSV 接口稳健读取数据"""
    url = f"{sheet_base_url}/gviz/tq?tqx=out:csv&sheet={worksheet_name}"
    try:
        data = pd.read_csv(url)
        if data.empty:
            if worksheet_name == "Expenses":
                return pd.DataFrame(columns=["日期", "分类", "金额", "备注"])
            else:
                return pd.DataFrame(columns=["资产项", "类型", "当前余额/价值"])
        return data
    except Exception as e:
        return pd.DataFrame()

# 初始化读取
df_exp = get_data("Expenses")
df_assets = get_data("Assets")

# 初始化连接对象（用于写入）
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. 侧边栏配置 ---
st.sidebar.header("⚙️ 管理面板")

# 自定义分类
default_cats = "🍽️ 餐饮,🚗 交通,🛒 购物,🏠 居住,🎮 娱乐,📦 其他"
custom_categories = st.sidebar.text_input("自定义记账分类（逗号隔开）", default_cats)
categories = [c.strip() for c in custom_categories.split(",")]

# 导航菜单
menu = st.sidebar.radio("跳转页面", ["日常记账", "资产大盘", "对账统计"])

st.sidebar.divider()
st.sidebar.info("💡 提示：数据将实时同步至您的 Google Sheets。")

# --- 4. 页面逻辑：日常记账 ---
if menu == "日常记账":
    st.title("📝 日常记账")
    
    with st.form("expense_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: date = st.date_input("日期", datetime.today())
        with col2: cat = st.selectbox("分类", categories)
        with col3: amt = st.number_input("金额", min_value=0.0, step=0.1)
        note = st.text_input("备注 (选填)")
        
        submit = st.form_submit_button("🚀 保存记录到云端")
        
        if submit:
            if amt <= 0:
                st.error("请输入有效的金额！")
            else:
                new_row = pd.DataFrame([{"日期": str(date), "分类": cat, "金额": amt, "备注": note}])
                # 合并并更新
                updated_df = pd.concat([df_exp, new_row], ignore_index=True)
                conn.update(worksheet="Expenses", data=updated_df)
                st.success("记录已成功同步至云端！")
                st.rerun()

    st.subheader("📋 最近 10 条账单")
    if not df_exp.empty:
        st.dataframe(df_exp.tail(10), use_container_width=True, hide_index=True)
    else:
        st.info("目前还没有账单记录，快去记一笔吧！")

# --- 5. 页面逻辑：资产大盘 ---
elif menu == "资产大盘":
    st.title("🏢 全资产价值统计")
    
    with st.expander("➕ 更新/添加资产 (房产、车子、账户余额)"):
        with st.form("asset_form"):
            a_name = st.text_input("资产名称 (如：支付宝, XX房产)")
            a_type = st.selectbox("资产类型", ["银行卡", "支付宝", "微信", "房产", "车辆", "股票投资", "其他"])
            a_val = st.number_input("当前价值/余额", min_value=0.0)
            if st.form_submit_button("确认更新"):
                # 过滤掉同名旧资产，实现更新效果
                df_assets = df_assets[df_assets['资产项'] != a_name]
                new_asset = pd.DataFrame([{"资产项": a_name, "类型": a_type, "当前余额/价值": a_val}])
                df_assets = pd.concat([df_assets, new_asset], ignore_index=True)
                conn.update(worksheet="Assets", data=df_assets)
                st.success(f"{a_name} 数据已更新！")
                st.rerun()

    if not df_assets.empty:
        total_wealth = df_assets["当前余额/价值"].sum()
        st.metric("总资产价值", f"¥ {total_wealth:,.2f}")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_asset = px.pie(df_assets, values="当前余额/价值", names="类型", hole=0.4, title="资产分布结构")
            st.plotly_chart(fig_asset, use_container_width=True)
        with c2:
            st.write("资产明细表")
            st.dataframe(df_assets, use_container_width=True, hide_index=True)
    else:
        st.warning("暂无资产数据，请先录入。")

# --- 6. 页面逻辑：对账统计 ---
elif menu == "对账统计":
    st.title("📅 多维度支出分析")
    
    if df_exp.empty:
        st.info("暂无数据可供分析。")
    else:
        # 数据预处理
        df_exp['日期'] = pd.to_datetime(df_exp['日期'])
        df_exp['月'] = df_exp['日期'].dt.strftime('%Y-%m')
        df_exp['周'] = df_exp['日期'].dt.isocalendar().week.astype(str)
        df_exp['年'] = df_exp['日期'].dt.year.astype(str)

        tab1, tab2, tab3 = st.tabs(["月度分析", "周统计", "年度概览"])

        with tab1:
            month_list = sorted(df_exp['月'].unique(), reverse=True)
            sel_month = st.selectbox("选择月份", month_list)
            m_df = df_exp[df_exp['月'] == sel_month]
            
            st.metric(f"{sel_month} 总支出", f"¥ {m_df['金额'].sum():,.2f}")
            fig_m = px.bar(m_df.groupby("分类")["金额"].sum().reset_index(), x="分类", y="金额", color="分类", title="本月支出构成")
            st.plotly_chart(fig_m, use_container_width=True)

        with tab2:
            fig_w = px.line(df_exp.groupby("周")["金额"].sum().reset_index(), x="周", y="金额", markers=True, title="每周支出趋势")
            st.plotly_chart(fig_w, use_container_width=True)

        with tab3:
            fig_y = px.sunburst(df_exp, path=['年', '分类'], values='金额', title="年度支出占比 (点击环块可下钻)")
            st.plotly_chart(fig_y, use_container_width=True)
