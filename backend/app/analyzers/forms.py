"""
CyberShield Form Analyzer

Phase 1
--------
Responsibilities

✓ Detect forms
✓ Count forms
✓ Extract form metadata
✓ Count inputs
✓ Count buttons
✓ Count textareas
✓ Count selects

Future Phases

✓ Login detection
✓ Password fields
✓ OTP forms
✓ Credit card forms
✓ Hidden inputs
✓ File uploads
✓ External actions
✓ CSRF detection
✓ Autofill detection
✓ Suspicious forms
"""

from urllib.parse import urlparse
from bs4 import BeautifulSoup

from app.models.browser_session import BrowserSession


class FormAnalyzer:
    """
    Analyze HTML forms.
    """

    async def analyze(
        self,
        browser_session: BrowserSession,
    ) -> dict:

        html = browser_session.html

        if not html:

            return {
                "forms_available": False,
                "error": "No rendered HTML available.",
            }

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        result = {
            # ---------------------------------
            # General
            # ---------------------------------
            "forms_available": True,
            "form_count": 0,
            # ---------------------------------
            # Form Details
            # ---------------------------------
            "forms": [],
            # ---------------------------------
            # Statistics
            # ---------------------------------
            "total_inputs": 0,
            "total_buttons": 0,
            "total_textareas": 0,
            "total_selects": 0,
            # ---------------------------------
            # Field Statistics
            # ---------------------------------
            "password_fields": 0,
            "email_fields": 0,
            "username_fields": 0,
            "hidden_inputs": 0,
            "file_upload_fields": 0,
            "otp_fields": 0,
            "credit_card_fields": 0,
            "phone_fields": 0,
            "search_fields": 0,
            "checkbox_fields": 0,
            "radio_fields": 0,
            "submit_buttons": 0,
            # ---------------------------------
            # Form Security
            # ---------------------------------
            "external_actions": [],
            "insecure_actions": [],
            "javascript_actions": [],
            "empty_actions": 0,
            "missing_actions": 0,
            "cross_domain_actions": 0,
            "get_login_forms": 0,
            "suspicious_forms": [],
            # ---------------------------------
            # Advanced Security
            # ---------------------------------
            "csrf_tokens": 0,
            "forms_without_csrf": 0,
            "autocomplete_off": 0,
            "autocomplete_on": 0,
            "multipart_forms": 0,
            "honeypot_fields": 0,
            "payment_forms": 0,
            "high_risk_forms": 0,
            # ---------------------------------
            # Phishing Detection
            # ---------------------------------
            "social_login_forms": 0,
            "captcha_forms": 0,
            "sensitive_forms": 0,
            "otp_phishing_forms": 0,
            "file_upload_forms": 0,
            "phishing_score": 0,
            "risk_level": "Low",
            # ---------------------------------
            # Future
            # ---------------------------------
            "error": None,
        }

        try:

            forms = soup.find_all("form")

            result["form_count"] = len(forms)

            for index, form in enumerate(forms, start=1):
                action = form.get("action")

                method = form.get(
                    "method",
                    "GET",
                ).upper()

                current_host = urlparse(browser_session.final_url).netloc

                action_host = ""

                risk_score = 0

                csrf_found = False

                honeypot_found = False

                payment_form = False

                social_login = False

                captcha_found = False

                sensitive_form = False

                otp_phishing = False

                file_upload_form = False

                if action:

                    action_host = urlparse(action).netloc

                inputs = form.find_all("input")
                password_count = 0

                email_count = 0

                username_count = 0

                hidden_count = 0

                file_count = 0

                otp_count = 0

                credit_card_count = 0

                phone_count = 0

                search_count = 0

                checkbox_count = 0

                radio_count = 0

                submit_count = 0

                buttons = form.find_all("button")

                textareas = form.find_all("textarea")

                selects = form.find_all("select")

                result["total_inputs"] += len(inputs)

                result["total_buttons"] += len(buttons)

                result["total_textareas"] += len(textareas)

                result["total_selects"] += len(selects)

                # ---------------------------------
                # CSRF Detection
                # ---------------------------------

                csrf_keywords = [
                    "csrf",
                    "_token",
                    "csrfmiddlewaretoken",
                    "__requestverificationtoken",
                ]

                for hidden in form.find_all("input", {"type": "hidden"}):

                    hidden_name = hidden.get("name", "").lower()

                    if any(token in hidden_name for token in csrf_keywords):

                        csrf_found = True

                        result["csrf_tokens"] += 1

                        break

                if not csrf_found:

                    result["forms_without_csrf"] += 1

                # ---------------------------------
                # Autocomplete
                # ---------------------------------

                autocomplete = form.get("autocomplete", "").lower()

                if autocomplete == "off":

                    result["autocomplete_off"] += 1

                elif autocomplete:

                    result["autocomplete_on"] += 1

                # ---------------------------------
                # Multipart Form
                # ---------------------------------

                if form.get("enctype", "").lower() == "multipart/form-data":

                    result["multipart_forms"] += 1

                    risk_score += 1

                # ---------------------------------
                # Analyze Inputs
                # ---------------------------------

                username_keywords = [
                    "username",
                    "user",
                    "login",
                ]

                otp_keywords = [
                    "otp",
                    "verification",
                    "code",
                    "pin",
                    "2fa",
                ]

                card_keywords = [
                    "credit",
                    "card",
                    "cvv",
                    "expiry",
                    "expiration",
                ]

                for inp in inputs:

                    input_type = inp.get("type", "text").lower()

                    input_name = inp.get("name", "").lower()

                    input_id = inp.get("id", "").lower()

                    placeholder = inp.get("placeholder", "").lower()

                    searchable = " ".join(
                        [
                            input_type,
                            input_name,
                            input_id,
                            placeholder,
                        ]
                    )

                    # ---------------------------------
                    # Sensitive Fields
                    # ---------------------------------

                    sensitive_keywords = [
                        "ssn",
                        "social",
                        "passport",
                        "license",
                        "aadhaar",
                        "pan",
                        "tax",
                        "bank",
                        "account",
                    ]

                    if any(keyword in searchable for keyword in sensitive_keywords):

                        sensitive_form = True

                    # ---------------------------------
                    # Honeypot Detection
                    # ---------------------------------

                    if input_type == "hidden" and any(
                        keyword in searchable
                        for keyword in [
                            "website",
                            "url",
                            "homepage",
                            "fax",
                        ]
                    ):
                        honeypot_found = True

                        result["honeypot_fields"] += 1

                    # -----------------------------
                    # Password
                    # -----------------------------

                    if input_type == "password":

                        password_count += 1

                        result["password_fields"] += 1

                    # -----------------------------
                    # Email
                    # -----------------------------

                    if input_type == "email" or "email" in searchable:

                        email_count += 1

                        result["email_fields"] += 1

                    # -----------------------------
                    # Username
                    # -----------------------------

                    if any(keyword in searchable for keyword in username_keywords):

                        username_count += 1

                        result["username_fields"] += 1

                    # -----------------------------
                    # Hidden
                    # -----------------------------

                    if input_type == "hidden":

                        hidden_count += 1

                        result["hidden_inputs"] += 1

                    # -----------------------------
                    # File Upload
                    # -----------------------------

                    if input_type == "file":

                        file_upload_form = True

                        file_count += 1

                        result["file_upload_fields"] += 1

                    # -----------------------------
                    # OTP
                    # -----------------------------

                    if any(keyword in searchable for keyword in otp_keywords):

                        otp_count += 1

                        result["otp_fields"] += 1
                        
                    # -----------------------------
                    # Credit Card
                    # -----------------------------

                    if any(keyword in searchable for keyword in card_keywords):

                        credit_card_count += 1

                        result["credit_card_fields"] += 1

                        payment_form = True

                    # -----------------------------
                    # Phone
                    # -----------------------------

                    if (
                        input_type == "tel"
                        or "phone" in searchable
                        or "mobile" in searchable
                    ):

                        phone_count += 1

                        result["phone_fields"] += 1

                    # -----------------------------
                    # Search
                    # -----------------------------

                    if input_type == "search":

                        search_count += 1

                        result["search_fields"] += 1

                    # -----------------------------
                    # Checkbox
                    # -----------------------------

                    if input_type == "checkbox":

                        checkbox_count += 1

                        result["checkbox_fields"] += 1

                    # -----------------------------
                    # Radio
                    # -----------------------------

                    if input_type == "radio":

                        radio_count += 1

                        result["radio_fields"] += 1

                    # -----------------------------
                    # Submit
                    # -----------------------------

                    if input_type in [
                        "submit",
                        "image",
                    ]:

                        submit_count += 1

                        result["submit_buttons"] += 1
                        
                # -----------------------------
                # OTP Phishing
                # -----------------------------

                if otp_count > 0 and password_count > 0:

                    otp_phishing = True

                # ---------------------------------
                # CAPTCHA
                # ---------------------------------

                captcha = form.find(
                    attrs={"class": lambda x: x and "captcha" in x.lower()}
                )

                if captcha:

                    captcha_found = True

                # ---------------------------------
                # Social Login
                # ---------------------------------

                social_keywords = [
                    "google",
                    "facebook",
                    "microsoft",
                    "apple",
                    "github",
                ]

                text = form.get_text(
                    " ",
                    strip=True,
                ).lower()

                if any(word in text for word in social_keywords):

                    social_login = True

                # ---------------------------------
                # Missing Action
                # ---------------------------------

                if action is None:

                    result["missing_actions"] += 1

                    result["suspicious_forms"].append(
                        {
                            "form": index,
                            "reason": "Missing action attribute",
                        }
                    )

                # ---------------------------------
                # Empty Action
                # ---------------------------------

                elif action == "":

                    result["empty_actions"] += 1

                # ---------------------------------
                # JavaScript Action
                # ---------------------------------

                elif action.lower().startswith("javascript:"):

                    result["javascript_actions"].append(action)

                    result["suspicious_forms"].append(
                        {
                            "form": index,
                            "reason": "JavaScript form action",
                        }
                    )

                # ---------------------------------
                # External Action
                # ---------------------------------

                elif action.startswith("http"):

                    result["external_actions"].append(action)

                    if action_host and action_host != current_host:

                        result["cross_domain_actions"] += 1

                        result["suspicious_forms"].append(
                            {
                                "form": index,
                                "reason": "Cross-domain submission",
                                "action": action,
                            }
                        )

                # ---------------------------------
                # Insecure HTTP Submission
                # ---------------------------------

                if action and action.startswith("http://"):

                    result["insecure_actions"].append(action)

                    result["suspicious_forms"].append(
                        {
                            "form": index,
                            "reason": "HTTP form submission",
                            "action": action,
                        }
                    )

                # ---------------------------------
                # GET Login Form
                # ---------------------------------

                if method == "GET" and password_count > 0:

                    result["get_login_forms"] += 1

                    result["suspicious_forms"].append(
                        {
                            "form": index,
                            "reason": "Password form uses GET",
                        }
                    )

                # ---------------------------------
                # Payment Form
                # ---------------------------------

                if payment_form:

                    result["payment_forms"] += 1

                    risk_score += 2

                # ---------------------------------
                # Phishing Indicators
                # ---------------------------------

                if social_login:

                    result["social_login_forms"] += 1

                if captcha_found:

                    result["captcha_forms"] += 1

                if sensitive_form:

                    result["sensitive_forms"] += 1

                    risk_score += 2

                if otp_phishing:

                    result["otp_phishing_forms"] += 1

                    risk_score += 2

                if file_upload_form:

                    result["file_upload_forms"] += 1

                    risk_score += 1

                # ---------------------------------
                # Risk Calculation
                # ---------------------------------

                if password_count > 0:

                    risk_score += 1

                if action and action.startswith("http://"):

                    risk_score += 3

                if action_host and action_host != current_host:

                    risk_score += 3

                if method == "GET" and password_count > 0:

                    risk_score += 2

                if not csrf_found:

                    risk_score += 1


                result["phishing_score"] += risk_score
                    
                if risk_score >= 5:


                    result["high_risk_forms"] += 1

                result["forms"].append(
                    {
                        "index": index,
                        "action": action,
                        "method": method,
                        "id": form.get("id"),
                        "name": form.get("name"),
                        "autocomplete": form.get("autocomplete"),
                        "input_count": len(inputs),
                        "button_count": len(buttons),
                        "textarea_count": len(textareas),
                        "select_count": len(selects),
                        "password_fields": password_count,
                        "email_fields": email_count,
                        "username_fields": username_count,
                        "hidden_inputs": hidden_count,
                        "file_upload_fields": file_count,
                        "otp_fields": otp_count,
                        "credit_card_fields": credit_card_count,
                        "phone_fields": phone_count,
                        "search_fields": search_count,
                        "checkbox_fields": checkbox_count,
                        "radio_fields": radio_count,
                        "submit_buttons": submit_count,
                        "csrf_found": csrf_found,
                        "honeypot_found": honeypot_found,
                        "payment_form": payment_form,
                        "social_login": social_login,
                        "captcha_found": captcha_found,
                        "sensitive_form": sensitive_form,
                        "otp_phishing": otp_phishing,
                        "file_upload_form": file_upload_form,
                        "risk_score": risk_score,
                    }
                )

            # ---------------------------------
            # Overall Risk
            # ---------------------------------

            if result["phishing_score"] >= 25:

                result["risk_level"] = "Critical"

            elif result["phishing_score"] >= 15:

                result["risk_level"] = "High"

            elif result["phishing_score"] >= 8:

                result["risk_level"] = "Medium"

            else:

                result["risk_level"] = "Low"

        except Exception as e:

            result["error"] = str(e)

        return result
