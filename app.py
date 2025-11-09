from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")  # deve começar com -100...
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")  # APP_USR-...

def send_tg(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        )
    except Exception as e:
        print("Erro ao enviar TG:", e)

# MP às vezes manda para "/" ou para "/pix". Aceitaremos os dois.
@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json(silent=True, force=True) or {}
    print("Recebido webhook:", data)

    # ✅ AVISO IMEDIATO: se isso não aparecer no grupo, o MP NÃO está chamando sua URL.
    send_tg("📥 *Webhook do MP chegou* (pré-processamento)")

    # Tentar achar o ID do pagamento em diferentes formatos
    payment_id = None
    if isinstance(data.get("data"), dict):
        payment_id = data["data"].get("id")
    if not payment_id:
        payment_id = data.get("id")
    # alguns formatos antigos usam "resource": ".../v1/payments/123456789"
    if not payment_id and isinstance(data.get("resource"), str) and "/payments/" in data["resource"]:
        try:
            payment_id = data["resource"].split("/payments/")[1].split("?")[0].strip("/ ")
        except Exception:
            payment_id = None

    if not payment_id:
        send_tg("⚠️ Webhook recebido, mas sem `payment_id`. Verifique eventos marcados (use *Pagamentos*).")
        return {"ok": False, "reason": "payment id not found"}, 200

    # Busca detalhes do pagamento
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    r = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers)
    print("MP status:", r.status_code, "body:", r.text[:400])

    if r.status_code != 200:
        send_tg(f"❌ Consulta ao MP falhou (HTTP {r.status_code}). ID: {payment_id}")
        return {"ok": False}, 200

    info = r.json()
    amount = float(info.get("transaction_amount", 0) or 0)
    status = (info.get("status") or "").lower()
    payer = info.get("payer", {}).get("email") or info.get("payer", {}).get("first_name") or "Cliente"

    if status == "approved" and amount > 0:
        send_tg(f"💰 *Novo Pix recebido!*\nValor: R$ {amount:.2f}\nCliente: {payer}\nID: `{payment_id}`")
    else:
        send_tg(f"ℹ️ Notificação MP\nStatus: {status or 'desconhecido'}\nID: `{payment_id}`")

    return {"ok": True}, 200

# Compatível com a URL do MP com /pix
@app.route('/pix', methods=['POST'])
def pix_webhook():
    return webhook()

# Rota de status para testar no navegador
@app.route('/', methods=['GET'])
def status():
    return "Bot ativo ✅", 200

# Rota de teste manual (chame no navegador para forçar uma mensagem TG)
@app.route('/test', methods=['GET'])
def test():
    send_tg("✅ Teste manual do servidor (/test).")
    return "Teste enviado ao Telegram.", 200
