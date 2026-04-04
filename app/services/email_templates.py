"""Email template rendering utilities."""
import base64
from pathlib import Path


def get_logo_base64() -> str:
    """Get the Zenk logo as base64 data URL."""
    logo_path = Path(__file__).parent.parent / "ZENK LOGO.png"
    if logo_path.exists():
        with logo_path.open("rb") as f:
            logo_data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{logo_data}"
    return ""


def render_admin_notification_html(
    *,
    persona_label: str,
    signup_id: str,
    full_name: str,
    email: str,
    mobile: str,
    kyc_status: str,
    website_url: str,
) -> str:
    """Render HTML email template for admin notification."""
    logo_url = get_logo_base64()
    
    template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zenk Notification</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    
                    <!-- Header with Logo -->
                    <tr>
                        <td style="padding: 40px 40px 30px 40px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px 8px 0 0;">
                            <img src="{logo_url}" alt="Zenk Logo" style="max-width: 180px; height: auto; display: block; margin: 0 auto;">
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 40px 40px 30px 40px;">
                            <h1 style="margin: 0 0 20px 0; font-size: 24px; font-weight: 600; color: #333333; line-height: 1.4;">
                                New {persona_label} Registration
                            </h1>
                            
                            <p style="margin: 0 0 25px 0; font-size: 16px; color: #666666; line-height: 1.6;">
                                Hello Admin,
                            </p>
                            
                            <p style="margin: 0 0 25px 0; font-size: 16px; color: #666666; line-height: 1.6;">
                                A new <strong>{persona_label}</strong> has registered on Zenk and is awaiting KYC review.
                            </p>
                            
                            <!-- Details Box -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f8f9fa; border-radius: 6px; padding: 20px; margin: 25px 0;">
                                <tr>
                                    <td style="padding: 8px 0;">
                                        <strong style="color: #333333; font-size: 14px;">Signup ID:</strong>
                                        <span style="color: #666666; font-size: 14px; margin-left: 10px;">{signup_id}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0;">
                                        <strong style="color: #333333; font-size: 14px;">Name:</strong>
                                        <span style="color: #666666; font-size: 14px; margin-left: 10px;">{full_name}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0;">
                                        <strong style="color: #333333; font-size: 14px;">Email:</strong>
                                        <span style="color: #666666; font-size: 14px; margin-left: 10px;">{email}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0;">
                                        <strong style="color: #333333; font-size: 14px;">Mobile:</strong>
                                        <span style="color: #666666; font-size: 14px; margin-left: 10px;">{mobile}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0;">
                                        <strong style="color: #333333; font-size: 14px;">Status:</strong>
                                        <span style="color: #f59e0b; font-size: 14px; margin-left: 10px; font-weight: 600;">{kyc_status}</span>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center" style="padding: 30px 0 20px 0;">
                                        <a href="{website_url}/admin/kyc" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);">
                                            Review KYC Documents
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 25px 0 0 0; font-size: 14px; color: #999999; line-height: 1.6;">
                                Please login to Zenk to review the KYC documents and approve the registration.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px 40px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="margin: 0 0 10px 0; font-size: 14px; color: #666666;">
                                <strong>Zenk Team</strong>
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #999999;">
                                This is an automated notification. Please do not reply to this email.
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    return template.format(
        logo_url=logo_url,
        persona_label=persona_label,
        signup_id=signup_id,
        full_name=full_name,
        email=email,
        mobile=mobile,
        kyc_status=kyc_status,
        website_url=website_url,
    )


def render_user_approval_html(
    *,
    full_name: str,
    persona_label: str,
    website_url: str,
) -> str:
    """Render HTML email template for user approval notification."""
    logo_url = get_logo_base64()
    
    template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KYC Approved - Zenk</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    
                    <!-- Header with Logo -->
                    <tr>
                        <td style="padding: 40px 40px 30px 40px; text-align: center; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 8px 8px 0 0;">
                            <img src="{logo_url}" alt="Zenk Logo" style="max-width: 180px; height: auto; display: block; margin: 0 auto;">
                        </td>
                    </tr>
                    
                    <!-- Success Icon -->
                    <tr>
                        <td align="center" style="padding: 30px 40px 20px 40px;">
                            <div style="width: 80px; height: 80px; background-color: #10b981; border-radius: 50%; display: inline-block; line-height: 80px; text-align: center;">
                                <span style="font-size: 48px; color: #ffffff;">✓</span>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <h1 style="margin: 0 0 20px 0; font-size: 28px; font-weight: 600; color: #333333; line-height: 1.4; text-align: center;">
                                Your KYC is Approved! 🎉
                            </h1>
                            
                            <p style="margin: 0 0 25px 0; font-size: 16px; color: #666666; line-height: 1.6; text-align: center;">
                                Hello <strong>{full_name}</strong>,
                            </p>
                            
                            <p style="margin: 0 0 25px 0; font-size: 16px; color: #666666; line-height: 1.6; text-align: center;">
                                Congratulations! Your <strong>{persona_label}</strong> registration on Zenk has been approved.
                            </p>
                            
                            <p style="margin: 0 0 30px 0; font-size: 16px; color: #666666; line-height: 1.6; text-align: center;">
                                You can now login to your account and start using Zenk services.
                            </p>
                            
                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center" style="padding: 20px 0;">
                                        <a href="{website_url}/login" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);">
                                            Login to Zenk
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px 40px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="margin: 0 0 10px 0; font-size: 14px; color: #666666;">
                                <strong>Zenk Team</strong>
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #999999;">
                                Welcome to Zenk! We're excited to have you on board.
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    return template.format(
        logo_url=logo_url,
        full_name=full_name,
        persona_label=persona_label,
        website_url=website_url,
    )

