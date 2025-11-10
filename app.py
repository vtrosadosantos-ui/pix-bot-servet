from flask import Flask, request, jsonify
import requests, os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")

TG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def tg(msg):
    try:
        requests.post(TG_URL, json={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Erro enviando TG:", e)

@app.get("/")
def health():
    return "Servidor ativo ✅", 200

# Aceita GET e POST, porque o MP às vezes envia dados na querystring
@app.route("/", methods=["POST", "GET"])
def webhook():
    # 1) Tenta ler JSON (pode não existir)
    try:
        data = request.get_json(force=False, silent=True) or {}
    except:
        data = {}

    # 2) Lê parâmetros de query (ex.: ?type=payment&data_id=123...)
    args = request.args or {}

    # 3) Coleta o máximo de pistas do ID e do tipo
    live_mode = data.get("live_mode")
    payment_id = (
        (data.get("data") or {}).get("id")
        or data.get("id")
        or args.get("data.id")
        or args.get("data_id")
        or args.get("id")
    )
    event_type = (
        data.get("type")
        or data.get("topic")
        or args.get("type")
        or args.get("topic")
    )

    # DEBUG pré-processamento
    tg(f"📩 Webhook do MP chegou (pré)\nlive_mode={live_mode}\nid={payment_id}\ntype={event_type}")

    # Ignora eventos de teste do painel
    if str(payment_id) == "123456" or live_mode is False:
        return jsonify({"ok": True, "ignored": "test_event"}), 200

    if not payment_id:
        # Loga o bruto para diagnóstico
        tg("⚠️ Webhook sem payment_id. Vou logar bruto nos logs do Render.")
        print("RAW JSON:", data)
        print("RAW ARGS:", dict(args))
        return jsonify({"ok": False, "msg": "no payment id"}), 200  # 200 para não re-tentar

    # 4) Consulta detalhes do pagamento
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        tg(f"❌ Consulta ao MP falhou (HTTP {r.status_code}).\nID: {payment_id}")
        print("MP RESP:", r.status_code, r.text)
        return jsonify({"ok": False, "mp_status": r.status_code}), 200

    info = r.json()
    amount = info.get("transaction_amount", 0)
    status = info.get("status", "desconhecido")
    payer = info.get("payer", {}).get("email") or info.get("payer", {}).get("first_name") or "Cliente"

    if status == "approved":
        tg(f"💰 Novo Pix recebido!\nValor: R$ {float(amount):.2f}\nCliente: {payer}\nID: {payment_id}")
    else:
        tg(f"ℹ️ Pagamento status: {status}\nID: {payment_id}")

    return jsonify({"ok": True}), 200
