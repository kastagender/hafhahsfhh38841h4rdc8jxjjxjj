import gspread
import os
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

spreadsheet_id = os.getenv("SHEET_ID")
sheet = client.open_by_key(spreadsheet_id).sheet1


# === Orders ===
def append_order(order: dict):
    row = [
        order.get("name", "—"),
        order.get("item", "—"),
        order.get("price", "—"),
        order.get("prepay", "—"),
        "", "", "", "Оформлен",
        order.get("manager", "—"),
        order.get("comment", "—")
    ]
    sheet.append_row(row)
    format_row(len(sheet.get_all_values()), "Оформлен")


def get_orders():
    data = sheet.get_all_values()
    return [(i+2, f"{row[0]} | {row[1]} | {row[2]} грн | Статус: {row[7]}")
            for i, row in enumerate(data[1:]) if len(row) >= 8 and row[7] != "Получено"]


def update_order_status(row_index: int, status: str):
    sheet.update_cell(row_index, 8, status)
    format_row(row_index, status)


def format_row(row_index: int, status: str):
    color = {
        "Оформлен": {"red": 1, "green": 0.6, "blue": 0},
        "Идёт доставка": {"red": 1, "green": 1, "blue": 0},
        "Получено": {"red": 0.6, "green": 1, "blue": 0.6},
    }.get(status, {"red": 1, "green": 1, "blue": 1})

    requests = [{
        "repeatCell": {
            "range": {
                "sheetId": sheet.id,
                "startRowIndex": row_index - 1,
                "endRowIndex": row_index,
                "startColumnIndex": 0,
                "endColumnIndex": 10,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": color
                }
            },
            "fields": "userEnteredFormat.backgroundColor"
        }
    }]

    client.session.post(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        json={"requests": requests},
        headers={"Authorization": "Bearer " + creds.token}
    )


def get_analytics():
    data = sheet.get_all_values()[1:]  # skip header
    total = len([r for r in data if len(r) >= 8])
    done = len([r for r in data if len(r) >= 8 and r[7] == "Получено"])
    not_done = total - done
    return done, not_done


# === PROMOS ===
def add_promo_code(code):
    col_k = sheet.col_values(11)  # column K = 11
    idx = len(col_k) + 1 if len(col_k) >= 2 else 2
    sheet.update_cell(idx, 11, f"PROMO:{code}")


def get_all_promos():
    all_rows = sheet.col_values(11)
    return [x.replace("PROMO:", "") for x in all_rows if x.startswith("PROMO:")]


def use_promo_code(username, price, payout):
    col_l = sheet.col_values(12)  # column L = 12
    idx = len(col_l) + 1 if len(col_l) >= 2 else 2
    sheet.update(f"L{idx}:O{idx}", [[username, str(price), str(payout), datetime.now().strftime('%Y-%m-%d %H:%M')]])


def get_used_promos():
    col = sheet.col_values(12)  # column L
    return [x for x in col[1:] if x.strip() != ""]

def get_motivation():
    from random import choice
    quotes = [
        "Действие — ключ к успеху!",
        "Ты делаешь круто! Продолжай в том же духе!",
        "Каждый заказ — шаг к вершине!",
        "Работа сегодня — результат завтра!",
        "Трудись, и всё получится!"
    ]
    return choice(quotes)
