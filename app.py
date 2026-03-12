import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# 1. 定义存储数据的文件路径 (使用本地 CSV 文件作为小型数据库)
DATA_FILE = "my_expenses.csv"

# 2. 读取数据的函数
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        # 如果文件不存在，创建一个带表头的空数据框
        return pd.DataFrame(columns=["日期", "分类", "金额", "备注"])

# 3. 保存数据的函数
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 页面基础设置 ---
st.set_page_config(page_title="我的记账本", page_icon="💰", layout="wide")
st.title("💰 个人记账与可视化工具")

# 加载当前数据
df = load_data()

# --- 侧边栏：添加新账单 ---
st.sidebar.header("📝 添加新账单")
with st.sidebar.form("expense_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.today())
    category = st.selectbox("支出分类", ["🍽️ 餐饮", "🚗 交通", "🛒 购物", "🏠 居住", "🎮 娱乐", "📦 其他"])
    amount = st.number_input("金额 (元)", min_value=0.01, step=10.0, format="%.2f")
    note = st.text_input("备注 (选填)")
    submit_button = st.form_submit_button("保存记录")

    # 当用户点击保存按钮时触发
    if submit_button:
        new_record = pd.DataFrame([{
            "日期": str(date),
            "分类": category,
            "金额": amount,
            "备注": note
        }])
        # 将新记录追加到现有数据中
        df = pd.concat([df, new_record], ignore_index=True)
        save_data(df)
        st.sidebar.success("✅ 记录添加成功！")
        st.rerun() # 刷新页面以显示最新数据

# --- 主界面：数据展示与可视化 ---
if df.empty:
    st.info("💡 目前还没有账单记录哦，请在左侧添加你的第一笔支出吧！")
else:
    # 核心指标展示
    total_expense = df["金额"].sum()
    st.metric(label="总支出", value=f"¥ {total_expense:.2f}")
    st.divider() # 分割线

    # 图表区域 (将页面分为左右两列)
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 各分类支出占比")
        # 按分类汇总金额
        cat_df = df.groupby("分类", as_index=False)["金额"].sum()
        # 绘制环形饼图
        fig_pie = px.pie(cat_df, values="金额", names="分类", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("📈 每日支出趋势")
        # 按日期汇总金额
        date_df = df.groupby("日期", as_index=False)["金额"].sum()
        # 绘制柱状图
        fig_bar = px.bar(date_df, x="日期", y="金额", text="金额")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # 详细数据表格展示
    st.subheader("📋 详细账单记录")
    # 展示 DataFrame，隐藏默认的数字索引
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 危险操作区
    if st.button("🗑️ 清空所有记录"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        st.rerun()