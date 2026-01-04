# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import mysql.connector
from datetime import date, datetime

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "community_hospital_db" 
}

MOCK_MODE = False

def get_connection():
    """建立数据库连接"""
    if MOCK_MODE: return None
    return mysql.connector.connect(**DB_CONFIG)

def run_query(query, params=None):
    if MOCK_MODE:
        return pd.DataFrame({"提示": ["模拟数据", "模拟数据"], "数值": [1, 2]})
    
    conn = get_connection()
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"查询出错: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def run_action(sql, params=None):
    if MOCK_MODE:
        st.success("【模拟模式】操作已执行")
        return True
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"操作失败: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def call_procedure(proc_name, args):
    if MOCK_MODE:
        st.success(f"【模拟模式】调用存储过程 {proc_name} 成功")
        return True

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.callproc(proc_name, args)
    
        conn.commit()
        return True
    except Exception as e:
        st.error(f"存储过程调用失败: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def main():
    st.set_page_config(page_title="社区医院管理系统", layout="wide")
    
    st.sidebar.title("🏥 门诊系统演示")
    role = st.sidebar.selectbox(
        "当前操作角色",
        ["患者 (在线预约)", "前台 (挂号/收费)", "管理员 (报表/排班)"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"当前模式: {'🚫 模拟数据' if MOCK_MODE else '✅ 实时数据库'}")

    # if st.sidebar.checkbox("显示数据库实时状态"):
    #    st.write("当前 Appointments 表：")
    #    st.dataframe(run_query("SELECT * FROM Appointments"))
    #    st.write("当前 Visits 表：")
    #    st.dataframe(run_query("SELECT * FROM Visits"))

    # --- 角色视图 1: 患者 ---
    if role == "患者 (在线预约)":
        st.title("📱 患者在线预约")
        dept_df = run_query("SELECT dept_id, dept_name FROM Departments")
        if dept_df.empty:
            st.error("数据库中未发现科室信息，请联系管理员初始化数据。")
        else:
            dept_options = dict(zip(dept_df['dept_name'], dept_df['dept_id']))
            with st.form("appt_form"):
                col1, col2 = st.columns(2)
                name = col1.text_input("姓名")
                phone = col2.text_input("手机号")
                personal_id = st.text_input("身份证号")
                selected_dept_name = st.selectbox("选择科室", options=list(dept_options.keys()))
                appt_date = st.date_input("预约日期", min_value=date.today())
                arrival_time = st.time_input("预计到达时间",step = 300)            
                submitted = st.form_submit_button("提交预约")
            
                if submitted:
                    if not name or not phone:
                        st.warning("请填写完整的姓名和电话。")
                    else:
                        target_dept_id = dept_options[selected_dept_name]
                    
                        sql = """
                            INSERT INTO Appointments (patient_name, phone, dept_id, appt_date, eta, status, id_card)
                            VALUES (%s, %s, %s, %s, %s, 'Pending', %s)
                        """
                        success = run_action(sql, (name, phone, target_dept_id, appt_date, arrival_time, personal_id))
                    
                        if success:
                            st.success(f"预约成功！科室：{selected_dept_name} (ID: {target_dept_id})")
                            st.balloons()

    # --- 角色视图 2: 前台 ---
    elif role == "前台 (挂号/收费)":
        st.title("🖥️ 前台工作台")
        
        tab1, tab2, tab3 = st.tabs(["📋 预约核验 (转挂号)", "🏥 现场挂号", "💰 缴费结算"])
        

        doc_df = run_query("SELECT staff_id, name, dept_id FROM Staff WHERE role='Doctor'")
        doc_options = {f"{row['name']} (ID:{row['staff_id']})": row['staff_id'] for i, row in doc_df.iterrows()} if not doc_df.empty else {}
        
        room_df = run_query("SELECT room_no, dept_id FROM Rooms WHERE status='Available'")
        room_list = room_df['room_no'].tolist() if not room_df.empty else []

        with tab1:
            st.subheader("今日待核验预约")
            q_appt = """
                SELECT a.appt_id, a.patient_name, a.phone, a.id_card, d.dept_name, a.appt_date 
                FROM Appointments a
                JOIN Departments d ON a.dept_id = d.dept_id
                WHERE a.status='Pending'
            """
            df_appt = run_query(q_appt)
            st.dataframe(df_appt, use_container_width=True)
            
            st.markdown("### 🟢 核验并分配诊室")
            with st.form("verify_form"):
                c1, c2 = st.columns(2)
                p_appt_id = c1.number_input("请输入预约 ID (Appt ID)", min_value=1, step=1)
                
                c3, c4 = st.columns(2)
                p_id_card = c3.text_input("核验身份证号 (必填)", max_chars=18)
                p_gender = c4.selectbox("性别 (补录)", ["M", "F"])
                
                c5, c6 = st.columns(2)
                selected_doc_key = c5.selectbox("分配医生", options=list(doc_options.keys()))
                p_room = c6.selectbox("分配诊室", options=room_list)
                
                if st.form_submit_button("确认到院 & 生成缴费单"):
                    if not df_appt.empty and p_appt_id in df_appt['appt_id'].values:
                        p_doctor_id = doc_options[selected_doc_key]
                        
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            
                            cursor.execute("SELECT patient_name, phone, dept_id FROM Appointments WHERE appt_id=%s", (p_appt_id,))
                            appt_data = cursor.fetchone()
                            
                            if appt_data:
                                p_name, p_phone, p_dept_id = appt_data
                                
                                sql_insert = """
                                    INSERT INTO Visits (appt_id, patient_name, phone, id_card, gender, dept_id, 
                                                        doctor_id, room_no, status)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ToPay')
                                """
                                cursor.execute(sql_insert, (p_appt_id, p_name, p_phone, p_id_card, p_gender, p_dept_id, p_doctor_id, p_room))
                                
                                cursor.execute("UPDATE Appointments SET status='Completed' WHERE appt_id=%s", (p_appt_id,))
                                
                                conn.commit()
                                st.success(f"✅ 核验成功！患者 {p_name} 已直接转入【待缴费】状态。")
                                st.rerun()
                            else:
                                st.error("未找到该预约信息的详细数据。")
                            cursor.close()
                            conn.close()
                        except Exception as e:
                            st.error(f"操作失败: {e}")
                    else:
                        st.error("无效的预约ID，请检查列表。")

        with tab2:
            st.subheader("🏥 现场挂号录入")
            with st.form("onsite_form"):
                col1, col2 = st.columns(2)
                o_name = col1.text_input("患者姓名")
                o_phone = col2.text_input("联系电话")
                
                col3, col4 = st.columns(2)
                o_id_card = col3.text_input("身份证号")
                o_gender = col4.selectbox("性别", ["M", "F"])
                
                dept_df = run_query("SELECT dept_id, dept_name FROM Departments")
                dept_opts = {row['dept_name']: row['dept_id'] for i, row in dept_df.iterrows()} if not dept_df.empty else {}
                
                col5, col6 = st.columns(2)
                sel_dept = col5.selectbox("挂号科室", list(dept_opts.keys()))
                sel_doc = col6.selectbox("指派医生", list(doc_options.keys()))
                o_room = st.selectbox("指派诊室", room_list)

                if st.form_submit_button("现场挂号 (生成缴费单)"):
                    if o_name and o_id_card:
                        o_dept_id = dept_opts[sel_dept]
                        o_doc_id = doc_options[sel_doc]
                        
                        sql_onsite = """
                            INSERT INTO Visits (patient_name, phone, id_card, gender, dept_id, 
                                                doctor_id, room_no, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ToPay')
                        """
                        if run_action(sql_onsite, (o_name, o_phone, o_id_card, o_gender, o_dept_id, o_doc_id, o_room)):
                            st.success(f"现场挂号成功！请引导患者前往缴费。")
                            st.rerun()
                    else:
                        st.warning("请填写完整的姓名和身份证号。")


        with tab3:
            st.subheader("💰 收银台")
            sql_topay = """
                SELECT v.visit_id, v.patient_name, d.dept_name, s.name as doctor 
                FROM Visits v
                JOIN Departments d ON v.dept_id = d.dept_id
                JOIN Staff s ON v.doctor_id = s.staff_id
                WHERE v.status='ToPay'
            """
            df_pay = run_query(sql_topay)
            
            if df_pay.empty:
                st.info("当前没有待缴费的患者。")
            else:
                st.dataframe(df_pay, use_container_width=True)
                
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                pay_opts = {f"{r['patient_name']} (ID: {r['visit_id']})": r['visit_id'] for i, r in df_pay.iterrows()}
                sel_patient = c1.selectbox("选择缴费患者", list(pay_opts.keys()))
                
                total_fee = c2.number_input("应收总金额 (¥)", min_value=0.0, value=50.0)
                pay_method = c3.selectbox("支付方式", ["医保卡", "微信/支付宝", "现金"]) 
                
                if st.button("✅ 确认收款"):
                    target_visit_id = pay_opts[sel_patient]
                    sql_pay = """
                        UPDATE Visits 
                        SET status='Finished', total_fee=%s, finish_time=NOW() 
                        WHERE visit_id=%s
                    """
                    if run_action(sql_pay, (total_fee, target_visit_id)):
                        st.balloons()
                        st.success(f"缴费成功！订单号 {target_visit_id} 已结清。")
                        st.rerun()

    # --- 角色视图 3: 管理员 ---
    elif role == "管理员 (报表/排班)":
        st.title("🛡️ 医院行政管理后台")
        
        tab1, tab2, tab3, tab4 = st.tabs(["📅 排班管理", "💰 财务报表", "📂 患者查询", "👥 员工管理"])

        with tab1:
            st.subheader("📅 医生排班设置")

            depts = run_query("SELECT dept_id, dept_name FROM Departments")
            dept_map = dict(zip(depts['dept_name'], depts['dept_id']))

            sel_dept_name = st.selectbox("1. 选择排班科室", list(dept_map.keys()))
            target_dept_id = dept_map[sel_dept_name]

            doc_sql = "SELECT staff_id, name FROM Staff WHERE dept_id = %s AND role = 'Doctor' AND is_active = 1"
            matching_docs = run_query(doc_sql, (target_dept_id,))
    
            room_sql = "SELECT room_no FROM Rooms WHERE dept_id = %s AND status = 'Available'"
            matching_rooms = run_query(room_sql, (target_dept_id,))

            with st.form("advanced_schedule_form"):
                col1, col2 = st.columns(2)
        
                if not matching_docs.empty:
                    doc_opts = {row['name']: row['staff_id'] for _, row in matching_docs.iterrows()}
                    selected_doc_name = col1.selectbox("2. 指派医生", list(doc_opts.keys()))
                else:
                    col1.error("该科室暂无可排班医生")
                    selected_doc_name = None

                if not matching_rooms.empty:
                    selected_room = col2.selectbox("3. 分配诊室", matching_rooms['room_no'].tolist())
                else:
                    col2.error("该科室暂无可分配诊室")
                    selected_room = None

                c3, c4 = st.columns(2)
                shift_date = c3.date_input("排班日期", min_value=date.today())
                shift_time = c4.selectbox("时段", ["Morning", "Afternoon"])

                if st.form_submit_button("保存排班"):
                    if selected_doc_name and selected_room:
                        target_doc_id = doc_opts[selected_doc_name]
                
                        conflict_sql = """
                            SELECT COUNT(*) as count FROM Schedules 
                            WHERE room_no = %s AND shift_date = %s AND shift_time = %s
                        """
                        conflict_check = run_query(conflict_sql, (selected_room, shift_date, shift_time))
                
                        if conflict_check.iloc[0]['count'] > 0:
                            st.error(f"❌ 冲突：诊室 {selected_room} 在该时段已有其他医生排班！")
                        else:

                            insert_sql = """
                                INSERT INTO Schedules (doctor_id, shift_date, shift_time, room_no)
                                VALUES (%s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE room_no = VALUES(room_no)
                            """
                            if run_action(insert_sql, (target_doc_id, shift_date, shift_time, selected_room)):
                                st.success(f"✅ 排班成功：{selected_doc_name} 于 {selected_room} 诊室")
                                st.rerun()
                    else:
                        st.warning("请确保已选择医生和诊室。")


        with tab2:
            st.subheader("门诊收入统计")
            
            col_filter1, col_filter2 = st.columns(2)
            start_date = col_filter1.date_input("开始日期", value=date.today().replace(day=1))
            end_date = col_filter2.date_input("结束日期", value=date.today())
            
            group_by = st.radio("统计维度", ["按科室统计", "按医生统计", "按日期统计"], horizontal=True)
            
            if group_by == "按科室统计":
                sql = """
                    SELECT d.dept_name as 维度, COUNT(v.visit_id) as 就诊人次, SUM(v.total_fee) as 总收入
                    FROM Visits v JOIN Departments d ON v.dept_id = d.dept_id
                    WHERE DATE(v.finish_time) BETWEEN %s AND %s AND v.status='Finished'
                    GROUP BY d.dept_name
                """
            elif group_by == "按医生统计":
                sql = """
                    SELECT s.name as 维度, COUNT(v.visit_id) as 就诊人次, SUM(v.total_fee) as 总收入
                    FROM Visits v JOIN Staff s ON v.doctor_id = s.staff_id
                    WHERE DATE(v.finish_time) BETWEEN %s AND %s AND v.status='Finished'
                    GROUP BY s.name
                """
            else: # 按日期
                sql = """
                    SELECT DATE(v.finish_time) as 维度, COUNT(v.visit_id) as 就诊人次, SUM(v.total_fee) as 总收入
                    FROM Visits v
                    WHERE DATE(v.finish_time) BETWEEN %s AND %s AND v.status='Finished'
                    GROUP BY DATE(v.finish_time)
                """
                
            df_report = run_query(sql, (start_date, end_date))
            
            total_rev = df_report["总收入"].sum() if not df_report.empty else 0
            st.metric("区间总营收", f"¥ {total_rev:,.2f}")
            
            if not df_report.empty:
                st.dataframe(df_report, use_container_width=True)
                st.bar_chart(df_report.set_index("维度")["总收入"])
            else:
                st.info("该时间段内无已结算数据。")

        with tab3:
            st.subheader("患者档案检索")
            search_term = st.text_input("输入关键字 (姓名 / 电话 / 身份证号 / 诊室号)", placeholder="例如：张三 或 1380000...")
            
            if st.button("🔍 搜索患者"):
                if search_term:
                    sql = """
                        SELECT v.visit_id, v.patient_name, v.gender, v.phone, v.id_card, 
                               d.dept_name, v.room_no, v.visit_time, v.status, v.total_fee
                        FROM Visits v
                        LEFT JOIN Departments d ON v.dept_id = d.dept_id
                        WHERE v.patient_name LIKE %s 
                           OR v.phone LIKE %s 
                           OR v.id_card LIKE %s 
                           OR v.room_no LIKE %s
                        ORDER BY v.visit_time DESC
                    """
                    param = f"%{search_term}%"
                    df_patient = run_query(sql, (param, param, param, param))
                    
                    if not df_patient.empty:
                        st.dataframe(df_patient)
                    else:
                        st.warning("未找到匹配的患者信息。")
        with tab4:
            st.subheader("👥 人力资源管理")

            dept_df_raw = run_query("SELECT dept_id, dept_name FROM Departments")
            dept_opts = dict(zip(dept_df_raw['dept_name'], dept_df_raw['dept_id'])) if not dept_df_raw.empty else {}

            st.markdown("### 📋 在职员工花名册")
            all_staff_sql = """
                SELECT s.staff_id, s.name, s.role, d.dept_name, s.title, s.phone, 
                       CASE WHEN s.is_active = 1 THEN '在职' ELSE '已离职' END as 状态
                FROM Staff s LEFT JOIN Departments d ON s.dept_id = d.dept_id
                ORDER BY s.is_active DESC, s.staff_id ASC
            """
            df_staff = run_query(all_staff_sql)
            st.dataframe(df_staff, use_container_width=True)

            st.markdown("---")

            col_hire, col_manage = st.columns(2)

            with col_hire:
                st.info("### ➕ 办理入职 (Hire)")
                with st.form("hire_staff_form"):
                    new_name = st.text_input("姓名 (必填)")
                    c1, c2 = st.columns(2)
                    new_role = c2.selectbox("岗位", ["Doctor", "Nurse", "Admin", "Cashier"])
                    
                    c3, c4 = st.columns(2)
                    new_dept_name = c3.selectbox("所属科室", list(dept_opts.keys()))
                    new_title = c4.text_input("职称 (如: 主治医师)")
                    
                    new_phone = st.text_input("联系电话")
                    
                    if st.form_submit_button("确认录入"):
                        if new_name and new_phone:
                            dept_id = dept_opts[new_dept_name]
                            insert_sql = """
                                INSERT INTO Staff (name, role, dept_id, title, phone, is_active)
                                VALUES (%s, %s, %s, %s, %s, 1)
                            """
                            if run_action(insert_sql, (new_name, new_role, dept_id, new_title, new_phone)):
                                st.success(f"员工 {new_name} 入职办理成功！")
                                st.rerun()
                        else:
                            st.error("姓名和电话为必填项。")

            with col_manage:
                st.warning("### ⚙️ 档案管理 / 离职 (Fire)")
                
                staff_select_df = run_query("SELECT staff_id, name, is_active FROM Staff")
                if not staff_select_df.empty:
                    staff_opts = {f"{r['staff_id']} - {r['name']} ({'在职' if r['is_active'] else '离职'})": r['staff_id'] for i, r in staff_select_df.iterrows()}
                    selected_staff_key = st.selectbox("选择要操作的员工", options=list(staff_opts.keys()))
                    selected_staff_id = staff_opts[selected_staff_key]
                    
                    curr_info_df = run_query("SELECT * FROM Staff WHERE staff_id = %s", (selected_staff_id,))
                    
                    if not curr_info_df.empty:
                        curr = curr_info_df.iloc[0]
                        
                        action_tab1, action_tab2 = st.tabs(["✏️ 修改信息", "❌ 办理离职"])
                        
                        with action_tab1:
                            with st.form("edit_staff_subform"):
                                e_phone = st.text_input("新电话", value=curr['phone'])
                                e_title = st.text_input("新职称", value=curr['title'])
                                e_role = st.selectbox("新岗位", ["Doctor", "Nurse", "Admin", "Cashier"], index=["Doctor", "Nurse", "Admin", "Cashier"].index(curr['role']))
                                                                
                                if st.form_submit_button("保存变更"):
                                    up_sql = "UPDATE Staff SET phone=%s, title=%s, role=%s WHERE staff_id=%s"
                                    if run_action(up_sql, (e_phone, e_title, e_role, selected_staff_id)):
                                        st.success("信息更新成功！")
                                        st.rerun()
                        
                        with action_tab2:
                            if curr['is_active'] == 0:
                                st.error("该员工已经是【离职】状态。")
                            else:
                                st.write(f"您正在为 **{curr['name']}** 办理离职手续。")
                                st.warning("⚠️ 注意：离职操作将保留其历史数据，但该员工将无法再被排班。")
                                
                                fire_confirm = st.checkbox("我确认执行解雇/离职操作")
                                
                                if st.button("确认解雇 (Fire)", type="primary"):
                                    if fire_confirm:
                                        fire_sql = "UPDATE Staff SET is_active = 0 WHERE staff_id = %s"
                                        if run_action(fire_sql, (selected_staff_id,)):
                                            st.error(f"员工 {curr['name']} 已确认为离职状态。")
                                            st.rerun()
                                    else:
                                        st.warning("请先勾选确认框。")  
        if st.button("查看所有表结构"):
            tables = run_query("SHOW TABLES")
            for tbl in tables.iloc[:, 0]:
                st.write(f"### 表名: {tbl}")
                st.dataframe(run_query(f"DESCRIBE {tbl}"))

if __name__ == "__main__":

    main()
