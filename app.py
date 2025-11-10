from flask import Flask, request, jsonify, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")

TG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def tg(msg):
    try:
        requests.post(TG_URL, json={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Erro enviando ao Telegram:", e)

@app.get("/")
def home():
    return "Servidor ativo ✅", 200

# Envia uma mensagem de teste pro seu grupo: /send?msg=Ola
@app.get("/send")
def send():
    msg = request.args.get("msg", "teste")
    tg(f"🔔 Teste: {msg}")
    return "ok", 200

@app.post("/")
def webhook():
    data = request.get_json(force=True) or {}
    # 1) Aviso pré-processamento (DEBUG)
    live = data.get("live_mode")
    pid = (data.get("data") or {}).get("id") or data.get("id")
    tg(f"📩 Webhook do MP chegou (pré)\nlive_mode={live}\nid={pid}")

    # 2) Ignora testes do painel (evita 401 e SPAM)
    if str(pid) == "123456" or live is False:
        return jsonify({"ok": True, "ignored": "test_event"}), 200

    if not pid:
        tg("⚠️ Webhook sem payment_id.")
        return jsonify({"ok": False, "msg": "no payment id"}), 400

    # 3) Consulta detalhes do pagamento
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    url = f"https://api.mercadopago.com/v1/payments/{pid}"
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        tg(f"❌ Consulta ao MP falhou (HTTP {r.status_code}).\nID: {pid}")
        return jsonify({"ok": False, "mp_status": r.status_code}), 200

    info = r.json()
    amount = info.get("transaction_amount", 0)
    status = info.get("status", "desconhecido")
    payer = info.get("payer", {}).get("email") or info.get("payer", {}).get("first_name") or "Cliente"

    if status == "approved":
        tg(f"💰 Novo Pix recebido!\nValor: R$ {amount:.2f}\nCliente: {payer}\nID: {pid}")
    else:
        tg(f"ℹ️ Pagamento status: {status}\nID: {pid}")

    return jsonify({"ok": True}), 200
