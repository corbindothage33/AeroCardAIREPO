import os
import time
import hmac
import hashlib
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)

MASTER_SALT = b"AEROCARD_CORBIN_DOTHAGE_SOLE_CREATOR_2026_VAULT"

# Stores paid status by HWID and by IP address:
# PAID_HWIDS[hwid] = {"tier": tier_code, "key": license_key, "ts": timestamp}
PAID_HWIDS = {}
# Tracks pending checkouts by IP and most recent session so Stripe redirects always know the buyer's HWID
PENDING_BY_IP = {}
LATEST_PENDING = {"hwid": "UNIVERSAL", "tier": "SUB1999", "email": ""}

STRIPE_LINKS = {
    "PROMO10": os.environ.get("STRIPE_PROMO10_URL", "https://buy.stripe.com/eVq14obPX14n2oB1zMbMQ01"),
    "SUB1999": os.environ.get("STRIPE_SUB1999_URL", "https://buy.stripe.com/eVq14obPX14n2oB1zMbMQ01"),
    "PERP1000": os.environ.get("STRIPE_PERP1000_URL", "https://buy.stripe.com/6oU8wQg6d3cv5ANbambMQ02"),
}

def normalize_tier(raw_tier):
    t = (raw_tier or "SUB1999").upper().replace("_", "").strip()
    if "PROMO" in t or "10" == t:
        return "PROMO10"
    if "1000" in t or "PERP" in t:
        return "PERP1000"
    return "SUB1999"

def get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"

def generate_key(hwid, tier_code):
    clean_tier = normalize_tier(tier_code)
    clean_hwid = (hwid or "UNIVERSAL").strip().upper()
    seed = f"{clean_hwid}|{clean_tier}|CORBIN_DOTHAGE_MASTER"
    digest = hmac.new(MASTER_SALT, seed.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    return f"AERO-{clean_tier}-{digest[:4]}-{digest[4:8]}-{digest[8:12]}"

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

@app.route("/api/register-checkout", methods=["POST", "GET"])
def register_checkout():
    """Registers the buyer's HWID + IP before opening Stripe so the redirect always knows their machine."""
    hwid = (request.args.get("hwid") or "").strip().upper()
    tier = normalize_tier(request.args.get("tier", "SUB1999"))
    email = (request.args.get("email") or "").strip()
    client_ip = get_client_ip()

    if hwid:
        PENDING_BY_IP[client_ip] = {"hwid": hwid, "tier": tier, "email": email, "ts": time.time()}
        LATEST_PENDING["hwid"] = hwid
        LATEST_PENDING["tier"] = tier
        LATEST_PENDING["email"] = email

    return jsonify({"registered": True, "hwid": hwid, "tier": tier, "ip": client_ip})

@app.route("/pay")
def pay_redirect():
    tier = normalize_tier(request.args.get("tier", "SUB1999"))
    hwid = (request.args.get("client_reference_id") or request.args.get("hwid") or "").strip().upper()
    email = (request.args.get("prefilled_email") or request.args.get("email") or "").strip()
    client_ip = get_client_ip()

    if hwid:
        PENDING_BY_IP[client_ip] = {"hwid": hwid, "tier": tier, "email": email, "ts": time.time()}
        LATEST_PENDING["hwid"] = hwid
        LATEST_PENDING["tier"] = tier
        LATEST_PENDING["email"] = email

    base_link = STRIPE_LINKS.get(tier, STRIPE_LINKS["SUB1999"])
    sep = "&" if "?" in base_link else "?"
    target = f"{base_link}{sep}client_reference_id={hwid}"
    if email:
        target += f"&prefilled_email={email}"
    return redirect(target)

@app.route("/payment-success")
def payment_success():
    """
    Called automatically when Stripe finishes checkout.
    Configure your Stripe Payment Links 'After payment -> Redirect to website' to:
    https://aerocardairepo-1.onrender.com/payment-success?tier=SUB1999
    (or ?tier=PERP1000)
    """
    client_ip = get_client_ip()
    pending = PENDING_BY_IP.get(client_ip) or LATEST_PENDING

    hwid = (request.args.get("hwid") or request.args.get("client_reference_id") or pending.get("hwid") or "UNIVERSAL").strip().upper()
    tier = normalize_tier(request.args.get("tier") or pending.get("tier") or "SUB1999")

    hw_key = generate_key(hwid, tier)
    uni_key = generate_key("UNIVERSAL", tier)

    # Mark both the specific HWID and the buyer's IP as paid so the desktop app auto-unlocks within 5 seconds
    record = {"tier": tier, "key": hw_key, "universal_key": uni_key, "ts": time.time()}
    PAID_HWIDS[hwid] = record
    PAID_HWIDS[f"IP:{client_ip}"] = record

    return f'''
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>AeroCardAIStudio™ — License Activation Key</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="font-family:'Segoe UI',sans-serif;text-align:center;padding:40px 20px;background:#0f172a;color:#f8fafc;">
        <div style="max-width:640px;margin:auto;background:#1e293b;border:2px solid #10b981;border-radius:12px;padding:32px;box-shadow:0 10px 25px rgba(0,0,0,0.4);">
            <h1 style="color:#10b981;margin-top:0;">✅ Payment Confirmed & License Generated!</h1>
            <p style="color:#cbd5e1;font-size:16px;">If your <b>AeroCard Professional</b> desktop app is open, it is <b>unlocking itself automatically right now</b> (within 5 seconds).</p>
            
            <div style="background:#0f172a;border:1px solid #38bdf8;border-radius:8px;padding:20px;margin:25px 0;">
                <div style="color:#94a3b8;font-size:13px;text-transform:uppercase;letter-spacing:1px;">Your Workstation Activation Key ({hwid})</div>
                <div id="hwkey" style="color:#38bdf8;font-family:Consolas,monospace;font-size:24px;font-weight:bold;margin:12px 0;user-select:all;">{hw_key}</div>
                <button onclick="navigator.clipboard.writeText('{hw_key}');this.innerText='✅ Copied to Clipboard!';" style="background:#0284c7;color:white;border:none;padding:10px 22px;border-radius:6px;font-weight:bold;cursor:pointer;font-size:14px;">📋 Copy Activation Key</button>
            </div>

            <div style="background:#0f172a;border:1px solid #475569;border-radius:8px;padding:14px;margin-top:18px;">
                <div style="color:#94a3b8;font-size:12px;">Backup Universal Activation Key (Works if you bought from your phone or another PC):</div>
                <div style="color:#10b981;font-family:Consolas,monospace;font-size:17px;font-weight:bold;margin-top:6px;user-select:all;">{uni_key}</div>
            </div>

            <p style="color:#94a3b8;font-size:13px;margin-top:24px;">
                <b>How to activate manually if needed:</b> Open AeroCard Professional ➔ Go to Tab 10 (<b>🔐 License & Billing</b>) ➔ Paste the key above into <b>Paste Activation Key</b> and click <b>🔑 Activate Key</b>.
            </p>
        </div>
    </body>
    </html>
    '''

@app.route("/api/check-license")
def check_license():
    hwid = (request.args.get("hwid") or "").strip().upper()
    client_ip = get_client_ip()

    rec = PAID_HWIDS.get(hwid) or PAID_HWIDS.get(f"IP:{client_ip}")
    if rec:
        tier = rec["tier"]
        key_for_machine = generate_key(hwid, tier) if hwid else rec["universal_key"]
        return jsonify({
            "paid": True,
            "active": True,
            "tier": tier,
            "license_key": key_for_machine
        })
    return jsonify({"paid": False, "active": False})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
