import streamlit as st
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
import time

# --- 1. 数据库配置 ---
st.set_page_config(page_title="机器人实验室预约系统", page_icon="🤖", layout="wide")

# 从 Streamlit Secrets 安全获取钥匙
try:
    MONGO_URI = st.secrets["mongo"]["uri"]
    client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=5000)
    db = client["lab_db"]          # 数据库名字
    collection = db["bookings"]     # 集合
    config_col = db["config"]       # 存放权限的集合
except Exception as e:
    st.error(f"数据库连接配置失败: {e}")
    st.stop()

# 读取老师设置
def load_config():
    conf = config_col.find_one({"name": "admin_config"})
    if conf:
        start = datetime.strptime(conf["start"], "%Y-%m-%d").date()
        end = datetime.strptime(conf["end"], "%Y-%m-%d").date()
        return start, end
    return datetime.now().date(), datetime(2030, 12, 31).date()

# 保存老师设置
def save_config(start_date, end_date):
    config_col.update_one(
        {"name": "admin_config"},
        {"$set": {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d")
        }},
        upsert=True
    )

# --- 2. 顶部标题 ---
st.title("🤖 百度机器人实验室预约系统 (云端增强版)")
st.markdown("---")

# --- 3. 核心 UI 布局 ---
col_left, col_right = st.columns([1.5, 2.5])

with col_left:
    st.subheader("🗓️ 课表查询")
    check_date = st.date_input("查看哪天的占用情况？", datetime.now())
    
    start_of_day = datetime.combine(check_date, datetime.min.time())
    end_of_day = datetime.combine(check_date, datetime.max.time())
    
    query = {"开始时间": {"$gte": start_of_day, "$lte": end_of_day}}
    results = list(collection.find(query).sort("开始时间", 1))
    
    if results:
        data_list = []
        for res in results:
            data_list.append({
                "时段": f"{res['开始时间'].strftime('%H:%M')} - {res['结束时间'].strftime('%H:%M')}",
                "预约人": res["预约人"],
                "预约事由": res["预约事由"]
            })
        st.dataframe(pd.DataFrame(data_list), width="stretch", hide_index=True)
    else:
        st.success(f"✅ {check_date} 全天暂无占用。")

with col_right:
    st.subheader("📝 填写预约信息")
    OPEN_START, OPEN_END = load_config()
    st.warning(f"📢 老师提示：当前仅开放 {OPEN_START} 至 {OPEN_END} 的预约")

    with st.form("booking_form", clear_on_submit=True):
        u_name = st.text_input("预约人姓名*")
        u_reason = st.text_input("预约事由*")
        c1, c2, c3 = st.columns(3)
        u_date = c1.date_input("预约日期", datetime.now())
        u_start = c2.time_input("开始时间", datetime.strptime("08:10", "%H:%M"))
        u_end = c3.time_input("结束时间", datetime.strptime("09:50", "%H:%M"))
        
        if st.form_submit_button("确认提交预约"):
            if not (OPEN_START <= u_date <= OPEN_END):
                st.error(f"❌ 预约失败！不在开放时段内。")
            elif not u_name or not u_reason:
                st.error("⚠️ 请填写完整信息！")
            elif u_start >= u_end:
                st.error("❌ 结束时间错误！")
            else:
                new_doc = {
                    "预约人": u_name,
                    "预约事由": u_reason,
                    "开始时间": datetime.combine(u_date, u_start),
                    "结束时间": datetime.combine(u_date, u_end),
                    "提交时间": datetime.now()
                }
                collection.insert_one(new_doc)
                st.success("🎉 预约成功！数据已实时同步到云端数据库。")
                st.balloons()
                time.sleep(2)
                st.rerun()

# --- 4. 管理员后台 ---
st.markdown("---")
with st.expander("🔐 管理员后台"):
    admin_pwd = st.text_input("管理密码", type="password")
    
    if admin_pwd == "123456":
        st.markdown("### ⚙️ 预约权限设置")
        c_start, c_end = st.columns(2)
        new_start = c_start.date_input("设置开放起始日", OPEN_START)
        new_end = c_end.date_input("设置开放截止日", OPEN_END)
        if st.button("保存权限设置"):
            save_config(new_start, new_end)
            st.success("权限已更新！")
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 预约记录管理 (支持批量删除)")

        col_m1, col_m2 = st.columns([1, 2])
        filter_mode = col_m1.radio("列表显示模式", ["查看全部", "按日期筛选"])
        
        query = {} 
        if filter_mode == "按日期筛选":
            target_date = col_m2.date_input("选择要查看的日期", datetime.now())
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())
            query = {"开始时间": {"$gte": start_of_day, "$lte": end_of_day}}
            st.info(f"📅 正在查看 {target_date} 的所有预约")
        else:
            st.info("📜 正在查看数据库中的全部预约记录")

        all_data = list(collection.find(query).sort("开始时间", -1))
        
        if all_data:
            # --- 【核心修复：强力全选逻辑】 ---
            # 定义回调函数：当“全选”按钮状态改变时，强制更新所有子勾选框
            def toggle_all():
                new_state = st.session_state.master_select  # 获取全选按钮当前的值
                for item in all_data:
                    # 通过 key 强制修改 session_state 里的每一个勾选框
                    st.session_state[f"chk_{item['_id']}"] = new_state

            # 全选按钮：增加 on_change 回调
            st.checkbox("✅ 一键全选当前列表下的所有记录", 
                        key="master_select", 
                        on_change=toggle_all)
            
            with st.form("batch_delete_form"):
                selected_ids = [] 
                
                for res in all_data:
                    with st.container():
                        col_info, col_chk = st.columns([3, 1])
                        
                        time_display = res['开始时间'].strftime('%Y-%m-%d %H:%M')
                        col_info.write(f"👤 **{res['预约人']}** | 🕒 {time_display}")
                        col_info.write(f"📝 事由：{res['预约事由']}")
                        
                        # 子勾选框：key 必须与上面回调函数中的 key 规则一致
                        is_checked = col_chk.checkbox("🗑️ 勾选", key=f"chk_{res['_id']}")
                        if is_checked:
                            selected_ids.append(res["_id"])
                        
                        st.divider() 
                
                if st.form_submit_button("🚨 确认删除所选记录"):
                    if selected_ids:
                        collection.delete_many({"_id": {"$in": selected_ids}})
                        st.success(f"🎉 成功删除了 {len(selected_ids)} 条记录！")
                        # 删除后清空全选状态
                        st.session_state.master_select = False
                        time.sleep(1.5) 
                        st.rerun()
                    else:
                        st.warning("⚠️ 请先勾选需要删除的记录！")
        else:
            st.warning("🔎 该条件下没有找到任何预约记录。")
