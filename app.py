from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    print("Recebido webhook:", data)

    payment_id = None
    if isinstance(data.get("data"), dict):
        payment_id = data["data"].get("id")

    if not payment_id:
        payment_id = data.get("id")

    if not payment_id:
        print("Nenhum ID encontrado")
        return {"ok": False}, 400

    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    r = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers)
    payment_info = r.json()

    amount = payment_info.get("transaction_amount", 0)
    status = payment_info.get("status", "")
    payer = payment_info.get("payer", {}).get("email", "Cliente")

    if status == "approved":
        msg = f"💰 *Novo Pix recebido!*\nValor: R$ {amount:.2f}\nCliente: {payer}"
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        )

    return {"ok": True}, 200

@app.route('/')
def home():
    return "Bot ativo ✅", 200
