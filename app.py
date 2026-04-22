import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Sales Intelligence Hub", layout="wide")

# ---------- DB ----------
def get_connection():
    return psycopg2.connect(
        host="dpg-d7gbf73eo5us73aofo40-a.singapore-postgres.render.com",
        database="salesdb_s9ap",
        user="divya",
        password="CLR4Gh9Eradz6eJIPgbdUlD3qPg9Gpzm"   # 🔒 hide in real deployment
    )

# ---------- LOGIN ----------
def login(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, branch_id FROM users WHERE username=%s AND password=%s",
        (username, password)
    )
    data = cur.fetchone()
    conn.close()
    return data

# ---------- RESET ----------
def reset_filters():
    for key in list(st.session_state.keys()):
        if "filter" in key or key in ["start_date", "end_date", "amount_range"]:
            del st.session_state[key]

# ---------- ADD SALES ----------
def add_sales_form():
    st.subheader("➕ Add Sales")

    conn = get_connection()
    df_branches = pd.read_sql("SELECT branch_id, branch_name FROM branches", conn)
    conn.close()

    role = st.session_state.get("role")
    user_branch_id = st.session_state.get("branch_id")

    # ---------- BRANCH RESTRICTION ----------
    if role != "Super Admin":
        df_branches = df_branches[df_branches["branch_id"] == user_branch_id]

        branch_name = df_branches["branch_name"].values[0]
        branch_id = int(df_branches["branch_id"].values[0])

        st.text_input("Branch", value=branch_name, disabled=True)
    else:
        branch_name = st.selectbox("Branch", df_branches["branch_name"])
        branch_id = int(df_branches[df_branches["branch_name"] == branch_name]["branch_id"].values[0])

    product_name = st.selectbox("Product Type", ["DS", "DA", "BA", "FSD", "ML", "AI"])
    customer_name = st.text_input("Customer Name")
    mobile_number = st.text_input("Mobile Number")
    gross_sales = st.number_input("Gross Sales", min_value=0.0, step=100.0)

    if st.button("Add Sale"):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO customer_sales 
            (branch_id, date, customer_name, mobile_number, product_name, gross_sales, received_amount, status)
            VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, %s, %s)
        """, (
            branch_id,
            customer_name,
            mobile_number,
            product_name,
            gross_sales,
            0,
            "Open"
        ))

        conn.commit()
        conn.close()
        st.success("✅ Sale added successfully!")

# ---------- ADD PAYMENT ----------
def add_payment_form():
    st.subheader("💳 Add Payment")

    conn = get_connection()
    df_sales = pd.read_sql("""
        SELECT sale_id, customer_name, gross_sales, received_amount
        FROM customer_sales
    """, conn)
    conn.close()

    if df_sales.empty:
        st.warning("No sales available to add payments.")
        return

    sale_id = st.selectbox("Select Sale ID", df_sales["sale_id"])
    payment_method = st.selectbox("Payment Method", ["Cash", "Card", "UPI"])
    amount_paid = st.number_input("Amount Paid", min_value=0.0, step=100.0)

    if st.button("Add Payment"):
        conn = get_connection()
        cur = conn.cursor()

        # Insert new payment record
        cur.execute("""
            INSERT INTO payment_splits 
            (sale_id, payment_date, amount_paid, payment_method)
            VALUES (%s, CURRENT_DATE, %s, %s)
        """, (sale_id, amount_paid, payment_method))

        # Recalculate received_amount from payment_splits
        cur.execute("""
            UPDATE customer_sales
            SET received_amount = (
                SELECT COALESCE(SUM(amount_paid), 0)
                FROM payment_splits
                WHERE sale_id = %s
            )
            WHERE sale_id = %s
        """, (sale_id, sale_id))

        conn.commit()
        conn.close()

        st.success("✅ Payment added successfully!")
def sql_queries_page():
    st.title("🧾 SQL Query Explorer")

    queries = {

        # ---------------- BASIC QUERIES ----------------
        "Retrieve all records from customer_sales":
            "SELECT * FROM customer_sales",

        "Retrieve all records from branches":
            "SELECT * FROM branches",

        "Retrieve all records from payment_splits":
            "SELECT * FROM payment_splits",

        "Display all Open sales":
            "SELECT * FROM customer_sales WHERE status='Open'",

        "Sales from Chennai branch":
            "SELECT cs.* FROM customer_sales cs "
            "JOIN branches b ON cs.branch_id = b.branch_id "
            "WHERE b.branch_name = 'Chennai'",

        # ---------------- AGGREGATION QUERIES ----------------
        "Total gross sales":
            "SELECT SUM(gross_sales) AS total_gross_sales FROM customer_sales",

        "Total received amount":
            "SELECT SUM(received_amount) AS total_received FROM customer_sales",

        "Total pending amount":
            "SELECT SUM(gross_sales - received_amount) AS total_pending FROM customer_sales",

        "Count sales per branch":
            "SELECT b.branch_name, COUNT(cs.sale_id) AS total_sales "
            "FROM customer_sales cs "
            "JOIN branches b ON cs.branch_id = b.branch_id "
            "GROUP BY b.branch_name",

        "Average gross sales":
            "SELECT AVG(gross_sales) AS avg_gross_sales FROM customer_sales",

        # ---------------- JOIN BASED QUERIES ----------------
        "Sales with branch name":
            "SELECT cs.*, b.branch_name "
            "FROM customer_sales cs "
            "JOIN branches b ON cs.branch_id = b.branch_id",

        "Sales with total payments":
            "SELECT cs.sale_id, cs.customer_name, "
            "COALESCE(SUM(ps.amount_paid),0) AS total_paid "
            "FROM customer_sales cs "
            "LEFT JOIN payment_splits ps ON cs.sale_id = ps.sale_id "
            "GROUP BY cs.sale_id, cs.customer_name",

        "Branch-wise total gross sales":
            "SELECT b.branch_name, SUM(cs.gross_sales) AS total_sales "
            "FROM customer_sales cs "
            "JOIN branches b ON cs.branch_id = b.branch_id "
            "GROUP BY b.branch_name",

        "Sales with payment method":
            "SELECT cs.sale_id, cs.customer_name, ps.payment_method, ps.amount_paid "
            "FROM customer_sales cs "
            "JOIN payment_splits ps ON cs.sale_id = ps.sale_id",

        "Sales with branch admin name":
            "SELECT cs.*, b.branch_name, u.username AS admin_name "
            "FROM customer_sales cs "
            "JOIN branches b ON cs.branch_id = b.branch_id "
            "LEFT JOIN users u ON u.branch_id = b.branch_id",

        # ---------------- FINANCIAL TRACKING ----------------
        "Pending > 5000 sales":
            "SELECT * FROM customer_sales "
            "WHERE (gross_sales - received_amount) > 5000",

        "Top 3 highest gross sales":
            "SELECT * FROM customer_sales "
            "ORDER BY gross_sales DESC LIMIT 3",

        "Branch with highest total sales":
            "SELECT b.branch_name, SUM(cs.gross_sales) AS total_sales "
            "FROM customer_sales cs "
            "JOIN branches b ON cs.branch_id = b.branch_id "
            "GROUP BY b.branch_name "
            "ORDER BY total_sales DESC LIMIT 1",

        "Monthly sales summary":
            "SELECT DATE_TRUNC('month', date) AS month, "
            "SUM(gross_sales) AS total_sales, "
            "SUM(received_amount) AS total_received "
            "FROM customer_sales "
            "GROUP BY month "
            "ORDER BY month",

        "Payment method wise collection":
            "SELECT payment_method, SUM(amount_paid) AS total_collection "
            "FROM payment_splits "
            "GROUP BY payment_method"
    }

    choice = st.selectbox("Choose SQL Query", list(queries.keys()))

    if st.button("Run Query"):
        conn = get_connection()
        try:
            df = pd.read_sql(queries[choice], conn)
            st.success("Query executed successfully")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")
        conn.close()
# ---------- DASHBOARD ----------
def dashboard(role, branch_id):
    st.title("📊 Sales Intelligence Hub")

    conn = get_connection()

    query = """
        SELECT 
            cs.sale_id,
            cs.customer_name,
            cs.mobile_number,
            cs.product_name,
            cs.gross_sales,
            cs.received_amount,
            (cs.gross_sales - cs.received_amount) AS pending_amount,
            cs.status,
            b.branch_name,
            cs.date
        FROM customer_sales cs
        LEFT JOIN branches b ON cs.branch_id = b.branch_id
    """

    if role != "Super Admin":
        query += " WHERE cs.branch_id = %s"
        df = pd.read_sql(query, conn, params=(branch_id,))
    else:
        df = pd.read_sql(query, conn)

    conn.close()

    if df.empty:
        st.warning("No Data Found")
        return

    df["date"] = pd.to_datetime(df["date"]).dt.date

    st.subheader("🔍 Filters")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    status_filter = col1.selectbox("Status", ["All"] + list(df["status"].unique()))
    branch_filter = col2.selectbox("Branch", ["All"] + list(df["branch_name"].unique()))
    product_filter = col3.selectbox("Product", ["All"] + list(df["product_name"].unique()))
    start_date = col4.date_input("Start Date", value=df["date"].min())
    end_date = col5.date_input("End Date", value=df["date"].max())
    amount_range = col6.slider(
        "Gross Sales Range ₹",
        min_value=float(df["gross_sales"].min()),
        max_value=float(df["gross_sales"].max()),
        value=(float(df["gross_sales"].min()), float(df["gross_sales"].max()))
    )

    filtered = df.copy()

    if status_filter != "All":
        filtered = filtered[filtered["status"] == status_filter]

    if branch_filter != "All":
        filtered = filtered[filtered["branch_name"] == branch_filter]

    if product_filter != "All":
        filtered = filtered[filtered["product_name"] == product_filter]

    filtered = filtered[(filtered["date"] >= start_date) & (filtered["date"] <= end_date)]

    filtered = filtered[
        (filtered["gross_sales"] >= amount_range[0]) &
        (filtered["gross_sales"] <= amount_range[1])
    ]

    total_sales = filtered["gross_sales"].sum()
    total_received = filtered["received_amount"].sum()
    total_pending = filtered["pending_amount"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Sales", f"₹{total_sales:,.2f}")
    c2.metric("✅ Received", f"₹{total_received:,.2f}")
    c3.metric("⏳ Pending", f"₹{total_pending:,.2f}")

    st.dataframe(filtered, use_container_width=True)
    st.bar_chart(filtered.groupby("branch_name")["gross_sales"].sum())

# ---------- SESSION ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------- LOGIN ----------
if not st.session_state.logged_in:
    st.sidebar.title("Login")

    u = st.sidebar.text_input("Username")
    p = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        user = login(u, p)

        if user:
            st.session_state.logged_in = True
            st.session_state.role = user[0]
            st.session_state.branch_id = user[1]
            st.rerun()
        else:
            st.error("Invalid Login")

# ---------- APP ----------
else:
    menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add Sales", "Add Payment", "SQL Queries"]
)

    if menu == "Dashboard":
        dashboard(st.session_state.role, st.session_state.branch_id)

    elif menu == "Add Sales":
        add_sales_form()

    elif menu == "Add Payment":
        add_payment_form()

    elif menu == "SQL Queries":
        sql_queries_page()

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

