import os
import sqlite3
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from fpdf import FPDF

# --- Database Connection Setup ---
sqlite3.register_adapter(datetime.date, lambda d: d.strftime("%Y-%m-%d"))
sqlite3.register_converter("DATE", lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"))

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE_PATH = os.path.join(PROJECT_DIR, "expenses.db")

conn = sqlite3.connect(DB_FILE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
conn.execute("""
CREATE TABLE IF NOT EXISTS ExpenseLog (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Date TEXT,
    Payee TEXT,
    Description TEXT,
    Category TEXT,
    Amount REAL,
    Mode TEXT
)
""")
conn.commit()

# --- GUI Initialization ---
app = Tk()
app.title("Budget Tracker & Visualizer ")
app.geometry("1000x700")
app.configure(bg="#FAF9F6")

# --- Header Banner ---
top_header = Frame(app, bg="#3F51B5", pady=12)
top_header.pack(fill=X)
Label(top_header, text="Budget Tracker & Visualizer Dashboard",
      font=("Arial", 21, "bold"), bg="#3F51B5", fg="white").pack()

# --- Style Config ---
ui_style = ttk.Style()
ui_style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
ui_style.configure("Treeview", font=("Arial", 11))

# --- State Variables ---
payee_var = StringVar()
description_var = StringVar()
category_var = StringVar(value="General")
amount_var = DoubleVar()
payment_mode_var = StringVar(value="Cash")
chart_mode = StringVar(value="Method")

# --- Function Definitions ---
def refresh_expenses():
    table.delete(*table.get_children())
    for entry in conn.execute("SELECT * FROM ExpenseLog"):
        table.insert('', END, values=entry)

def reset_fields():
    payee_var.set("")
    description_var.set("")
    category_var.set("General")
    amount_var.set(0.0)
    payment_mode_var.set("Cash")
    date_input.set_date(datetime.date.today())

def insert_expense():
    if not payee_var.get() or not description_var.get() or amount_var.get() <= 0:
        messagebox.showwarning("Incomplete Data", "Please provide complete expense details.")
        return
    try:
        conn.execute("INSERT INTO ExpenseLog (Date, Payee, Description, Category, Amount, Mode) VALUES (?, ?, ?, ?, ?, ?)",
                     (date_input.get_date().strftime("%Y-%m-%d"), payee_var.get(), description_var.get(),
                      category_var.get(), amount_var.get(), payment_mode_var.get()))
        conn.commit()
        refresh_expenses()
        reset_fields()
        messagebox.showinfo("Added", "Expense logged successfully.")
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to insert expense.\n{e}")

def delete_entry():
    selected_item = table.selection()
    if not selected_item:
        messagebox.showwarning("Select Entry", "Choose an item to delete.")
        return
    item_id = table.item(selected_item[0])["values"][0]
    conn.execute("DELETE FROM ExpenseLog WHERE ID = ?", (item_id,))
    conn.commit()
    refresh_expenses()
    messagebox.showinfo("Removed", "Entry deleted.")

def clear_all_data():
    if messagebox.askyesno("Confirmation", "This will delete all entries. Proceed?"):
        conn.execute("DELETE FROM ExpenseLog")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='ExpenseLog'")
        conn.commit()
        refresh_expenses()

def calculate_total():
    total = conn.execute("SELECT SUM(Amount) FROM ExpenseLog").fetchone()[0] or 0
    messagebox.showinfo("Spending Total", f"Total Expenditure: ₹{total:.2f}")

def generate_chart():
    selection = chart_mode.get()
    if selection == "Method":
        sql = "SELECT Mode, SUM(Amount) FROM ExpenseLog GROUP BY Mode"
        graph_title = "Expenses by Payment Method"
    elif selection == "Receiver":
        sql = "SELECT Payee, SUM(Amount) FROM ExpenseLog GROUP BY Payee"
        graph_title = "Expenses by Payee"
    elif selection == "Category":
        sql = "SELECT Category, SUM(Amount) FROM ExpenseLog GROUP BY Category"
        graph_title = "Expenses by Category"
    else:
        sql = "SELECT strftime('%Y-%m', Date), SUM(Amount) FROM ExpenseLog GROUP BY strftime('%Y-%m', Date)"
        graph_title = "Monthly Expense Overview"

    results = conn.execute(sql).fetchall()
    if not results:
        messagebox.showwarning("No Data", "Add expenses to generate a chart.")
        return

    labels, values = zip(*results)
    plt.figure(figsize=(8, 6))
    plt.bar(labels, values, color="#7E57C2")
    plt.title(graph_title)
    plt.ylabel("Amount in ₹")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def render_pie_chart():
    data = conn.execute("SELECT Category, SUM(Amount) FROM ExpenseLog GROUP BY Category").fetchall()
    if not data:
        messagebox.showwarning("Empty Data", "Pie chart requires logged expenses.")
        return
    parts, shares = zip(*data)
    plt.figure(figsize=(7, 7))
    plt.pie(shares, labels=parts, autopct="%1.1f%%", startangle=120)
    plt.title("Expense Allocation by Category")
    plt.tight_layout()
    plt.show()

def download_report():
    logs = conn.execute("SELECT * FROM ExpenseLog").fetchall()
    if not logs:
        messagebox.showinfo("No Records", "No expense data to export.")
        return

    dataframe = pd.DataFrame(logs, columns=["ID", "Date", "Payee", "Description", "Category", "Amount", "Mode"])
    export_frame = Toplevel(app)
    export_frame.title("Export Report")
    export_frame.configure(bg="#E8EAF6")

    def export_to_csv():
        filename = filedialog.asksaveasfilename(defaultextension=".csv")
        if filename:
            dataframe.to_csv(filename, index=False)
            messagebox.showinfo("Done", f"CSV file saved at: {filename}")

    def export_to_excel():
        filename = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if filename:
            dataframe.to_excel(filename, index=False)
            messagebox.showinfo("Done", f"Excel file saved at: {filename}")

    def export_to_pdf():
        filename = filedialog.asksaveasfilename(defaultextension=".pdf")
        if filename:
            pdf_gen = FPDF()
            pdf_gen.add_page()
            pdf_gen.set_font("Arial", size=10)
            for row in logs:
                for cell in row:
                    pdf_gen.cell(30, 10, str(cell), 1)
                pdf_gen.ln()
            pdf_gen.output(filename)
            messagebox.showinfo("Done", f"PDF file saved at: {filename}")

    Button(export_frame, text="CSV", width=20, bg="#43A047", fg="white", command=export_to_csv).pack(pady=5)
    Button(export_frame, text="Excel", width=20, bg="#1E88E5", fg="white", command=export_to_excel).pack(pady=5)
    Button(export_frame, text="PDF", width=20, bg="#F4511E", fg="white", command=export_to_pdf).pack(pady=5)

# --- Input Section ---
input_container = Frame(app, bg="#FAF9F6")
input_container.pack(pady=10)

Label(input_container, text="Date:", bg="#FAF9F6", font=("Arial", 12)).grid(row=0, column=0)
date_input = DateEntry(input_container, width=15)
date_input.grid(row=0, column=1)

Label(input_container, text="Payee:", bg="#FAF9F6", font=("Arial", 12)).grid(row=1, column=0)
Entry(input_container, textvariable=payee_var, font=("Arial", 12)).grid(row=1, column=1)

Label(input_container, text="Description:", bg="#FAF9F6", font=("Arial", 12)).grid(row=2, column=0)
Entry(input_container, textvariable=description_var, font=("Arial", 12)).grid(row=2, column=1)

Label(input_container, text="Category:", bg="#FAF9F6", font=("Arial", 12)).grid(row=3, column=0)
OptionMenu(input_container, category_var, "General", "Food", "Travel", "Bills", "Health", "Shopping", "Other").grid(row=3, column=1)

Label(input_container, text="Amount (₹):", bg="#FAF9F6", font=("Arial", 12)).grid(row=4, column=0)
Entry(input_container, textvariable=amount_var, font=("Arial", 12)).grid(row=4, column=1)

Label(input_container, text="Payment Mode:", bg="#FAF9F6", font=("Arial", 12)).grid(row=5, column=0)
OptionMenu(input_container, payment_mode_var, "Cash", "Card", "UPI", "Net Banking", "Other").grid(row=5, column=1)

Button(input_container, text="Add Entry", bg="#4CAF50", fg="white", font=("Arial", 12), command=insert_expense).grid(row=6, column=0, pady=10)
Button(input_container, text="Reset", bg="#E53935", fg="white", font=("Arial", 12), command=reset_fields).grid(row=6, column=1)

# --- Table Section ---
table_frame = Frame(app, bg="#FAF9F6")
table_frame.pack(pady=10, fill=X)

headers = ["ID", "Date", "Payee", "Description", "Category", "Amount", "Mode"]
table = ttk.Treeview(table_frame, columns=headers, show="headings")
for head in headers:
    table.heading(head, text=head)
    table.column(head, anchor=CENTER, width=100)
table.pack(fill=BOTH, expand=True)

# --- Controls ---
control_area = Frame(app, bg="#FAF9F6")
control_area.pack(pady=10)

Button(control_area, text="Remove", width=14, bg="#D81B60", fg="white", font=("Arial", 12), command=delete_entry).pack(side=LEFT, padx=5)
Button(control_area, text="Delete All", width=14, bg="#8E24AA", fg="white", font=("Arial", 12), command=clear_all_data).pack(side=LEFT, padx=5)
Button(control_area, text="Total", width=14, bg="#00796B", fg="white", font=("Arial", 12), command=calculate_total).pack(side=LEFT, padx=5)
Button(control_area, text="Bar Chart", width=14, bg="#FFA000", fg="white", font=("Arial", 12), command=generate_chart).pack(side=LEFT, padx=5)
Button(control_area, text="Pie Chart", width=14, bg="#303F9F", fg="white", font=("Arial", 12), command=render_pie_chart).pack(side=LEFT, padx=5)
OptionMenu(control_area, chart_mode, "Method", "Receiver", "Category", "Month").pack(side=LEFT, padx=5)
Button(control_area, text="Export", width=14, bg="#6D4C41", fg="white", font=("Arial", 12), command=download_report).pack(side=LEFT, padx=5)
Button(control_area, text="Exit", width=10, bg="#455A64", fg="white", font=("Arial", 12), command=app.quit).pack(side=RIGHT, padx=10)

# --- Launch ---
refresh_expenses()
app.mainloop()
