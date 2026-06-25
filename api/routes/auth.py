"""
api/routes/auth.py
------------------
Simple JWT-based authentication endpoints.
Uses in-memory user store (no DB needed for demo).
For production: replace with a real database.
"""
import os
import hashlib
import hmac
import time
import json
import base64
import logging
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from services.db import users_collection, subscribers_collection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")
security = HTTPBearer(auto_error=False)

# ── Secret key ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("JWT_SECRET", "tripmind-super-secret-change-in-production")

# MongoDB users collection is used for user store


# ── Models ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=60)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    created_at: float


class SubscribeRequest(BaseModel):
    email: str = Field(..., description="Email to subscribe to newsletter")

    @field_validator("email", mode="after")
    @classmethod
    def validate_email(cls, v: str) -> str:
        email_regex = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        v_clean = v.strip().lower()
        if not re.match(email_regex, v_clean):
            raise ValueError("Invalid email address format")
        return v_clean


class SubscribeResponse(BaseModel):
    message: str
    email: str
    email_sent: bool


# ── Token helpers (simple HMAC-based JWT-like token) ──────────────────────────

def _hash_password(password: str) -> str:
    return hmac.new(SECRET_KEY.encode(), password.encode(), hashlib.sha256).hexdigest()


def _create_token(user_id: str, email: str) -> str:
    """Create a simple signed token: base64(header).base64(payload).signature"""
    payload = json.dumps({"uid": user_id, "email": email, "exp": time.time() + 86400 * 7})
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def _verify_token(token: str) -> Optional[dict]:
    """Verify token and return payload dict, or None if invalid/expired."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "==").decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Dependency: extract and verify Bearer token from Authorization header."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = _verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = users_collection.find_one({"email": payload["email"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, summary="Register new user")
async def register(body: RegisterRequest) -> AuthResponse:
    """Create a new account. Returns a JWT token on success."""
    email = body.email.lower().strip()
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user_id = hashlib.md5(email.encode()).hexdigest()[:12]
    user = {
        "id": user_id,
        "name": body.name.strip(),
        "email": email,
        "password_hash": _hash_password(body.password),
        "created_at": time.time(),
    }
    users_collection.insert_one(user)
    token = _create_token(user_id, email)
    logger.info("New user registered: %s", email)

    return AuthResponse(
        token=token,
        user={"id": user_id, "name": user["name"], "email": email},
    )


@router.post("/login", response_model=AuthResponse, summary="Login")
async def login(body: LoginRequest) -> AuthResponse:
    """Login with email and password. Returns a JWT token."""
    email = body.email.lower().strip()
    user = users_collection.find_one({"email": email})

    if not user or user["password_hash"] != _hash_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = _create_token(user["id"], email)
    logger.info("User logged in: %s", email)

    return AuthResponse(
        token=token,
        user={"id": user["id"], "name": user["name"], "email": email},
    )


@router.get("/me", response_model=UserProfile, summary="Get current user profile")
async def get_me(current_user: dict = Depends(get_current_user)) -> UserProfile:
    """Returns the logged-in user's profile. Requires Bearer token."""
    return UserProfile(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        created_at=current_user["created_at"],
    )


@router.post("/logout", summary="Logout (client-side)")
async def logout() -> dict:
    """
    Logout endpoint. Since tokens are stateless, actual invalidation
    is done client-side by deleting the token from localStorage.
    """
    return {"message": "Logged out successfully. Please delete your token client-side."}


def send_confirmation_email(recipient_email: str) -> bool:
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user or "noreply@tripmind.ai")

    if not smtp_host or not smtp_user or not smtp_pass:
        logger.warning(
            "SMTP configuration missing in environment. Email simulation logged: "
            "Welcome/newsletter confirmation email for %s", recipient_email
        )
        return False

    try:
        port = int(smtp_port) if smtp_port else 587
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Welcome to TripMind AI Newsletter!"
        msg["From"] = smtp_from
        msg["To"] = recipient_email

        text_content = (
            "Thank you for subscribing to TripMind AI Newsletter!\n\n"
            "You will now receive smart travel deal analytics, pricing insights, and "
            "recommendations directly in your inbox.\n\n"
            "Best regards,\nThe TripMind Team"
        )

        html_content = """
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <div style="text-align: center; border-bottom: 2px solid #38bdf8; padding-bottom: 20px;">
              <h2 style="color: #0770e3; margin: 0;">TripMind AI</h2>
              <p style="margin: 5px 0 0 0; color: #64748b; font-size: 14px;">Your AI-Powered Travel Assistant</p>
            </div>
            <div style="padding: 20px 0;">
              <p><strong>Hi there!</strong></p>
              <p>Thank you for subscribing to the <strong>TripMind AI Newsletter</strong>.</p>
              <p>You'll now be the first to know about smart flight deal analytics, premium hotel insights, and customized travel updates curated by our AI agents.</p>
              <div style="margin: 30px 0; text-align: center;">
                <a href="#" style="background-color: #0770e3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Explore TripMind</a>
              </div>
              <p style="font-size: 13px; color: #64748b;">If you did not request this subscription, please ignore this email.</p>
            </div>
            <div style="border-top: 1px solid #e2e8f0; padding-top: 15px; text-align: center; font-size: 12px; color: #94a3b8;">
              &copy; 2026 TripMind AI · Powered by Neuronet Systems Pvt. Ltd.
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Connect to SMTP server (TLS)
        server = smtplib.SMTP(smtp_host, port, timeout=10)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, recipient_email, msg.as_string())
        server.quit()
        
        logger.info("Successfully sent welcome email to %s via SMTP", recipient_email)
        return True
    except Exception as e:
        logger.error("Failed to send subscription email to %s: %s", recipient_email, e)
        return False


@router.post("/subscribe", response_model=SubscribeResponse, summary="Subscribe to newsletter")
async def subscribe_newsletter(body: SubscribeRequest) -> SubscribeResponse:
    """Subscribe email to the newsletter and send a welcome email."""
    email = body.email.lower().strip()
    
    # Save to MongoDB subscribers collection
    try:
        subscribers_collection.update_one(
            {"email": email},
            {"$set": {"email": email, "subscribed_at": time.time()}},
            upsert=True
        )
        logger.info("Email registered in subscribers database: %s", email)
    except Exception as e:
        logger.error("Database error saving subscriber %s: %s", email, e)
        # We can still proceed to try and send the email even if DB fails

    # Send confirmation email
    email_sent = send_confirmation_email(email)
    
    if email_sent:
        message = "Successfully subscribed! A welcome email has been sent to you."
    else:
        message = "Successfully subscribed! (Welcome email simulation logged; please configure SMTP in backend .env to send real emails)."

    return SubscribeResponse(
        message=message,
        email=email,
        email_sent=email_sent
    )