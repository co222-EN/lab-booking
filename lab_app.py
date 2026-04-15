import streamlit as st
import pandas as pd
from datetime import datetime
import os

import streamlit as st
import pandas as pd
from datetime import datetime
import os
import json  # 【新增】用来处理配置文件的工具

# --- 1. 基础配置 ---
st.set_page_config(page_title="实验室预约系统", page_icon="🤖", layout="wide")
EXCEL_FILE = "lab_data.xlsx"
CONFIG_FILE = "config.json" # 【新增】老师的权限备忘录

# 【新增】读取老师设置的日期
def load_config():
    # 默认值：从今天到很久以后（防止一开始没文件时报错）
    default_start = datetime.now().date()
    default_end = datetime(2030, 12, 31).date()
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                start = datetime.strptime(data["start"], "%Y-%m-%d").date()
                end = datetime.strptime(data["end"], "%Y-%m-%d").date()
                return start, end
        except:
            pass
    return default_start, default_end

# 【新增】保存老师设置的日期
def save_config(start_date, end_date):
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d")
        }, f)

# 加载 Excel 数据函数 (保持你原来的不变)
def load_data():
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE)
            df['开始时间'] = pd.to_datetime(df['开始时间'], errors='coerce')
            df['结束时间'] = pd.to_datetime(df['结束时间'], errors='coerce')
            df = df.dropna(subset=['开始时间', '结束时间'])
            return df
        except Exception as e:
            st.error(f"读取文件出错: {e}")
            return pd.DataFrame(columns=["预约人", "预约事由", "开始时间", "结束时间", "备注"])
    return pd.DataFrame(columns=["预约人", "预约事由", "开始时间", "结束时间", "备注"])
    
df = load_data()

# 加载数据函数
def load_data():
    if os.path.exists(EXCEL_FILE):
        try:
            # 读取 Excel
            df = pd.read_excel(EXCEL_FILE)
            
            # 【核心修复】强行转换格式，errors='coerce' 会把乱码变成空值，防止程序崩溃
            df['开始时间'] = pd.to_datetime(df['开始时间'], errors='coerce')
            df['结束时间'] = pd.to_datetime(df['结束时间'], errors='coerce')
            
            # 剔除掉那些时间转换失败的行
            df = df.dropna(subset=['开始时间', '结束时间'])
            return df
        except Exception as e:
            st.error(f"读取文件出错: {e}")
            return pd.DataFrame(columns=["预约人", "预约事由", "开始时间", "结束时间", "备注"])
    return pd.DataFrame(columns=["预约人", "预约事由", "开始时间", "结束时间", "备注"])
    
df = load_data()

# --- 2. 顶部标题 ---
st.title("🤖 百度机器人实验室预约系统")
st.markdown("---")

# --- 3. 核心 UI 布局（左侧课表，右侧预约） ---
col_left, col_right = st.columns([1.5, 2.5]) # 设置左右比例

with col_left:
    st.subheader("🗓️ 课表查询")
    # 让查询日期跟随预约日期联动，或者独立选择
    check_date = st.date_input("查看哪天的占用情况？", datetime.now())
    
    # 筛选数据
    target_data = df[df['开始时间'].dt.date == check_date].sort_values("开始时间")
    
    if not target_data.empty:
        st.write(f"以下是 **{check_date}** 的已占用时段：")
        # 格式化时间显示，只看时分
        display_df = target_data.copy()
        display_df['时段'] = display_df['开始时间'].dt.strftime('%H:%M') + " - " + display_df['结束时间'].dt.strftime('%H:%M')
        st.dataframe(display_df[['时段', '预约人', '预约事由']], use_container_width=True, hide_index=True)
    else:
        st.success(f"✅ {check_date} 全天暂无占用，请放心预约！")
    
    st.info("💡 提示：请避开上方显示的固定课表时段。")

with col_right:
    st.subheader("📝 填写预约信息")
    
    # --- 动态读取老师在后台设置的日期 ---
    OPEN_START, OPEN_END = load_config()
    # ------------------------------------
    
    st.warning(f"📢 老师提示：当前仅开放 {OPEN_START} 至 {OPEN_END} 的预约")

    with st.form("booking_form", clear_on_submit=True):
        u_name = st.text_input("预约人姓名*", placeholder="请输入您的真实姓名")
        # ...(这下面的代码完全保持你之前的样子，不要动)...
        u_reason = st.text_input("预约事由*", placeholder="例如：备赛/项目调试/自习")
        
        c1, c2, c3 = st.columns(3)
        u_date = c1.date_input("预约日期", datetime.now())
        u_start = c2.time_input("开始时间", datetime.strptime("08:10", "%H:%M"))
        u_end = c3.time_input("结束时间", datetime.strptime("09:50", "%H:%M"))
        
        submit_btn = st.form_submit_button("确认提交预约")
        
        if submit_btn:
            if u_name and u_reason:
                # 组合日期时间
                start_dt = datetime.combine(u_date, u_start)
                end_dt = datetime.combine(u_date, u_end)
                
                # 存入 Excel
                new_row = {
                    "预约人": u_name,
                    "预约事由": u_reason,
                    "开始时间": start_dt,
                    "结束时间": end_dt,
                    "备注": "学生预约"
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_excel(EXCEL_FILE, index=False)
                
                st.success("🎉 预约成功！数据已更新。")
                st.balloons()
                st.rerun() # 提交后自动刷新，左侧课表立刻就能看到刚约的
            else:
                st.error("请完整填写姓名和事由！")

# --- 4. 底部管理区域 ---
st.markdown("---")
with st.expander("🔐 管理员后台 (点击展开)"):
    admin_pwd = st.text_input("管理密码", type="password")
    
    if admin_pwd == "123456": # 你的专属密码
        
        # 1. 权限控制面板
        st.markdown("### ⚙️ 预约权限设置")
        current_start, current_end = load_config()
        
        with st.form("config_form"):
            c_start, c_end = st.columns(2)
            new_start = c_start.date_input("设置开放起始日", current_start)
            new_end = c_end.date_input("设置开放截止日", current_end)
            update_btn = st.form_submit_button("保存权限设置")
            
            if update_btn:
                if new_start > new_end:
                    st.error("❌ 起始日期不能晚于截止日期！")
                else:
                    save_config(new_start, new_end)
                    st.success(f"✅ 设置成功！现在学生只能预约 {new_start} 到 {new_end} 的时间。")
                    st.rerun() # 刷新网页，让新规矩立刻生效

        st.markdown("---")
        
        # 2. 原来的数据管理面板
        st.markdown("### 📊 所有预约数据")
        st.write("提示：双击表格单元格可以直接修改数据，改完记得点下方保存。")
        edited = st.data_editor(df)
        if st.button("保存数据修改"):
            edited.to_excel(EXCEL_FILE, index=False)
            st.success("✅ 数据已更新！")
            st.rerun()
