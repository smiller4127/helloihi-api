# rentcast_land_comp_api.py

from flask import Flask, request, jsonify
import requests
import statistics

app = Flask(__name__)

# 🔐 Use your real API key here or load from environment variable
RENTCAST_API_KEY = "669b3a7e48ba411eb08e117820acfba7"

@app.route("/rentcast_land_comp", methods=["POST"])
def rentcast_land_comp():
    data = request.get_json()
    address = data.get("address")

    if not address:
        return jsonify({"error": "Missing address"}), 400

    try:
        # 🔌 Call RentCast API with the provided address
        response = requests.get(
            f"https://api.rentcast.io/v1/properties/rental-estimate?address={address}",
            headers={"X-Api-Key": RENTCAST_API_KEY}
        )

        if response.status_code != 200:
            return jsonify({
                "error": "RentCast API request failed.",
                "status_code": response.status_code,
                "response": response.text
            }), 400

        data = response.json()
        comps = data.get("rental_comps", [])
        prices = [comp.get("price", 0) for comp in comps if comp.get("price")]

        if not prices:
            return jsonify({"error": "No rental comps found."}), 404

        avg_rent = round(statistics.mean(prices), 2)
        estimated_home_price = round(avg_rent / 0.008, 2)  # 0.8% rent-to-value ratio
        land_value = round(estimated_home_price * 0.10, 2)
        offer_price = round(land_value * 0.70, 2)

        return jsonify({
            "address": address,
            "average_rent": f"${avg_rent:,.2f}",
            "estimated_home_price": f"${estimated_home_price:,.2f}",
            "land_value_10_percent": f"${land_value:,.2f}",
            "recommended_offer_70_percent": f"${offer_price:,.2f}",
            "rental_comps_used": len(prices)
        })

    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# ✅ To run: python rentcast_land_comp_api.py
if __name__ == "__main__":
    app.run(debug=True, port=5000)

from flask import request
from twilio.twiml.messaging_response import MessagingResponse
import datetime

inbox_log = []

@app.route("/incoming", methods=["POST"])
def incoming_sms():
    from_number = request.form.get("From")
    body = request.form.get("Body")
    timestamp = datetime.datetime.now().isoformat()

    log_entry = {
        "from": from_number,
        "body": body,
        "received_at": timestamp
    }
    inbox_log.append(log_entry)

    print(f"📥 Received message from {from_number}: {body}")

    resp = MessagingResponse()
    resp.message("Thanks for your message! We'll get back to you shortly.")
    return str(resp)

@app.route("/inbox", methods=["GET"])
def get_inbox():
    return jsonify(inbox_log)


from flask import request

stored_leads = []  # Replace with DB or persistent storage if needed

@app.route("/upload-leads", methods=["POST"])
def upload_leads():
    leads = request.json
    if not isinstance(leads, list):
        return {"error": "Invalid format"}, 400

    for lead in leads:
        if "name" in lead and "phone" in lead:
            stored_leads.append(lead)

    return {"message": f"{len(leads)} leads uploaded."}, 200

@app.route("/leads", methods=["GET"])
def get_leads():
    return jsonify(stored_leads)


from datetime import datetime, timedelta
import threading

scheduled_messages = []

def send_scheduled_message(msg):
    print(f"⏰ Scheduled message going out to {msg['to']} at {datetime.now()}: {msg['message']}")
    # Here you would use Twilio API to actually send it

@app.route("/schedule", methods=["POST"])
def schedule_message():
    data = request.json
    required = {"to", "message", "send_at"}
    if not all(k in data for k in required):
        return {"error": "Missing required fields"}, 400

    try:
        send_time = datetime.fromisoformat(data["send_at"])
        delay = (send_time - datetime.now()).total_seconds()
        if delay < 0:
            return {"error": "Time must be in the future"}, 400

        msg = {
            "to": data["to"],
            "message": data["message"],
            "send_at": data["send_at"]
        }
        scheduled_messages.append(msg)
        threading.Timer(delay, send_scheduled_message, args=[msg]).start()
        return {"message": "Message scheduled"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/scheduled", methods=["GET"])
def get_scheduled():
    return jsonify(scheduled_messages)


@app.route("/conversation/<phone>", methods=["GET"])
def get_conversation(phone):
    conv = []

    # Pull from inbox (received messages)
    for msg in inbox_messages:
        if msg.get("from") == phone:
            conv.append({
                "type": "inbound",
                "body": msg.get("body"),
                "timestamp": msg.get("received_at")
            })

    # Pull from responseLog (sent messages)
    for msg in response_log:
        if msg.get("to") == phone:
            conv.append({
                "type": "outbound",
                "body": msg.get("message"),
                "timestamp": msg.get("timestamp", "N/A")
            })

    conv.sort(key=lambda x: x["timestamp"])
    return jsonify(conv)


# Simulated in-memory database of leads
lead_db = {}

@app.route("/lead/<phone>", methods=["GET"])
def get_lead(phone):
    lead = lead_db.get(phone, {})
    return jsonify(lead)

@app.route("/lead/<phone>", methods=["POST"])
def update_lead(phone):
    data = request.json
    if not data:
        return {"error": "Missing data"}, 400
    if phone not in lead_db:
        lead_db[phone] = {}

    lead_db[phone].update(data)
    return {"message": "Lead updated", "lead": lead_db[phone]}


from datetime import datetime, timedelta

# Simulate scheduled drips
drip_queue = []

# Add background drip check (for demo: callable manually)
@app.route("/run-drip-check", methods=["GET"])
def run_drip_check():
    now = datetime.utcnow()
    results = []

    for lead in lead_db:
        data = lead_db[lead]
        last_sent = None
        last_reply = None

        # Pull last sent
        for msg in reversed(response_log):
            if msg.get("to") == lead:
                last_sent = datetime.strptime(msg.get("timestamp"), "%Y-%m-%d %H:%M:%S")
                break

        # Pull last reply
        for msg in reversed(inbox_messages):
            if msg.get("from") == lead:
                last_reply = datetime.strptime(msg.get("received_at"), "%Y-%m-%d %H:%M:%S")
                break

        # If sent but no reply in 3+ days, drip follow-up
        if last_sent and (not last_reply or (now - last_reply).days >= 3):
            follow_up = {
                "to": lead,
                "message": "Hey just following up—any thoughts on our last message?",
                "send_at": (now + timedelta(minutes=1)).isoformat()
            }
            drip_queue.append(follow_up)
            results.append(follow_up)

    return jsonify({"scheduled_drips": results})


# Detect DNC replies
@app.route("/check-dnc", methods=["GET"])
def check_dnc():
    keywords = ["stop", "remove", "no more", "unsubscribe"]
    flagged = []

    for msg in inbox_messages:
        body = msg.get("body", "").lower()
        sender = msg.get("from")
        if any(word in body for word in keywords):
            if sender in lead_db:
                lead_db[sender]["status"] = "DNC"
                flagged.append(sender)

    return jsonify({"flagged_dnc": flagged})
