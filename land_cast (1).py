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
