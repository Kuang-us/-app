import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 页面设置 ---
st.set_page_config(page_title="全能资产助手", layout="wide")
st.title("💰 资产管理与记账可视化")
# --- 1. 连接与数据读取 (跳过库插件，直接读 CSV 链接) ---
sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
# 提取表格的基础 ID
base_url = sheet_url.split("/edit")[0]

def load_gsheet_data(worksheet_name):
    # 通过 Google 的 export 接口直接获取 CSV
    csv_url = f"{base_url}/gviz/tq?tqx=out:csv&sheet={worksheet_name}"
    try:
        data = pd.read_csv(csv_url)
        # 如果表是空的，构造一个带表头的 DataFrame
        if data.empty:
            if worksheet_name == "Expenses":
                return pd.DataFrame(columns=["日期", "分类", "金额", "备注"])
            else:
                return pd.DataFrame(columns=["资产项", "类型", "当前余额/价值"])
        return data
    except Exception as e:
        # 如果读取失败，返回空表
        return pd.DataFrame()

# 执行读取
df_exp = load_gsheet_data("Expenses")
df_assets = load_gsheet_data("Assets")

# --- 2. 依然保留 conn 对象用于写入数据 ---
# 写入操作还是用 st-gsheets-connection 最方便
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    # 构造导出 CSV 的直接链接，这种方式最不容易报 400 错误
    url = f"{sheet_base_url}/gviz/tq?tqx=out:csv&sheet={worksheet_name}"
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"无法读取工作表 {worksheet_name}: {e}")
        return pd.DataFrame()

# 调用函数读取两个工作表
df_exp = get_data("Expenses")
df_assets = get_data("Assets")

# 检查是否成功
if df_exp.empty and df_assets.empty:
    st.warning("⚠️ 未能从 Google Sheets 读取到数据，请检查工作表名称是否完全匹配（Expenses 和 Assets）")

# --- 页面 1：日常记账 ---
if menu == "日常记账":
    st.header("📝 录入新支出")
    with st.form("expense_form"):
        col1, col2, col3 = st.columns(3)
        with col1: date = st.date_input("日期")
        with col2: cat = st.selectbox("分类", categories)
        with col3: amt = st.number_input("金额", min_value=0.0)
        note = st.text_input("备注")
        
        if st.form_submit_button("保存到云端"):
            new_data = pd.DataFrame([{"日期": str(date), "分类": cat, "金额": amt, "备注": note}])
            updated_df = pd.concat([df_exp, new_data], ignore_index=True)
            conn.update(worksheet="Expenses", data=updated_df)
            st.success("同步成功！")
            st.rerun()

    st.subheader("最近记录")
    st.dataframe(df_exp.tail(10), use_container_width=True)

# --- 页面 2：资产大盘 ---
elif menu == "资产大盘":
    st.header("🏢 全资产统计")
    
    # 编辑资产数据
    with st.expander("➕ 更新资产价值 (房产、车子、余额等)"):
        asset_name = st.text_input("资产名称 (如：XX银行卡, 某小区房产)")
        asset_type = st.selectbox("类型", ["房产", "车辆", "银行卡", "支付宝", "微信", "股票投资"])
        asset_val = st.number_input("当前价值/余额", min_value=0.0)
        if st.button("更新资产"):
            # 如果资产名存在则更新，不存在则添加
            df_assets = df_assets[df_assets['资产项'] != asset_name]
            new_asset = pd.DataFrame([{"资产项": asset_name, "类型": asset_type, "当前余额/价值": asset_val}])
            df_assets = pd.concat([df_assets, new_asset], ignore_index=True)
            conn.update(worksheet="Assets", data=df_assets)
            st.success(f"{asset_name} 更新成功")
            st.rerun()

    if not df_assets.empty:
        total_wealth = df_assets["当前余额/价值"].sum()
        st.metric("净资产总计", f"¥ {total_wealth:,.2f}")
        
        c1, c2 = st.columns(2)
        with c1:
            fig_asset = px.pie(df_assets, values="当前余额/价值", names="类型", title="资产构成")
            st.plotly_chart(fig_asset)
        with c2:
            st.dataframe(df_assets, use_container_width=True)

# --- 页面 3：对账统计 ---
elif menu == "对账统计":
    st.header("📅 多维度对账统计")
    if df_exp.empty:
        st.info("暂无数据")
    else:
        df_exp['日期'] = pd.to_datetime(df_exp['日期'])
        df_exp['年'] = df_exp['日期'].dt.year
        df_exp['月'] = df_exp['日期'].dt.to_period('M').astype(str)
        df_exp['周'] = df_exp['日期'].dt.isocalendar().week

        mode = st.radio("统计维度", ["按月", "按周", "按年"], horizontal=True)
        
        group_col = "月" if mode == "按月" else ("周" if mode == "按周" else "年")
        
        summary = df_exp.groupby(group_col)["金额"].sum().reset_index()
        fig_trend = px.line(summary, x=group_col, y="金额", title=f"{mode}支出趋势", markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # 分类饼图筛选
        selected_period = st.selectbox(f"选择具体{mode}", summary[group_col].unique())
        period_df = df_exp[df_exp[group_col] == selected_period]
        fig_period_pie = px.sunburst(period_df, path=['分类', '备注'], values='金额', title=f"{selected_period} 支出分布")
        st.plotly_chart(fig_period_pie)



