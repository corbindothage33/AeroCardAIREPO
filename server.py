import os
import hmac
import hashlib
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)

MASTER_SALT = b"AEROCARD_CORBIN_DOTHAGE_SOLE_CREATOR_2026_VAULT"
PAID_HWIDS = {}

# Active subscription & perpetual license tiers linked to Stripe (including PROMO10)
STRIPE_LINKS = {
    "PROMO10": os.environ.get("STRIPE_PROMO10_URL", "https://buy.stripe.com/3cIeVecU1cN5fbn0vIbMQ00"),
    "SUB1999": os.environ.get("STRIPE_SUB1999_URL", "https://buy.stripe.com/3cIeVecU1cN5fbn0vIbMQ00"),
}

def generate_key(hwid, tier_code):
    seed = f"{hwid}|{tier_code}|CORBIN_DOTHAGE_MASTER"
    digest = hmac.new(MASTER_SALT, seed.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    return f"AERO-{tier_code}-{digest[:4]}-{digest[4:8]}-{digest[8:12]}"

@app.route("/", methods=["GET"])
def home():
    return '''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>AeroCardAIStudio™ — Official Sports Card & TCG Software</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 0; }
            .header { background: #1e293b; padding: 28px 20px; text-align: center; border-bottom: 2px solid #0284c7; }
            .header h1 { margin: 0; color: #38bdf8; font-size: 28px; }
            .header p { margin: 8px 0 0; color: #94a3b8; font-size: 15px; }
            .container { max-width: 960px; margin: 40px auto; padding: 0 20px; }
            .cards { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
            .card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 25px; width: 270px; text-align: center; display: flex; flex-direction: column; justify-content: space-between; }
            .card h3 { color: #38bdf8; margin-top: 0; }
            .price { font-size: 26px; font-weight: bold; color: #10b981; margin: 15px 0; }
            .btn { background: #0284c7; color: white; border: none; padding: 12px 20px; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 15px; }
            .btn:hover { background: #0369a1; }
            .footer { text-align: center; padding: 30px; color: #64748b; font-size: 13px; border-top: 1px solid #1e293b; margin-top: 50px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>AeroCardAIStudio™</h1>
            <p>Professional Sports Card & TCG Computer Vision Grading & Market Valuation Suite</p>
            <p style="font-size:13px; color:#cbd5e1;">Sole Creator & Owner: Corbin Dothage</p>
        </div>
        <div class="container">
            <h2 style="text-align:center; margin-bottom:30px;">Official Software Licensing & Subscriptions</h2>
            <div class="cards">
                <div class="card">
                    <div>
                        <h3>First-Time Email Promo</h3>
                        <div class="price">$10.00 / mo</div>
                        <p style="color:#cbd5e1; font-size:14px;">First 3 months ($10/mo then $19.99/mo). Unlocks all 9 desktop modules & deal finder.</p>
                    </div>
                    <a href="/pay?tier=PROMO10" class="btn">Select Promo Tier</a>
                </div>
                <div class="card">
                    <div>
                        <h3>Cloud Subscription</h3>
                        <div class="price">$19.99 / mo</div>
                        <p style="color:#cbd5e1; font-size:14px;">Monthly recurring license. Unlocks all 9 desktop grading modules, live comps, and deal finder.</p>
                    </div>
                    <a href="/pay?tier=SUB1999" class="btn">Select Subscription</a>
                </div>
                <div class="card">
                    <div>
                        <h3>Full Perpetual License</h3>
                        <div class="price">$1,000.00</div>
                        <p style="color:#cbd5e1; font-size:14px;">One-time flat payment. Permanent lifetime commercial workstation license with zero recurring monthly fees.</p>
                    </div>
                    <a href="/pay?tier=PERP1000" class="btn" style="background:#059669;">Buy Perpetual License</a>
                </div>
            </div>
        </div>
        <div class="footer">
            © 2026 AeroCardAIStudio™ — Created by Corbin Dothage. All Rights Reserved.
        </div>
    </body>
    </html>
    '''

@app.route("/pay")
def pay_redirect():
    tier = request.args.get("tier", "SUB1999")
    hwid = request.args.get("client_reference_id", "")
    email = request.args.get("prefilled_email", "")
    base_link = STRIPE_LINKS.get(tier, STRIPE_LINKS["SUB1999"])
    sep = "&" if "?" in base_link else "?"
    return redirect(f"{base_link}{sep}client_reference_id={hwid}&prefilled_email={email}")

@app.route("/payment-success")
def payment_success():
    hwid = request.args.get("hwid", "")
    tier = request.args.get("tier", "SUB1999")
    if hwid:
        PAID_HWIDS[hwid] = tier
        key = generate_key(hwid, tier)
        return f"<body style='font-family:sans-serif;text-align:center;padding:50px;background:#0f172a;color:#10b981;'><h2>✅ Payment Verified!</h2><p style='color:#f8fafc;'>Your Workstation (<b>{hwid}</b>) is unlocking automatically.</p><p style='color:#38bdf8;'>Activation Key: <b>{key}</b></p></body>"
    return "<h2>Thank you for your purchase!</h2>"

@app.route("/api/check-license")
def check_license():
    hwid = request.args.get("hwid", "")
    tier = PAID_HWIDS.get(hwid)
    if tier:
        return jsonify({"paid": True, "active": True, "license_key": generate_key(hwid, tier)})
    return jsonify({"paid": False, "active": False})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
