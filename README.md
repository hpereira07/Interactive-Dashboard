# 📊 Interactive PS2 Dashboard

An **interactive dashboard** built to visualize and analyze data from **.PS2 banking files**, commonly used for **direct debit and batch financial operations in Portugal**.

This project complements the **PS2 File Generator**:
- 🛠️ The generator creates `.PS2` files  
- 📊 This dashboard reads and displays their data  

---

## 📌 Overview

This application allows users to:

- Read `.PS2` files from a data directory  
- Extract structured financial information  
- Display it through an **interactive dashboard interface**  

The goal is to **simplify the interpretation of PS2 files**, making otherwise raw text data easy to understand through visual and tabular representations.

---

## ⚙️ Features

- ✅ Automatic reading of `.PS2` files  
- ✅ Data extraction from PS2 structured records  
- ✅ Interactive dashboard interface (Shiny for Python)  
- ✅ Data visualization (charts, tables, comparisons)  
- ✅ User-friendly presentation of transactions  
- ✅ Real-time updates when files change  

---

## 🧩 How It Works

1. The application scans the `/data` directory  
2. Reads `.PS2` files  
3. Parses the structured records:
   - Header (file metadata)  
   - Transactions (movements)  
   - Footer (totals)  
4. Displays the processed data in a dashboard  

---

## ▶️ How to Run

### 1. Requirements

Make sure you have Python installed and the required libraries (e.g., Shiny for Python).

### 2. Run the Dashboard

```bash
shiny run --reload --port 8000 app.py
```

---

## ⚠️ Important Note

The `app.py` file must be **outside the `src/` folder**, in the root directory of the project.

This is required because the application is configured to read `.PS2` files from the `/data` directory.

---

## 📊 Dashboard Features

The dashboard includes:

- 📈 Graphical representations (e.g., line charts, comparisons)  
- 📋 Tabular data views  
- 🔍 Transaction analysis  
- 👥 Client-based comparisons  
- 💡 Interactive UI elements for better usability

---

## 📄 Documentation

Project documentation was generated using **Doxygen**.

To open it:
```/ref/docs/build/html/index.html```

---

## 🎓 Academic Context

This project was developed as part of the **Computer Labs** course in the **Computer Systems Engineering degree**.

It demonstrates:

- Data parsing and processing in Python  
- Visualization of structured financial data  
- Development of interactive dashboards  
- Application of real-world file formats (.PS2)  
- Team collaboration using Git and GitHub

---

## 🔗 Related Project

👉 **PS2 File Generator**  
This dashboard was designed to work alongside the PS2 file generator project, forming a complete pipeline:

---

## 📜 License

This project is provided for **educational purposes only**.

You are free to:
- Use the code for learning and academic reference  

However:
- It is not intended for production financial use  
- No guarantees are provided regarding correctness or compliance

---

## 👤 Author

**Henrique Santos Pereira**  
Computer Systems Engineering Student  

GitHub: https://github.com/hpereira07
