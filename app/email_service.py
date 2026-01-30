"""
Email notification service for traffic alerts
"""

import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Handles email notifications"""
    
    def __init__(
        self,
        sender: str,
        password: str,
        receiver: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 465
    ):
        self.sender = sender
        self.password = password
        self.receiver = receiver
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
    
    def _format_body(self, results: list, check_time: datetime) -> str:
        """Create formatted email body"""
        if not results:
            return "No route data available."
        
        best = results[0]
        
        # Calculate time saved
        if len(results) >= 2:
            diff = (results[-1].duration_seconds - best.duration_seconds) // 60
            time_saved = f"{diff} minutes"
        else:
            time_saved = "N/A"
        
        body = f"""
╔══════════════════════════════════════════════════════════╗
║          TRAFFIC ANALYSIS REPORT                         ║
╚══════════════════════════════════════════════════════════╝

📅 {check_time.strftime('%A, %B %d, %Y')}
🕐 Generated at: {check_time.strftime('%I:%M %p')}
📍 From: Pitman House → Home (South C)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 RECOMMENDED ROUTE

{best.name}

⏱️  Travel Time: {best.duration_text}
📏 Distance: {best.distance_text}
💾 Time Saved: {time_saved} vs slowest route

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 ALL ROUTES (Ranked by Speed)

"""
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, route in enumerate(results):
            emoji = medals[i] if i < 3 else f"{i+1}."
            icon = "🚦" if route.has_traffic_data else "⏱️"
            
            extra = ""
            if i > 0:
                diff = (route.duration_seconds - best.duration_seconds) // 60
                extra = f" (+{diff} min slower)"
            
            body += f"{emoji} {route.name}\n"
            body += f"   {icon} {route.duration_text}{extra}\n"
            body += f"   📏 {route.distance_text}\n\n"
        
        body += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEGEND:
🚦 = Live traffic data
⏱️  = Estimated time

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Automated Traffic Analyzer | Nairobi Routes
"""
        return body
    
    def send(self, results: list, check_time: Optional[datetime] = None) -> bool:
        """Send traffic alert email"""
        if not results:
            logger.error("No results to send")
            return False
        
        check_time = check_time or datetime.now()
        best = results[0]
        route_short = best.name.split(':')[1].strip() if ':' in best.name else best.name
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚗 Traffic Alert {check_time.strftime('%I:%M %p')}: Take {route_short} - {best.duration_text}"
        msg['From'] = self.sender
        msg['To'] = self.receiver
        
        body = self._format_body(results, check_time)
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.login(self.sender, self.password)
                server.send_message(msg)
            logger.info(f"✅ Email sent to {self.receiver}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False


def get_email_service() -> Optional[EmailService]:
    """Factory function to create email service from environment"""
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")
    
    if not all([sender, password, receiver]):
        logger.warning("Email credentials not fully configured")
        return None
    
    return EmailService(sender, password, receiver)