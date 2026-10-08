import itertools
import os
import random
import sqlite3
from datetime import date, timedelta

random.seed(42)
DB_PATH = "./data/database.sqlite"

MONTH_TOTALS = {
    1: 3_600_000, 2: 3_700_000, 3: 3_900_000,
    4: 3_800_000, 5: 3_900_000, 6: 4_000_000,
    7: 3_800_000, 8: 3_700_000, 9: 4_000_000,
}
REGION_SHARES = {"North America": 0.50, "EMEA": 0.30, "APAC": 0.14}  # LATAM = remainder

Q4_REGIONAL = {
    10: {"North America": 2_150_000, "EMEA": 1_300_000, "APAC": 750_000, "LATAM": 300_000},
    11: {"North America": 2_200_000, "EMEA": 1_300_000, "APAC": 800_000, "LATAM": 300_000},
    12: {"North America": 2_550_000, "EMEA": 1_500_000, "APAC": 850_000, "LATAM": 200_000},
}

PRODUCTS = {  # product: (share of revenue, typical unit price)
    "Platform": (0.55, 1200),
    "Analytics Suite": (0.30, 800),
    "Support Services": (0.15, 450),
}


def regional_revenue(month: int) -> dict:
    if month in Q4_REGIONAL:
        return Q4_REGIONAL[month]
    total = MONTH_TOTALS[month]
    out = {r: round(total * s / 1000) * 1000 for r, s in REGION_SHARES.items()}
    out["LATAM"] = total - sum(out.values())
    return out


def split_by_product(total: int) -> dict:
    items = list(PRODUCTS.items())
    parts, remaining = {}, total
    for name, (share, _) in items[:-1]:
        amount = round(total * share / 100) * 100
        parts[name] = amount
        remaining -= amount
    parts[items[-1][0]] = remaining
    return parts


def build_sales() -> list[tuple]:
    rows = []
    for month in range(1, 13):
        for region, region_total in regional_revenue(month).items():
            for product, revenue in split_by_product(region_total).items():
                price = PRODUCTS[product][1] * random.uniform(0.9, 1.1)
                units = max(1, round(revenue / price))
                sale_date = date(2025, month, random.randint(1, 28)).isoformat()
                rows.append((region, product, revenue, sale_date, units))
    return rows


INDUSTRIES = ["Financial Services", "Healthcare", "Retail", "Manufacturing",
              "Technology", "Energy", "Telecommunications", "Logistics"]
PREFIXES = ["Apex", "Blue", "Crest", "Delta", "Evergreen", "Falcon", "Granite",
            "Harbor", "Ion", "Juniper"]
MIDDLES = ["Holdings", "Systems", "Partners", "Group", "Labs", "Industries",
           "Networks", "Solutions", "Dynamics", "Global"]
ENDINGS = ["Inc", "Ltd", "Corp"]


def build_customers(total: int = 250, churned: int = 28) -> list[tuple]:
    names = [f"{p} {m} {e}" for p, m, e in itertools.product(PREFIXES, MIDDLES, ENDINGS)]
    random.shuffle(names)
    churn_ids = set(random.sample(range(total), churned))
    rows = []
    for i in range(total):
        if i in churn_ids:
            churn_date = (date(2025, 1, 1) + timedelta(days=random.randint(0, 364))).isoformat()
            score = random.choice([2.0, 2.5, 3.0, 3.0, 3.5])
        else:
            churn_date = None
            score = random.choice([4.0, 4.0, 4.5, 4.5, 4.5, 5.0, 5.0])
        rows.append((names[i], random.choice(INDUSTRIES), churn_date, score))
    return rows


DEPARTMENTS = {  # name: (headcount, mean satisfaction on a 1-5 scale)
    "Engineering": (170, 3.4),
    "Customer Support": (80, 3.2),
    "Sales": (70, 3.6),
    "Customer Success": (60, 3.7),
    "G&A": (94, 3.95),
}


def build_employees() -> list[tuple]:
    rows = []
    for dept, (count, mean) in DEPARTMENTS.items():
        for _ in range(count):
            score = min(5.0, max(1.0, round(random.gauss(mean, 0.6), 1)))
            rows.append((dept, score, round(random.uniform(0.2, 12.0), 1)))
    return rows


def main():
    os.makedirs("./data", exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT, product TEXT, revenue REAL, date TEXT, units_sold INTEGER
        );
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, industry TEXT, churn_date TEXT, satisfaction_score REAL
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT, satisfaction_score REAL, tenure_years REAL
        );
    """)
    cur.executemany("INSERT INTO sales (region, product, revenue, date, units_sold) VALUES (?,?,?,?,?)", build_sales())
    cur.executemany("INSERT INTO customers (name, industry, churn_date, satisfaction_score) VALUES (?,?,?,?)", build_customers())
    cur.executemany("INSERT INTO employees (department, satisfaction_score, tenure_years) VALUES (?,?,?)", build_employees())
    conn.commit()

    print("Rows:", {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in ("sales", "customers", "employees")})
    print("FY2025 revenue:", cur.execute("SELECT SUM(revenue) FROM sales").fetchone()[0])
    print("Churn rate %:", cur.execute(
        "SELECT ROUND(100.0 * SUM(churn_date IS NOT NULL) / COUNT(*), 1) FROM customers").fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()