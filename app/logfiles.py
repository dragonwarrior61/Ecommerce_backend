LOG_DIR = "/var/www/html/log/"

LOG_UPDATE_AWB = f"{LOG_DIR}update_awb"
LOG_REFRESH_ORDERS = f"{LOG_DIR}refresh_orders"
LOG_GENERATE_INVOICE = f"{LOG_DIR}generate_invoice"
LOG_REFRESH_MONTH_ORDER = f"{LOG_DIR}refresh_month_order"
LOG_SEND_STOCK = f"{LOG_DIR}send_stock"
LOG_REFRESH_STOCK = f"{LOG_DIR}refresh_stock"
LOG_REFRESH_RETURNS = f"{LOG_DIR}refresh_data"

def log_msg_file(filepath: str, content: str):
    file = open(filepath, "+a", encoding="utf-8")
    file.write(f"{content}\n")
    file.close()

def log_update_awb(content: str):
    log_msg_file(LOG_UPDATE_AWB, content)

def log_refresh_orders(content: str):
    log_msg_file(LOG_REFRESH_ORDERS, content)

def log_generate_invoice(content: str):
    log_msg_file(LOG_GENERATE_INVOICE, content)

def log_refresh_month_order(content: str):
    log_msg_file(LOG_REFRESH_MONTH_ORDER, content)

def log_send_stock(content: str):
    log_msg_file(LOG_SEND_STOCK, content)

def log_refresh_stock(content: str):
    log_msg_file(LOG_REFRESH_STOCK, content)

def log_refresh_returns(content: str):
    log_msg_file(LOG_REFRESH_RETURNS, content)
